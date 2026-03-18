# Databricks notebook source
# MAGIC %md
# MAGIC # Notebook 05 — Model Serving & Real-Time Inference
# MAGIC
# MAGIC Deploys the champion churn model to a **Databricks Model Serving** endpoint
# MAGIC and demonstrates real-time scoring via the REST API.
# MAGIC
# MAGIC Steps:
# MAGIC 1. Create (or update) the Model Serving endpoint
# MAGIC 2. Wait for the endpoint to become ready
# MAGIC 3. Score a sample of customers in real time
# MAGIC 4. Generate personalised retention recommendations using the LLM

# COMMAND ----------
# MAGIC %md
# MAGIC ## 0. Imports and configuration

# COMMAND ----------
import os
import json
import time
import yaml
import requests
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder.getOrCreate()

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "demo_config.yml",
)
with open(CONFIG_PATH) as fh:
    cfg = yaml.safe_load(fh)

CATALOG        = cfg["catalog"]
SCHEMA         = cfg["schema"]
TABLES         = cfg["tables"]
MODEL_NAME     = f"{CATALOG}.{SCHEMA}.{cfg['mlflow']['model_name']}"
MODEL_ALIAS    = cfg["mlflow"]["registered_model_alias"]
ENDPOINT_NAME  = cfg["serving"]["endpoint_name"]
WORKLOAD_SIZE  = cfg["serving"]["workload_size"]
SCALE_TO_ZERO  = cfg["serving"]["scale_to_zero"]
LLM_ENDPOINT   = cfg["llm"]["endpoint"]
MAX_TOKENS     = cfg["llm"]["max_tokens"]

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

# Databricks credentials from notebook context
try:
    ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()  # noqa: F821
    DATABRICKS_HOST  = "https://" + ctx.browserHostName().get()
    DATABRICKS_TOKEN = ctx.apiToken().get()
except Exception:
    DATABRICKS_HOST  = os.environ.get("DATABRICKS_HOST", "")
    DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {DATABRICKS_TOKEN}",
    "Content-Type": "application/json",
}

print(f"Endpoint  : {ENDPOINT_NAME}")
print(f"Model     : {MODEL_NAME}  alias={MODEL_ALIAS}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Create or update the Model Serving endpoint

# COMMAND ----------
def _get_model_version(name: str, alias: str) -> str:
    """Resolve a registered-model alias to a version number."""
    import mlflow
    mlflow.set_registry_uri("databricks-uc")
    client = mlflow.tracking.MlflowClient()
    return client.get_model_version_by_alias(name, alias).version


model_version = _get_model_version(MODEL_NAME, MODEL_ALIAS)
print(f"Deploying model version: {model_version}")

endpoint_config = {
    "name": ENDPOINT_NAME,
    "config": {
        "served_models": [
            {
                "model_name":             MODEL_NAME,
                "model_version":          model_version,
                "workload_size":          WORKLOAD_SIZE,
                "scale_to_zero_enabled":  SCALE_TO_ZERO,
            }
        ]
    },
}

# Check whether the endpoint already exists
existing = requests.get(
    f"{DATABRICKS_HOST}/api/2.0/serving-endpoints/{ENDPOINT_NAME}",
    headers=HEADERS,
)

if existing.status_code == 404:
    resp = requests.post(
        f"{DATABRICKS_HOST}/api/2.0/serving-endpoints",
        headers=HEADERS,
        json=endpoint_config,
    )
    resp.raise_for_status()
    print("✅  Endpoint created")
else:
    resp = requests.put(
        f"{DATABRICKS_HOST}/api/2.0/serving-endpoints/{ENDPOINT_NAME}/config",
        headers=HEADERS,
        json=endpoint_config["config"],
    )
    resp.raise_for_status()
    print("✅  Endpoint updated")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Wait for the endpoint to become ready

# COMMAND ----------
MAX_WAIT_SECS = 600
poll_interval = 15
elapsed = 0

while elapsed < MAX_WAIT_SECS:
    status_resp = requests.get(
        f"{DATABRICKS_HOST}/api/2.0/serving-endpoints/{ENDPOINT_NAME}",
        headers=HEADERS,
    )
    state = status_resp.json().get("state", {}).get("ready", "NOT_READY")
    print(f"[{elapsed:>4}s] endpoint state: {state}")
    if state == "READY":
        break
    time.sleep(poll_interval)
    elapsed += poll_interval
else:
    raise TimeoutError(f"Endpoint did not become READY within {MAX_WAIT_SECS}s")

print(f"✅  Endpoint ready after ~{elapsed}s")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Score customers in real time

# COMMAND ----------
FEATURE_COLS = [
    "tenure_days", "monthly_spend", "num_support_cases",
    "num_reviews", "avg_rating", "min_rating", "max_rating",
    "spend_per_day", "support_intensity",
    "is_pro_plan", "is_enterprise_plan", "is_gold_tier",
    "positive_reviews", "negative_reviews", "neutral_reviews", "sentiment_score",
]

# Include extra context columns for the LLM retention prompt (not used for scoring)
CONTEXT_COLS = ["product", "support_tier"]

df_sample = (
    spark.table(TABLES["gold_customer_features"])
    .select(["customer_id"] + FEATURE_COLS + CONTEXT_COLS + ["label"])
    .limit(10)
)

pdf_sample = df_sample.toPandas()

payload = {
    "dataframe_records": pdf_sample[FEATURE_COLS].to_dict(orient="records")
}

score_resp = requests.post(
    f"{DATABRICKS_HOST}/serving-endpoints/{ENDPOINT_NAME}/invocations",
    headers=HEADERS,
    json=payload,
    timeout=60,
)
score_resp.raise_for_status()

predictions = score_resp.json()["predictions"]
pdf_sample["churn_prediction"] = predictions
pdf_sample["churn_risk"] = pdf_sample["churn_prediction"].map({0: "Low", 1: "High"})

print("Real-time churn predictions:")
print(pdf_sample[["customer_id", "label", "churn_prediction", "churn_risk"]].to_string(index=False))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. LLM-generated personalised retention recommendations
# MAGIC
# MAGIC For each high-risk customer, call the Foundation Model API to generate a
# MAGIC tailored retention offer based on their profile.

# COMMAND ----------
RETENTION_SYSTEM_PROMPT = """You are a customer-success specialist at a SaaS company.
Given a customer's profile, write a concise (2-3 sentence) personalised retention message
that addresses their specific situation and offers a relevant incentive."""


def generate_retention_message(row: dict) -> str:
    prompt = (
        f"Customer profile:\n"
        f"  Product        : {row.get('product', 'unknown')}\n"
        f"  Monthly spend  : ${row.get('monthly_spend', 0):.2f}\n"
        f"  Tenure (days)  : {row.get('tenure_days', 0)}\n"
        f"  Support cases  : {row.get('num_support_cases', 0)}\n"
        f"  Avg review rating: {row.get('avg_rating', 3):.1f}/5\n"
        f"  Sentiment score: {row.get('sentiment_score', 0):.2f}\n"
        "\nWrite the personalised retention message:"
    )
    payload = {
        "messages": [
            {"role": "system", "content": RETENTION_SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.7,
    }
    resp = requests.post(
        f"{DATABRICKS_HOST}/serving-endpoints/{LLM_ENDPOINT}/invocations",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


high_risk = pdf_sample[pdf_sample["churn_prediction"] == 1].to_dict(orient="records")

print(f"\nGenerating retention messages for {len(high_risk)} high-risk customers...\n")
for row in high_risk:
    msg = generate_retention_message(row)
    print(f"Customer: {row['customer_id']}")
    print(f"  → {msg}\n")

print("✅  End-to-end demo complete!")
