# Databricks notebook source
# MAGIC %md
# MAGIC # Notebook 04 — ML Training with MLflow and AutoML
# MAGIC
# MAGIC Trains a **customer churn prediction** model using:
# MAGIC - Databricks **AutoML** (automated feature engineering + model selection)
# MAGIC - **MLflow** for experiment tracking, artefact logging and the model registry
# MAGIC
# MAGIC The model is then registered to Unity Catalog and tagged as the `champion` alias.

# COMMAND ----------
# MAGIC %md
# MAGIC ## 0. Imports and configuration

# COMMAND ----------
import os
import yaml
import mlflow
import mlflow.sklearn
from databricks import automl
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

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
EXPERIMENT    = cfg["mlflow"]["experiment_name"]
MODEL_NAME    = f"{CATALOG}.{SCHEMA}.{cfg['mlflow']['model_name']}"
MODEL_ALIAS   = cfg["mlflow"]["registered_model_alias"]

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment(EXPERIMENT)

print(f"Model registry target : {MODEL_NAME}")
print(f"Experiment            : {EXPERIMENT}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Prepare the feature matrix

# COMMAND ----------
FEATURE_COLS = [
    "tenure_days",
    "monthly_spend",
    "num_support_cases",
    "num_reviews",
    "avg_rating",
    "min_rating",
    "max_rating",
    "spend_per_day",
    "support_intensity",
    "is_pro_plan",
    "is_enterprise_plan",
    "is_gold_tier",
    "positive_reviews",
    "negative_reviews",
    "neutral_reviews",
    "sentiment_score",
]
TARGET_COL = "label"

df_model = (
    spark.table(TABLES["gold_customer_features"])
    .select(FEATURE_COLS + [TARGET_COL])
    .dropna()
)

# Train / test split (80/20, stratified by label)
df_train, df_test = df_model.randomSplit([0.8, 0.2], seed=42)
df_train = df_train.cache()
df_test  = df_test.cache()

print(f"Train rows : {df_train.count()}")
print(f"Test rows  : {df_test.count()}")
print(f"Churn rate : {df_model.agg(F.avg(TARGET_COL)).collect()[0][0]:.1%}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Run Databricks AutoML

# COMMAND ----------
summary = automl.classify(
    dataset           = df_train,
    target_col        = TARGET_COL,
    primary_metric    = "f1",
    timeout_minutes   = 10,   # Increase for a more thorough search
    experiment_name   = EXPERIMENT,
)

best_run = summary.best_trial
print(f"Best trial run ID : {best_run.mlflow_run_id}")
print(f"Best F1 (val)     : {best_run.metrics.get('val_f1_score', 'n/a'):.4f}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Evaluate best model on held-out test set

# COMMAND ----------
import sklearn.metrics as skm
import pandas as pd

model_uri = f"runs:/{best_run.mlflow_run_id}/model"
loaded_model = mlflow.sklearn.load_model(model_uri)

pdf_test = df_test.toPandas()
X_test   = pdf_test[FEATURE_COLS]
y_test   = pdf_test[TARGET_COL]

y_pred = loaded_model.predict(X_test)
y_prob = loaded_model.predict_proba(X_test)[:, 1]

report = skm.classification_report(y_test, y_pred, target_names=["retained", "churned"])
auc    = skm.roc_auc_score(y_test, y_prob)

print(report)
print(f"AUC-ROC: {auc:.4f}")

# Log test metrics back to the best run
with mlflow.start_run(run_id=best_run.mlflow_run_id):
    mlflow.log_metric("test_f1",      skm.f1_score(y_test, y_pred))
    mlflow.log_metric("test_auc_roc", auc)
    mlflow.log_metric("test_accuracy",skm.accuracy_score(y_test, y_pred))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Register model in Unity Catalog and assign champion alias

# COMMAND ----------
registered = mlflow.register_model(
    model_uri = model_uri,
    name      = MODEL_NAME,
)

client = mlflow.tracking.MlflowClient()
client.set_registered_model_alias(
    name    = MODEL_NAME,
    alias   = MODEL_ALIAS,
    version = registered.version,
)

print(f"✅  {MODEL_NAME} v{registered.version} registered as '{MODEL_ALIAS}'")
