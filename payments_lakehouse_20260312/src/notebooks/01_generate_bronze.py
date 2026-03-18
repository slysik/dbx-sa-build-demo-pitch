# Databricks notebook source
# MAGIC %md
# MAGIC # Payment Transactions — Bronze Generation
# MAGIC | Table | Rows | Method |
# MAGIC |-------|------|--------|
# MAGIC | `bronze_payment_types` | 10K | `spark.range(10_000)` |
# MAGIC | `bronze_payment_transactions` | 10K | `spark.range(10_000)` |
# MAGIC
# MAGIC **Pattern:** `spark.range()` → Spark-native columns → broadcast join → Bronze Delta

# COMMAND ----------

# TALK: Config cell — one place to change scale, zero code changes needed
# SCALING: Change N_TRANSACTIONS from 10K → 1M → 100M, same code runs
# DW-BRIDGE: Like a Netezza CREATE TABLE AS SELECT from generate_series()

from pyspark.sql import functions as F

CATALOG = "interview"
SCHEMA = "payments"
BATCH_ID = "batch_001"

N_TYPES = 10_000
N_TRANSACTIONS = 10_000

START_DATE = "2025-01-01"
DAYS_SPAN = 365

print(f"Target: {CATALOG}.{SCHEMA} | Types: {N_TYPES:,} | Transactions: {N_TRANSACTIONS:,}")

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Dimension: Payment Types (10K rows)

# COMMAND ----------

# TALK: Dimension table — lean, 6 columns, broadcastable
# DW-BRIDGE: Like a Netezza zone map dimension — small, replicated to every SPU

payment_types = (
    spark.range(N_TYPES)
    .withColumnRenamed("id", "type_seq")
    .withColumn("payment_type_id",
        F.concat(F.lit("PT-"), F.lpad(F.col("type_seq").cast("string"), 5, "0")))
    .withColumn("type_name",
        F.when(F.col("type_seq") % 8 == 0, "ACH Transfer")
         .when(F.col("type_seq") % 8 == 1, "Wire Transfer")
         .when(F.col("type_seq") % 8 == 2, "Credit Card")
         .when(F.col("type_seq") % 8 == 3, "Debit Card")
         .when(F.col("type_seq") % 8 == 4, "PayPal")
         .when(F.col("type_seq") % 8 == 5, "Venmo")
         .when(F.col("type_seq") % 8 == 6, "Apple Pay")
         .otherwise("Crypto"))
    .withColumn("category",
        F.when(F.col("type_seq") % 4 == 0, "Bank Transfer")
         .when(F.col("type_seq") % 4 == 1, "Card Payment")
         .when(F.col("type_seq") % 4 == 2, "Digital Wallet")
         .otherwise("Alternative"))
    .withColumn("processor",
        F.when(F.col("type_seq") % 5 == 0, "Visa")
         .when(F.col("type_seq") % 5 == 1, "Mastercard")
         .when(F.col("type_seq") % 5 == 2, "Stripe")
         .when(F.col("type_seq") % 5 == 3, "PayPal")
         .otherwise("Square"))
    .withColumn("is_active", F.when(F.col("type_seq") % 10 == 0, F.lit(False)).otherwise(F.lit(True)))
    .withColumn("ingest_ts", F.current_timestamp())
    .drop("type_seq")
)

display(payment_types.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fact: Payment Transactions (10K rows)

# COMMAND ----------

# TALK: Fact table — spark.range gives distributed generation, no driver pressure
# SCALING: At 100M rows this runs across all executors — zero code change
# DW-BRIDGE: Like Netezza generate_series + hash distribution across SPUs

transactions = (
    spark.range(N_TRANSACTIONS)
    .withColumnRenamed("id", "txn_seq")
    .withColumn("transaction_id",
        F.concat(F.lit("TXN-"), F.lpad(F.col("txn_seq").cast("string"), 8, "0")))
    # FK — modulo guarantees referential integrity without lookup maps
    .withColumn("payment_type_id",
        F.concat(F.lit("PT-"), F.lpad((F.col("txn_seq") % N_TYPES).cast("string"), 5, "0")))
    # Amount: $0.50 – $9,999.50 via hash for deterministic distribution
    .withColumn("amount",
        F.round(F.abs(F.hash(F.col("txn_seq"))) % 999900 / F.lit(100.0) + 0.50, 2))
    # Currency: USD-weighted (~70%), some EUR/GBP/JPY
    .withColumn("currency",
        F.when(F.col("txn_seq") % 20 < 3, "EUR")
         .when(F.col("txn_seq") % 20 < 5, "GBP")
         .when(F.col("txn_seq") % 20 == 5, "JPY")
         .otherwise("USD"))
    # Sender/receiver IDs via hash for realistic spread
    .withColumn("sender_id",
        F.concat(F.lit("SEND-"), F.lpad((F.abs(F.hash(F.col("txn_seq"))) % 5000).cast("string"), 6, "0")))
    .withColumn("receiver_id",
        F.concat(F.lit("RECV-"), F.lpad((F.abs(F.hash(F.col("txn_seq") + 1000)) % 5000).cast("string"), 6, "0")))
    # Status: COMPLETED 70%, PENDING 15%, FAILED 10%, REVERSED 5%
    .withColumn("status",
        F.when(F.col("txn_seq") % 20 < 3, "PENDING")
         .when(F.col("txn_seq") % 20 < 5, "FAILED")
         .when(F.col("txn_seq") % 20 == 5, "REVERSED")
         .otherwise("COMPLETED"))
    # Transaction timestamp spread across date range
    .withColumn("transaction_ts",
        F.to_timestamp(
            F.concat(
                F.date_add(F.lit(START_DATE), (F.abs(F.hash(F.col("txn_seq"), F.lit("date"))) % DAYS_SPAN).cast("int")).cast("string"),
                F.lit(" "),
                F.lpad((F.abs(F.hash(F.col("txn_seq"), F.lit("hour"))) % 24).cast("string"), 2, "0"),
                F.lit(":"),
                F.lpad((F.abs(F.hash(F.col("txn_seq"), F.lit("min"))) % 60).cast("string"), 2, "0"),
                F.lit(":00"))))
    .drop("txn_seq")
)

display(transactions.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Broadcast Join + Bronze Metadata + Write

# COMMAND ----------

# TALK: Broadcast join — 10K dim fits in driver memory, zero shuffle
# SCALING: Even at 100K dims this broadcasts fine — threshold is ~10MB
# DW-BRIDGE: Like Netezza replicated dimension — copied to every SPU, joined locally

bronze_transactions = (
    transactions
    .join(F.broadcast(payment_types.drop("ingest_ts")), "payment_type_id", "left")
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("source_system", F.lit("synthetic_generator"))
    .withColumn("batch_id", F.lit(BATCH_ID))
)

# Write dim
payment_types.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_payment_types")
print(f"Wrote bronze_payment_types")

# Write fact
(bronze_transactions
    .write.format("delta").mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_payment_transactions"))
print(f"Wrote bronze_payment_transactions")

# COMMAND ----------

# MAGIC %md
# MAGIC ## CHECK Constraints + Validation

# COMMAND ----------

# TALK: CHECK constraints — shift-left DQ, catch bad data at Bronze, not downstream
# DW-BRIDGE: Like Netezza CONSTRAINT CHECK — enforced at write time

spark.sql(f"ALTER TABLE {CATALOG}.{SCHEMA}.bronze_payment_transactions ADD CONSTRAINT chk_amount CHECK (amount > 0)")
spark.sql(f"ALTER TABLE {CATALOG}.{SCHEMA}.bronze_payment_transactions ADD CONSTRAINT chk_status CHECK (status IN ('COMPLETED', 'PENDING', 'FAILED', 'REVERSED'))")

# Single validation pass
for tbl in ["bronze_payment_types", "bronze_payment_transactions"]:
    cnt = spark.table(f"{CATALOG}.{SCHEMA}.{tbl}").count()
    print(f"  {tbl}: {cnt:,}")

# Distribution check
spark.table(f"{CATALOG}.{SCHEMA}.bronze_payment_transactions").groupBy("status").count().orderBy("status").show()
spark.table(f"{CATALOG}.{SCHEMA}.bronze_payment_transactions").groupBy("currency").count().orderBy("currency").show()
