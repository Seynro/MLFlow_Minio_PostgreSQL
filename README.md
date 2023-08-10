
# Script Documentation

## Overview

The script provided above is designed for automatic monitoring and logging of data changes in a PostgreSQL database, saving the results in MLflow, exporting metrics to an Excel file, and subsequently uploading this file to a MinIO server.

---

## General Workflow:

1. Initialize the signal handler for safe script termination.
2. Configure and initialize the MinIO client.
3. Connect to the PostgreSQL database.
4. Continuously monitor for changes in the database and log the results.

## Script Workflow:

1. Connect to the PostgreSQL database.
2. Determine the last checked ID.
3. Identify the MLflow experiment or create a new one if it doesn't exist.
4. Continuously perform the following:
    - Connect to MLflow.
    - Search for changes in the database exceeding the last checked ID.
    - For each detected change:
        - Start a new run in MLflow.
        - Log metrics in MLflow.
        - Save MLflow metrics to an Excel file.
        - Upload the Excel file to the MinIO server.
        - Save MLflow metrics in PostgreSQL.
    - Wait for the next check.

---

## Functions and Descriptions:

### 1. `signal_handler(sig, frame)`

A signal interruption handler (CTRL+C). When this function is invoked, it deletes temporary files and safely terminates the script.

### 2. `save_csv_to_postgresql(csv_filename, db_url, table_name)`

Saves a CSV file to a PostgreSQL database.

- **Arguments**:
  - `csv_filename`: Path to the CSV file.
  - `db_url`: PostgreSQL connection string.
  - `table_name`: Table name in PostgreSQL.

### 3. `save_mlflow_data_to_excel(experiment_id, output_filename)`

Stores MLflow data in an Excel file on the local machine.

- **Arguments**:
  - `experiment_id`: MLflow experiment ID.
  - `output_filename`: Output Excel file name.

### 4. `log_dataframe_as_artifact(data, artifact_name)`

Logs DataFrame data as an artifact in MLflow.

- **Arguments**:
  - `data`: DataFrame data.
  - `artifact_name`: Artifact name.

### 5. `log_change_and_metrics_to_excel(change, data)`

Logs change information and metrics in an Excel file.

- **Arguments**:
  - `change`: Change information.
  - `data`: Data.

---
### Setting up a Trigger and Function in PostgreSQL

#### Creating a Function

Before creating a trigger, you need to create a function that will be called by the trigger during a specific event:

```sql
CREATE OR REPLACE FUNCTION log_change()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        INSERT INTO changes_log (operation, changed_data) VALUES ('DELETE', OLD::text);
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO changes_log (operation, changed_data) VALUES ('UPDATE', NEW::text);
        RETURN NEW;
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO changes_log (operation, changed_data) VALUES ('INSERT', NEW::text);
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

#### Creating a Trigger

After creating the function, you can create a trigger:

- **INSERT**:
```sql
CREATE TRIGGER changes_after_insert
AFTER INSERT ON test_data3
FOR EACH ROW
EXECUTE FUNCTION log_change();
```

- **UPDATE**:
```sql
CREATE TRIGGER changes_after_update
AFTER UPDATE ON test_data3
FOR EACH ROW
EXECUTE FUNCTION log_change();
```

- **DELETE**:
```sql
CREATE TRIGGER changes_after_delete
AFTER DELETE ON test_data3
FOR EACH ROW
EXECUTE FUNCTION log_change();
```

#### Verifying the Operation

Perform INSERT, UPDATE, or DELETE operations on the `test_data3` table and ensure that the `log_change` function correctly logs these events.

---
---

## Notes:

- Ensure proper access parameters and connections are provided for all services: PostgreSQL, MLflow, and MinIO.
- The script assumes that the PostgreSQL database and MLflow are on the same server. If this is not the case, connection strings need to be adjusted.
- Ensure you have write permissions to the specified directories and access to the mentioned services.
