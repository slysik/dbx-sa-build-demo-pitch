# Databricks notebook source
# MAGIC %md
# MAGIC # Apex Financial Services — Bronze Generation
# MAGIC
# MAGIC | Table | Rows | Method |
# MAGIC |-------|------|--------|
# MAGIC | `bronze_dim_customers` | 200 | spark.range → broadcast |
# MAGIC | `bronze_dim_accounts` | 2,000 | spark.range → broadcast |
# MAGIC | `bronze_fact_transactions` | 100,000 | spark.range → FK modulo |
# MAGIC
# MAGIC **Pattern:** `spark.range(N)` native — no Faker, no Pandas, no Python loops.
# MAGIC Scales 100 → 1M by changing one parameter.

# COMMAND ----------

import pyspark.sql.functions as F
from pyspark.sql import DataFrame, SparkSession

CATALOG    = "workspace"
SCHEMA     = "finserv"
BATCH_ID   = "batch_001"

N_CUSTOMERS = 200
N_ACCOUNTS  = 2_000
N_EVENTS    = 100_000   # ← change this to scale

START_DATE  = "2024-01-01"
DAYS_SPAN   = 365

print(f"Target: {CATALOG}.{SCHEMA}  |  Transactions: {N_EVENTS:,}")

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

# COMMAND ----------

# --- Dim: Customers (200 rows, 5 cols, broadcastable) ---
dim_customers = (
    spark.range(N_CUSTOMERS)
    .withColumn("customer_id",
        F.concat(F.lit("CUST-"), F.lpad(F.col("id").cast("string"), 5, "0")))
    .withColumn("_r", F.rand(seed=11))
    .withColumn("segment",
        F.when(F.col("_r") < 0.55, "Retail")
         .when(F.col("_r") < 0.75, "SME")
         .when(F.col("_r") < 0.90, "Corporate")
         .otherwise("Private Banking"))
    .withColumn("_r2", F.rand(seed=22))
    .withColumn("risk_tier",
        F.when(F.col("_r2") < 0.60, "Low")
         .when(F.col("_r2") < 0.85, "Medium")
         .otherwise("High"))
    .withColumn("region",
        F.when(F.col("id") % 4 == 0, "Northeast")
         .when(F.col("id") % 4 == 1, "Southeast")
         .when(F.col("id") % 4 == 2, "Midwest")
         .otherwise("West"))
    .withColumn("customer_since_year", (2010 + (F.col("id") % 15)).cast("int"))
    .drop("id", "_r", "_r2")
)

display(dim_customers.limit(5))

# COMMAND ----------

# --- Dim: Accounts (2,000 rows, 5 cols, broadcastable) ---
dim_accounts = (
    spark.range(N_ACCOUNTS)
    .withColumn("account_id",
        F.concat(F.lit("ACCT-"), F.lpad(F.col("id").cast("string"), 6, "0")))
    .withColumn("customer_id",
        F.concat(F.lit("CUST-"), F.lpad((F.col("id") % N_CUSTOMERS).cast("string"), 5, "0")))
    .withColumn("account_type",
        F.when(F.col("id") % 4 == 0, "Checking")
         .when(F.col("id") % 4 == 1, "Savings")
         .when(F.col("id") % 4 == 2, "Credit")
         .otherwise("Investment"))
    .withColumn("branch",
        F.when(F.col("id") % 5 == 0, "New York")
         .when(F.col("id") % 5 == 1, "San Francisco")
         .when(F.col("id") % 5 == 2, "Chicago")
         .when(F.col("id") % 5 == 3, "Los Angeles")
         .otherwise("Boston"))
    .withColumn("account_status",
        F.when(F.col("id") % 20 == 0, "Frozen")
         .when(F.col("id") % 10 == 0, "Inactive")
         .otherwise("Active"))
    .drop("id")
)

display(dim_accounts.limit(5))

# COMMAND ----------

# --- Fact: Transactions (100K rows) ---
# Note: column named txn_status (not status) to avoid collision with account_status on join
fact_txns = (
    spark.range(N_EVENTS)
    .withColumnRenamed("id", "event_seq")
    .withColumn("txn_id",
        F.concat(F.lit("TXN-"), F.lpad(F.col("event_seq").cast("string"), 8, "0")))
    .withColumn("account_id",
        F.concat(F.lit("ACCT-"), F.lpad((F.col("event_seq") % N_ACCOUNTS).cast("string"), 6, "0")))
    .withColumn("txn_date",
        F.date_add(F.lit(START_DATE), (F.rand(seed=42) * DAYS_SPAN).cast("int")))
    .withColumn("amount",
        F.round(10 + (F.pow(F.rand(seed=99), 2) * 4990), 2))
    .withColumn("_r", F.rand(seed=55))
    .withColumn("merchant_category",
        F.when(F.col("_r") < 0.30, "Retail")
         .when(F.col("_r") < 0.50, "Food & Dining")
         .when(F.col("_r") < 0.65, "Travel")
         .when(F.col("_r") < 0.75, "Healthcare")
         .when(F.col("_r") < 0.85, "Entertainment")
         .when(F.col("_r") < 0.92, "Fuel")
         .otherwise("Other"))
    .withColumn("txn_type",
        F.when(F.col("event_seq") % 5 == 0, "ATM Withdrawal")
         .when(F.col("event_seq") % 5 == 1, "Online Purchase")
         .when(F.col("event_seq") % 5 == 2, "Contactless")
         .when(F.col("event_seq") % 5 == 3, "Wire Transfer")
         .otherwise("Point of Sale"))
    # txn_status — named explicitly to avoid collision with account_status from dim join
    .withColumn("_r2", F.rand(seed=77))
    .withColumn("txn_status",
        F.when(F.col("_r2") < 0.02, "Flagged")
         .when(F.col("_r2") < 0.05, "Declined")
         .when(F.col("_r2") < 0.08, "Pending")
         .otherwise("Approved"))
    .withColumn("risk_score",
        F.least(F.lit(100.0),
            F.greatest(F.lit(0.0),
                F.round(
                    F.when(F.col("txn_status") == "Flagged",  70 + F.rand(seed=88) * 30)
                     .when(F.col("txn_status") == "Declined", 50 + F.rand(seed=89) * 30)
                     .otherwise(F.rand(seed=90) * 45), 1))))
    .drop("event_seq", "_r", "_r2")
)

# COMMAND ----------

# --- Broadcast join: accounts → customers → fact, add Bronze metadata ---
bronze = (
    fact_txns
    .join(F.broadcast(dim_accounts.select(
            "account_id", "customer_id", "account_type", "branch", "account_status")),
          "account_id", "left")
    .join(F.broadcast(dim_customers.select(
            "customer_id", "segment", "risk_tier", "region")),
          "customer_id", "left")
    .withColumn("ingest_ts",     F.current_timestamp())
    .withColumn("source_system", F.lit("apex_core_banking"))
    .withColumn("batch_id",      F.lit(BATCH_ID))
)

# Write dims (small — no repartition)
dim_customers.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_dim_customers")
dim_accounts.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_dim_accounts")

# Write fact (repartition for downstream read performance)
(bronze.repartition(8)
    .write.format("delta")
    .mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_fact_transactions"))

print("✅ Bronze tables written")

# COMMAND ----------

# --- Validation (single pass) ---
for tbl in ["bronze_dim_customers", "bronze_dim_accounts", "bronze_fact_transactions"]:
    cnt = spark.table(f"{CATALOG}.{SCHEMA}.{tbl}").count()
    print(f"  {tbl}: {cnt:,}")

print("\nTransaction status distribution:")
(spark.table(f"{CATALOG}.{SCHEMA}.bronze_fact_transactions")
    .groupBy("txn_status").count().orderBy(F.desc("count")).show())
