# Databricks notebook source
# MAGIC %md
# MAGIC # Phase 4: Gold Layer — Business Aggregates + ML Features
# MAGIC
# MAGIC **What you'll learn:**
# MAGIC - Window functions and aggregations in PySpark
# MAGIC - Delta Lake optimization: Z-ORDER, OPTIMIZE, VACUUM
# MAGIC - Feature engineering for ML (fraud detection features)
# MAGIC - Delta time travel and versioning
# MAGIC
# MAGIC **FinServ context:** Gold layer serves two audiences:
# MAGIC 1. **Risk & Compliance** — merchant risk dashboards, suspicious activity reports (SARs)
# MAGIC 2. **Data Science** — feature tables for fraud detection models
# MAGIC
# MAGIC ```
# MAGIC Silver → Gold
# MAGIC          ├── merchant_risk_summary (BI/dashboards)
# MAGIC          ├── cardholder_features (ML fraud detection)
# MAGIC          └── hourly_volume_stats (operations monitoring)
# MAGIC ```

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

silver_df = spark.read.table("dbx_weg.silver.transactions")
print(f"Silver rows available: {silver_df.count():,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold Table 1: Merchant Risk Summary
# MAGIC
# MAGIC **Use case:** Risk analysts need merchant-level aggregates to
# MAGIC identify suspicious patterns. This is a classic BI/reporting table.

# COMMAND ----------

merchant_risk = (
    silver_df
    .groupBy("merchant_name", "mcc_category", "merchant_state", "is_high_risk_mcc")
    .agg(
        F.count("*").alias("total_transactions"),
        F.sum("amount").alias("total_volume"),
        F.avg("amount").alias("avg_ticket_size"),
        F.max("amount").alias("max_transaction"),
        F.countDistinct("cardholder_token").alias("unique_cardholders"),
        F.avg("risk_score_raw").alias("avg_risk_score"),
        F.sum(F.when(F.col("risk_score_raw") >= 50, 1).otherwise(0)).alias("high_risk_txns"),
        F.sum(F.when(F.col("is_online"), 1).otherwise(0)).alias("online_txns"),
        F.sum(F.when(F.col("is_international"), 1).otherwise(0)).alias("intl_txns"),
        F.sum(F.when(F.col("velocity_flag"), 1).otherwise(0)).alias("velocity_alerts"),
    )
    .withColumn("high_risk_pct",
        F.round(F.col("high_risk_txns") / F.col("total_transactions") * 100, 2))
    .withColumn("online_pct",
        F.round(F.col("online_txns") / F.col("total_transactions") * 100, 2))
)

# Write to Gold
merchant_risk.write.format("delta").mode("overwrite").saveAsTable(
    "dbx_weg.gold.merchant_risk_summary"
)

print(f"Merchant risk summary: {merchant_risk.count()} merchants")
display(
    merchant_risk
    .orderBy(F.desc("avg_risk_score"))
    .limit(20)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold Table 2: Cardholder Features (ML Feature Table)
# MAGIC
# MAGIC **Use case:** Feature engineering for fraud detection model.
# MAGIC Each row = one cardholder's behavioral profile.
# MAGIC
# MAGIC **FinServ ML features:**
# MAGIC - Spending velocity (avg transactions per hour)
# MAGIC - Amount distribution (mean, std, max)
# MAGIC - MCC diversity (how many categories)
# MAGIC - Online vs in-store ratio
# MAGIC - Geographic spread

# COMMAND ----------

# Window for cardholder-level features
cardholder_window = Window.partitionBy("cardholder_token")

cardholder_features = (
    silver_df
    .groupBy("cardholder_token")
    .agg(
        # Volume metrics
        F.count("*").alias("total_txns"),
        F.sum("amount").alias("total_spend"),
        F.avg("amount").alias("avg_amount"),
        F.stddev("amount").alias("std_amount"),
        F.max("amount").alias("max_amount"),
        F.min("amount").alias("min_amount"),

        # Behavioral patterns
        F.countDistinct("mcc_category").alias("mcc_diversity"),
        F.countDistinct("merchant_name").alias("merchant_diversity"),
        F.countDistinct("merchant_state").alias("geo_spread"),

        # Channel mix
        F.sum(F.when(F.col("is_online"), 1).otherwise(0)).alias("online_txns"),
        F.sum(F.when(~F.col("is_online"), 1).otherwise(0)).alias("instore_txns"),
        F.sum(F.when(F.col("is_international"), 1).otherwise(0)).alias("intl_txns"),

        # Risk indicators
        F.avg("risk_score_raw").alias("avg_risk_score"),
        F.max("risk_score_raw").alias("max_risk_score"),
        F.sum(F.when(F.col("velocity_flag"), 1).otherwise(0)).alias("velocity_alerts"),
        F.sum(F.when(F.col("amount_anomaly_flag"), 1).otherwise(0)).alias("amount_anomalies"),

        # Card mix
        F.countDistinct("card_type").alias("card_type_count"),
        F.countDistinct("card_network").alias("network_count"),

        # Time patterns
        F.min("event_timestamp").alias("first_seen"),
        F.max("event_timestamp").alias("last_seen"),
    )
    # Derived features
    .withColumn("online_ratio",
        F.round(F.col("online_txns") / F.col("total_txns"), 4))
    .withColumn("intl_ratio",
        F.round(F.col("intl_txns") / F.col("total_txns"), 4))
    .withColumn("avg_amount_per_merchant",
        F.round(F.col("total_spend") / F.col("merchant_diversity"), 2))
    .withColumn("coefficient_of_variation",
        F.round(F.col("std_amount") / F.col("avg_amount"), 4))
    # Target variable: flag cardholders with high risk indicators
    # In production, this comes from confirmed fraud labels
    .withColumn("is_suspicious",
        F.when(
            (F.col("avg_risk_score") >= 40) |
            (F.col("velocity_alerts") >= 2) |
            (F.col("amount_anomalies") >= 3),
            1
        ).otherwise(0))
)

# Write to Gold
cardholder_features.write.format("delta").mode("overwrite").saveAsTable(
    "dbx_weg.gold.cardholder_features"
)

print(f"Cardholder feature table: {cardholder_features.count()} cardholders")
print(f"Suspicious cardholders: {cardholder_features.filter(F.col('is_suspicious') == 1).count()}")

display(
    cardholder_features
    .orderBy(F.desc("avg_risk_score"))
    .limit(20)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold Table 3: Hourly Volume Stats (Operations)
# MAGIC
# MAGIC **Use case:** Operations team monitors transaction volume for
# MAGIC anomalies (system outages, DDoS, fraud rings).

# COMMAND ----------

hourly_stats = (
    silver_df
    .groupBy("event_date", "event_hour", "card_network", "mcc_category")
    .agg(
        F.count("*").alias("txn_count"),
        F.sum("amount").alias("total_volume"),
        F.avg("amount").alias("avg_amount"),
        F.countDistinct("cardholder_token").alias("unique_cardholders"),
        F.avg("risk_score_raw").alias("avg_risk"),
    )
)

hourly_stats.write.format("delta").mode("overwrite").saveAsTable(
    "dbx_weg.gold.hourly_volume_stats"
)

print(f"Hourly stats: {hourly_stats.count()} rows")
display(
    hourly_stats
    .orderBy("event_date", "event_hour")
    .limit(20)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step: Delta Lake Optimization
# MAGIC
# MAGIC **Z-ORDER:** Colocates related data for faster reads on common
# MAGIC filter columns. Critical for FinServ queries that always filter
# MAGIC by merchant, date, or cardholder.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Optimize + Z-ORDER: colocate data by common query patterns
# MAGIC OPTIMIZE dbx_weg.gold.merchant_risk_summary
# MAGIC ZORDER BY (mcc_category, merchant_state);
# MAGIC
# MAGIC OPTIMIZE dbx_weg.gold.cardholder_features
# MAGIC ZORDER BY (avg_risk_score, is_suspicious);
# MAGIC
# MAGIC OPTIMIZE dbx_weg.gold.hourly_volume_stats
# MAGIC ZORDER BY (event_date, card_network);

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Delta time travel: see the full write history
# MAGIC DESCRIBE HISTORY dbx_weg.gold.cardholder_features LIMIT 5;

# COMMAND ----------

# MAGIC %md
# MAGIC ## What You Just Learned (SA Talking Points)
# MAGIC
# MAGIC | Concept | What You Did | SA Value |
# MAGIC |---------|-------------|----------|
# MAGIC | Window Functions | Cardholder behavioral profiles | "PySpark window functions for entity-level feature engineering at scale" |
# MAGIC | Feature Engineering | 20+ features from raw transactions | "Gold layer isn't just aggregates — it's ML-ready feature tables" |
# MAGIC | Z-ORDER | Colocate data by query pattern | "10-100x scan reduction on filtered queries" |
# MAGIC | OPTIMIZE | Compact small files from streaming writes | "Essential after streaming — reduces file count, improves read perf" |
# MAGIC | Multi-audience Gold | Risk + ML features + Ops monitoring | "One pipeline serves BI, ML, and operations — no data duplication" |
# MAGIC | Risk Scoring | Multi-signal fraud indicators | "Combine velocity, amount, geography, MCC for composite risk" |
# MAGIC
# MAGIC **Next:** Phase 5 — Train a fraud detection model with MLflow.
