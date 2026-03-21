# Databricks notebook source
# MAGIC %md
# MAGIC # Finance Lakehouse — Bronze Generation
# MAGIC
# MAGIC | Table | Rows | Description |
# MAGIC |---|---|---|
# MAGIC | `bronze_dim_customers` | 500 | Customer risk profiles |
# MAGIC | `bronze_dim_merchants` | 200 | Merchant categories + risk flags |
# MAGIC | `bronze_fact_transactions` | 100K | Raw payment transactions |
# MAGIC
# MAGIC **Pattern:** `spark.range()` → broadcast join dims → Delta Bronze (direct, no intermediate files)

# COMMAND ----------

import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark.sql import DataFrame

# ── Config ────────────────────────────────────────────────────────────────────
def _w(name: str, default: str) -> str:
    try:
        v = dbutils.widgets.get(name)
        return v if v else default
    except Exception:
        return default

CATALOG   = _w("catalog",  "workspace")
SCHEMA    = _w("schema",   "finance")
N_EVENTS  = int(_w("n_events", "10000"))   # light — demo scale
BATCH_ID  = "batch_001"

N_CUSTOMERS = 200
N_MERCHANTS = 100
START_DATE  = "2025-01-01"
DAYS_SPAN   = 364   # full calendar year 2025

print(f"Target : {CATALOG}.{SCHEMA}")
print(f"Scale  : {N_EVENTS:,} transactions | {N_CUSTOMERS} customers | {N_MERCHANTS} merchants")

# COMMAND ----------

# ── Schema ────────────────────────────────────────────────────────────────────
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"Schema ready: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# ── Dim 1: Customers  (500 rows — broadcastable) ──────────────────────────────
# Segments weighted to mirror a real bank portfolio
dim_customers = (
    spark.range(N_CUSTOMERS)
    .withColumn("customer_id",
        F.concat(F.lit("CUST-"), F.lpad(F.col("id").cast("string"), 5, "0")))
    .withColumn("_r", F.rand(seed=11))
    .withColumn("segment",
        F.when(F.col("_r") < 0.55, "Retail")
         .when(F.col("_r") < 0.75, "SMB")
         .when(F.col("_r") < 0.90, "Wealth")
         .otherwise("Corporate"))
    # 70% LOW, 20% MEDIUM, 10% HIGH — realistic risk distribution
    .withColumn("_r2", F.rand(seed=22))
    .withColumn("risk_tier",
        F.when(F.col("_r2") < 0.70, "LOW")
         .when(F.col("_r2") < 0.90, "MEDIUM")
         .otherwise("HIGH"))
    .withColumn("country",
        F.when(F.col("id") % 5 == 0, "US")
         .when(F.col("id") % 5 == 1, "UK")
         .when(F.col("id") % 5 == 2, "CA")
         .when(F.col("id") % 5 == 3, "DE")
         .otherwise("SG"))
    .withColumn("member_since_days", ((F.rand(seed=33) * 3650) + 30).cast("int"))
    .drop("id", "_r", "_r2")
)

display(dim_customers.limit(5))

# COMMAND ----------

# ── Dim 2: Merchants  (200 rows — broadcastable) ──────────────────────────────
dim_merchants = (
    spark.range(N_MERCHANTS)
    .withColumn("merchant_id",
        F.concat(F.lit("MCH-"), F.lpad(F.col("id").cast("string"), 5, "0")))
    .withColumn("category",
        F.when(F.col("id") % 7 == 0, "Retail")
         .when(F.col("id") % 7 == 1, "Restaurant")
         .when(F.col("id") % 7 == 2, "Travel")
         .when(F.col("id") % 7 == 3, "Gas")
         .when(F.col("id") % 7 == 4, "ATM")
         .when(F.col("id") % 7 == 5, "Online")
         .otherwise("Crypto"))
    # MCC code — 4-digit industry code (for regulatory reporting)
    .withColumn("mcc_code",
        F.lpad(((F.col("id") % 9000) + 1000).cast("string"), 4, "0"))
    # 12% of merchants are flagged high-risk (Crypto, shell companies, sanctioned regions)
    .withColumn("is_high_risk", (F.col("id") % 9 == 0))
    .drop("id")
)

display(dim_merchants.limit(5))

# COMMAND ----------

# ── Fact: Transactions  (N_EVENTS rows) ───────────────────────────────────────
# Amount distribution mirrors real payments: 70% small (<$200), 20% mid, 10% large
fact_raw = (
    spark.range(N_EVENTS)
    .withColumnRenamed("id", "seq")
    .withColumn("txn_id",
        F.concat(F.lit("TXN-"), F.lpad(F.col("seq").cast("string"), 8, "0")))
    # FK → dims via modulo (guaranteed referential integrity, no lookup maps)
    .withColumn("customer_id",
        F.concat(F.lit("CUST-"), F.lpad((F.col("seq") % N_CUSTOMERS).cast("string"), 5, "0")))
    .withColumn("merchant_id",
        F.concat(F.lit("MCH-"), F.lpad((F.col("seq") % N_MERCHANTS).cast("string"), 5, "0")))
    # Amount: tiered distribution for realistic fraud signal
    .withColumn("_r_amt", F.rand(seed=42))
    .withColumn("amount", F.round(
        F.when(F.col("_r_amt") < 0.70, F.col("_r_amt") * 200 + 5)       # $5–$145
         .when(F.col("_r_amt") < 0.90, F.col("_r_amt") * 800 + 100)     # $100–$820
         .otherwise(F.col("_r_amt") * 9000 + 1000), 2))                  # $1000–$10000
    # Channel weighted: most transactions are online/mobile
    .withColumn("_r_ch", F.rand(seed=55))
    .withColumn("channel",
        F.when(F.col("_r_ch") < 0.35, "Online")
         .when(F.col("_r_ch") < 0.60, "Mobile")
         .when(F.col("_r_ch") < 0.80, "POS")
         .when(F.col("_r_ch") < 0.93, "ATM")
         .otherwise("Wire"))
    # Spread across 2025
    .withColumn("txn_date",
        F.date_add(F.lit(START_DATE), (F.rand(seed=77) * DAYS_SPAN).cast("int")))
    .withColumn("txn_ts", F.to_timestamp(
        F.concat(F.col("txn_date").cast("string"), F.lit(" "),
                 F.lpad((F.rand(seed=88) * 24).cast("int").cast("string"), 2, "0"),
                 F.lit(":"),
                 F.lpad((F.rand(seed=99) * 60).cast("int").cast("string"), 2, "0"),
                 F.lit(":00"))))
    # 3% of transactions pre-flagged as suspicious (mimics rules engine output)
    .withColumn("is_flagged", (F.rand(seed=13) < 0.03))
    .drop("seq", "_r_amt", "_r_ch")
)

# Broadcast join dims → enrich fact with customer + merchant attributes
bronze_txn = (
    fact_raw
    .join(F.broadcast(dim_customers), "customer_id", "left")
    .join(F.broadcast(dim_merchants), "merchant_id", "left")
    .withColumn("ingest_ts",     F.current_timestamp())
    .withColumn("source_system", F.lit("core_banking_synthetic"))
    .withColumn("batch_id",      F.lit(BATCH_ID))
)

# COMMAND ----------

# ── Write Bronze Delta ─────────────────────────────────────────────────────────
# Dims: small, no repartition needed
dim_customers.write.format("delta").mode("overwrite") \
    .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_dim_customers")

dim_merchants.write.format("delta").mode("overwrite") \
    .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_dim_merchants")

# Fact: repartition for optimal file sizing downstream
(bronze_txn
    .repartition(8)
    .write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_fact_transactions"))

print(f"Bronze write complete → {CATALOG}.{SCHEMA}")

# COMMAND ----------

# ── Validate ──────────────────────────────────────────────────────────────────
print("── Row counts ──")
for tbl in ["bronze_dim_customers", "bronze_dim_merchants", "bronze_fact_transactions"]:
    cnt = spark.table(f"{CATALOG}.{SCHEMA}.{tbl}").count()
    print(f"  {tbl:<35} {cnt:>10,}")

print("\n── Channel distribution (Bronze fact) ──")
(spark.table(f"{CATALOG}.{SCHEMA}.bronze_fact_transactions")
    .groupBy("channel")
    .agg(F.count("*").alias("txn_count"),
         F.round(F.sum("amount"), 2).alias("total_amount"))
    .orderBy(F.desc("txn_count"))
    .show())

print("\n── Customer risk tier distribution ──")
(spark.table(f"{CATALOG}.{SCHEMA}.bronze_dim_customers")
    .groupBy("segment", "risk_tier")
    .count()
    .orderBy("segment", "risk_tier")
    .show())
