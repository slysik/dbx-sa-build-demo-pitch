# Databricks notebook source
# MAGIC %md
# MAGIC # Notebook 02 — Data Ingestion (Bronze → Silver → Gold)
# MAGIC
# MAGIC Implements a three-layer Medallion Architecture on Delta Lake:
# MAGIC
# MAGIC | Layer | Content |
# MAGIC |---|---|
# MAGIC | **Bronze** | Raw CSV ingested as-is with audit columns |
# MAGIC | **Silver** | Cleansed, deduplicated, typed data |
# MAGIC | **Gold** | Feature-rich, analytics-ready table used by downstream ML |

# COMMAND ----------
# MAGIC %md
# MAGIC ## 0. Imports and configuration

# COMMAND ----------
import os
import sys
import yaml
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, BooleanType

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from utils import compute_support_intensity

spark = SparkSession.builder.getOrCreate()

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "demo_config.yml",
)
with open(CONFIG_PATH) as fh:
    cfg = yaml.safe_load(fh)

CATALOG  = cfg["catalog"]
SCHEMA   = cfg["schema"]
VOLUME   = cfg["volume"]
TABLES   = cfg["tables"]

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

volume_path = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"
print(f"Reading from {volume_path}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Bronze layer — raw ingest with audit columns

# COMMAND ----------

# ── Customers ────────────────────────────────────────────────────────────────
df_raw_customers = (
    spark.read.option("header", True).option("inferSchema", True)
    .csv(f"{volume_path}/customers")
)

df_bronze_customers = df_raw_customers.withColumn(
    "_ingested_at", F.current_timestamp()
).withColumn(
    "_source", F.lit(f"{volume_path}/customers")
)

df_bronze_customers.write.format("delta").mode("overwrite").saveAsTable(
    TABLES["bronze_customers"]
)
print(f"✅  bronze_customers: {df_bronze_customers.count()} rows")

# ── Reviews ──────────────────────────────────────────────────────────────────
df_raw_reviews = (
    spark.read.option("header", True).option("inferSchema", True)
    .csv(f"{volume_path}/reviews")
)

df_bronze_reviews = df_raw_reviews.withColumn(
    "_ingested_at", F.current_timestamp()
).withColumn(
    "_source", F.lit(f"{volume_path}/reviews")
)

df_bronze_reviews.write.format("delta").mode("overwrite").saveAsTable(
    TABLES["bronze_reviews"]
)
print(f"✅  bronze_reviews: {df_bronze_reviews.count()} rows")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Silver layer — cleansing and deduplication

# COMMAND ----------

# ── Customers ────────────────────────────────────────────────────────────────
df_silver_customers = (
    spark.table(TABLES["bronze_customers"])
    # Drop private audit columns for the public silver view
    .drop("_ingested_at", "_source")
    # Cast types that come back as strings from CSV inference
    .withColumn("monthly_spend",     F.col("monthly_spend").cast(DoubleType()))
    .withColumn("num_support_cases", F.col("num_support_cases").cast(IntegerType()))
    .withColumn("is_churned",        F.col("is_churned").cast(BooleanType()))
    # Normalise string columns
    .withColumn("product",       F.trim(F.col("product")))
    .withColumn("region",        F.trim(F.upper(F.col("region"))))
    .withColumn("support_tier",  F.trim(F.col("support_tier")))
    # Drop duplicates by primary key (keep latest)
    .dropDuplicates(["customer_id"])
    # Remove obviously invalid rows
    .filter(F.col("customer_id").isNotNull())
    .filter(F.col("monthly_spend") > 0)
)

df_silver_customers.write.format("delta").mode("overwrite").saveAsTable(
    TABLES["silver_customers"]
)
print(f"✅  silver_customers: {df_silver_customers.count()} rows")

# ── Reviews ──────────────────────────────────────────────────────────────────
df_silver_reviews = (
    spark.table(TABLES["bronze_reviews"])
    .drop("_ingested_at", "_source")
    .withColumn("rating", F.col("rating").cast(IntegerType()))
    .withColumn("review_text", F.trim(F.col("review_text")))
    .dropDuplicates(["review_id"])
    .filter(F.col("review_id").isNotNull())
    .filter(F.col("review_text").isNotNull() & (F.length(F.col("review_text")) > 5))
)

df_silver_reviews.write.format("delta").mode("overwrite").saveAsTable(
    TABLES["silver_reviews"]
)
print(f"✅  silver_reviews: {df_silver_reviews.count()} rows")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Gold layer — feature engineering for ML

# COMMAND ----------

# Aggregate review stats per customer
df_review_agg = (
    spark.table(TABLES["silver_reviews"])
    .groupBy("customer_id")
    .agg(
        F.count("review_id").alias("num_reviews"),
        F.avg("rating").alias("avg_rating"),
        F.min("rating").alias("min_rating"),
        F.max("rating").alias("max_rating"),
        F.countDistinct("review_date").alias("review_days"),
    )
)

# Join with customer data and compute tenure in days
compute_support_intensity_udf = F.udf(compute_support_intensity)

df_gold = (
    spark.table(TABLES["silver_customers"])
    .join(df_review_agg, on="customer_id", how="left")
    .fillna({"num_reviews": 0, "avg_rating": 3.0, "min_rating": 3, "max_rating": 3, "review_days": 0})
    .withColumn(
        "tenure_days",
        F.datediff(F.col("last_login_date"), F.col("signup_date")),
    )
    .withColumn(
        "spend_per_day",
        F.when(F.col("tenure_days") > 0, F.col("monthly_spend") / F.col("tenure_days"))
        .otherwise(F.col("monthly_spend")),
    )
    .withColumn(
        "support_intensity",
        compute_support_intensity_udf(
            F.col("num_support_cases").cast("int"),
            F.col("tenure_days").cast("int"),
        ),
    )
    # One-hot encode categorical features
    .withColumn("is_pro_plan",        (F.col("product") == "Pro Plan").cast("int"))
    .withColumn("is_enterprise_plan", (F.col("product") == "Enterprise Plan").cast("int"))
    .withColumn("is_gold_tier",       (F.col("support_tier") == "Gold").cast("int"))
    .withColumn("label",              F.col("is_churned").cast("int"))
)

df_gold.write.format("delta").mode("overwrite").saveAsTable(
    TABLES["gold_customer_features"]
)
print(f"✅  gold_customer_features: {df_gold.count()} rows")
display(df_gold.limit(5))
