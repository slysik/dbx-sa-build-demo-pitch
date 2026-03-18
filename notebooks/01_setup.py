# Databricks notebook source
# MAGIC %md
# MAGIC # Notebook 01 — Workspace Setup
# MAGIC
# MAGIC This notebook bootstraps the Unity Catalog objects and generates synthetic
# MAGIC sample data so the rest of the demo can run without any external data source.
# MAGIC
# MAGIC **Run once** before executing the other notebooks.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 0. Imports and configuration

# COMMAND ----------
import yaml
import random
import string
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    DoubleType, BooleanType, TimestampType,
)

spark = SparkSession.builder.getOrCreate()

# Load config from the repo (works both locally and in Databricks Repos)
import os

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "demo_config.yml",
)
with open(CONFIG_PATH) as fh:
    cfg = yaml.safe_load(fh)

CATALOG = cfg["catalog"]
SCHEMA  = cfg["schema"]
VOLUME  = cfg["volume"]
SEED    = cfg["sample_data"]["random_seed"]
N_CUST  = cfg["sample_data"]["num_customers"]
N_REV   = cfg["sample_data"]["num_reviews"]

print(f"catalog={CATALOG}  schema={SCHEMA}  volume={VOLUME}")
print(f"Generating {N_CUST} customers and {N_REV} reviews  (seed={SEED})")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Create Unity Catalog objects

# COMMAND ----------
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
spark.sql(f"USE SCHEMA {SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME}")

print("✅  Catalog, schema and volume are ready.")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Generate synthetic customer data

# COMMAND ----------
random.seed(SEED)

PRODUCTS       = ["Basic Plan", "Pro Plan", "Enterprise Plan"]
REGIONS        = ["North", "South", "East", "West"]
SUPPORT_TIERS  = ["Bronze", "Silver", "Gold"]

def _rand_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))

start_date = datetime(2022, 1, 1)
end_date   = datetime(2024, 12, 31)

customers = []
for i in range(N_CUST):
    signup     = _rand_date(start_date, end_date)
    churned    = random.random() < 0.25          # ~25 % churn rate
    last_login = _rand_date(signup, end_date) if not churned else _rand_date(signup, signup + timedelta(days=90))
    customers.append({
        "customer_id":       f"CUST{i:05d}",
        "signup_date":       signup,
        "last_login_date":   last_login,
        "product":           random.choice(PRODUCTS),
        "region":            random.choice(REGIONS),
        "support_tier":      random.choice(SUPPORT_TIERS),
        "monthly_spend":     round(random.uniform(10, 500), 2),
        "num_support_cases": random.randint(0, 20),
        "is_churned":        churned,
    })

schema_customers = StructType([
    StructField("customer_id",       StringType(),    False),
    StructField("signup_date",       TimestampType(), True),
    StructField("last_login_date",   TimestampType(), True),
    StructField("product",           StringType(),    True),
    StructField("region",            StringType(),    True),
    StructField("support_tier",      StringType(),    True),
    StructField("monthly_spend",     DoubleType(),    True),
    StructField("num_support_cases", IntegerType(),   True),
    StructField("is_churned",        BooleanType(),   True),
])

df_customers = spark.createDataFrame(customers, schema=schema_customers)
print(f"Customer rows: {df_customers.count()}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Generate synthetic review data

# COMMAND ----------
POSITIVE_PHRASES = [
    "Great product, very easy to use!",
    "Excellent support team, resolved my issue quickly.",
    "Highly recommend, worth every penny.",
    "Fantastic experience overall, will renew.",
    "The new features are game-changing.",
]
NEGATIVE_PHRASES = [
    "Very disappointed, the service keeps crashing.",
    "Support took too long to respond.",
    "Not worth the price, looking for alternatives.",
    "Billing issues that were never resolved.",
    "Too many bugs, extremely frustrating experience.",
]
NEUTRAL_PHRASES = [
    "It is okay, nothing special.",
    "Does what it says on the tin.",
    "Average experience, could be better.",
    "Some features are good, others need work.",
]

customer_ids = [c["customer_id"] for c in customers]
reviews = []
for i in range(N_REV):
    sentiment_roll = random.random()
    if sentiment_roll < 0.45:
        text, true_label = random.choice(POSITIVE_PHRASES), "positive"
    elif sentiment_roll < 0.75:
        text, true_label = random.choice(NEGATIVE_PHRASES), "negative"
    else:
        text, true_label = random.choice(NEUTRAL_PHRASES),  "neutral"

    # Add minor variation so each row is unique
    text += " " + "".join(random.choices(string.ascii_lowercase, k=3))

    reviews.append({
        "review_id":    f"REV{i:06d}",
        "customer_id":  random.choice(customer_ids),
        "review_text":  text,
        "true_sentiment": true_label,
        "review_date":  _rand_date(start_date, end_date),
        "rating":       random.randint(1, 5),
    })

schema_reviews = StructType([
    StructField("review_id",      StringType(),    False),
    StructField("customer_id",    StringType(),    True),
    StructField("review_text",    StringType(),    True),
    StructField("true_sentiment", StringType(),    True),
    StructField("review_date",    TimestampType(), True),
    StructField("rating",         IntegerType(),   True),
])

df_reviews = spark.createDataFrame(reviews, schema=schema_reviews)
print(f"Review rows: {df_reviews.count()}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Persist raw data to the UC Volume (CSV landing zone)

# COMMAND ----------
volume_path = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME}"

df_customers.write.mode("overwrite").option("header", True).csv(
    f"{volume_path}/customers"
)
df_reviews.write.mode("overwrite").option("header", True).csv(
    f"{volume_path}/reviews"
)

print(f"✅  Raw CSVs written to {volume_path}")
print("\nSetup complete — run 02_data_ingestion.py next.")
