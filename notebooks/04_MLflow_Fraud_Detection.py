# Databricks notebook source
# MAGIC %md
# MAGIC # Phase 5: MLflow — Fraud Detection Model
# MAGIC
# MAGIC **What you'll learn:**
# MAGIC - MLflow experiment tracking (params, metrics, artifacts)
# MAGIC - Model training with scikit-learn on Gold features
# MAGIC - MLflow Model Registry for versioning
# MAGIC - Batch inference: score predictions back to Delta
# MAGIC
# MAGIC **FinServ context:** Fraud detection is THE #1 ML use case in
# MAGIC financial services. Every bank, payment processor, and FinTech
# MAGIC needs it. This demonstrates the full lifecycle:
# MAGIC
# MAGIC ```
# MAGIC Gold Features → Train (MLflow) → Register → Score → Delta
# MAGIC                  ↑ experiment tracking     ↑ batch inference
# MAGIC ```
# MAGIC
# MAGIC **SA demo value:** Shows the customer that Databricks unifies
# MAGIC data engineering AND ML on one platform — no separate ML infra.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Load Features from Gold

# COMMAND ----------

import mlflow
import mlflow.sklearn
from pyspark.sql import functions as F
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, confusion_matrix,
                             classification_report)
from sklearn.preprocessing import StandardScaler
import pandas as pd
import numpy as np

# Load the cardholder feature table from Gold
features_df = spark.read.table("dbx_weg.gold.cardholder_features").toPandas()
print(f"Loaded {len(features_df):,} cardholders from Gold")
print(f"Suspicious: {features_df['is_suspicious'].sum()} ({features_df['is_suspicious'].mean()*100:.1f}%)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Prepare Features for ML
# MAGIC
# MAGIC **Feature selection rationale (FinServ domain):**
# MAGIC - Spending patterns: avg, std, max amounts
# MAGIC - Behavioral diversity: MCC categories, merchants, geography
# MAGIC - Channel risk: online ratio, international ratio
# MAGIC - Velocity indicators: alerts, anomalies

# COMMAND ----------

# Select ML features (exclude identifiers and target)
feature_cols = [
    "total_txns", "total_spend", "avg_amount", "std_amount",
    "max_amount", "min_amount",
    "mcc_diversity", "merchant_diversity", "geo_spread",
    "online_txns", "instore_txns", "intl_txns",
    "avg_risk_score", "max_risk_score",
    "velocity_alerts", "amount_anomalies",
    "card_type_count", "network_count",
    "online_ratio", "intl_ratio",
    "avg_amount_per_merchant", "coefficient_of_variation",
]
target_col = "is_suspicious"

# Clean data
ml_df = features_df[feature_cols + [target_col]].dropna()
print(f"ML dataset: {len(ml_df)} rows, {len(feature_cols)} features")
print(f"Class balance: {ml_df[target_col].value_counts().to_dict()}")

# Handle single-class edge case: if all labels are the same (common with
# small/synthetic datasets), create a risk-based label using median split
# on avg_risk_score. In production, use confirmed fraud labels from investigations.
if ml_df[target_col].nunique() < 2:
    print("\n*** Single class detected — creating risk-based label from avg_risk_score ***")
    print("*** In production, use confirmed fraud labels from case management ***")
    median_risk = ml_df["avg_risk_score"].median()
    ml_df["is_suspicious"] = (ml_df["avg_risk_score"] > median_risk).astype(int)
    print(f"New class balance (median split at {median_risk:.1f}): {ml_df[target_col].value_counts().to_dict()}")

X = ml_df[feature_cols]
y = ml_df[target_col]

# Train/test split (stratified to preserve class balance)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Train: {len(X_train)}, Test: {len(X_test)}")

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Train Model 1 — Gradient Boosting (with MLflow)
# MAGIC
# MAGIC **Key MLflow concepts:**
# MAGIC - `mlflow.start_run()` — creates an experiment run
# MAGIC - `mlflow.log_param()` — log hyperparameters
# MAGIC - `mlflow.log_metric()` — log performance metrics
# MAGIC - `mlflow.log_artifact()` — log files (charts, reports)
# MAGIC - `mlflow.sklearn.log_model()` — serialize + log the model

# COMMAND ----------

# Set MLflow experiment
# NOTE: On serverless, mlflow uses the workspace-level tracking server.
# The experiment path must be under your user namespace.
experiment_name = "/Users/slysik@gmail.com/finserv-fraud-detection"
try:
    mlflow.set_experiment(experiment_name)
    print(f"MLflow experiment: {experiment_name}")
except Exception as e:
    print(f"Could not set experiment (using default): {e}")
    # Fall back to default experiment

# COMMAND ----------

# Train Gradient Boosting model
with mlflow.start_run(run_name="gradient_boosting_v1") as run:
    # Log parameters
    params = {
        "n_estimators": 100,
        "max_depth": 5,
        "learning_rate": 0.1,
        "random_state": 42,
        "model_type": "GradientBoostingClassifier",
    }
    mlflow.log_params(params)
    mlflow.log_param("feature_count", len(feature_cols))
    mlflow.log_param("training_rows", len(X_train))
    mlflow.log_param("test_rows", len(X_test))
    mlflow.log_param("features", ", ".join(feature_cols))

    # Train
    gb_model = GradientBoostingClassifier(**{k: v for k, v in params.items()
                                             if k != "model_type" and k != "feature_count"
                                             and k != "training_rows" and k != "test_rows"
                                             and k != "features"})
    gb_model.fit(X_train_scaled, y_train)

    # Predict
    y_pred = gb_model.predict(X_test_scaled)
    y_prob = gb_model.predict_proba(X_test_scaled)[:, 1]

    # Log metrics
    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "auc_roc": roc_auc_score(y_test, y_prob) if len(set(y_test)) > 1 else 0,
    }
    mlflow.log_metrics(metrics)

    # Log feature importance as artifact
    importance_df = pd.DataFrame({
        "feature": feature_cols,
        "importance": gb_model.feature_importances_
    }).sort_values("importance", ascending=False)
    importance_df.to_csv("/tmp/gb_feature_importance.csv", index=False)
    mlflow.log_artifact("/tmp/gb_feature_importance.csv")

    # Log classification report
    report = classification_report(y_test, y_pred)
    with open("/tmp/gb_classification_report.txt", "w") as f:
        f.write(report)
    mlflow.log_artifact("/tmp/gb_classification_report.txt")

    # Log the model
    mlflow.sklearn.log_model(
        gb_model, "fraud_model",
        input_example=X_train.iloc[:5]
    )

    gb_run_id = run.info.run_id
    print(f"=== Gradient Boosting Results ===")
    print(f"Run ID: {gb_run_id}")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")
    print(f"\nTop features:")
    print(importance_df.head(10).to_string(index=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Train Model 2 — Random Forest (compare in MLflow)
# MAGIC
# MAGIC **SA talking point:** "MLflow makes model comparison trivial.
# MAGIC Train multiple models, compare metrics side-by-side, promote
# MAGIC the best one to the registry. No spreadsheets."

# COMMAND ----------

with mlflow.start_run(run_name="random_forest_v1") as run:
    params_rf = {
        "n_estimators": 200,
        "max_depth": 8,
        "random_state": 42,
        "model_type": "RandomForestClassifier",
        "class_weight": "balanced",
    }
    mlflow.log_params(params_rf)
    mlflow.log_param("feature_count", len(feature_cols))
    mlflow.log_param("training_rows", len(X_train))

    rf_model = RandomForestClassifier(
        n_estimators=200, max_depth=8, random_state=42, class_weight="balanced"
    )
    rf_model.fit(X_train_scaled, y_train)

    y_pred_rf = rf_model.predict(X_test_scaled)
    y_prob_rf = rf_model.predict_proba(X_test_scaled)[:, 1]

    metrics_rf = {
        "accuracy": accuracy_score(y_test, y_pred_rf),
        "precision": precision_score(y_test, y_pred_rf, zero_division=0),
        "recall": recall_score(y_test, y_pred_rf, zero_division=0),
        "f1": f1_score(y_test, y_pred_rf, zero_division=0),
        "auc_roc": roc_auc_score(y_test, y_prob_rf) if len(set(y_test)) > 1 else 0,
    }
    mlflow.log_metrics(metrics_rf)

    mlflow.sklearn.log_model(
        rf_model, "fraud_model",
        input_example=X_train.iloc[:5]
    )

    rf_run_id = run.info.run_id
    print(f"=== Random Forest Results ===")
    print(f"Run ID: {rf_run_id}")
    for k, v in metrics_rf.items():
        print(f"  {k}: {v:.4f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Compare Models + Register Best

# COMMAND ----------

# Compare the two models
print("=" * 60)
print("MODEL COMPARISON")
print("=" * 60)
print(f"{'Metric':<15} {'Gradient Boost':>15} {'Random Forest':>15}")
print("-" * 45)
for metric in ["accuracy", "precision", "recall", "f1", "auc_roc"]:
    gb_val = metrics.get(metric, 0)
    rf_val = metrics_rf.get(metric, 0)
    winner = " ← best" if gb_val >= rf_val else ""
    winner2 = " ← best" if rf_val > gb_val else ""
    print(f"{metric:<15} {gb_val:>14.4f}{winner}  {rf_val:>14.4f}{winner2}")

# Determine best model by F1 score (balances precision + recall for fraud)
best_run_id = gb_run_id if metrics["f1"] >= metrics_rf["f1"] else rf_run_id
best_model_name = "GradientBoosting" if best_run_id == gb_run_id else "RandomForest"
print(f"\nBest model (by F1): {best_model_name}")

# COMMAND ----------

# Register best model to MLflow Model Registry
# NOTE: On serverless, UC model registry may require additional catalog permissions.
# We try registration first; if it fails, we fall back to run-based model loading.
model_uri = f"runs:/{best_run_id}/fraud_model"
model_name = "finserv-fraud-detection"
registered_version = None

try:
    registered = mlflow.register_model(model_uri, model_name)
    registered_version = registered.version
    print(f"Registered model: {model_name}")
    print(f"Version: {registered.version}")
    print(f"Source run: {best_run_id}")
except Exception as e:
    print(f"Model registry unavailable (common on serverless trials): {e}")
    print(f"Using run-based model URI instead: {model_uri}")
    print("In production with full UC permissions, registration would succeed.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Batch Inference — Score All Cardholders
# MAGIC
# MAGIC **Use case:** Nightly batch scoring to flag suspicious accounts.
# MAGIC Results written back to Delta for downstream consumption
# MAGIC (compliance dashboards, case management systems).

# COMMAND ----------

# Load the best model (from registry if available, else from run)
if registered_version:
    load_uri = f"models:/{model_name}/{registered_version}"
else:
    load_uri = model_uri
print(f"Loading model from: {load_uri}")
loaded_model = mlflow.sklearn.load_model(load_uri)

# Score all cardholders
all_features = spark.read.table("dbx_weg.gold.cardholder_features").toPandas()
X_all = all_features[feature_cols].fillna(0)
X_all_scaled = scaler.transform(X_all)

# Get predictions + probabilities
all_features["fraud_prediction"] = loaded_model.predict(X_all_scaled)
all_features["fraud_probability"] = loaded_model.predict_proba(X_all_scaled)[:, 1]
all_features["model_version"] = int(registered_version) if registered_version else 0
all_features["scored_at"] = pd.Timestamp.now()

# Write scored predictions to Gold
scored_df = spark.createDataFrame(all_features)
scored_df.write.format("delta").mode("overwrite").saveAsTable(
    "dbx_weg.gold.fraud_predictions"
)

print(f"Scored {len(all_features):,} cardholders")
print(f"Flagged as suspicious: {all_features['fraud_prediction'].sum()}")
print(f"Mean fraud probability: {all_features['fraud_probability'].mean():.4f}")

# Show highest risk cardholders
display(
    spark.read.table("dbx_weg.gold.fraud_predictions")
    .select("cardholder_token", "total_txns", "total_spend",
            "avg_risk_score", "fraud_prediction", "fraud_probability",
            "model_version", "scored_at")
    .orderBy(F.desc("fraud_probability"))
    .limit(20)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## What You Just Learned (SA Talking Points)
# MAGIC
# MAGIC | Concept | What You Did | SA Value |
# MAGIC |---------|-------------|----------|
# MAGIC | MLflow Tracking | Logged params, metrics, artifacts for 2 models | "Complete experiment reproducibility — no more 'which model was that?'" |
# MAGIC | Model Comparison | Side-by-side F1/AUC/precision/recall | "Data scientists compare experiments in the UI, not spreadsheets" |
# MAGIC | Model Registry | Registered best model with versioning | "Governed model lifecycle — dev → staging → prod with approval gates" |
# MAGIC | Batch Inference | Scored all cardholders, wrote to Delta | "ML predictions are first-class data — queryable, versioned, governed" |
# MAGIC | End-to-End | Kafka → Bronze → Silver → Gold → ML → Predictions | "One platform: data engineering + analytics + ML. No integration tax." |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## Full Pipeline Summary (Interview Whiteboard)
# MAGIC
# MAGIC ```
# MAGIC Card Networks    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
# MAGIC POS Terminals ──→│  BRONZE  │─→│  SILVER  │─→│   GOLD   │─→│  MLflow  │
# MAGIC Mobile Wallets   │ Raw/ACID │  │ PII Mask │  │ Features │  │  Models  │
# MAGIC                  │ Audit    │  │ Validate │  │ Aggregates│ │ Registry │
# MAGIC                  └──────────┘  └──────────┘  └──────────┘  └────┬─────┘
# MAGIC                                                                  │
# MAGIC                  Unity Catalog: governance, lineage, RBAC       │
# MAGIC                  ─────────────────────────────────────────      │
# MAGIC                                                                  ▼
# MAGIC                  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐
# MAGIC                  │  DBSQL   │  │ Power BI │  │  Fraud Predictions   │
# MAGIC                  │Dashboard │  │DirectQuery│  │  (Delta Gold table)  │
# MAGIC                  └──────────┘  └──────────┘  └──────────────────────┘
# MAGIC ```
# MAGIC
# MAGIC **Key FinServ value props:**
# MAGIC - **Regulatory compliance:** Immutable Bronze audit trail, PII masking in Silver
# MAGIC - **Real-time + batch:** Same Spark API, different trigger modes
# MAGIC - **Unified platform:** Data eng + ML + governance = no integration tax
# MAGIC - **Open formats:** Delta Lake = no vendor lock-in on your data
