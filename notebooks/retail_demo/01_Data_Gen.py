# Databricks notebook source
# MAGIC %md
# MAGIC # 01 - PySpark Data Gen (Retail)
# MAGIC **100k retail orders** using `spark.range()` + hash-based columns.
# MAGIC
# MAGIC > TALK: "spark.range() distributes row generation across executors — same code at 1M, just change N."

# COMMAND ----------

# TALK: Generating 100k retail orders with realistic distribution
# SCALING: spark.range() distributes across executors — embarrassingly parallel, like nzload across SPUs
# DW-BRIDGE: Hash-based assignment is deterministic, like Netezza distribution keys — reproducible every run

from pyspark.sql import functions as F

N = 100_000
N_CUSTOMERS = 10_000
N_PRODUCTS = 5_000
N_STORES = 200

df = (spark.range(N)  # noqa: F821
    .withColumn("order_id", F.concat(F.lit("ORD-"), F.lpad(F.col("id").cast("string"), 10, "0")))
    .withColumn("customer_id", F.concat(F.lit("C"), F.lpad((F.abs(F.hash(F.col("id"), F.lit("cust"))) % N_CUSTOMERS).cast("string"), 6, "0")))
    .withColumn("store_id", F.concat(F.lit("S"), F.lpad((F.abs(F.hash(F.col("id"), F.lit("store"))) % N_STORES).cast("string"), 4, "0")))
    .withColumn("product_id", F.concat(F.lit("P"), F.lpad((F.abs(F.hash(F.col("id"), F.lit("prod"))) % N_PRODUCTS).cast("string"), 5, "0")))
    # Spread order timestamps over 14 days
    .withColumn("seconds_ago", (F.abs(F.hash(F.col("id"), F.lit("ts"))) % (14 * 86400)).cast("int"))
    .withColumn("order_ts", F.current_timestamp() - F.expr("make_interval(0,0,0,0,0,0,seconds_ago)"))
    .drop("seconds_ago")
    .withColumn("quantity", (F.abs(F.hash(F.col("id"), F.lit("qty"))) % 10 + 1).cast("int"))
    .withColumn("unit_price", F.round(F.abs(F.hash(F.col("id"), F.lit("price"))) % 50000 / 100.0 + 0.99, 2).cast("decimal(18,2)"))
    .withColumn("total_amount", F.round(F.col("quantity") * F.col("unit_price"), 2).cast("decimal(18,2)"))
    .withColumn("currency", F.lit("USD"))
    # TALK: Status distribution — 85% completed, 10% pending, 5% returned
    .withColumn("status", F.when(F.abs(F.hash(F.col("id"), F.lit("st"))) % 100 < 85, "COMPLETED")
                           .when(F.abs(F.hash(F.col("id"), F.lit("st"))) % 100 < 95, "PENDING")
                           .otherwise("RETURNED"))
    .withColumn("loyalty_tier", F.when(F.abs(F.hash(F.col("id"), F.lit("tier"))) % 100 < 10, "Gold")
                                 .when(F.abs(F.hash(F.col("id"), F.lit("tier"))) % 100 < 35, "Silver")
                                 .when(F.abs(F.hash(F.col("id"), F.lit("tier"))) % 100 < 70, "Bronze")
                                 .otherwise("Basic"))
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("source_system", F.lit("synthetic_demo"))
    .drop("id")
)

# SCALING: At 1M rows, this completes in <30s — just change N
display(df.limit(10))  # noqa: F821

# COMMAND ----------

# MAGIC %md
# MAGIC ### Write to Bronze (append-only, raw data preserved)

# COMMAND ----------

# TALK: Loading into Bronze as append-only — no transforms, raw data preserved
df.write.mode("append").saveAsTable("retail_demo.bronze.order_events")

# Gate check
count = spark.sql("SELECT count(*) AS cnt FROM retail_demo.bronze.order_events").collect()[0]["cnt"]  # noqa: F821
print(f"✅ Bronze row count: {count}")
