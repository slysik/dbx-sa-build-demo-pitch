# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # Media Lakehouse — Bronze Generation (CDC)
# MAGIC
# MAGIC | Table | Rows | Type |
# MAGIC |-------|------|------|
# MAGIC | `bronze_content` | 200 | Dim |
# MAGIC | `bronze_subscribers` | 2,000 | Dim |
# MAGIC | `bronze_stream_events` | 105,000 | Fact (CDC) |
# MAGIC
# MAGIC **Pattern:** `spark.range()` native — 100K INSERTs + 4K UPDATEs + 1K DELETEs.
# MAGIC Silver resolves via `APPLY CHANGES` (SCD Type 1).

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG     = "interview"
SCHEMA      = "media"
BATCH_ID    = "batch_001"

N_CONTENT      = 200
N_SUBSCRIBERS  = 2_000
N_EVENTS       = 100_000
N_UPDATES      = 4_000
N_DELETES      = 1_000

START_DATE  = "2025-09-12"
DAYS_SPAN   = 180

print(f"Target: {CATALOG}.{SCHEMA} | Events: {N_EVENTS:,} + {N_UPDATES:,} updates + {N_DELETES:,} deletes")

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"Schema ready: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# ── Dim 1: Content (200 titles) ──
content = (
    spark.range(N_CONTENT)
    .withColumn("content_id", F.concat(F.lit("CNT-"), F.lpad(F.col("id").cast("string"), 5, "0")))
    .withColumn("title", F.concat(F.lit("Title "), F.col("id").cast("string")))
    .withColumn("genre",
        F.when(F.col("id") % 6 == 0, "Action")
         .when(F.col("id") % 6 == 1, "Comedy")
         .when(F.col("id") % 6 == 2, "Drama")
         .when(F.col("id") % 6 == 3, "Sci-Fi")
         .when(F.col("id") % 6 == 4, "Horror")
         .otherwise("Documentary"))
    .withColumn("release_year", (F.col("id") % 10 + 2015).cast("int"))
    .withColumn("rating", F.round(F.rand(seed=3) * 4 + 1, 1))
    .drop("id")
)

content.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_content")
display(content.limit(5))

# COMMAND ----------

# ── Dim 2: Subscribers (2K accounts) ──
subscribers = (
    spark.range(N_SUBSCRIBERS)
    .withColumn("subscriber_id", F.concat(F.lit("SUB-"), F.lpad(F.col("id").cast("string"), 6, "0")))
    .withColumn("plan_type",
        F.when(F.col("id") % 4 == 0, "free")
         .when(F.col("id") % 4 == 1, "basic")
         .when(F.col("id") % 4 == 2, "standard")
         .otherwise("premium"))
    .withColumn("region",
        F.when(F.col("id") % 4 == 0, "North America")
         .when(F.col("id") % 4 == 1, "Europe")
         .when(F.col("id") % 4 == 2, "Asia Pacific")
         .otherwise("Latin America"))
    .withColumn("signup_date", F.date_add(F.lit("2023-01-01"), (F.col("id") % 730).cast("int")))
    .withColumn("status",
        F.when(F.col("id") % 10 < 8, "active")
         .otherwise("churned"))
    .drop("id")
)

subscribers.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_subscribers")
display(subscribers.limit(5))

# COMMAND ----------

# ── Fact: Stream Events — CDC Feed ──
# 100K INSERTs | 4K UPDATEs (corrected watch_minutes) | 1K DELETEs
# APPLY CHANGES at Silver resolves to 99K latest-state rows

inserts = (
    spark.range(N_EVENTS)
    .withColumn("event_id", F.concat(F.lit("EVT-"), F.lpad(F.col("id").cast("string"), 8, "0")))
    .withColumn("subscriber_id", F.concat(F.lit("SUB-"), F.lpad((F.col("id") % N_SUBSCRIBERS).cast("string"), 6, "0")))
    .withColumn("content_id", F.concat(F.lit("CNT-"), F.lpad((F.col("id") % N_CONTENT).cast("string"), 5, "0")))
    .withColumn("event_type",
        F.when(F.col("id") % 5 == 0, "play")
         .when(F.col("id") % 5 == 1, "pause")
         .when(F.col("id") % 5 == 2, "resume")
         .when(F.col("id") % 5 == 3, "complete")
         .otherwise("skip"))
    .withColumn("watch_minutes", F.round(F.rand(seed=42) * 120 + 1, 1))
    .withColumn("event_ts", F.to_timestamp(
        F.concat(
            F.date_add(F.lit(START_DATE), (F.rand(seed=7) * DAYS_SPAN).cast("int")).cast("string"),
            F.lit(" "),
            F.lpad((F.rand(seed=13) * 24).cast("int").cast("string"), 2, "0"),
            F.lit(":"),
            F.lpad((F.rand(seed=17) * 60).cast("int").cast("string"), 2, "0"),
            F.lit(":00"))))
    .withColumn("_change_type", F.lit("INSERT"))
    .withColumn("_commit_timestamp", F.col("event_ts"))
    .drop("id")
)

# UPDATEs: first 4K events get corrected watch_minutes, later commit
updates = (
    spark.range(N_UPDATES)
    .withColumn("event_id", F.concat(F.lit("EVT-"), F.lpad(F.col("id").cast("string"), 8, "0")))
    .withColumn("subscriber_id", F.concat(F.lit("SUB-"), F.lpad((F.col("id") % N_SUBSCRIBERS).cast("string"), 6, "0")))
    .withColumn("content_id", F.concat(F.lit("CNT-"), F.lpad((F.col("id") % N_CONTENT).cast("string"), 5, "0")))
    .withColumn("event_type",
        F.when(F.col("id") % 5 == 0, "play")
         .when(F.col("id") % 5 == 1, "pause")
         .when(F.col("id") % 5 == 2, "resume")
         .when(F.col("id") % 5 == 3, "complete")
         .otherwise("skip"))
    .withColumn("watch_minutes", F.round(F.rand(seed=77) * 180 + 5, 1))
    .withColumn("event_ts", F.to_timestamp(
        F.concat(
            F.date_add(F.lit(START_DATE), (F.rand(seed=7) * DAYS_SPAN).cast("int")).cast("string"),
            F.lit(" "),
            F.lpad((F.rand(seed=13) * 24).cast("int").cast("string"), 2, "0"),
            F.lit(":"),
            F.lpad((F.rand(seed=17) * 60).cast("int").cast("string"), 2, "0"),
            F.lit(":00"))))
    .withColumn("_change_type", F.lit("UPDATE"))
    .withColumn("_commit_timestamp", F.to_timestamp(F.lit("2026-03-10 00:00:00")))
    .drop("id")
)

# DELETEs: events 4000–4999 removed, latest commit
deletes = (
    spark.range(N_DELETES)
    .withColumn("event_id", F.concat(F.lit("EVT-"), F.lpad((F.col("id") + N_UPDATES).cast("string"), 8, "0")))
    .withColumn("subscriber_id", F.concat(F.lit("SUB-"), F.lpad(((F.col("id") + N_UPDATES) % N_SUBSCRIBERS).cast("string"), 6, "0")))
    .withColumn("content_id", F.concat(F.lit("CNT-"), F.lpad(((F.col("id") + N_UPDATES) % N_CONTENT).cast("string"), 5, "0")))
    .withColumn("event_type", F.lit("play"))
    .withColumn("watch_minutes", F.lit(0.0))
    .withColumn("event_ts", F.to_timestamp(F.lit("2025-10-01 00:00:00")))
    .withColumn("_change_type", F.lit("DELETE"))
    .withColumn("_commit_timestamp", F.to_timestamp(F.lit("2026-03-11 00:00:00")))
    .drop("id")
)

stream_events = inserts.unionByName(updates).unionByName(deletes)
print(f"CDC breakdown — INSERT: {N_EVENTS:,} | UPDATE: {N_UPDATES:,} | DELETE: {N_DELETES:,} | Total: {N_EVENTS + N_UPDATES + N_DELETES:,}")

# COMMAND ----------

# ── Add Bronze metadata + write all tables ──
bronze_events = (
    stream_events
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("source_system", F.lit("synthetic_cdc_generator"))
    .withColumn("batch_id", F.lit(BATCH_ID))
)

(bronze_events.repartition(8)
    .write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_stream_events"))

print("All Bronze tables written.")

# COMMAND ----------

# ── Validate ──
for tbl in ["bronze_content", "bronze_subscribers", "bronze_stream_events"]:
    cnt = spark.table(f"{CATALOG}.{SCHEMA}.{tbl}").count()
    print(f"  {tbl}: {cnt:,}")

# CDC distribution
spark.table(f"{CATALOG}.{SCHEMA}.bronze_stream_events").groupBy("_change_type").count().orderBy("_change_type").show()
