# Databricks notebook source
# MAGIC %md
# MAGIC # Retail Streaming - Zerobus Trickle Ingestion (v2)
# MAGIC **3 Vs Demo**: Volume (1000 records) | Variety (multi-type) | Velocity (trickle every 10s)
# MAGIC
# MAGIC This notebook reads pre-generated retail JSON batches from a UC Volume
# MAGIC and feeds them into a Delta table via Zerobus gRPC -- no message bus needed.

# COMMAND ----------

# MAGIC %pip install databricks-zerobus-ingest-sdk>=0.2.0
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json
import time
from datetime import datetime
from zerobus.sdk.sync import ZerobusSdk
from zerobus.sdk.shared import RecordType, StreamConfigurationOptions, TableProperties

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

SERVER_ENDPOINT = "7405613453749188.zerobus.eastus2.azuredatabricks.net"
WORKSPACE_URL = "https://adb-7405613453749188.8.azuredatabricks.net"
TABLE_NAME = "dbx_weg.bronze.retail_streaming_events_v2"
CLIENT_ID = "2e8cb2d1-b997-4271-a52c-a3be849886fc"
CLIENT_SECRET = dbutils.secrets.get(scope="zerobus", key="client-secret")
VOLUME_PATH = "/Volumes/dbx_weg/bronze/streaming_data_v2"
BATCH_SIZE = 50
N_BATCHES = 20  # 20 batches x 50 = 1000 records

# COMMAND ----------

# MAGIC %md
# MAGIC ## Initialize Zerobus Stream

# COMMAND ----------

sdk = ZerobusSdk(SERVER_ENDPOINT, WORKSPACE_URL)
options = StreamConfigurationOptions(record_type=RecordType.JSON)
table_props = TableProperties(TABLE_NAME)
stream = sdk.create_stream(CLIENT_ID, CLIENT_SECRET, table_props, options)
print("Zerobus stream ready -- no Kafka, no Kinesis, no Event Hub!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Trickle Ingest (1 batch every 10 seconds)
# MAGIC Shows **Velocity** -- data arrives in micro-batches just like a real streaming bus

# COMMAND ----------

total = 0
try:
    for b in range(N_BATCHES):
        content = dbutils.fs.head(f"{VOLUME_PATH}/batch_{b:03d}.json", 65536)
        records = []
        for line in content.strip().split("\n"):
            if line.strip():
                rec = json.loads(line)
                ts = datetime.strptime(rec["event_timestamp"], "%Y-%m-%dT%H:%M:%S.%f")
                rec["event_timestamp"] = int(ts.timestamp() * 1_000_000)
                records.append(rec)

        t0 = time.time()
        for rec in records:
            stream.ingest_record_nowait(rec)
        stream.flush()
        elapsed = time.time() - t0
        total += len(records)
        print(f"Batch {b+1:2d}/{N_BATCHES}: {len(records)} records in {elapsed:.2f}s | Cumulative: {total}")

        if b < N_BATCHES - 1:
            time.sleep(10)
finally:
    stream.close()

print(f"\nDone! {total} records ingested via Zerobus into {TABLE_NAME}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT COUNT(*) as total_records,
# MAGIC        COUNT(DISTINCT category) as categories,
# MAGIC        ROUND(SUM(total_amount), 2) as total_revenue
# MAGIC FROM dbx_weg.bronze.retail_streaming_events_v2
