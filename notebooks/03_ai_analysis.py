# Databricks notebook source
# MAGIC %md
# MAGIC # Notebook 03 — AI Analysis with Databricks Foundation Model APIs
# MAGIC
# MAGIC Uses the Databricks Foundation Model APIs (LLM-as-a-service) to:
# MAGIC
# MAGIC 1. Classify the **sentiment** of every customer review (positive / negative / neutral)
# MAGIC 2. Enrich the Gold customer-features table with a `llm_sentiment` column
# MAGIC 3. Compare LLM predictions against the ground-truth labels generated in setup

# COMMAND ----------
# MAGIC %md
# MAGIC ## 0. Imports and configuration

# COMMAND ----------
import os
import json
import yaml
import requests
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from utils import normalise_sentiment, compute_sentiment_score

spark = SparkSession.builder.getOrCreate()

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "demo_config.yml",
)
with open(CONFIG_PATH) as fh:
    cfg = yaml.safe_load(fh)

CATALOG       = cfg["catalog"]
SCHEMA        = cfg["schema"]
TABLES        = cfg["tables"]
LLM_ENDPOINT  = cfg["llm"]["endpoint"]
MAX_TOKENS    = cfg["llm"]["max_tokens"]
TEMPERATURE   = cfg["llm"]["temperature"]

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

# Retrieve the Databricks host and token from the notebook context
try:
    ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()  # noqa: F821
    DATABRICKS_HOST  = "https://" + ctx.browserHostName().get()
    DATABRICKS_TOKEN = ctx.apiToken().get()
except Exception:
    # Fall back to environment variables (useful for local testing)
    DATABRICKS_HOST  = os.environ.get("DATABRICKS_HOST", "")
    DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN", "")

print(f"LLM endpoint : {LLM_ENDPOINT}")
print(f"Host         : {DATABRICKS_HOST}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Build a prompt-based sentiment classifier

# COMMAND ----------

SYSTEM_PROMPT = """You are a customer-sentiment classifier.
Classify the customer review below into exactly one of: positive, negative, neutral.
Reply with only the single word — no explanation, no punctuation."""

def classify_sentiment(review_text: str) -> str:
    """Call the Databricks Foundation Model API and return a sentiment label."""
    url = f"{DATABRICKS_HOST}/serving-endpoints/{LLM_ENDPOINT}/invocations"
    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": review_text},
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    raw = response.json()["choices"][0]["message"]["content"]
    return normalise_sentiment(raw)


# Register as a Spark UDF for distributed inference
classify_sentiment_udf = F.udf(classify_sentiment, StringType())

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Apply the classifier to a sample of reviews
# MAGIC
# MAGIC For the demo we cap at 200 rows to keep API costs and latency low.
# MAGIC Remove `.limit(200)` to score the full dataset.

# COMMAND ----------
SAMPLE_SIZE = 200

df_reviews = (
    spark.table(TABLES["silver_reviews"])
    .select("review_id", "customer_id", "review_text", "true_sentiment", "rating")
    .limit(SAMPLE_SIZE)
)

df_scored = df_reviews.withColumn(
    "llm_sentiment", classify_sentiment_udf(F.col("review_text"))
)

df_scored.cache()
print(f"Scored {df_scored.count()} reviews")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Evaluate accuracy vs ground-truth labels

# COMMAND ----------
df_eval = df_scored.withColumn(
    "correct", (F.col("llm_sentiment") == F.col("true_sentiment")).cast("int")
)

accuracy = df_eval.agg(F.avg("correct").alias("accuracy")).collect()[0]["accuracy"]
print(f"LLM sentiment accuracy: {accuracy:.1%}")

display(
    df_eval.groupBy("true_sentiment", "llm_sentiment")
    .count()
    .orderBy("true_sentiment", "llm_sentiment")
)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Persist sentiment-enriched data and join to Gold

# COMMAND ----------
df_scored.write.format("delta").mode("overwrite").saveAsTable("silver_reviews_scored")
print("✅  silver_reviews_scored written")

# Aggregate per-customer sentiment counts and join back to Gold
df_sentiment_agg = (
    df_scored.groupBy("customer_id")
    .agg(
        F.sum((F.col("llm_sentiment") == "positive").cast("int")).alias("positive_reviews"),
        F.sum((F.col("llm_sentiment") == "negative").cast("int")).alias("negative_reviews"),
        F.sum((F.col("llm_sentiment") == "neutral").cast("int")).alias("neutral_reviews"),
    )
)

compute_sentiment_score_udf = F.udf(compute_sentiment_score)

df_gold_enriched = (
    spark.table(TABLES["gold_customer_features"])
    .join(df_sentiment_agg, on="customer_id", how="left")
    .fillna({"positive_reviews": 0, "negative_reviews": 0, "neutral_reviews": 0})
    .withColumn(
        "sentiment_score",
        compute_sentiment_score_udf(
            F.col("positive_reviews").cast("int"),
            F.col("negative_reviews").cast("int"),
            F.col("neutral_reviews").cast("int"),
        ),
    )
)

df_gold_enriched.write.format("delta").mode("overwrite").saveAsTable(
    TABLES["gold_customer_features"]
)
print(f"✅  gold_customer_features enriched with LLM sentiment ({df_gold_enriched.count()} rows)")
display(df_gold_enriched.select(
    "customer_id", "positive_reviews", "negative_reviews", "neutral_reviews", "sentiment_score", "label"
).limit(10))
