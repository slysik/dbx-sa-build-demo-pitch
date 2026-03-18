# Databricks notebook source
# ruff: noqa: F821
# MAGIC %md
# MAGIC # Retail Data Generation — 100 Rows
# MAGIC PySpark `spark.range()` + hash-based deterministic generation

# COMMAND ----------

# TALK: Generating 100 retail order events using spark.range() — embarrassingly parallel
# SCALING: spark.range() distributes row generation across executors — same code at 1M, just change N
# DW-BRIDGE: Like nzload parallelizing inserts across SPUs in Netezza

from pyspark.sql import functions as F

NUM_ROWS = 100
NUM_CUSTOMERS = 20
NUM_PRODUCTS = 10
NUM_STORES = 5

df = (
    spark.range(0, NUM_ROWS)
    .withColumn("order_id", F.concat(F.lit("ORD-"), F.lpad(F.col("id").cast("string"), 6, "0")))
    .withColumn("customer_id", F.concat(F.lit("C"), F.lpad((F.abs(F.hash(F.col("id"), F.lit("cust"))) % NUM_CUSTOMERS + 1).cast("string"), 4, "0")))
    .withColumn("product_id", F.concat(F.lit("P"), F.lpad((F.abs(F.hash(F.col("id"), F.lit("prod"))) % NUM_PRODUCTS + 1).cast("string"), 3, "0")))
    .withColumn("quantity", (F.abs(F.hash(F.col("id"), F.lit("qty"))) % 5 + 1).cast("int"))
    .withColumn("unit_price", F.round((F.abs(F.hash(F.col("id"), F.lit("price"))) % 9900 + 100) / 100.0, 2).cast("decimal(18,2)"))
    .withColumn("order_total", F.round(F.col("quantity") * F.col("unit_price"), 2).cast("decimal(18,2)"))
    .withColumn("order_status",
        F.when(F.abs(F.hash(F.col("id"), F.lit("status"))) % 100 < 70, F.lit("completed"))
         .when(F.abs(F.hash(F.col("id"), F.lit("status"))) % 100 < 85, F.lit("shipped"))
         .when(F.abs(F.hash(F.col("id"), F.lit("status"))) % 100 < 95, F.lit("pending"))
         .otherwise(F.lit("returned")))
    .withColumn("store_id", F.concat(F.lit("S"), F.lpad((F.abs(F.hash(F.col("id"), F.lit("store"))) % NUM_STORES + 1).cast("string"), 3, "0")))
    .withColumn("order_date", F.date_sub(F.current_date(), (F.abs(F.hash(F.col("id"), F.lit("date"))) % 90).cast("int")))
    .withColumn("ingest_ts", F.current_timestamp())
    .drop("id")
)

# COMMAND ----------

# TALK: Preview the generated data before writing anywhere
display(df)

# COMMAND ----------

print(f"Row count: {df.count()}")
