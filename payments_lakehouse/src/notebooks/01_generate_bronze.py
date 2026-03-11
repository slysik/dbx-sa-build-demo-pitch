# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # Payment Transactions — Bronze Generation
# MAGIC
# MAGIC | Table | Rows | Type |
# MAGIC |-------|------|------|
# MAGIC | `bronze_payment_types` | 10,000 | Dim |
# MAGIC | `bronze_payment_transactions` | 100,000,000 | Fact |
# MAGIC
# MAGIC **Pattern:** `spark.range()` + `F.hash()` deterministic generation — no Faker, no Pandas, no Python loops.

# COMMAND ----------

# Config
from pyspark.sql import functions as F

CATALOG    = "interview"
SCHEMA     = "payments"
BATCH_ID   = "batch_001"

N_TYPES    = 10_000
N_EVENTS   = 100_000_000   # ← change this one param to scale

START_DATE = "2025-01-01"
DAYS_SPAN  = 365

print(f"Target: {CATALOG}.{SCHEMA}")
print(f"  Transactions: {N_EVENTS:,}")
print(f"  Payment types: {N_TYPES:,}")

# COMMAND ----------

# Create schema
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"✓ Schema {CATALOG}.{SCHEMA} ready")

# COMMAND ----------

# Dim: payment_types (10K rows, 6 columns)
# Hash-based deterministic assignment — same id always maps to same category

TYPE_NAMES = ["credit_card", "debit_card", "wire_transfer", "ach",
              "digital_wallet", "check", "crypto", "prepaid"]
CATEGORIES = ["card", "bank_transfer", "digital", "other"]
PROCESSORS = ["visa", "mastercard", "amex", "stripe",
              "paypal", "square", "plaid", "internal"]

payment_types = (
    spark.range(N_TYPES)
    .withColumnRenamed("id", "payment_type_id")
    .withColumn("type_name",
        F.element_at(
            F.array(*[F.lit(t) for t in TYPE_NAMES]),
            (F.abs(F.hash(F.col("payment_type_id")).cast("bigint")) % len(TYPE_NAMES) + 1).cast("int")))
    .withColumn("category",
        F.element_at(
            F.array(*[F.lit(c) for c in CATEGORIES]),
            (F.abs(F.hash(F.col("payment_type_id"), F.lit("cat")).cast("bigint")) % len(CATEGORIES) + 1).cast("int")))
    .withColumn("processor",
        F.element_at(
            F.array(*[F.lit(p) for p in PROCESSORS]),
            (F.abs(F.hash(F.col("payment_type_id"), F.lit("proc")).cast("bigint")) % len(PROCESSORS) + 1).cast("int")))
    .withColumn("is_active",
        (F.abs(F.hash(F.col("payment_type_id"), F.lit("active")).cast("bigint")) % 10 > 0))
    .withColumn("ingest_ts", F.current_timestamp())
)

# Write dim (small — no repartition needed)
payment_types.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_payment_types")

cnt = spark.table(f"{CATALOG}.{SCHEMA}.bronze_payment_types").count()
print(f"✓ bronze_payment_types: {cnt:,} rows")
display(spark.table(f"{CATALOG}.{SCHEMA}.bronze_payment_types").limit(5))

# COMMAND ----------

# Fact: payment_transactions (100M rows)
# Every column derived from hash(id, salt) — fully deterministic, no rand()
# SKEW: 40% of rows → payment_type_id 0 (ACH/PayPal hot key)

# Hash buckets for weighted distributions
h_skew     = F.abs(F.hash(F.col("id"), F.lit("skew")).cast("bigint")) % 100
h_status   = F.abs(F.hash(F.col("id"), F.lit("status")).cast("bigint")) % 100
h_currency = F.abs(F.hash(F.col("id"), F.lit("currency")).cast("bigint")) % 100

transactions = (
    spark.range(N_EVENTS)
    # Unique transaction ID
    .withColumn("transaction_id",
        F.concat(F.lit("TXN-"), F.lpad(F.col("id").cast("string"), 10, "0")))
    # FK with SKEW: 40% → type 0 (hot key), 60% → distributed across 1-9999
    .withColumn("payment_type_id",
        F.when(h_skew < 40, F.lit(0).cast("bigint"))
         .otherwise((F.abs(F.hash(F.col("id"), F.lit("fk")).cast("bigint")) % 9999 + 1).cast("bigint")))
    # Amount: hash-derived, always positive ($0.50 to $10,000.49)
    .withColumn("amount",
        F.round(
            (F.abs(F.hash(F.col("id"), F.lit("amt")).cast("bigint")) % 999_950) / 100.0 + 0.50,
            2))
    # Currency: USD-weighted (70/15/10/5)
    .withColumn("currency",
        F.when(h_currency < 70, "USD")
         .when(h_currency < 85, "EUR")
         .when(h_currency < 95, "GBP")
         .otherwise("JPY"))
    # Sender & receiver IDs (1M unique users each)
    .withColumn("sender_id",
        F.concat(F.lit("USR-"),
                 F.lpad((F.abs(F.hash(F.col("id"), F.lit("snd")).cast("bigint")) % 1_000_000).cast("string"), 7, "0")))
    .withColumn("receiver_id",
        F.concat(F.lit("USR-"),
                 F.lpad((F.abs(F.hash(F.col("id"), F.lit("rcv")).cast("bigint")) % 1_000_000).cast("string"), 7, "0")))
    # Status: COMPLETED 70%, PENDING 15%, FAILED 10%, REVERSED 5%
    .withColumn("status",
        F.when(h_status < 70, "COMPLETED")
         .when(h_status < 85, "PENDING")
         .when(h_status < 95, "FAILED")
         .otherwise("REVERSED"))
    # Timestamp: spread across 365 days with hour/min/sec variation
    .withColumn("_day_offset",
        (F.abs(F.hash(F.col("id"), F.lit("day")).cast("bigint")) % DAYS_SPAN).cast("int"))
    .withColumn("transaction_ts", F.to_timestamp(
        F.concat(
            F.date_add(F.lit(START_DATE), F.col("_day_offset")).cast("string"),
            F.lit(" "),
            F.lpad((F.abs(F.hash(F.col("id"), F.lit("hr")).cast("bigint")) % 24).cast("string"), 2, "0"),
            F.lit(":"),
            F.lpad((F.abs(F.hash(F.col("id"), F.lit("min")).cast("bigint")) % 60).cast("string"), 2, "0"),
            F.lit(":"),
            F.lpad((F.abs(F.hash(F.col("id"), F.lit("sec")).cast("bigint")) % 60).cast("string"), 2, "0"))))
    # Bronze metadata
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("source_system", F.lit("payment_gateway"))
    .withColumn("batch_id", F.lit(BATCH_ID))
    .drop("id", "_day_offset")
)

display(transactions.limit(5))

# COMMAND ----------

# Write fact table — let Delta optimize write handle file sizing (no manual repartition at 100M)
(transactions
    .write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_payment_transactions"))

# Apply liquid clustering — auto-optimized, no partition skew on high-cardinality timestamp
spark.sql(f"""
    ALTER TABLE {CATALOG}.{SCHEMA}.bronze_payment_transactions
    CLUSTER BY (transaction_ts)
""")

print(f"✓ bronze_payment_transactions written with CLUSTER BY (transaction_ts)")

# COMMAND ----------

# CHECK constraints — DQ gates at Bronze (enforced on future writes)
constraints = {
    "bronze_payment_transactions": [
        ("chk_amount_positive",  "amount > 0"),
        ("chk_valid_status",     "status IN ('COMPLETED', 'PENDING', 'FAILED', 'REVERSED')"),
        ("chk_valid_currency",   "currency IN ('USD', 'EUR', 'GBP', 'JPY')"),
        ("chk_txn_id_not_null",  "transaction_id IS NOT NULL"),
    ],
    "bronze_payment_types": [
        ("chk_type_id_not_null", "payment_type_id IS NOT NULL"),
    ],
}

print("Applying CHECK constraints...")
for table, checks in constraints.items():
    fqn = f"{CATALOG}.{SCHEMA}.{table}"
    for name, expr in checks:
        try:
            spark.sql(f"ALTER TABLE {fqn} ADD CONSTRAINT {name} CHECK ({expr})")
            print(f"  ✓ {table}.{name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  ○ {table}.{name} (exists)")
            else:
                print(f"  ✗ {table}.{name}: {e}")

# COMMAND ----------

# Validation — one pass for counts, distributions, null audit, constraints

print("=" * 60)
print("ROW COUNTS")
print("=" * 60)
for tbl in ["bronze_payment_types", "bronze_payment_transactions"]:
    cnt = spark.table(f"{CATALOG}.{SCHEMA}.{tbl}").count()
    print(f"  {tbl}: {cnt:,}")

print("\n" + "=" * 60)
print("STATUS DISTRIBUTION (target: COMPLETED 70%, PENDING 15%, FAILED 10%, REVERSED 5%)")
print("=" * 60)
(spark.table(f"{CATALOG}.{SCHEMA}.bronze_payment_transactions")
    .groupBy("status").count()
    .withColumn("pct", F.round(F.col("count") / N_EVENTS * 100, 1))
    .orderBy(F.desc("count")).show())

print("CURRENCY DISTRIBUTION (target: USD 70%, EUR 15%, GBP 10%, JPY 5%)")
(spark.table(f"{CATALOG}.{SCHEMA}.bronze_payment_transactions")
    .groupBy("currency").count()
    .withColumn("pct", F.round(F.col("count") / N_EVENTS * 100, 1))
    .orderBy(F.desc("count")).show())

print("NULL AUDIT (fact)")
spark.sql(f"""
    SELECT
        COUNT(*)                                                    AS total_rows,
        SUM(CASE WHEN transaction_id IS NULL THEN 1 ELSE 0 END)    AS null_txn_id,
        SUM(CASE WHEN payment_type_id IS NULL THEN 1 ELSE 0 END)   AS null_type_id,
        SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END)            AS null_amount,
        SUM(CASE WHEN transaction_ts IS NULL THEN 1 ELSE 0 END)    AS null_ts
    FROM {CATALOG}.{SCHEMA}.bronze_payment_transactions
""").show()

print("DELTA TABLE DETAILS")
spark.sql(f"DESCRIBE DETAIL {CATALOG}.{SCHEMA}.bronze_payment_transactions").select(
    "name", "format", "numFiles", "sizeInBytes", "clusteringColumns"
).show(truncate=False)

print("CHECK CONSTRAINTS")
(spark.sql(f"SHOW TBLPROPERTIES {CATALOG}.{SCHEMA}.bronze_payment_transactions")
    .filter(F.col("key").contains("constraint"))
    .show(truncate=False))

print("SAMPLE DATA (5 rows)")
display(spark.table(f"{CATALOG}.{SCHEMA}.bronze_payment_transactions").limit(5))
