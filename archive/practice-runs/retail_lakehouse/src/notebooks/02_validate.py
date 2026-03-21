# Databricks notebook source

# MAGIC %md
# MAGIC # Retail Lakehouse — Validation
# MAGIC Runs after SDP pipeline completes. Checks row counts, duplicates, and nulls across all layers.

# COMMAND ----------

CATALOG = "interview"
SCHEMA = "retail"

# Row counts across all layers
tables = [
    "bronze_products", "bronze_stores", "bronze_transactions",
    "silver_transactions",
    "gold_sales_by_category", "gold_sales_by_store", "gold_daily_revenue"
]

print("📊 Row Counts Across Layers")
print("-" * 40)
for tbl in tables:
    try:
        cnt = spark.table(f"{CATALOG}.{SCHEMA}.{tbl}").count()
        print(f"  ✅ {tbl}: {cnt:,}")
    except Exception as e:
        print(f"  ❌ {tbl}: {e}")

# COMMAND ----------

# Duplicate check on Silver
dupes = spark.sql(f"""
    SELECT transaction_id, COUNT(*) AS cnt
    FROM {CATALOG}.{SCHEMA}.silver_transactions
    GROUP BY transaction_id HAVING cnt > 1
""")
dupe_count = dupes.count()
print(f"\n🔍 Silver Duplicate Check: {'✅ No duplicates' if dupe_count == 0 else f'❌ {dupe_count} duplicates found'}")

# COMMAND ----------

# Null audit on Silver
null_audit = spark.sql(f"""
    SELECT
      COUNT(*) AS total_rows,
      SUM(CASE WHEN transaction_id IS NULL THEN 1 ELSE 0 END) AS null_txn_ids,
      SUM(CASE WHEN product_id IS NULL THEN 1 ELSE 0 END) AS null_product_ids,
      SUM(CASE WHEN total_amount IS NULL THEN 1 ELSE 0 END) AS null_amounts
    FROM {CATALOG}.{SCHEMA}.silver_transactions
""")
display(null_audit)
print("✅ Validation complete")
