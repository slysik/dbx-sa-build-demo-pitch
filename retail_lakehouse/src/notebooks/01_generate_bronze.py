# Databricks notebook source
# MAGIC %md
# MAGIC # Retail Bronze Generation
# MAGIC
# MAGIC | Table | Rows | Method |
# MAGIC |-------|------|--------|
# MAGIC | `bronze_products` | 200 | spark.range — dim |
# MAGIC | `bronze_stores` | 50 | spark.range — dim |
# MAGIC | `bronze_transactions` | 100,000 | spark.range — fact, broadcast joined |
# MAGIC
# MAGIC **Pattern:** `spark.range(N)` → Spark-native columns → broadcast join → Bronze Delta

# COMMAND ----------

import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark.sql import DataFrame, SparkSession

CATALOG    = "workspace"
SCHEMA     = "retail"
BATCH_ID   = "batch_001"

N_PRODUCTS = 200
N_STORES   = 50
N_EVENTS   = 100_000   # ← change to scale: 1_000_000 for prod demo

START_DATE = "2025-01-01"
DAYS_SPAN  = 365

print(f"Target: {CATALOG}.{SCHEMA} | Events: {N_EVENTS:,}")

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"Schema ready: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# --- Dim: Products (200 rows, 5 columns) ---
products = (
    spark.range(N_PRODUCTS)
    .withColumn("product_id", F.concat(F.lit("PRD-"), F.lpad(F.col("id").cast("string"), 4, "0")))
    .withColumn("product_name", F.concat(F.lit("Product-"), F.col("id").cast("string")))
    .withColumn("category",
        F.when(F.col("id") % 6 == 0, "Electronics")
         .when(F.col("id") % 6 == 1, "Apparel")
         .when(F.col("id") % 6 == 2, "Grocery")
         .when(F.col("id") % 6 == 3, "Home & Garden")
         .when(F.col("id") % 6 == 4, "Sports")
         .otherwise("Toys"))
    .withColumn("brand",
        F.when(F.col("id") % 4 == 0, "BrandA")
         .when(F.col("id") % 4 == 1, "BrandB")
         .when(F.col("id") % 4 == 2, "BrandC")
         .otherwise("BrandD"))
    .withColumn("unit_price", F.round(F.rand(seed=7) * 490 + 10, 2))
    .drop("id")
)

display(products.limit(5))

# COMMAND ----------

# --- Dim: Stores (50 rows, 5 columns) ---
stores = (
    spark.range(N_STORES)
    .withColumn("store_id", F.concat(F.lit("STR-"), F.lpad(F.col("id").cast("string"), 3, "0")))
    .withColumn("store_name", F.concat(F.lit("Store-"), F.col("id").cast("string")))
    .withColumn("region",
        F.when(F.col("id") % 4 == 0, "North")
         .when(F.col("id") % 4 == 1, "South")
         .when(F.col("id") % 4 == 2, "East")
         .otherwise("West"))
    .withColumn("store_format",
        F.when(F.col("id") % 3 == 0, "Flagship")
         .when(F.col("id") % 3 == 1, "Standard")
         .otherwise("Express"))
    .withColumn("city", F.concat(F.lit("City-"), (F.col("id") % 20).cast("string")))
    .drop("id")
)

display(stores.limit(5))

# COMMAND ----------

# --- Fact: Transactions (100K rows) ---
# FK integrity via modulo — every product_id and store_id guaranteed to exist in dims
fact = (
    spark.range(N_EVENTS)
    .withColumnRenamed("id", "event_seq")
    .withColumn("txn_id", F.concat(F.lit("TXN-"), F.lpad(F.col("event_seq").cast("string"), 8, "0")))
    .withColumn("product_id", F.concat(F.lit("PRD-"), F.lpad((F.col("event_seq") % N_PRODUCTS).cast("string"), 4, "0")))
    .withColumn("store_id", F.concat(F.lit("STR-"), F.lpad((F.col("event_seq") % N_STORES).cast("string"), 3, "0")))
    .withColumn("txn_date", F.date_add(F.lit(START_DATE), (F.rand(seed=42) * DAYS_SPAN).cast("int")))
    .withColumn("quantity", (F.col("event_seq") % 5 + 1).cast("int"))
    .withColumn("unit_price_sold", F.round(F.rand(seed=99) * 490 + 10, 2))
    .withColumn("discount_pct",
        F.when(F.rand(seed=3) < 0.15, F.round(F.rand(seed=5) * 0.30, 2))
         .otherwise(F.lit(0.0)))
    .withColumn("amount", F.round(
        F.col("unit_price_sold") * F.col("quantity") * (1 - F.col("discount_pct")), 2))
    .drop("event_seq")
)

# COMMAND ----------

# --- Broadcast join dims into fact, add Bronze metadata, write ---
bronze = (
    fact
    .join(F.broadcast(products), "product_id", "left")
    .join(F.broadcast(stores), "store_id", "left")
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("source_system", F.lit("synthetic_generator"))
    .withColumn("batch_id", F.lit(BATCH_ID))
)

# Dims (small — no repartition)
products.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_products")
stores.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_stores")

# Fact (repartition for file sizing)
(bronze.repartition(8)
    .write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_transactions"))

print("Bronze tables written ✅")

# COMMAND ----------

# --- Validation (single pass) ---
for tbl in ["bronze_products", "bronze_stores", "bronze_transactions"]:
    cnt = spark.table(f"{CATALOG}.{SCHEMA}.{tbl}").count()
    print(f"  {tbl}: {cnt:,}")

# Distribution check
print("\nTransaction distribution by category:")
(spark.table(f"{CATALOG}.{SCHEMA}.bronze_transactions")
    .groupBy("category").count()
    .orderBy(F.desc("count"))
    .show())
