import time
import os
import uuid
import random
from zerobus.sdk.sync import ZerobusSdk
from zerobus.sdk.shared import RecordType, StreamConfigurationOptions, TableProperties

# 1. Configuration
CATALOG = "workspace"
SCHEMA = "finserv"
TABLE = "transactions"
FULL_TABLE_NAME = f"{CATALOG}.{SCHEMA}.{TABLE}"

workspace_url = os.environ.get("DATABRICKS_HOST", "https://dbc-61514402-8451.cloud.databricks.com")
server_endpoint = "7474656067656578.zerobus.us-east-2.cloud.databricks.com"

client_id = os.environ.get("DATABRICKS_CLIENT_ID", "5d54409d-304c-42aa-8a21-8070a8879443")
client_secret = os.environ.get("DATABRICKS_CLIENT_SECRET", "REDACTED_DATABRICKS_OAUTH_SECRET")

# 2. Data Generation using Pure Python (1000 records)
# (Substituted for PySpark locally due to lack of Java runtime & Spark Cluster)
N_RECORDS = 1000
print(f"Generating {N_RECORDS} synthetic finserv JSON records using Python...")

records = []
for _ in range(N_RECORDS):
    r_val = random.random()
    if r_val > 0.9:
        currency = "GBP"
    elif r_val > 0.8:
        currency = "EUR"
    else:
        currency = "USD"
        
    transaction_type = "CREDIT" if random.random() > 0.5 else "DEBIT"
    
    # Zerobus requires TS as unix timestamp in MICROSECONDS
    ts_micros = int(time.time() * 1000000)
    
    records.append({
        "transaction_id": str(uuid.uuid4()),
        "account_id": f"ACC-{random.randint(0, 99):05d}",
        "amount": round(random.uniform(10, 5010), 2),
        "currency": currency,
        "transaction_type": transaction_type,
        "ts": ts_micros
    })

print(f"Sample generated record: {records[0]}")

# 3. Zerobus Ingestion (Trickle Feed)
print(f"Connecting to Zerobus at {server_endpoint} ...")
sdk = ZerobusSdk(server_endpoint, workspace_url)

options = StreamConfigurationOptions(record_type=RecordType.JSON)
table_props = TableProperties(FULL_TABLE_NAME)

stream = sdk.create_stream(client_id, client_secret, table_props, options)

BATCH_SIZE = 100
WAIT_SECS = 1

try:
    total_batches = (N_RECORDS + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Starting trickle feed: {total_batches} batches of {BATCH_SIZE} records every {WAIT_SECS}s")
    
    for i in range(0, N_RECORDS, BATCH_SIZE):
        batch = records[i:i+BATCH_SIZE]
        
        # Ingest and flush
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
