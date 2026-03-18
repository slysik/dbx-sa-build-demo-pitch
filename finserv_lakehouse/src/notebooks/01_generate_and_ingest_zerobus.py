# Databricks notebook source
# MAGIC %pip install databricks-zerobus-ingest-sdk>=0.2.0 databricks-sdk>=0.85.0 grpcio-tools protobuf
# MAGIC dbutils.library.restartPython()

# COMMAND ----------
import time
import uuid
import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark.sql import DataFrame, SparkSession
from zerobus.sdk.sync import ZerobusSdk
from zerobus.sdk.shared import RecordType, StreamConfigurationOptions, TableProperties

# 1. Configuration
CATALOG = "workspace"
SCHEMA = "finserv"
TABLE = "transactions"
FULL_TABLE_NAME = f"{CATALOG}.{SCHEMA}.{TABLE}"

import os
workspace_url = os.environ.get("DATABRICKS_HOST", "https://dbc-61514402-8451.cloud.databricks.com")

# AWS Zerobus endpoint: <workspace-id>.zerobus.<region>.cloud.databricks.com
server_endpoint = "615144028451.zerobus.us-east-2.cloud.databricks.com"

# The free tier SP credentials
client_id = os.environ.get("DATABRICKS_CLIENT_ID", "5d54409d-304c-42aa-8a21-8070a8879443")
client_secret = os.environ.get("DATABRICKS_CLIENT_SECRET", "REDACTED_DATABRICKS_OAUTH_SECRET")

# COMMAND ----------
# 2. Data Generation using PySpark (1000 records)
N_RECORDS = 1000

print(f"Generating {N_RECORDS} synthetic finserv JSON records...")

df = spark.range(N_RECORDS).withColumn(
    "transaction_id", F.expr("uuid()")
).withColumn(
    "account_id", F.concat(F.lit("ACC-"), F.format_string("%05d", (F.rand() * 100).cast("int")))
).withColumn(
    "amount", F.round(F.rand() * 5000 + 10, 2)
).withColumn(
    "currency", F.when(F.rand() > 0.8, "EUR").when(F.rand() > 0.9, "GBP").otherwise("USD")
).withColumn(
    "transaction_type", F.when(F.rand() > 0.5, "CREDIT").otherwise("DEBIT")
).withColumn(
    # ZeroBus requires timestamp fields as Unix integer timestamps in MICROSECONDS
    "ts", (F.unix_timestamp(F.current_timestamp()) * 1000000).cast("long")
)

# Convert to list of dictionaries (JSON)
records_df = df.collect()
records = [row.asDict() for row in records_df]

print(f"Sample generated record: {records[0]}")

# COMMAND ----------
# 3. Zerobus Ingestion (Trickle Feed)

if client_id and client_secret:
    print(f"Connecting to Zerobus at {server_endpoint} ...")
    sdk = ZerobusSdk(server_endpoint, workspace_url)
    
    # We'll use JSON ingestion to avoid the complexity of dynamic Protobuf schema generation in a notebook.
    options = StreamConfigurationOptions(record_type=RecordType.JSON)
    table_props = TableProperties(FULL_TABLE_NAME)

    stream = sdk.create_stream(client_id, client_secret, table_props, options)

    BATCH_SIZE = 50
    WAIT_SECS = 10
    
    try:
        total_batches = (N_RECORDS + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"Starting trickle feed: {total_batches} batches of {BATCH_SIZE} records every {WAIT_SECS}s")
        
        for i in range(0, N_RECORDS, BATCH_SIZE):
            batch = records[i:i+BATCH_SIZE]
            
            # Fire-and-forget batch
            stream.ingest_records_nowait(batch)
            stream.flush()
            
            print(f"Sent batch {i // BATCH_SIZE + 1}/{total_batches} ({len(batch)} records) to {FULL_TABLE_NAME}")
            if i + BATCH_SIZE < N_RECORDS:
                time.sleep(WAIT_SECS)
                
    except Exception as e:
        print(f"Error streaming to Zerobus: {e}")
    finally:
        stream.close()
        print("Zerobus stream closed.")
else:
    print("DATABRICKS_CLIENT_ID or DATABRICKS_CLIENT_SECRET not found. Skipping Zerobus ingest.")
    
# COMMAND ----------
# Validate
display(spark.sql(f"SELECT count(*) FROM {FULL_TABLE_NAME}"))