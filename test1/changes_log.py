import time
import mlflow
import pandas as pd
from sqlalchemy import create_engine
import os
import tempfile
import subprocess

import boto3
from botocore.client import Config

# Настройка параметров MinIO
MINIO_ENDPOINT = 'http://10.5.108.12:9000'
ACCESS_KEY = 'minioadmin'
SECRET_KEY = 'minioadmin'
BUCKET_NAME = 'mlruns'

# Инициализация клиента MinIO
s3 = boto3.resource('s3',
    endpoint_url=f'{MINIO_ENDPOINT}',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'  # Это может измениться в зависимости от вашей конфигурации
)




def save_csv_to_postgresql(csv_filename, db_url, table_name):
    """
    Saves CSV-file into PostgreSQL.

    Args:
    - csv_filename (str): Path to CSV-file.
    - db_url (str): connecting to PostgreSQL.
    - table_name (str): Table name in PostgreSQL.
    """
    # Reading CSV-file
    df = pd.read_csv(csv_filename)
    
    # Connecting to Data Base
    engine = create_engine(db_url)
    
    # Saving DataFrame into PostgreSQL
    df.to_sql(table_name, engine, if_exists='replace', index=False)


def save_mlflow_data_to_excel(experiment_id, output_filename):
    '''
    Saves Excel-file on Local Machine.
    '''
    # Creating CSV-file
    csv_filename = "temp_mlflow_data.csv"
    subprocess.run(["mlflow", "experiments", "csv", "-x", str(experiment_id), "-o", csv_filename])

    # Reading CSV-file and saving it as Excel
    df = pd.read_csv(csv_filename)
    df.to_excel(output_filename, index=False)



def log_dataframe_as_artifact(data, artifact_name):
    """
    Creates logs for DataFrame as artefact in MLflow.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_path = os.path.join(tmp_dir, artifact_name)
        data.to_csv(temp_path, index=False)
        mlflow.log_artifact(temp_path, artifact_name)


def log_change_and_metrics_to_excel(change, data):
    """
    Loges information about changes and metrics in Excel file
    """
    print('Writing Excel')
    numeric_columns = ["net_quantity", "gross_sales", "discounts", "returns", "total_net_sales"]
    metrics = {}
    
    for col in numeric_columns:
        mean_value = data[col].mean()
        median_value = data[col].median()
        std_dev_value = data[col].std()

        metrics[f"{col}_mean"] = mean_value
        metrics[f"{col}_median"] = median_value
        metrics[f"{col}_std_dev"] = std_dev_value

        # Writes metrics in MLflow
        mlflow.log_metric(f"{col}_mean", mean_value)
        mlflow.log_metric(f"{col}_median", median_value)
        mlflow.log_metric(f"{col}_std_dev", std_dev_value)

    # Creates DataFrame for current changes
    current_change_df = pd.DataFrame({
        'Date': [change['changed_at']],
        'Operation': [change['operation']],
        **metrics
    })

    file_path = "changes_log.xlsx"

    # If Excel file exists, it updates with new information, if not - creates new 
    if os.path.exists(file_path):
        existing_data = pd.read_excel(file_path)
        combined_data = pd.concat([existing_data, current_change_df], ignore_index=True)
    else:
        combined_data = current_change_df

    # Saves combined data in one file
    combined_data.to_excel(file_path, index=False)

    print('Excel ready')


print('Connecting to Postagesql')

# Connecting to PostgreSQL
engine = create_engine('postgresql://postgres:seymur2003@localhost/mlflow')

last_checked_id = 0

experiment_name = "AutoLog"

if mlflow.get_experiment_by_name(experiment_name) is None:
    mlflow.create_experiment(name=experiment_name)

mlflow.set_experiment(experiment_name)

print('Connected')

# Creating one continius run
while True:
    try:
        print('Connecting to MLFlow')
        query = f"SELECT * FROM changes_log WHERE id > {last_checked_id} ORDER BY id ASC"
        changes = pd.read_sql(query, engine)
        
        for _, change in changes.iterrows():
            with mlflow.start_run():
                # Creating run's name with time when it created
                formatted_time = change["changed_at"].strftime('%Y-%m-%d %H:%M:%S')
                mlflow.set_tag('mlflow.runName', formatted_time)
                
                data = pd.read_sql("SELECT * FROM test_data3", engine)
                mlflow.set_tag("changed_at", str(change["changed_at"]))
                mlflow.set_tag("operation", change["operation"])

                log_dataframe_as_artifact(data, "changed_data.csv")
                
                log_change_and_metrics_to_excel(change, data)

                last_checked_id = change["id"]

                # Saving MLFlow's metrics in Excel file
                save_mlflow_data_to_excel(746541849908770046, "mlflow_data.xlsx")

                print('Connecting to Minio')
                # Загрузка файла
                file_name = 'mlflow_data.xlsx'
                s3.Bucket(BUCKET_NAME).upload_file(file_name, 'logs_data.xlsx')


                # Saving MLFlow's metrics in Postgre SQL
                DB_URL = 'postgresql://postgres:seymur2003@localhost/mlflow_logs'
                save_csv_to_postgresql("temp_mlflow_data.csv", DB_URL, "mlflow_logs")
                
        print('Connected, wating for next check...')
        time.sleep(30)
    except Exception as e:
        print(f"Error occurred: {e}")
        print('Waiting for next try')
        time.sleep(30)






