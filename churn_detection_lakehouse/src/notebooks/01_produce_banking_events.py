# Databricks notebook source

"""
Zerobus Producer: BOA iOS App Events → Real-Time Stream

Simulates 2K banking events per batch from BOA iOS app.
Pushes to Zerobus Ingest stream every 5 minutes (orchestrated by bundle job).

Event types:
- app_open: User opened app
- transaction: Successful transaction
- failed_login: Failed authentication attempt (RISK SIGNAL)
- app_crash: App crashed (RISK SIGNAL)
- support_call: User called support (RISK SIGNAL)
- slow_transaction: Transaction took >5sec (RISK SIGNAL)
"""

from databricks.sdk.service.compute import ZerobusSinkConfig
import pyspark.sql.functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, LongType
import uuid
from datetime import datetime, timedelta
import random

# Configuration
CATALOG = "finserv"
SCHEMA = "churn_demo"
ZEROBUS_TABLE = f"{CATALOG}.{SCHEMA}.bronze_banking_events"

# Ensure schema exists
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

# ── Generate 2K synthetic banking events from BOA app ──────────────────────

print("🏦 Generating 2K BOA iOS App events...")

# User population (200 unique users)
user_ids = [f"USER-{str(i).zfill(5)}" for i in range(1, 201)]

# Event types weighted by likelihood (some events are risk signals)
event_weights = {
    "app_open": 0.40,         # Most common
    "transaction": 0.30,      # Normal behavior
    "failed_login": 0.10,     # Risk signal
    "app_crash": 0.08,        # Risk signal
    "support_call": 0.07,     # Risk signal
    "slow_transaction": 0.05, # Risk signal
}

# Generate 2K events
events = []
base_timestamp = datetime.now() - timedelta(hours=24)

for i in range(2000):
    user_id = random.choice(user_ids)
    event_type = random.choices(
        list(event_weights.keys()),
        weights=list(event_weights.values()),
        k=1
    )[0]
    
    timestamp = base_timestamp + timedelta(minutes=random.randint(0, 1440))
    
    # Risk signals: failed login, crash, slow transaction, support call
    is_risk_signal = event_type in ["failed_login", "app_crash", "support_call", "slow_transaction"]
    
    event = {
        "event_id": f"EVT-{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "event_type": event_type,
        "timestamp": timestamp.isoformat() + "Z",
        "is_risk_signal": is_risk_signal,
        "metadata": {
            "app_version": "7.2.1",
            "os": random.choice(["iOS 17", "iOS 18"]),
            "session_duration_sec": random.randint(10, 600) if event_type == "app_open" else None,
            "transaction_amount_usd": round(random.uniform(5, 5000), 2) if event_type == "transaction" else None,
            "error_code": f"ERR-{random.randint(100, 999)}" if is_risk_signal else None,
        }
    }
    events.append(event)

print(f"✓ Generated {len(events)} events")
print(f"  Risk signals: {sum(1 for e in events if e['is_risk_signal'])}")

# ── Write to bronze via Zerobus Ingest ────────────────────────────────────

print(f"\n📤 Pushing events to Zerobus → {ZEROBUS_TABLE}...")

# Create DataFrame from events
df_events = spark.createDataFrame([
    (
        e["event_id"],
        e["user_id"],
        e["event_type"],
        e["timestamp"],
        e["is_risk_signal"],
        F.to_json(F.struct(*[F.lit(v).cast("string") if not isinstance(v, dict) else F.to_json(F.struct(*[F.lit(k2).alias(k2), F.lit(str(v2)) for k2, v2 in v.items()])) for k, v in e["metadata"].items()])).cast("string"),
        F.current_timestamp()
    )
    for e in events
], ["event_id", "user_id", "event_type", "timestamp", "is_risk_signal", "metadata_json", "ingest_ts"])

# Write to bronze table (Delta Lake)
df_events.write \
    .format("delta") \
    .mode("append") \
    .option("overwriteSchema", "true") \
    .saveAsTable(ZEROBUS_TABLE, path=f"abfss://finserv@{spark.conf.get('fs.azure.account.name.finserv.dfs.core.windows.net')}/churn_demo/bronze_banking_events")

print(f"✓ Wrote {len(events)} events to {ZEROBUS_TABLE}")

# ── Validation ─────────────────────────────────────────────────────────────

result = spark.sql(f"""
SELECT 
  event_type,
  COUNT(*) as count
FROM {ZEROBUS_TABLE}
WHERE ingest_ts >= CURRENT_TIMESTAMP() - INTERVAL 5 MINUTES
GROUP BY event_type
ORDER BY count DESC
""")

print("\n📊 Event type distribution (last 5 min):")
result.show(truncate=False)

print(f"\n✅ Producer complete. SDP pipeline will process these events in next run.")
