# Databricks notebook source
# MAGIC %md
# MAGIC # Phase 3: Silver Layer — Cleanse, Validate, Mask PII
# MAGIC
# MAGIC **What you'll learn:**
# MAGIC - `foreachBatch` for complex streaming transforms
# MAGIC - Delta Lake `MERGE INTO` for idempotent upserts
# MAGIC - PII masking patterns (FinServ regulatory requirement)
# MAGIC - Data quality validation and quarantine
# MAGIC
# MAGIC **FinServ context:** Silver is your "single source of truth."
# MAGIC PII must be masked/tokenized before downstream consumption.
# MAGIC Regulators (GDPR, CCPA, PCI-DSS) require controlled access to
# MAGIC cardholder data. Silver is where governance enforcement happens.
# MAGIC
# MAGIC ```
# MAGIC Bronze (raw) → Silver (cleansed, PII-masked, validated)
# MAGIC                 ├── quarantine table (bad records)
# MAGIC                 └── governance: PII masked, schema enforced
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Define Data Quality Rules
# MAGIC
# MAGIC **FinServ DQ requirements:**
# MAGIC - Transaction amount must be positive
# MAGIC - Card number must be 16 digits
# MAGIC - MCC code must be in valid set
# MAGIC - No null transaction IDs

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import *
from delta.tables import DeltaTable

# Valid MCC codes (same set as Bronze generator)
VALID_MCC = ["5411", "5541", "5812", "5912", "5999",
             "6011", "4829", "7011", "5732", "3000"]

MCC_LOOKUP = {
    "5411": "Grocery", "5541": "Gas", "5812": "Restaurant",
    "5912": "Pharmacy", "5999": "Retail", "6011": "ATM",
    "4829": "Wire Transfer", "7011": "Hotel", "5732": "Electronics",
    "3000": "Airlines"
}

print("Data quality rules defined ✓")
print(f"  Valid MCC codes: {len(VALID_MCC)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: PII Masking Functions
# MAGIC
# MAGIC **PCI-DSS requirement:** Card numbers must be masked except
# MAGIC last 4 digits. Cardholder names tokenized or removed.
# MAGIC
# MAGIC In production, use Unity Catalog **column masks** for dynamic
# MAGIC masking based on user role. Here we do it at the transform layer
# MAGIC to demonstrate the pattern.

# COMMAND ----------

def mask_card_number(col):
    """Mask card number: show only last 4 digits. PCI-DSS compliant."""
    return F.concat(F.lit("****-****-****-"), F.substring(col, -4, 4))

def tokenize_name(col):
    """Hash cardholder name for privacy. Preserves join capability."""
    return F.sha2(F.lower(F.trim(col)), 256)

print("PII masking functions defined ✓")
print("  mask_card_number: ****-****-****-1234")
print("  tokenize_name: SHA-256 hash (deterministic, joinable)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Silver Transform with foreachBatch
# MAGIC
# MAGIC **Key concept:** `foreachBatch` gives you a regular DataFrame
# MAGIC per micro-batch. This is where you do things that don't work
# MAGIC in pure streaming mode:
# MAGIC - MERGE INTO (upserts)
# MAGIC - Multi-table writes (good records + quarantine)
# MAGIC - Complex validation logic
# MAGIC
# MAGIC **SA talking point:** "foreachBatch is the bridge between
# MAGIC streaming ingestion and batch-quality transforms. You get
# MAGIC the latency of streaming with the power of batch."

# COMMAND ----------

def process_silver_batch(batch_df, batch_id):
    """
    Process each micro-batch:
    1. Validate data quality
    2. Quarantine bad records
    3. Mask PII
    4. Enrich with derived fields
    5. MERGE INTO Silver table (idempotent)
    """
    if batch_df.isEmpty():
        return

    # ========================================
    # 1. DATA QUALITY: Split good vs bad
    # ========================================
    valid_df = (
        batch_df
        .filter(F.col("transaction_id").isNotNull())
        .filter(F.col("amount") > 0)
        .filter(F.length("card_number") == 16)
        .filter(F.col("mcc_code").isin(VALID_MCC))
    )

    quarantine_df = batch_df.subtract(valid_df)

    # Write bad records to quarantine (FinServ audit requirement)
    if quarantine_df.count() > 0:
        (quarantine_df
         .withColumn("quarantine_reason", F.lit("DQ_VALIDATION_FAILED"))
         .withColumn("quarantine_timestamp", F.current_timestamp())
         .write.format("delta").mode("append")
         .saveAsTable("dbx_weg.silver.transactions_quarantine"))

    # ========================================
    # 2. PII MASKING (PCI-DSS / GDPR)
    # ========================================
    masked_df = (
        valid_df
        .withColumn("card_number_masked", mask_card_number("card_number"))
        .withColumn("cardholder_token", tokenize_name("cardholder_name"))
        .drop("card_number", "cardholder_name")  # Remove raw PII
    )

    # ========================================
    # 3. ENRICH with derived fields
    # ========================================
    enriched_df = (
        masked_df
        .withColumn("mcc_category",
            F.create_map(*[item for k, v in MCC_LOOKUP.items()
                          for item in (F.lit(k), F.lit(v))])[F.col("mcc_code")])
        .withColumn("event_date", F.to_date("event_timestamp"))
        .withColumn("event_hour", F.hour("event_timestamp"))
        .withColumn("amount_bucket",
            F.when(F.col("amount") < 25, "micro")
             .when(F.col("amount") < 100, "small")
             .when(F.col("amount") < 500, "medium")
             .otherwise("large"))
        # Risk enrichment
        .withColumn("is_high_risk_mcc",
            F.when(F.col("mcc_code").isin("6011", "4829"), True)  # ATM, Wire
             .otherwise(False))
        .withColumn("risk_score_raw",
            (F.when(F.col("velocity_flag"), 30).otherwise(0) +
             F.when(F.col("amount_anomaly_flag"), 25).otherwise(0) +
             F.when(F.col("is_international"), 15).otherwise(0) +
             F.when(F.col("is_high_risk_mcc"), 20).otherwise(0) +
             F.when(F.col("is_online"), 10).otherwise(0)))
        .withColumn("silver_timestamp", F.current_timestamp())
    )

    # ========================================
    # 4. MERGE INTO Silver (idempotent upsert)
    # ========================================
    # NOTE: Using spark.catalog.tableExists() instead of DeltaTable.isDeltaTable()
    # because isDeltaTable fails on serverless Spark Connect (treats UC table
    # names as file paths). tableExists() is the serverless-compatible pattern.
    if spark.catalog.tableExists("dbx_weg.silver.transactions"):
        silver_table = DeltaTable.forName(spark, "dbx_weg.silver.transactions")
        (silver_table.alias("target")
         .merge(enriched_df.alias("source"),
                "target.transaction_id = source.transaction_id")
         .whenMatchedUpdateAll()
         .whenNotMatchedInsertAll()
         .execute())
    else:
        # First batch — create the table
        enriched_df.write.format("delta").saveAsTable("dbx_weg.silver.transactions")

print("Silver transform function defined ✓")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Run Silver Stream (Bronze → Silver)
# MAGIC
# MAGIC Reads from Bronze Delta table as a stream, applies transforms,
# MAGIC writes to Silver. In production this runs 24/7.

# COMMAND ----------

silver_query = (
    spark.readStream
    .table("dbx_weg.bronze.transactions")
    .writeStream
    .foreachBatch(process_silver_batch)
    .option("checkpointLocation", "/Volumes/dbx_weg/bronze/checkpoints/silver_finserv_transactions")
    .trigger(availableNow=True)  # Process all available data then stop
    .start()
)

print("Silver stream started (availableNow mode — will process all Bronze data then stop)")
silver_query.awaitTermination()
print("Silver stream completed ✓")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Verify Silver Results

# COMMAND ----------

silver_df = spark.read.table("dbx_weg.silver.transactions")
print(f"Silver table rows: {silver_df.count():,}")
print(f"\nSchema (note: no raw PII columns):")
silver_df.printSchema()

# Show sample — notice PII is masked
display(
    silver_df
    .select("transaction_id", "card_number_masked", "cardholder_token",
            "amount", "amount_bucket", "mcc_category", "merchant_name",
            "risk_score_raw", "is_high_risk_mcc", "event_timestamp")
    .orderBy(F.desc("event_timestamp"))
    .limit(20)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Data Quality Summary

# COMMAND ----------

# Risk distribution
print("=== Risk Score Distribution ===")
display(
    silver_df
    .groupBy("amount_bucket")
    .agg(
        F.count("*").alias("txn_count"),
        F.avg("risk_score_raw").alias("avg_risk_score"),
        F.sum(F.when(F.col("risk_score_raw") >= 50, 1).otherwise(0)).alias("high_risk_count"),
        F.avg("amount").alias("avg_amount"),
    )
    .orderBy("amount_bucket")
)

# COMMAND ----------

# MCC category breakdown
print("=== Transactions by MCC Category ===")
display(
    silver_df
    .groupBy("mcc_category", "is_high_risk_mcc")
    .agg(
        F.count("*").alias("txn_count"),
        F.sum("amount").alias("total_volume"),
        F.avg("amount").alias("avg_ticket"),
    )
    .orderBy(F.desc("total_volume"))
)

# COMMAND ----------

# Check quarantine table
try:
    quarantine_df = spark.read.table("dbx_weg.silver.transactions_quarantine")
    print(f"Quarantined records: {quarantine_df.count()}")
    display(quarantine_df.limit(10))
except Exception:
    print("No quarantined records (all data passed quality checks) ✓")

# COMMAND ----------

# MAGIC %md
# MAGIC ## What You Just Learned (SA Talking Points)
# MAGIC
# MAGIC | Concept | What You Did | SA Value |
# MAGIC |---------|-------------|----------|
# MAGIC | foreachBatch | Complex transforms on streaming data | "Bridge between streaming latency and batch-quality transforms" |
# MAGIC | MERGE INTO | Idempotent upserts (replay-safe) | "Critical for FinServ — replay any batch without duplicates" |
# MAGIC | PII Masking | Card number masked, name tokenized | "PCI-DSS at the transform layer. UC column masks for dynamic masking by role." |
# MAGIC | Data Quality | Validation + quarantine pattern | "Bad data doesn't pollute downstream. Auditable quarantine for compliance." |
# MAGIC | Risk Enrichment | Raw risk scoring from multiple signals | "Silver layer adds business context — not just cleansing" |
# MAGIC | `availableNow` | Streaming API, batch execution | "Same code runs streaming or batch — just change the trigger" |
# MAGIC
# MAGIC **Next:** Phase 4 — Gold layer with business aggregates and ML feature engineering.
