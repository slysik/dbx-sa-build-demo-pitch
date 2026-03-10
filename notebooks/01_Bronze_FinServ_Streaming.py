# Databricks notebook source
# MAGIC %md
# MAGIC # Phase 2: Bronze Layer — FinServ Streaming Ingestion
# MAGIC
# MAGIC **What you'll learn:**
# MAGIC - Structured Streaming with Spark's `rate` source (simulates Kafka)
# MAGIC - Writing streaming data to Delta Lake tables
# MAGIC - Checkpointing for exactly-once semantics
# MAGIC - Schema-on-read pattern for raw data
# MAGIC
# MAGIC **FinServ context:** Simulates a real-time credit card transaction feed
# MAGIC — the kind of data a bank, payment processor, or FinTech ingests
# MAGIC from card networks (Visa/MC), POS terminals, and mobile wallets.
# MAGIC
# MAGIC ```
# MAGIC Card Networks / POS → Kafka → Bronze (Delta) → Silver → Gold → ML
# MAGIC                       ↑ we simulate this
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Define the FinServ Transaction Schema
# MAGIC
# MAGIC In production, this arrives as JSON from Kafka topics like
# MAGIC `card.transactions.raw`. We simulate it with Spark's `rate` source
# MAGIC + random data generation — same patterns, zero infrastructure.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import *
import random

# Reference data for realistic FinServ transactions
# Merchant Category Codes (MCC) — real ISO 18245 codes used in payment processing
MCC_CATEGORIES = {
    "5411": "Grocery Stores",
    "5541": "Gas Stations",
    "5812": "Restaurants",
    "5912": "Drug Stores/Pharmacies",
    "5999": "Misc Retail",
    "6011": "ATM/Cash Disbursement",
    "4829": "Wire Transfers",
    "7011": "Hotels/Lodging",
    "5732": "Electronics Stores",
    "3000": "Airlines",
}

CARD_NETWORKS = ["VISA", "MASTERCARD", "AMEX", "DISCOVER"]
CURRENCIES = ["USD", "USD", "USD", "USD", "EUR", "GBP"]  # weighted toward USD
STATES = ["NY", "CA", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "NJ",
          "MA", "WA", "AZ", "CO", "TN", "SC", "VA", "MD", "MN", "OR"]

print("Reference data loaded ✓")
print(f"  MCC categories: {len(MCC_CATEGORIES)}")
print(f"  Card networks: {CARD_NETWORKS}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create the Simulated Transaction Stream
# MAGIC
# MAGIC **Key Spark concept:** `readStream` with `format("rate")` generates
# MAGIC a continuous stream of rows at a configurable rate. Each row gets
# MAGIC a `timestamp` and incrementing `value`. We enrich it with random
# MAGIC transaction fields to simulate real card swipes.
# MAGIC
# MAGIC **Why this matters for the SA role:** In customer POCs, you often
# MAGIC start with simulated data before connecting to real Kafka/Event Hubs.
# MAGIC The `rate` source lets you demo streaming pipelines without
# MAGIC requiring any external infrastructure.

# COMMAND ----------

# Generate a streaming DataFrame at 20 transactions/second
# In production, this would be spark.readStream.format("kafka")...
raw_stream = (
    spark.readStream
    .format("rate")
    .option("rowsPerSecond", 20)
    .load()
)

# Enrich with realistic FinServ transaction fields
# Each column uses deterministic transforms on the incrementing 'value'
# so the data is reproducible but looks realistic
mcc_keys = list(MCC_CATEGORIES.keys())

transactions_stream = (
    raw_stream
    # Transaction identifiers
    .withColumn("transaction_id",
        F.concat(F.lit("TXN-"), F.date_format("timestamp", "yyyyMMdd"), F.lit("-"),
                 F.lpad(F.col("value").cast("string"), 8, "0")))
    .withColumn("card_number",
        F.concat(F.lit("4"), F.lpad((F.col("value") * 7 % 999999999).cast("string"), 15, "0")))
    # PII - will be masked in Silver layer (FinServ governance requirement)
    .withColumn("cardholder_name",
        F.concat(
            F.element_at(F.array(*[F.lit(n) for n in ["James", "Maria", "Robert", "Sarah", "Michael",
                                                        "Jennifer", "David", "Lisa", "William", "Emily"]]),
                         (F.col("value") % 10 + 1).cast("int")),
            F.lit(" "),
            F.element_at(F.array(*[F.lit(n) for n in ["Smith", "Johnson", "Williams", "Brown", "Jones",
                                                        "Garcia", "Miller", "Davis", "Wilson", "Anderson"]]),
                         (F.col("value") * 3 % 10 + 1).cast("int"))))
    # Transaction details
    .withColumn("amount",
        F.round(F.abs(F.sin(F.col("value").cast("double") * 0.1)) * 500 + 1.50, 2))
    .withColumn("currency",
        F.element_at(F.array(*[F.lit(c) for c in CURRENCIES]),
                     (F.col("value") % len(CURRENCIES) + 1).cast("int")))
    .withColumn("mcc_code",
        F.element_at(F.array(*[F.lit(k) for k in mcc_keys]),
                     (F.col("value") % len(mcc_keys) + 1).cast("int")))
    .withColumn("merchant_name",
        F.concat(
            F.element_at(F.array(*[F.lit(n) for n in ["QuickMart", "FuelStop", "Bistro", "MedPlus",
                                                        "ShopAll", "CashPoint", "WireNow", "StayInn",
                                                        "TechZone", "SkyAir"]]),
                         (F.col("value") % 10 + 1).cast("int")),
            F.lit(" #"),
            (F.col("value") % 500 + 1).cast("string")))
    # Location
    .withColumn("merchant_state",
        F.element_at(F.array(*[F.lit(s) for s in STATES]),
                     (F.col("value") % len(STATES) + 1).cast("int")))
    .withColumn("merchant_country", F.lit("US"))
    # Card info
    .withColumn("card_network",
        F.element_at(F.array(*[F.lit(n) for n in CARD_NETWORKS]),
                     (F.col("value") % len(CARD_NETWORKS) + 1).cast("int")))
    .withColumn("card_type",
        F.when(F.col("value") % 3 == 0, "CREDIT")
         .when(F.col("value") % 3 == 1, "DEBIT")
         .otherwise("PREPAID"))
    # Authorization
    .withColumn("auth_code",
        F.lpad((F.col("value") * 13 % 999999).cast("string"), 6, "0"))
    .withColumn("is_online",
        F.when(F.col("value") % 4 == 0, True).otherwise(False))
    .withColumn("is_international",
        F.when(F.col("value") % 20 == 0, True).otherwise(False))
    # Risk signals (raw — will be scored in Gold layer)
    .withColumn("velocity_flag",
        F.when(F.col("value") % 50 == 0, True).otherwise(False))
    .withColumn("amount_anomaly_flag",
        F.when(F.col("amount") > 400, True).otherwise(False))
    # Metadata
    .withColumn("event_timestamp", F.col("timestamp"))
    .withColumn("ingestion_timestamp", F.current_timestamp())
    .withColumn("ingestion_date", F.current_date())
    .drop("timestamp", "value")
)

print("Streaming DataFrame schema:")
transactions_stream.printSchema()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Write to Bronze Delta Table
# MAGIC
# MAGIC **Key concepts:**
# MAGIC - `writeStream` → continuous write to Delta
# MAGIC - `checkpointLocation` → enables exactly-once (Spark tracks offsets here)
# MAGIC - `trigger(availableNow=True)` → process all available data (serverless-compatible)
# MAGIC - `partitionBy("ingestion_date")` → efficient time-range queries
# MAGIC
# MAGIC **FinServ note:** In production, Bronze is your regulatory "golden source."
# MAGIC Regulators (OCC, SEC, FINRA) may require you to retain raw transaction
# MAGIC data for 5-7 years. Bronze = immutable audit trail.

# COMMAND ----------

# Write streaming transactions to Bronze Delta table
# NOTE: Using availableNow=True (serverless-compatible) instead of processingTime
# In production on dedicated clusters, you'd use: .trigger(processingTime="10 seconds")
# Checkpoint stored in Unity Catalog Volume (DBFS is disabled on serverless)
bronze_query = (
    transactions_stream.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", "/Volumes/dbx_weg/bronze/checkpoints/bronze_finserv_transactions")
    .partitionBy("ingestion_date")
    .trigger(availableNow=True)
    .toTable("dbx_weg.bronze.transactions")
)

print(f"Bronze streaming query started: {bronze_query.name}")
print(f"Query ID: {bronze_query.id}")
print("Writing to: dbx_weg.bronze.transactions")
print("Checkpoint: /Volumes/dbx_weg/bronze/checkpoints/bronze_finserv_transactions")
print("\nNote: availableNow=True processes all available data and auto-stops.")
print("In production with dedicated clusters, use trigger(processingTime='10 seconds') for continuous streaming.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Wait for Stream to Complete
# MAGIC
# MAGIC With `availableNow=True`, the stream processes all available data and
# MAGIC auto-terminates. We wait for it to finish, then check results.
# MAGIC
# MAGIC **SA note:** On dedicated clusters with `processingTime`, you'd monitor
# MAGIC the stream continuously. On serverless, `availableNow` is the pattern —
# MAGIC it's how you'd run scheduled batch-streaming jobs.

# COMMAND ----------

# Wait for the availableNow query to finish processing
bronze_query.awaitTermination()
print("Bronze stream completed ✓")
print(f"\nRecent progress:")
for p in bronze_query.recentProgress[-3:]:
    print(f"  Batch {p['batchId']}: {p['numInputRows']} rows, "
          f"{p['processedRowsPerSecond']:.1f} rows/sec")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Query Bronze Table
# MAGIC
# MAGIC **Key Delta Lake features to explore:**
# MAGIC - Table is queryable while streaming writes are happening (ACID!)
# MAGIC - `DESCRIBE HISTORY` shows every write operation
# MAGIC - `VERSION AS OF` lets you time-travel to any point

# COMMAND ----------

# Query the Bronze table — works even while stream is running
bronze_df = spark.read.table("dbx_weg.bronze.transactions")
row_count = bronze_df.count()
print(f"Bronze table row count: {row_count:,}")

# Show sample data
display(
    bronze_df
    .select("transaction_id", "cardholder_name", "amount", "currency",
            "mcc_code", "merchant_name", "card_network", "card_type",
            "is_online", "velocity_flag", "event_timestamp")
    .orderBy(F.desc("event_timestamp"))
    .limit(20)
)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Delta Lake time travel: see the write history
# MAGIC -- Each micro-batch is a separate version (ACID commit)
# MAGIC DESCRIBE HISTORY dbx_weg.bronze.transactions LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Verify Final State
# MAGIC
# MAGIC The stream has auto-terminated (availableNow). Let's verify the data.
# MAGIC In production with `processingTime`, you'd call `bronze_query.stop()`.

# COMMAND ----------

# Verify final Bronze table state
final_count = spark.read.table("dbx_weg.bronze.transactions").count()
print(f"Final Bronze table row count: {final_count:,}")
print("Bronze ingestion complete ✓ — ready for Silver layer")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What You Just Learned (SA Talking Points)
# MAGIC
# MAGIC | Concept | What You Did | SA Value |
# MAGIC |---------|-------------|----------|
# MAGIC | Structured Streaming | `readStream` → `writeStream` pipeline | "Databricks handles real-time and batch with the same API — no separate streaming infrastructure" |
# MAGIC | Delta Lake ACID | Queried table while stream was writing | "ACID on object storage — warehouse reliability at data lake economics" |
# MAGIC | Checkpointing | Exactly-once delivery guarantee | "Critical for FinServ — no duplicate or lost transactions" |
# MAGIC | Time Travel | `DESCRIBE HISTORY`, `VERSION AS OF` | "Built-in audit trail — regulators love this" |
# MAGIC | Schema on Read | Bronze stores raw without transformation | "Never lose data. Transform downstream, not at ingest." |
# MAGIC
# MAGIC **Next:** Phase 3 — Silver layer with PII masking, dedup, and data quality checks.
