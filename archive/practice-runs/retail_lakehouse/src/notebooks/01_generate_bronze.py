# Databricks notebook source

# MAGIC %md
# MAGIC # Retail Bronze — Synthetic Data Generation
# MAGIC
# MAGIC | Table | Rows | Method |
# MAGIC |-------|------|--------|
# MAGIC | `bronze_products` | 200 | `spark.range()` dim |
# MAGIC | `bronze_stores` | 50 | `spark.range()` dim |
# MAGIC | `bronze_transactions` | 100,000 | `spark.range()` fact + broadcast join |
# MAGIC
# MAGIC **Pattern:** Distributed generation via `spark.range()` — same code scales 100 → 1M by changing one param.

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG  = "interview"
SCHEMA   = "retail"
BATCH_ID = "batch_001"

N_PRODUCTS     = 200
N_STORES       = 50
N_TRANSACTIONS = 100_000  # ← change this to scale

START_DATE = "2025-01-01"
DAYS_SPAN  = 365

print(f"Target: {CATALOG}.{SCHEMA} | Transactions: {N_TRANSACTIONS:,}")

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"Schema {CATALOG}.{SCHEMA} ready")

# COMMAND ----------

# --- Dimension: Products (200 rows, 6 cols) ---
products = (
    spark.range(N_PRODUCTS)
    .withColumn("product_id", F.concat(F.lit("PRD-"), F.lpad(F.col("id").cast("string"), 5, "0")))
    .withColumn("_r", F.rand(seed=1))
    .withColumn("category",
        F.when(F.col("_r") < 0.25, "Electronics")
         .when(F.col("_r") < 0.45, "Clothing")
         .when(F.col("_r") < 0.60, "Grocery")
         .when(F.col("_r") < 0.75, "Home & Garden")
         .when(F.col("_r") < 0.85, "Sports")
         .otherwise("Books"))
    .withColumn("brand",
        F.concat(F.lit("Brand_"), F.lpad((F.col("id") % 30).cast("string"), 2, "0")))
    .withColumn("unit_price", F.round(F.rand(seed=42) * 200 + 5, 2))
    .withColumn("product_name",
        F.concat(F.col("category"), F.lit(" Item "), F.col("id").cast("string")))
    .drop("id", "_r")
)

products.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_products")
display(products.limit(5))

# COMMAND ----------

# --- Dimension: Stores (50 rows, 5 cols) ---
stores = (
    spark.range(N_STORES)
    .withColumn("store_id", F.concat(F.lit("STR-"), F.lpad(F.col("id").cast("string"), 4, "0")))
    .withColumn("region",
        F.when(F.col("id") % 5 == 0, "Northeast")
         .when(F.col("id") % 5 == 1, "Southeast")
         .when(F.col("id") % 5 == 2, "Midwest")
         .when(F.col("id") % 5 == 3, "Southwest")
         .otherwise("West"))
    .withColumn("store_format",
        F.when(F.col("id") % 3 == 0, "Superstore")
         .when(F.col("id") % 3 == 1, "Express")
         .otherwise("Standard"))
    .withColumn("city",
        F.concat(F.lit("City_"), F.lpad((F.col("id") % 25).cast("string"), 2, "0")))
    .withColumn("open_date",
        F.date_add(F.lit("2015-01-01"), (F.col("id") * 73 % 3000).cast("int")))
    .drop("id")
)

stores.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_stores")
display(stores.limit(5))

# COMMAND ----------

# --- Fact: Transactions (100K rows) ---
# Modulo on FK guarantees referential integrity — no lookup maps needed
transactions = (
    spark.range(N_TRANSACTIONS)
    .withColumnRenamed("id", "txn_seq")
    .withColumn("transaction_id",
        F.concat(F.lit("TXN-"), F.lpad(F.col("txn_seq").cast("string"), 8, "0")))
    # Foreign keys via modulo — always valid
    .withColumn("product_id",
        F.concat(F.lit("PRD-"), F.lpad((F.col("txn_seq") % N_PRODUCTS).cast("string"), 5, "0")))
    .withColumn("store_id",
        F.concat(F.lit("STR-"), F.lpad((F.col("txn_seq") % N_STORES).cast("string"), 4, "0")))
    # Date spread across 1 year
    .withColumn("transaction_date",
        F.date_add(F.lit(START_DATE), (F.rand(seed=42) * DAYS_SPAN).cast("int")))
    # Timestamp with random hour/minute
    .withColumn("transaction_ts", F.to_timestamp(
        F.concat(
            F.col("transaction_date").cast("string"), F.lit(" "),
            F.lpad((F.rand(seed=7) * 24).cast("int").cast("string"), 2, "0"), F.lit(":"),
            F.lpad((F.rand(seed=13) * 60).cast("int").cast("string"), 2, "0"), F.lit(":00"))))
    # Measures
    .withColumn("quantity", (F.col("txn_seq") % 10 + 1).cast("int"))
    .withColumn("unit_price", F.round(F.rand(seed=99) * 200 + 5, 2))
    .withColumn("total_amount", F.round(F.col("quantity") * F.col("unit_price"), 2))
    .withColumn("payment_method",
        F.when(F.col("txn_seq") % 4 == 0, "Credit Card")
         .when(F.col("txn_seq") % 4 == 1, "Debit Card")
         .when(F.col("txn_seq") % 4 == 2, "Cash")
         .otherwise("Digital Wallet"))
    .drop("txn_seq")
)

display(transactions.limit(5))

# COMMAND ----------

# --- Broadcast join dims into fact + add Bronze metadata ---
bronze_transactions = (
    transactions
    .join(F.broadcast(products.select("product_id", "category", "brand", "product_name")), "product_id", "left")
    .join(F.broadcast(stores.select("store_id", "region", "store_format", "city")), "store_id", "left")
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("source_system", F.lit("synthetic_generator"))
    .withColumn("batch_id", F.lit(BATCH_ID))
)

# Write all Bronze tables
bronze_transactions.repartition(8).write.format("delta") \
    .mode("overwrite").option("overwriteSchema", "true") \
    .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_transactions")

print("✅ All Bronze tables written")

# COMMAND ----------

# --- Validation (single pass) ---
for tbl in ["bronze_products", "bronze_stores", "bronze_transactions"]:
    cnt = spark.table(f"{CATALOG}.{SCHEMA}.{tbl}").count()
    print(f"  {tbl}: {cnt:,}")

# Distribution check
print("\n📊 Sales by Category:")
spark.table(f"{CATALOG}.{SCHEMA}.bronze_transactions") \
    .groupBy("category").count().orderBy(F.desc("count")).show()

print("\n📊 Sales by Region:")
spark.table(f"{CATALOG}.{SCHEMA}.bronze_transactions") \
    .groupBy("region").count().orderBy(F.desc("count")).show()

# --- Status ---
import datetime
print("=" * 60)
print(f"🟢 NOTEBOOK READY — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   Catalog: {CATALOG}.{SCHEMA}")
print(f"   Tables:  bronze_products ({N_PRODUCTS}), bronze_stores ({N_STORES}), bronze_transactions ({N_TRANSACTIONS:,})")
print(f"   Next:    Run SDP pipeline → Silver/Gold materialized views")
print("=" * 60)
