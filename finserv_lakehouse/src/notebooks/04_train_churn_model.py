# Databricks notebook source

# COMMAND ----------
# %md
# # Apex Banking — Churn Prediction Model
#
# **The connection:** Reads from `gold_rfm_features` — the feature store built
# by the SDP pipeline from transaction history + AI-scored CRM notes.
# Data foundation feeds the ML layer directly.
#
# **Output:** `gold_churn_predictions` — churn probability per customer,
# consumed by the dashboard and Genie Space.
#
# **In production:** wrap `pipe.fit()` in `mlflow.start_run()` for full
# experiment tracking, model versioning, and drift monitoring.
# Same model, one additional context manager.

# COMMAND ----------
import pandas as pd
import pyspark.sql.functions as F
import pyspark.sql.types     as T
from sklearn.linear_model    import LogisticRegression
from sklearn.preprocessing   import StandardScaler
from sklearn.pipeline        import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics         import roc_auc_score

CATALOG = "finserv"
SCHEMA  = "banking"

# COMMAND ----------
# %md ## Load features from Gold layer

# COMMAND ----------
features_pd = spark.table(f"{CATALOG}.{SCHEMA}.gold_rfm_features").toPandas()
print(f"Customers: {len(features_pd):,}")
print(features_pd[["customer_id","txn_count","days_since_last_txn",
                    "complaint_count","avg_sentiment_score"]].head(5).to_string())

# COMMAND ----------
# %md ## Label, train, evaluate

# COMMAND ----------
# At-risk label: 2+ complaints OR any escalation OR negative sentiment
# (days_since_last_txn excluded — all transactions predate 90-day window in demo data)
# Production: labels come from historical closed-account records
features_pd["label"] = (
    (features_pd["complaint_count"]   >= 2)    |
    (features_pd["escalation_count"]  >= 1)    |
    (features_pd["avg_sentiment_score"] < -0.3)
).astype(int)

print(f"At-risk:  {features_pd['label'].sum():,}  ({features_pd['label'].mean()*100:.0f}%)")
print(f"Low-risk: {(features_pd['label']==0).sum():,}")

FEATURES = [
    "txn_count",            # How often do they use us?
    "days_since_last_txn",  # How recently?
    "complaint_count",      # How many complaints?
    "escalation_count",     # Did it escalate?
    "avg_sentiment_score",  # What does AI say about how they feel?
]

X = features_pd[FEATURES].fillna(0)
y = features_pd["label"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("lr",     LogisticRegression(max_iter=200, C=5, random_state=42)),
])
pipe.fit(X_train, y_train)

auc = roc_auc_score(y_test, pipe.predict_proba(X_test)[:, 1])
print(f"\n  AUC: {auc:.4f}")
print(f"  Features: {FEATURES}")
print(f"  In production: log with mlflow.start_run() → register in UC Model Registry → serve as SQL UDF")

# COMMAND ----------
# %md ## Score all customers → write to Gold

# COMMAND ----------
features_pd["churn_probability"] = pipe.predict_proba(X)[:, 1]
features_pd["churn_tier"] = features_pd["churn_probability"].apply(
    lambda p: "HIGH" if p >= 0.65 else ("MEDIUM" if p >= 0.35 else "LOW")
)
features_pd["scored_at"] = pd.Timestamp.now()

scored = spark.createDataFrame(
    features_pd[["customer_id", "churn_probability", "churn_tier", "scored_at"]]
)

(scored
    .write.format("delta")
    .mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA}.gold_churn_predictions"))

scored.groupBy("churn_tier").count().orderBy("churn_tier").show()
print(f"✓ gold_churn_predictions: {scored.count():,} customers scored  |  AUC: {auc:.4f}")

# COMMAND ----------
# %md ## AI Enrichment — Customer Interaction Summaries
# ai_summarize + COLLECT_LIST is non-deterministic → rejected in SDP Materialized Views.
# Running here in a notebook — no determinism constraint. Same result, right place.

# COMMAND ----------
ai_summary = spark.sql(f"""
  SELECT
    customer_id,
    COUNT(*)                                                              AS total_interactions,
    SUM(CASE WHEN interaction_category = 'complaint'  THEN 1 ELSE 0 END) AS complaint_count,
    SUM(CASE WHEN interaction_category = 'escalation' THEN 1 ELSE 0 END) AS escalation_count,
    MAX(interaction_date)                                                 AS last_interaction_date,
    ai_summarize(CONCAT_WS('. ', COLLECT_LIST(note_text)), 50)           AS interaction_summary
  FROM {CATALOG}.{SCHEMA}.silver_interactions
  GROUP BY customer_id
""")

(ai_summary
    .write.format("delta")
    .mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA}.gold_customer_ai_summary"))

print(f"✓ gold_customer_ai_summary enriched: {ai_summary.count():,} AI briefs")
ai_summary.select("customer_id","complaint_count","interaction_summary").show(3, truncate=80)
