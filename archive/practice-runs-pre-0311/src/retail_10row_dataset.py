# Databricks notebook source
# MAGIC %md
# MAGIC # Retail Orders — Synthetic Dataset Generator
# MAGIC
# MAGIC **10-row fixture** with intentional imperfections (1 null, 1 duplicate).
# MAGIC Scales to 1000+ via `crossJoin` — stays distributed, no Python rebuild.

# COMMAND ----------

from pyspark.sql import SparkSession
import pyspark.sql.functions as F

spark = SparkSession.builder.getOrCreate()

# -- TALK: Starting with spark.range() so this stays distributed-ready even at 10 rows.
# -- TALK: Using hash() for deterministic column derivation — no rand(column) which fails on Databricks.

products = ["Laptop", "Headphones", "Keyboard", "Mouse", "Monitor", "Charger", "Cable", "Stand", "Webcam", "Speaker"]
categories = {"Laptop": "electronics", "Headphones": "accessories", "Keyboard": "peripherals",
              "Mouse": "peripherals", "Monitor": "electronics", "Charger": "accessories",
              "Cable": "accessories", "Stand": "peripherals", "Webcam": "electronics", "Speaker": "electronics"}
regions = ["East", "South", "Midwest", "West"]
statuses = ["complete", "complete", "complete", "complete", "complete", "pending", "pending", "returned", "cancelled", "complete"]

products_col = F.array(*[F.lit(p) for p in products])
regions_col = F.array(*[F.lit(r) for r in regions])
statuses_col = F.array(*[F.lit(s) for s in statuses])
cat_map = F.create_map(*[item for p in products for item in (F.lit(p), F.lit(categories[p]))])

df = (
    spark.range(0, 10)
    .withColumn("order_id", F.concat(F.lit("ORD-"), F.lpad((F.col("id") + 1).cast("string"), 5, "0")))
    .withColumn("order_ts", F.current_timestamp() - F.expr("make_interval(0, 0, abs(hash(id, 'day')) % 30, abs(hash(id, 'hr')) % 12, 0, 0)"))
    .withColumn("customer_id", (F.abs(F.hash(F.col("id"), F.lit("cust"))) % 500 + 1).cast("int"))
    .withColumn("product", products_col[F.abs(F.hash(F.col("id"), F.lit("prod"))) % 10])
    .withColumn("category", cat_map[F.col("product")])
    .withColumn("quantity", (F.abs(F.hash(F.col("id"), F.lit("qty"))) % 5 + 1).cast("int"))
    .withColumn("amount", F.round((F.abs(F.hash(F.col("id"), F.lit("amt"))) % 50000).cast("double") / 100.0 + 9.99, 2))
    .withColumn("region", regions_col[F.abs(F.hash(F.col("id"), F.lit("reg"))) % 4])
    .withColumn("status", statuses_col[F.col("id").cast("int")])
    # -- TALK: Injecting a null customer_id on row 7 to demonstrate null-awareness for Silver layer
    .withColumn("customer_id", F.when(F.col("id") == 7, F.lit(None).cast("int")).otherwise(F.col("customer_id")))
    .drop("id")
)

# -- TALK: Adding a duplicate row (same order_id as row 0) to demonstrate dedup awareness
row0 = df.filter(F.col("order_id") == "ORD-00001")
df = df.unionByName(row0)

df.show(truncate=False)
df.printSchema()
print(f"Total rows: {df.count()} | Null customer_ids: {df.filter(F.col('customer_id').isNull()).count()} | Duplicate order_ids: {df.groupBy('order_id').count().filter('count > 1').count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Scale to 1000 rows

# COMMAND ----------

# -- SCALING: crossJoin(spark.range(100)) keeps it in Spark — no Python rebuild.
df_base = df.dropDuplicates(["order_id"])

df_scaled = (
    df_base
    .crossJoin(spark.range(100).withColumnRenamed("id", "_mult"))
    .withColumn("order_id", F.expr("uuid()"))
    .withColumn("order_ts", F.col("order_ts") + F.expr("make_interval(0, 0, 0, _mult, 0, 0)"))
    .drop("_mult")
)

print(f"Rows: {df_scaled.count()} | Partitions: {df_scaled.rdd.getNumPartitions()}")
df_scaled.show(5, truncate=False)
