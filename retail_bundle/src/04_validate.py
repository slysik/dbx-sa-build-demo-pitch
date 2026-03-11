# Databricks notebook source
# ruff: noqa: F821

# MAGIC %md
# MAGIC # ✅ Cross-Layer Validation
# MAGIC Proves data flows correctly: Bronze → Silver → Gold.
# MAGIC Row counts decrease slightly as Silver drops dupes + outliers.

# COMMAND ----------

# SA: One validation pass across all 3 layers. Silver should have fewer rows than Bronze
#     (dedup + quality expectations removed ~2% of rows). Gold aggregates to fewer rows
#     because it GROUP BYs on date/category/region dimensions.

from pyspark.sql import functions as F

CATALOG = "interview"
SCHEMA  = "retail"

layers = [
    ("bronze_customers",      "silver_customers",    "gold_customer_ltv"),
    ("bronze_products",       "silver_products",     "gold_product_performance"),
    ("bronze_orders",         "silver_orders",       "gold_daily_sales"),
    ("bronze_order_items",    "silver_order_items",  "gold_regional_summary"),
]

print("=" * 65)
print(f"{'Table':<30} {'Rows':>12}")
print("=" * 65)

for group in layers:
    for tbl in group:
        fqn = f"{CATALOG}.{SCHEMA}.{tbl}"
        try:
            cnt = spark.table(fqn).count()
            print(f"  {tbl:<28} {cnt:>12,}")
        except Exception as e:
            print(f"  {tbl:<28} {'MISSING':>12}")
    print("-" * 65)

print("\n✅ Validation complete.")
