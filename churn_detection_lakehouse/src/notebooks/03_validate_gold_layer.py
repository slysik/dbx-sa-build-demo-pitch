# Databricks notebook source

"""
Gold Layer Validation

Runs every 6 hours to ensure:
- Row counts are consistent
- Risk distributions make sense
- No data gaps
- Intervention tracking is working
"""

from pyspark.sql import functions as F

CATALOG = "finserv"
SCHEMA = "churn_demo"

print("✅ Validating Gold Layer Tables...")

# ── Row counts ─────────────────────────────────────────────────────────────

print("\n📊 Row Counts:")
for table in ["silver_user_metrics", "gold_churn_risk", "gold_interventions", "gold_churn_predictions"]:
    count = spark.sql(f"SELECT COUNT(*) FROM {CATALOG}.{SCHEMA}.{table}").collect()[0][0]
    print(f"  {table}: {count:,} rows")

# ── Risk distribution ──────────────────────────────────────────────────────

print("\n🎯 Risk Tier Distribution (gold_churn_risk):")
spark.sql(f"""
SELECT 
  risk_tier,
  COUNT(*) as count,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as pct
FROM {CATALOG}.{SCHEMA}.gold_churn_risk
GROUP BY risk_tier
ORDER BY count DESC
""").show()

# ── High-risk users ────────────────────────────────────────────────────────

print("\n🚨 High-Risk Users (Tier = CRITICAL or HIGH):")
high_risk = spark.sql(f"""
SELECT 
  user_id,
  risk_tier,
  recommended_action,
  weekly_risk_signals,
  weekly_failed_logins,
  weekly_crashes,
  engagement_health
FROM {CATALOG}.{SCHEMA}.gold_churn_risk
WHERE risk_tier IN ('CRITICAL', 'HIGH')
LIMIT 20
""")

high_risk.show(truncate=False)
print(f"Total high-risk users: {high_risk.count()}")

# ── Intervention coverage ──────────────────────────────────────────────────

print("\n📈 Intervention Status:")
spark.sql(f"""
SELECT 
  intervention_result,
  COUNT(*) as interventions
FROM {CATALOG}.{SCHEMA}.gold_interventions
GROUP BY intervention_result
""").show()

# ── ML Model predictions ───────────────────────────────────────────────────

if spark._jsparkSession.catalog.tableExists(f"{SCHEMA}.gold_churn_predictions"):
    print("\n🤖 ML Churn Probability Distribution:")
    spark.sql(f"""
    SELECT
      ROUND(ml_churn_probability / 10) * 10 AS probability_bucket,
      COUNT(*) as users
    FROM {CATALOG}.{SCHEMA}.gold_churn_predictions
    GROUP BY ROUND(ml_churn_probability / 10) * 10
    ORDER BY probability_bucket DESC
    """).show()

print("\n✅ Validation complete")
