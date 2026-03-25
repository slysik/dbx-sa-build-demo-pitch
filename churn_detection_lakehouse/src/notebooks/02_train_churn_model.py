# Databricks notebook source

"""
ML Training: Churn Prediction Model

LogisticRegression on user engagement features.
Trained weekly, results exported to gold_churn_predictions table for scoring.
"""

from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.classification import LogisticRegression
import pyspark.sql.functions as F
from pyspark.sql.types import DoubleType
import mlflow
import mlflow.spark

CATALOG = "finserv"
SCHEMA = "churn_demo"

print("🤖 Training Churn Prediction Model...")

# ── Prepare Training Data ──────────────────────────────────────────────────

# Label: Churn if user had no transactions in past 2 weeks AND had risk signals
train_df = spark.sql(f"""
SELECT
  m.user_id,
  
  -- Features (all weekly metrics)
  m.weekly_app_opens,
  m.weekly_transactions,
  m.weekly_risk_signals,
  m.weekly_failed_logins,
  m.weekly_crashes,
  m.weekly_support_calls,
  m.days_since_last_event,
  
  -- Label: 1 if at-risk, 0 otherwise
  CASE
    WHEN m.engagement_health IN ('DORMANT', 'AT_RISK') OR m.weekly_risk_signals >= 2 THEN 1
    ELSE 0
  END AS churn_risk_label
  
FROM {CATALOG}.{SCHEMA}.silver_user_metrics m
WHERE m.metric_week >= CURRENT_DATE() - INTERVAL 8 WEEKS
  AND m.weekly_app_opens + m.weekly_transactions > 0  -- Exclude completely inactive
""")

print(f"Training samples: {train_df.count()}")
print(f"Churn distribution:")
train_df.groupBy("churn_risk_label").count().show()

# ── Feature Engineering ────────────────────────────────────────────────────

feature_cols = [
    "weekly_app_opens",
    "weekly_transactions",
    "weekly_risk_signals",
    "weekly_failed_logins",
    "weekly_crashes",
    "weekly_support_calls",
    "days_since_last_event"
]

# Feature vector assembly
assembler = VectorAssembler(inputCols=feature_cols, outputCol="features")
scaler = StandardScaler(inputCol="features", outputCol="scaled_features")

# Logistic Regression
lr = LogisticRegression(
    featuresCol="scaled_features",
    labelCol="churn_risk_label",
    maxIter=100,
    regParam=0.01,
    elasticNetParam=0.5
)

pipeline = Pipeline(stages=[assembler, scaler, lr])

# ── Train Model ────────────────────────────────────────────────────────────

with mlflow.start_run(run_name="churn_prediction_weekly"):
    mlflow.set_tag("model_type", "LogisticRegression")
    mlflow.set_tag("feature_count", len(feature_cols))
    
    model = pipeline.fit(train_df)
    
    # Get training metrics
    train_summary = model.stages[-1].summary
    mlflow.log_metric("accuracy", train_summary.accuracy)
    mlflow.log_metric("areaUnderROC", train_summary.areaUnderROC)
    mlflow.log_metric("areaUnderPR", train_summary.areaUnderPR)
    
    print(f"\n✅ Model trained:")
    print(f"   Accuracy: {train_summary.accuracy:.3f}")
    print(f"   AUC-ROC: {train_summary.areaUnderROC:.3f}")
    print(f"   AUC-PR: {train_summary.areaUnderPR:.3f}")
    
    # Register model
    mlflow.spark.log_model(model, "churn_model", registered_model_name="churn_prediction_model")

# ── Score all users for real-time predictions ──────────────────────────────

print("\n📊 Generating predictions for all users...")

scoring_df = spark.sql(f"""
SELECT
  m.user_id,
  m.metric_week,
  m.weekly_app_opens,
  m.weekly_transactions,
  m.weekly_risk_signals,
  m.weekly_failed_logins,
  m.weekly_crashes,
  m.weekly_support_calls,
  m.days_since_last_event
FROM {CATALOG}.{SCHEMA}.silver_user_metrics m
WHERE m.metric_week = DATE_TRUNC('WEEK', CURRENT_DATE())
""")

predictions = model.transform(scoring_df)

# Extract churn probability (probability of class 1)
from pyspark.ml.linalg import DenseVector

def extract_prob_1(v):
    """Extract probability of churn class"""
    if v is None:
        return None
    return float(v[1])

prob_udf = F.udf(extract_prob_1, DoubleType())

predictions_final = predictions.select(
    F.col("user_id"),
    F.col("metric_week"),
    (prob_udf(F.col("probability")) * 100).alias("ml_churn_probability"),  # 0-100 scale
    F.col("prediction").alias("ml_churn_class")  # 0 or 1
)

# Write predictions to gold table
predictions_final.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(f"{CATALOG}.{SCHEMA}.gold_churn_predictions")

print(f"✓ Predictions written to gold_churn_predictions")
print(f"\nChurn probability distribution:")
predictions_final.select("ml_churn_probability").describe().show()

print("\n✅ ML training pipeline complete")
