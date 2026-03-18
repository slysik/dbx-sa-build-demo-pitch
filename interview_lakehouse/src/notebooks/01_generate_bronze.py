# Databricks notebook source
# MAGIC %md
# MAGIC # Interview Lakehouse — Bronze Generation
# MAGIC | Table | Rows | Notes |
# MAGIC |-------|------|-------|
# MAGIC | `bronze_dim_interviewers` | `N_INTERVIEWERS` | Interviewer attributes and staffing lenses |
# MAGIC | `bronze_dim_candidates` | `N_CANDIDATES` | Candidate profile and application signals |
# MAGIC | `bronze_fact_interviews` | `N_INTERVIEWS` | Scheduled interviews enriched with dim context |
# MAGIC 
# MAGIC Spark-native generation using `spark.range()`, broadcast joins, and Delta writes ready for Silver/Gold SQL.

# COMMAND ----------
import pyspark.sql.functions as F
from pyspark.sql import DataFrame, SparkSession
from datetime import datetime

spark: SparkSession = spark

CATALOG = "dbx_weg"
SCHEMA = "interview"
BATCH_ID = f"batch_{datetime.utcnow().strftime('%Y%m%d')}"

N_INTERVIEWERS = 150
N_CANDIDATES = 2_000
N_INTERVIEWS = 100_000

START_DATE = "2025-01-01"
DAYS_SPAN = 120

spark.conf.set("spark.sql.shuffle.partitions", 16)
print(f"Target: {CATALOG}.{SCHEMA} | Interviews: {N_INTERVIEWS:,} | Batch: {BATCH_ID}")

# COMMAND ----------
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

# COMMAND ----------
dim_interviewers: DataFrame = (
    spark.range(N_INTERVIEWERS)
    .withColumn(
        "interviewer_id",
        F.concat(F.lit("INT-"), F.lpad(F.col("id").cast("string"), 4, "0")),
    )
    .withColumn(
        "department",
        F.when(F.col("id") % 4 == 0, "Solutions Architecture")
        .when(F.col("id") % 4 == 1, "Field Engineering")
        .when(F.col("id") % 4 == 2, "Customer Success")
        .otherwise("Professional Services"),
    )
    .withColumn(
        "experience_band",
        F.when(F.col("id") % 5 < 1, "Lead")
        .when(F.col("id") % 5 < 2, "Senior")
        .when(F.col("id") % 5 < 3, "Mid")
        .when(F.col("id") % 5 < 4, "Associate")
        .otherwise("Principal"),
    )
    .withColumn(
        "panel_specialty",
        F.when(F.rand(seed=11) < 0.35, "Architecture Deep Dive")
        .when(F.rand(seed=13) < 0.65, "Design Exercise")
        .when(F.rand(seed=17) < 0.85, "Whiteboard Collaboration")
        .otherwise("Executive Alignment"),
    )
    .withColumn(
        "preferred_region",
        F.when(F.col("id") % 3 == 0, "AMER")
        .when(F.col("id") % 3 == 1, "EMEA")
        .otherwise("APJ"),
    )
    .withColumn(
        "panel_capacity_per_week",
        (F.col("id") % 6 + 2).cast("int"),
    )
    .drop("id")
)

display(dim_interviewers.limit(10))

# COMMAND ----------
dim_candidates: DataFrame = (
    spark.range(N_CANDIDATES)
    .withColumn(
        "candidate_id",
        F.concat(F.lit("CAN-"), F.lpad(F.col("id").cast("string"), 6, "0")),
    )
    .withColumn(
        "primary_background",
        F.when(F.rand(seed=21) < 0.40, "Data Engineering")
        .when(F.rand(seed=23) < 0.65, "Solutions Architecture")
        .when(F.rand(seed=29) < 0.85, "Consulting")
        .otherwise("Product Management"),
    )
    .withColumn(
        "experience_years",
        (F.rand(seed=31) * 15 + 1).cast("int"),
    )
    .withColumn(
        "current_role_level",
        F.when(F.col("experience_years") <= 3, "Associate")
        .when(F.col("experience_years") <= 6, "Mid")
        .when(F.col("experience_years") <= 10, "Senior")
        .otherwise("Principal"),
    )
    .withColumn(
        "preferred_region",
        F.when(F.col("id") % 4 == 0, "AMER")
        .when(F.col("id") % 4 == 1, "EMEA")
        .when(F.col("id") % 4 == 2, "APJ")
        .otherwise("LATAM"),
    )
    .withColumn(
        "application_channel",
        F.when(F.col("id") % 5 == 0, "Referral")
        .when(F.col("id") % 5 == 1, "Inbound Lead")
        .when(F.col("id") % 5 == 2, "Recruiter Sourced")
        .when(F.col("id") % 5 == 3, "Talent Community")
        .otherwise("Campus"),
    )
    .drop("id")
)

display(dim_candidates.limit(10))

# COMMAND ----------
interview_fact: DataFrame = (
    spark.range(N_INTERVIEWS)
    .withColumnRenamed("id", "interview_seq")
    .withColumn(
        "interview_id",
        F.concat(F.lit("INTVW-"), F.lpad(F.col("interview_seq").cast("string"), 8, "0")),
    )
    .withColumn(
        "interviewer_id",
        F.concat(
            F.lit("INT-"),
            F.lpad((F.col("interview_seq") % N_INTERVIEWERS).cast("string"), 4, "0"),
        ),
    )
    .withColumn(
        "candidate_id",
        F.concat(
            F.lit("CAN-"),
            F.lpad((F.col("interview_seq") % N_CANDIDATES).cast("string"), 6, "0"),
        ),
    )
    .withColumn(
        "interview_stage",
        F.when(F.rand(seed=41) < 0.30, "Recruiter Screen")
        .when(F.rand(seed=43) < 0.55, "Technical Deep Dive")
        .when(F.rand(seed=47) < 0.80, "Panel Presentation")
        .otherwise("Executive Alignment"),
    )
    .withColumn(
        "interview_mode",
        F.when(F.col("interview_seq") % 3 == 0, "In Person").otherwise("Virtual"),
    )
    .withColumn(
        "scheduled_date",
        F.date_add(
            F.lit(START_DATE),
            (F.rand(seed=53) * DAYS_SPAN).cast("int"),
        ),
    )
    .withColumn(
        "scheduled_ts",
        F.to_timestamp(
            F.concat_ws(
                " ",
                F.col("scheduled_date").cast("string"),
                F.lpad((F.rand(seed=59) * 24).cast("int").cast("string"), 2, "0"),
                F.concat_ws(":", F.lpad((F.rand(seed=61) * 60).cast("int").cast("string"), 2, "0"), F.lit("00")),
            )
        ),
    )
    .withColumn(
        "duration_minutes",
        (F.rand(seed=67) * 45 + 30).cast("int"),
    )
    .withColumn(
        "feedback_score",
        F.round(F.rand(seed=71) * 4 + 1, 1),
    )
    .withColumn(
        "decision",
        F.when(F.rand(seed=73) < 0.15, "Offer")
        .when(F.rand(seed=79) < 0.45, "Advance")
        .when(F.rand(seed=83) < 0.75, "Hold")
        .otherwise("Reject"),
    )
    .drop("interview_seq")
)

interview_fact.printSchema()

# COMMAND ----------
bronze_fact_interviews: DataFrame = (
    interview_fact.alias("f")
    .join(F.broadcast(dim_interviewers).alias("i"), "interviewer_id", "left")
    .join(F.broadcast(dim_candidates).alias("c"), "candidate_id", "left")
    .select(
        "f.interview_id",
        "f.interviewer_id",
        "f.candidate_id",
        "f.interview_stage",
        "f.interview_mode",
        "f.scheduled_date",
        "f.scheduled_ts",
        "f.duration_minutes",
        "f.feedback_score",
        "f.decision",
        F.col("i.department").alias("interviewer_department"),
        F.col("i.experience_band").alias("interviewer_experience_band"),
        F.col("i.panel_specialty").alias("interviewer_panel_specialty"),
        F.col("i.preferred_region").alias("interviewer_region"),
        F.col("i.panel_capacity_per_week").alias("interviewer_capacity_per_week"),
        F.col("c.primary_background").alias("candidate_primary_background"),
        F.col("c.experience_years").alias("candidate_experience_years"),
        F.col("c.current_role_level").alias("candidate_role_level"),
        F.col("c.preferred_region").alias("candidate_region"),
        F.col("c.application_channel").alias("candidate_application_channel"),
    )
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("source_system", F.lit("synthetic_interview_pipeline"))
    .withColumn("batch_id", F.lit(BATCH_ID))
)

# COMMAND ----------
dim_interviewers.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{CATALOG}.{SCHEMA}.bronze_dim_interviewers"
)

dim_candidates.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{CATALOG}.{SCHEMA}.bronze_dim_candidates"
)

(
    bronze_fact_interviews.repartition(8)
    .write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_fact_interviews")
)

# COMMAND ----------
for table_name in [
    "bronze_dim_interviewers",
    "bronze_dim_candidates",
    "bronze_fact_interviews",
]:
    full_name = f"{CATALOG}.{SCHEMA}.{table_name}"
    row_count = spark.table(full_name).count()
    print(f"{full_name}: {row_count:,} rows")

spark.table(f"{CATALOG}.{SCHEMA}.bronze_fact_interviews").groupBy("interview_stage").count().orderBy(F.desc("count")).show()
