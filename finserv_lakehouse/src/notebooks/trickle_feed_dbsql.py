import time
import os
import uuid
import random
import json
from databricks import sql

# 1. Configuration
CATALOG = "workspace"
SCHEMA = "finserv"
TABLE = "transactions"
FULL_TABLE_NAME = f"{CATALOG}.{SCHEMA}.{TABLE}"

workspace_host = "dbc-61514402-8451.cloud.databricks.com"
http_path = "/sql/1.0/warehouses/4bbaafe9538467a0"
client_id = "5d54409d-304c-42aa-8a21-8070a8879443"
client_secret = "REDACTED_DATABRICKS_OAUTH_SECRET"

# 2. Data Generation using Pure Python (1000 records)
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
    ts_micros = time.time()
    
    records.append({
        "transaction_id": str(uuid.uuid4()),
        "account_id": f"ACC-{random.randint(0, 99):05d}",
        "amount": round(random.uniform(10, 5010), 2),
        "currency": currency,
        "transaction_type": transaction_type,
        "ts": ts_micros # unix timestamp seconds
    })

print(f"Sample generated record: {records[0]}")

# 3. Emulating Zerobus Ingestion (Trickle Feed via DBSQL)
print(f"Connecting to Serverless SQL at {workspace_host} ...")

from databricks.sdk.core import Config

config = Config(host=workspace_host, client_id=client_id, client_secret=client_secret)
access_token = config.authenticate()

# Sometimes it's a dict, sometimes a callable. If dict, extract access_token. 
# If string, use it. If callable, call it.
if callable(access_token):
    access_token = access_token()
if isinstance(access_token, dict) and "access_token" in access_token:
    access_token = access_token["access_token"]
elif hasattr(access_token, "token_value"):
    access_token = access_token.token_value
elif callable(getattr(access_token, "token_value", None)):
    access_token = access_token.token_value()
elif isinstance(access_token, str):
    pass
elif hasattr(access_token, "get"):
    access_token = access_token.get("access_token")

with sql.connect(
    server_hostname=workspace_host,
    http_path=http_path,
    access_token=access_token
) as connection:
    with connection.cursor() as cursor:
        BATCH_SIZE = 50
        WAIT_SECS = 5

        try:
            total_batches = (N_RECORDS + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"Starting trickle feed: {total_batches} batches of {BATCH_SIZE} records every {WAIT_SECS}s")
            
            for i in range(0, N_RECORDS, BATCH_SIZE):
                batch = records[i:i+BATCH_SIZE]
                
                # Construct INSERT statement
                values = []
                for r in batch:
                    # ts conversion
                    from datetime import datetime
                    dt_str = datetime.fromtimestamp(r["ts"]).strftime('%Y-%m-%d %H:%M:%S')
                    v = f"('{r['transaction_id']}', '{r['account_id']}', {r['amount']}, '{r['currency']}', '{r['transaction_type']}', '{dt_str}')"
                    values.append(v)
                
                insert_sql = f"INSERT INTO {FULL_TABLE_NAME} VALUES " + ", ".join(values)
                
                cursor.execute(insert_sql)
                
                print(f"Sent batch {i // BATCH_SIZE + 1}/{total_batches} ({len(batch)} records) to {FULL_TABLE_NAME}")
                if i + BATCH_SIZE < N_RECORDS:
                    time.sleep(WAIT_SECS)
                    
        except Exception as e:
            print(f"Error streaming data: {e}")
        finally:
            print("Stream closed.")
