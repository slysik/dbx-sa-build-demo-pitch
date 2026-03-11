# Databricks notebook source
# MAGIC %md
# MAGIC # Media Streaming — Bronze Data Generation
# MAGIC
# MAGIC | Table | Type | Rows | Key Columns |
# MAGIC |-------|------|------|-------------|
# MAGIC | `bronze_content` | Dimension | 500 | content_id, genre, content_type, duration_min |
# MAGIC | `bronze_subscribers` | Dimension | 5,000 | subscriber_id, plan_type, country, age_group |
# MAGIC | `bronze_stream_events` | Fact | 100,000 | event_id, content_id, subscriber_id, stream_date, watch_min, device |
# MAGIC
# MAGIC **Pattern:** `spark.range()` → native columns → broadcast join → Bronze Delta

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG   = "interview"
SCHEMA    = "media"
BATCH_ID  = "batch_001"

N_CONTENT     = 500
N_SUBSCRIBERS = 5_000
N_EVENTS      = 100_000       # ← change to 1_000_000 to scale

START_DATE = "2025-06-01"
DAYS_SPAN  = 270

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"Target: {CATALOG}.{SCHEMA} | Events: {N_EVENTS:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Dimension 1: Content Library

# COMMAND ----------

content = (
    spark.range(N_CONTENT)
    .withColumn("content_id", F.concat(F.lit("CNT-"), F.lpad(F.col("id").cast("string"), 5, "0")))
    .withColumn("_r", F.rand(seed=1))
    .withColumn("genre",
        F.when(F.col("_r") < 0.20, "Drama")
         .when(F.col("_r") < 0.38, "Comedy")
         .when(F.col("_r") < 0.54, "Action")
         .when(F.col("_r") < 0.68, "Documentary")
         .when(F.col("_r") < 0.80, "Sci-Fi")
         .when(F.col("_r") < 0.90, "Horror")
         .otherwise("Romance"))
    .withColumn("content_type",
        F.when(F.col("id") % 3 == 0, "movie")
         .when(F.col("id") % 3 == 1, "series")
         .otherwise("short"))
    .withColumn("duration_min",
        F.when(F.col("content_type") == "movie", (F.rand(seed=2) * 90 + 80).cast("int"))
         .when(F.col("content_type") == "series", (F.rand(seed=3) * 40 + 20).cast("int"))
         .otherwise((F.rand(seed=4) * 15 + 5).cast("int")))
    .withColumn("release_year", (F.rand(seed=5) * 10 + 2015).cast("int"))
    .drop("id", "_r")
)
display(content.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Dimension 2: Subscribers

# COMMAND ----------

subscribers = (
    spark.range(N_SUBSCRIBERS)
    .withColumn("subscriber_id", F.concat(F.lit("SUB-"), F.lpad(F.col("id").cast("string"), 6, "0")))
    .withColumn("_r", F.rand(seed=10))
    .withColumn("plan_type",
        F.when(F.col("_r") < 0.35, "free")
         .when(F.col("_r") < 0.60, "basic")
         .when(F.col("_r") < 0.82, "standard")
         .otherwise("premium"))
    .withColumn("country",
        F.when(F.col("id") % 5 == 0, "US")
         .when(F.col("id") % 5 == 1, "UK")
         .when(F.col("id") % 5 == 2, "Germany")
         .when(F.col("id") % 5 == 3, "Japan")
         .otherwise("Brazil"))
    .withColumn("age_group",
        F.when(F.col("id") % 4 == 0, "18-24")
         .when(F.col("id") % 4 == 1, "25-34")
         .when(F.col("id") % 4 == 2, "35-49")
         .otherwise("50+"))
    .withColumn("signup_date", F.date_add(F.lit("2023-01-01"), (F.rand(seed=11) * 730).cast("int")))
    .drop("id", "_r")
)
display(subscribers.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fact: Stream Events

# COMMAND ----------

fact = (
    spark.range(N_EVENTS)
    .withColumnRenamed("id", "event_seq")
    .withColumn("event_id", F.concat(F.lit("EVT-"), F.lpad(F.col("event_seq").cast("string"), 8, "0")))
    # FK — modulo guarantees valid references
    .withColumn("content_id", F.concat(F.lit("CNT-"), F.lpad((F.col("event_seq") % N_CONTENT).cast("string"), 5, "0")))
    .withColumn("subscriber_id", F.concat(F.lit("SUB-"), F.lpad((F.col("event_seq") % N_SUBSCRIBERS).cast("string"), 6, "0")))
    # Date spread
    .withColumn("stream_date", F.date_add(F.lit(START_DATE), (F.rand(seed=42) * DAYS_SPAN).cast("int")))
    .withColumn("stream_ts", F.to_timestamp(
        F.concat(F.col("stream_date").cast("string"), F.lit(" "),
                 F.lpad((F.rand(seed=7) * 24).cast("int").cast("string"), 2, "0"), F.lit(":"),
                 F.lpad((F.rand(seed=13) * 60).cast("int").cast("string"), 2, "0"), F.lit(":00"))))
    # Measures
    .withColumn("watch_min", F.round(F.rand(seed=99) * 120 + 1, 1))
    .withColumn("_dr", F.rand(seed=55))
    .withColumn("device",
        F.when(F.col("_dr") < 0.40, "mobile")
         .when(F.col("_dr") < 0.70, "smart_tv")
         .when(F.col("_dr") < 0.88, "tablet")
         .otherwise("desktop"))
    .withColumn("completed", (F.rand(seed=77) > 0.3).cast("boolean"))
    .drop("event_seq", "_dr")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Broadcast Join + Metadata + Write Bronze

# COMMAND ----------

bronze_events = (
    fact
    .join(F.broadcast(content), "content_id", "left")
    .join(F.broadcast(subscribers), "subscriber_id", "left")
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("source_system", F.lit("synthetic_generator"))
    .withColumn("batch_id", F.lit(BATCH_ID))
)

# Write dims
content.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_content")
subscribers.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_subscribers")

# Write fact (repartition for file sizing)
(bronze_events.repartition(8).write.format("delta")
    .mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_stream_events"))

print("Bronze tables written ✓")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validate

# COMMAND ----------

for tbl in ["bronze_content", "bronze_subscribers", "bronze_stream_events"]:
    cnt = spark.table(f"{CATALOG}.{SCHEMA}.{tbl}").count()
    print(f"  {tbl}: {cnt:,}")

# Distribution check
print("\n--- Genre Distribution ---")
spark.table(f"{CATALOG}.{SCHEMA}.bronze_stream_events").groupBy("genre").count().orderBy(F.desc("count")).show()

print("--- Plan Distribution ---")
spark.table(f"{CATALOG}.{SCHEMA}.bronze_stream_events").groupBy("plan_type").count().orderBy(F.desc("count")).show()
