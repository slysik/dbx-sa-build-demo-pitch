# Databricks notebook source

# MAGIC %md
# MAGIC # 🎬 Media Streaming — Synthetic Bronze Dataset
# MAGIC
# MAGIC **Pattern:** `spark.range()` → Spark-native columns → broadcast join dims → direct Delta Bronze
# MAGIC
# MAGIC | Table | Type | Rows | Scales to |
# MAGIC |-------|------|------|-----------|
# MAGIC | `bronze_content` | Dim | 200 | Same |
# MAGIC | `bronze_subscribers` | Dim | 2,000 | Same |
# MAGIC | `bronze_stream_events` | Fact | 100K | 1M (change one param) |

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 · Configuration
# MAGIC **All knobs at the top.** Change `N_EVENTS` to scale — no other code changes needed.

# COMMAND ----------

from pyspark.sql import functions as F

# -- Unity Catalog target (3-level namespace, always) --
CATALOG  = "interview"
SCHEMA   = "media"
BATCH_ID = "batch_001"

# -- Row counts: change N_EVENTS to 1_000_000 for scale test --
N_CONTENT     = 200       # small dim — broadcastable
N_SUBSCRIBERS = 2_000     # small dim — broadcastable
N_EVENTS      = 100_000   # fact table — the analytical grain

# -- Date range: last 180 days --
START_DATE = "2025-09-12"  # ~6 months back from today
DAYS_SPAN  = 180

print(f"Target: {CATALOG}.{SCHEMA} | Events: {N_EVENTS:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · Create Schema

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"✅ {CATALOG}.{SCHEMA} ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 · Content Dimension (200 rows, 6 cols)
# MAGIC
# MAGIC **Why `spark.range()`?** Distributed row generation — no driver memory pressure, scales identically at any size.
# MAGIC
# MAGIC **Why modulo + `when()`?** Deterministic categorical assignment using pure Spark expressions.
# MAGIC No Faker, no Python loops, no Pandas. Same code runs at 200 or 200K.

# COMMAND ----------

content_dim = (
    spark.range(N_CONTENT)
    .withColumn("content_id", F.concat(F.lit("CNT-"), F.lpad(F.col("id").cast("string"), 5, "0")))
    .withColumn("title", F.concat(F.lit("Title_"), F.col("id").cast("string")))
    .withColumn("genre",
        F.when(F.col("id") % 10 < 3, "Drama")      # 30%
         .when(F.col("id") % 10 < 5, "Comedy")      # 20%
         .when(F.col("id") % 10 < 7, "Action")      # 20%
         .when(F.col("id") % 10 < 8, "Thriller")    # 10%
         .when(F.col("id") % 10 < 9, "Sci-Fi")      # 10%
         .otherwise("Documentary"))                   # 10%
    .withColumn("content_type",
        F.when(F.col("id") % 5 < 2, "series")       # 40% — streaming platforms are series-heavy
         .when(F.col("id") % 5 < 4, "movie")         # 40%
         .otherwise("documentary"))                   # 20%
    .withColumn("duration_min",
        F.when(F.col("content_type") == "movie", 90 + (F.col("id") % 60).cast("int"))      # 90-149 min
         .when(F.col("content_type") == "series", 25 + (F.col("id") % 35).cast("int"))     # 25-59 min
         .otherwise(45 + (F.col("id") % 45).cast("int")))                                   # 45-89 min
    .withColumn("release_year", 2015 + (F.col("id") % 11).cast("int"))  # 2015-2025
    .drop("id")
)

display(content_dim.limit(5))
print(f"✅ content_dim: {N_CONTENT} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 · Subscribers Dimension (2,000 rows, 6 cols)
# MAGIC
# MAGIC **Weighted plan distribution** via `rand()` thresholds — Premium is smallest segment but
# MAGIC highest engagement. We use this in the fact table to weight streaming activity by plan.

# COMMAND ----------

content_dim.groupBy("genre").count().orderBy(F.desc("count")).show()

# COMMAND ----------

subscriber_dim = (
    spark.range(N_SUBSCRIBERS)
    .withColumn("subscriber_id", F.concat(F.lit("SUB-"), F.lpad(F.col("id").cast("string"), 6, "0")))
    # -- Weighted plan: Free 40%, Basic 25%, Standard 20%, Premium 15% --
    .withColumn("_r", F.rand(seed=1))
    .withColumn("plan_type",
        F.when(F.col("_r") < 0.40, "free")
         .when(F.col("_r") < 0.65, "basic")
         .when(F.col("_r") < 0.85, "standard")
         .otherwise("premium"))
    .withColumn("country",
        F.when(F.col("id") % 10 < 4, "US")           # 40%
         .when(F.col("id") % 10 < 5, "UK")            # 10%
         .when(F.col("id") % 10 < 6, "Canada")        # 10%
         .when(F.col("id") % 10 < 7, "Germany")       # 10%
         .when(F.col("id") % 10 < 8, "Brazil")        # 10%
         .when(F.col("id") % 10 < 9, "Japan")         # 10%
         .otherwise("India"))                          # 10%
    .withColumn("age_group",
        F.when(F.col("id") % 5 == 0, "18-24")
         .when(F.col("id") % 5 == 1, "25-34")
         .when(F.col("id") % 5 == 2, "35-44")
         .when(F.col("id") % 5 == 3, "45-54")
         .otherwise("55+"))
    .withColumn("signup_date",
        F.date_add(F.lit(START_DATE), -(F.col("id") % 730).cast("int")))  # up to 2 yrs ago
    .withColumn("preferred_device",
        F.when(F.col("id") % 5 == 0, "smart_tv")
         .when(F.col("id") % 5 == 1, "mobile")
         .when(F.col("id") % 5 == 2, "tablet")
         .when(F.col("id") % 5 == 3, "desktop")
         .otherwise("streaming_stick"))
    .drop("id", "_r")
)

display(subscriber_dim.limit(5))
print(f"✅ subscriber_dim: {N_SUBSCRIBERS} rows")

# COMMAND ----------

subscriber_dim.groupBy("plan_type").count().orderBy(F.desc("count")).show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 · Stream Events Fact (100K rows)
# MAGIC
# MAGIC **This is the analytical grain** — one row = one streaming session.
# MAGIC
# MAGIC **Key patterns:**
# MAGIC - `spark.range(N_EVENTS)` — distributed, no driver pressure, scales to 1M+ unchanged
# MAGIC - Foreign keys via modulo — `subscriber_id` and `content_id` reference dims
# MAGIC - `rand()` for realistic numeric variation (duration, buffering)
# MAGIC - Event dates spread across 180 days via `rand()` for natural distribution

# COMMAND ----------

fact_df = (
    spark.range(N_EVENTS)
    .withColumnRenamed("id", "event_seq")
    .withColumn("event_id",
        F.concat(F.lit("EVT-"), F.lpad(F.col("event_seq").cast("string"), 8, "0")))
    # -- Foreign keys (modulo ensures valid references to dims) --
    .withColumn("subscriber_id",
        F.concat(F.lit("SUB-"), F.lpad((F.col("event_seq") % N_SUBSCRIBERS).cast("string"), 6, "0")))
    .withColumn("content_id",
        F.concat(F.lit("CNT-"), F.lpad((F.col("event_seq") % N_CONTENT).cast("string"), 5, "0")))
    # -- Event timestamp: spread across 180 days with random offset --
    .withColumn("event_date",
        F.date_add(F.lit(START_DATE), (F.rand(seed=42) * DAYS_SPAN).cast("int")))
    .withColumn("event_ts",
        F.to_timestamp(
            F.concat(
                F.col("event_date").cast("string"), F.lit(" "),
                F.lpad((F.rand(seed=7) * 24).cast("int").cast("string"), 2, "0"), F.lit(":"),
                F.lpad((F.rand(seed=13) * 60).cast("int").cast("string"), 2, "0"), F.lit(":00")
            )
        ))
    # -- Measures --
    .withColumn("stream_duration_sec",
        (F.rand(seed=99) * 7200 + 60).cast("int"))   # 1-120 min in seconds
    .withColumn("quality",
        F.when(F.rand(seed=3) < 0.30, "SD")
         .when(F.rand(seed=3) < 0.65, "HD")
         .when(F.rand(seed=3) < 0.90, "4K")
         .otherwise("4K HDR"))
    .withColumn("buffering_events",
        (F.rand(seed=21) * 5).cast("int"))            # 0-4 buffering events
    .withColumn("completed",
        F.when(F.rand(seed=55) < 0.45, True).otherwise(False))
    .drop("event_seq")
)

display(fact_df.limit(5))
print(f"✅ fact_df: {N_EVENTS:,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6 · Broadcast Join Dims → Fact, Add Bronze Metadata
# MAGIC
# MAGIC **Why broadcast?** Dims are tiny (200 + 2K rows) — Spark sends them to every executor.
# MAGIC No shuffle, no skew. This is the #1 perf optimization for star-schema joins.
# MAGIC
# MAGIC **Bronze metadata:** `ingest_ts`, `source_system`, `batch_id` — enables lineage,
# MAGIC replay, and debugging. This is what makes Bronze a proper governed landing layer.

# COMMAND ----------

bronze_events = (
    fact_df
    .join(F.broadcast(subscriber_dim), "subscriber_id", "left")
    .join(F.broadcast(content_dim), "content_id", "left")
    # -- Bronze metadata --
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("source_system", F.lit("synthetic_generator"))
    .withColumn("batch_id", F.lit(BATCH_ID))
)

print(f"✅ bronze_events enriched — {len(bronze_events.columns)} columns")
bronze_events.printSchema()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7 · Write Bronze Delta Tables
# MAGIC
# MAGIC **Direct to Delta** — no intermediate parquet/Volume hop.
# MAGIC When data is born in Spark, Bronze Delta is the first durable layer.
# MAGIC
# MAGIC **`repartition(8)`** on the fact table sizes files for downstream reads (~12.5K rows/file).
# MAGIC Dims are tiny — no repartition needed.

# COMMAND ----------

# -- Dims --
content_dim.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_content")
print(f"  ✓ {CATALOG}.{SCHEMA}.bronze_content")

subscriber_dim.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_subscribers")
print(f"  ✓ {CATALOG}.{SCHEMA}.bronze_subscribers")

# -- Fact (repartition for file sizing) --
(
    bronze_events
    .repartition(8)
    .write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_stream_events")
)
print(f"  ✓ {CATALOG}.{SCHEMA}.bronze_stream_events")

print(f"\n✅ All Bronze tables written to {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8 · Validate
# MAGIC Row counts + quick distribution check. One scan each — no repeated `count()` calls.

# COMMAND ----------

for tbl in ["bronze_content", "bronze_subscribers", "bronze_stream_events"]:
    cnt = spark.table(f"{CATALOG}.{SCHEMA}.{tbl}").count()
    print(f"  {tbl}: {cnt:,}")

# Quick distribution sanity
print("\n── Genre Distribution ──")
spark.table(f"{CATALOG}.{SCHEMA}.bronze_stream_events").groupBy("genre").count().orderBy(F.desc("count")).show()

print("── Plan Distribution ──")
spark.table(f"{CATALOG}.{SCHEMA}.bronze_stream_events").groupBy("plan_type").count().orderBy(F.desc("count")).show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Done — Next Steps
# MAGIC 1. **Scale:** Change `N_EVENTS = 1_000_000` and re-run (same code, no changes)
# MAGIC 2. **SDP Pipeline:** SQL-based Silver (clean/dedup) → Gold (aggregate) on these Bronze tables
# MAGIC 3. **Dashboard:** AI/BI dashboard on Gold tables
