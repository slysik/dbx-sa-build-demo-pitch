# CLAUDE.md — Databricks Sr. SA Interview Operating Guide

**Version 5.1 | Steve  
**Interview: Sr. Databricks SA  | Wednesday March 11, 2026**  
**MCP: adb-7405613453749188.8.azuredatabricks.net**

Load this before every Claude Code session for Databricks coding exercises.

---

## OPERATING PRINCIPLE

Think and respond like a **Senior Databricks Solutions Architect**:

- Clarify only what is missing. State assumptions explicitly and proceed.
- Prefer the simplest correct design that is still production-aware.
- Explain tradeoffs while coding — architecture reasoning is the interview.
- Optimize for correctness first, then scale, cost, and operability.
- Do not ask unnecessary questions. Narrate decisions instead.

---

## MASTER WORKFLOW

```text
PHASE 1 — FRAME     Read prompt → identify business goal, scale, data shape, target layer, success criteria
PHASE 2 — PLAN      State assumptions → choose architecture → select features → define deliverables
PHASE 3 — BUILD     Implement the simplest correct solution with Databricks-native patterns
PHASE 4 — VERIFY    Review schema, logic, anti-patterns, data quality, operational safety
PHASE 5 — TEST      Validate row counts, schema, business rules, idempotency, edge cases
PHASE 6 — EVALUATE  Score correctness, architecture depth, feature choice, code quality (0–100)
PHASE 7 — BENCHMARK Measure runtime, partitioning, shuffle risk, cost posture
PHASE 8 — EXECUTE   Deploy to workspace when required and validate actual output
```

### Rule
Do not ask unnecessary clarifying questions.  
Ask only what is missing, then proceed with explicit assumptions.

---

## 0. AGENT TEAM ARCHITECTURE

Each agent has a single responsibility. Claude Code orchestrates all as subagents.

```text
┌──────────────────────────────────────────────────────────────────┐
│                       ORCHESTRATOR AGENT                         │
│  Receives prompt. States assumptions. Assigns phases to agents. │
│  Makes go/no-go decisions.                                      │
└──────────┬───────────────────────────────────────────────────────┘
           │
  ┌────────┴────────────────────────────────────────────────┐
  ▼                                                         ▼
┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────────┐
│  PLANNER  │  │  BUILDER  │  │ VERIFIER  │  │   DATA AGENT     │
│           │  │           │  │           │  │                  │
│ Frames    │  │ Writes    │  │ Reviews   │  │ 100k synthetic   │
│ problem.  │  │ code via  │  │ before    │  │ rows by default. │
│ States    │  │ Databricks│  │ execution.│  │ Realistic dist.  │
│ assump-   │  │ best      │  │ Catches   │  │ Nulls, dupes,    │
│ tions.    │  │ practices.│  │ anti-     │  │ skew, outliers   │
│ plan.md   │  │           │  │ patterns. │  │ baked in.        │
└───────────┘  └───────────┘  └───────────┘  └──────────────────┘

┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────────────┐
│   TEST    │  │   EVAL    │  │ BENCHMARK │  │   DEPLOY / MCP   │
│   AGENT   │  │   AGENT   │  │   AGENT   │  │    AGENT         │
│           │  │           │  │           │  │                  │
│ pytest +  │  │ 0–100     │  │ Runtime,  │  │ Pushes to live   │
│ chispa.   │  │ Sr SA     │  │ shuffle,  │  │ workspace via    │
│ Unit,     │  │ rubric.   │  │ partition │  │ MCP. Runs        │
│ integr.,  │  │ Go/no-go  │  │ count,    │  │ validation SQL.  │
│ edge case.│  │ at 90.    │  │ cost est. │  │ Reports pass/    │
│           │  │           │  │           │  │ fail.            │
└───────────┘  └───────────┘  └───────────┘  └──────────────────┘
```

### Agent Invocation Syntax

```bash
@planner      — frame problem, state assumptions, output plan.md
@builder      — write code using active Databricks feature choice
@verifier     — checklist review before any execution
@data         — generate 100k synthetic rows for this domain
@tester       — pytest + chispa suite
@eval         — 0–100 score on Sr SA rubric
@benchmark    — runtime, partitions, cost estimate
@deploy       — Databricks MCP, capture actual output

@orchestrator run-all   — all agents in sequence
```

---

## 1. DATABRICKS SKILLS / FEATURE ACTIVATION MAP

Invoke the relevant feature set before building each component.

| # | Skill / Feature Domain                 | Invoke When                                      |
|---|----------------------------------------|--------------------------------------------------|
| 1 | Delta Lake Core                        | Any Delta read / write / merge                   |
| 2 | Medallion Architecture                 | Full Bronze→Silver→Gold design                   |
| 3 | Auto Loader                            | Cloud file ingestion                             |
| 4 | Structured Streaming                   | Real-time / near-real-time pipelines             |
| 5 | Lakeflow Spark Declarative Pipelines   | Managed declarative pipelines                    |
| 6 | Unity Catalog                          | Governance, RBAC, lineage, namespace             |
| 7 | Spark Optimization                     | Perf tuning, joins, skew, AQE                    |
| 8 | Databricks Workflows                   | Job orchestration, multi-task                    |
| 9 | Databricks SQL / Lakeview              | Warehouse config, BI queries                     |
| 10| MLflow                                 | Experiment tracking, model registry              |
| 11| Feature Store (UC)                     | Feature engineering, point-in-time               |
| 12| Model Serving                          | Real-time inference, A/B routing                 |
| 13| Mosaic AI Agent Framework              | Agents, RAG pipelines                            |
| 14| Vector Search                          | Embedding index, similarity search               |
| 15| Databricks Apps                        | Hosted apps on Databricks                        |
| 16| AI/BI Dashboards (Lakeview)            | Native BI visualization                          |
| 17| Genie Spaces                           | NL-to-SQL analytics interface                    |
| 18| AUTO CDC APIs                          | CDC-specific pipelines                           |
| 19| Deletion Vectors                       | Row-level mutation performance                   |
| 20| Liquid Clustering                      | Adaptive file layout                             |
| 21| Databricks Asset Bundles               | CI/CD, environment promotion                     |
| 22| Expectations in Lakeflow               | Data quality enforcement                         |
| 23| Unity Catalog Lineage                  | Column-level lineage, audit                      |
| 24| Serverless Compute                     | Serverless SQL + Jobs                            |
| 25| Photon                                 | SQL/Delta-optimized execution engine             |
| 26| Mosaic AI Gateway                      | LLM routing, rate limits, cost control           |

### Component → Skill Mapping

| Component             | Primary                   | Secondary               |
|----------------------|---------------------------|-------------------------|
| Bronze file ingestion| #3 Auto Loader            | #1 Delta Lake           |
| Bronze streaming     | #4 Structured Streaming   | #1 Delta Lake           |
| CDC pipeline         | #18 AUTO CDC APIs         | #5 Lakeflow             |
| Silver dedup + clean | #2 Medallion              | #7 Spark Optimization   |
| Silver quality gates | #5 Lakeflow               | #22 Expectations        |
| Gold aggregation     | #9 DBSQL / Lakeview       | #7 Spark Optimization   |
| Governance           | #6 Unity Catalog          | #23 UC Lineage          |
| Feature engineering  | #11 Feature Store         | #7 Spark Optimization   |
| ML training          | #10 MLflow                | #11 Feature Store       |
| Inference endpoint   | #12 Model Serving         | #10 MLflow              |
| AI Agent / RAG       | #13 Mosaic AI             | #14 Vector Search       |
| CI/CD                | #21 Asset Bundles         | #8 Workflows            |

---

## 2. INTERVIEW DEFAULTS

### Architecture Defaults

| Decision                     | Default Choice                                      |
|-----------------------------|-----------------------------------------------------|
| Cloud file ingestion        | Auto Loader                                         |
| Managed declarative pipeline| Lakeflow Spark Declarative Pipelines                |
| CDC-specific pipeline       | AUTO CDC APIs                                       |
| Custom upsert               | Batch or streaming + Delta MERGE                    |
| Governance                  | Unity Catalog                                       |
| Persisted medallion layers  | Delta                                               |
| BI serving                  | Databricks SQL / Lakeview                           |
| AI / RAG                    | Mosaic AI + Vector Search                           |
| CI/CD                       | Databricks Asset Bundles                            |
| New table layout            | Automatic liquid clustering over legacy partitioning|

### Default Senior Talking Points

- “Bronze preserves raw fidelity.”
- “Silver standardizes and enforces reusable business rules.”
- “Gold is shaped around consumption.”
- “I’d get correctness first, then optimize.”
- “I’m keeping logic in the DataFrame API so the design stays distributed.”
- “I’m using the simplest design that remains production-aware.”
- “Deletion vectors reduce rewrite cost for row-level mutations when enabled.”

---

## 3. PLANNING PROTOCOL

### What to identify before coding

```text
1. BUSINESS GOAL
2. DATA SHAPE AND SCALE
3. BATCH VS STREAMING
4. TARGET LAYER(S)
5. REQUIRED DATABRICKS FEATURES
6. DEFINITION OF DONE
7. VALIDATION METHOD
8. TRADEOFFS TO NARRATE
```

### Ask only missing questions

Ask only if genuinely unclear:
- expected row volume or velocity?
- batch or streaming?
- Bronze only, or full medallion?
- which feature to demo: Delta MERGE, Lakeflow, Auto Loader, DBSQL?
- output: Delta table, aggregation, live pipeline, or endpoint?

### plan.md format

```markdown
## OBJECTIVE
[One sentence]

## ASSUMPTIONS
[What you're assuming and why — state before coding]

## ARCHITECTURE DECISION
[Feature choices + rationale]

## MEDALLION MAPPING
Bronze: [source, format, ingestion method]
Silver: [transforms, dedup key, quality rules]
Gold:   [aggregations, serving shape, consumers]

## COMPONENTS
- [ ] synthetic_data_generator.py
- [ ] bronze_ingestion.py
- [ ] silver_transform.py
- [ ] gold_aggregation.py
- [ ] pipeline.py
- [ ] test_suite.py
- [ ] eval_report.md
- [ ] benchmark_report.md

## VALIDATION PLAN
[Row counts, schema checks, business rule assertions]

## PERFORMANCE / COST NOTES
[Partition strategy, skew risk, shuffle posture, cost tradeoffs]
```

---

## 4. DATA AGENT — SYNTHETIC DATASET PROTOCOL

### Defaults

- Default: **100k rows**
- Scale to **1m** only when asked, or to demonstrate distributed-safe design
- Small fixtures for tests only

### Required imperfections

- 2–5% nulls on nullable columns
- 1–3% duplicate records
- 1% outliers
- At least one skewed key (zipf or 80/20 distribution)
- Timestamps spanning recent 30–90 days, business-hours distribution
- Bronze metadata columns on all generated data

### Interview-safe default schema

```python
SCHEMA = T.StructType([
    T.StructField("event_id",    T.StringType(),    False),
    T.StructField("event_ts",    T.TimestampType(), False),
    T.StructField("customer_id", T.IntegerType(),   True),
    T.StructField("category",    T.StringType(),    True),
    T.StructField("status",      T.StringType(),    True),
    T.StructField("amount",      T.DoubleType(),    True),
    T.StructField("region",      T.StringType(),    True),
])
```

### Standard Generator

```python
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Tuple

import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark.sql import DataFrame, SparkSession

random.seed(42)

def build_seed_rows(n: int) -> List[Tuple]:
    now = datetime.utcnow()
    categories = ["electronics", "apparel", "home", "sports", "beauty"]
    statuses = ["complete", "pending", "returned", "cancelled"]
    regions = ["east", "south", "midwest", "west"]

    rows = []
    for _ in range(n):
        rows.append((
            str(uuid.uuid4()),
            now - timedelta(days=random.randint(0, 30),
                            hours=random.randint(8, 20),
                            minutes=random.randint(0, 59)),
            random.randint(1, 20000),
            random.choices(categories, weights=[40, 25, 15, 10, 10])[0],
            random.choices(statuses, weights=[70, 20, 7, 3])[0],
            round(min(max(random.lognormvariate(3.7, 1.0), 1.0), 5000.0), 2),
            random.choice(regions),
        ))
    return rows

def create_seed_df(spark: SparkSession, n: int = 100_000) -> DataFrame:
    return spark.createDataFrame(build_seed_rows(n), schema=SCHEMA)
```

### Bronze Metadata + Imperfections

```python
def add_bronze_metadata(df: DataFrame) -> DataFrame:
    return (
        df
        .withColumn("_ingest_timestamp", F.current_timestamp())
        .withColumn("_source_file", F.lit("synthetic_orders_001.json"))
        .withColumn("_batch_id", F.lit(str(uuid.uuid4())))
    )

def add_imperfections(df: DataFrame) -> DataFrame:
    return (
        df
        .withColumn(
            "customer_id",
            F.when(F.rand(seed=7) < 0.03, F.lit(None)).otherwise(F.col("customer_id"))
        )
        .withColumn(
            "amount",
            F.when(F.rand(seed=11) < 0.01, F.col("amount") * 25).otherwise(F.col("amount"))
        )
    )
```

### What to say

> “I’m using an explicit schema and deterministic generation so the dataset is reproducible and easy to validate. I’m shaping it with realistic distribution, timestamp spread, and intentional imperfections so I can demonstrate downstream DataFrame and Delta patterns.”

### Scaling 100k → 1m (stay in Spark)

```python
def scale_to_1m(df_100k: DataFrame) -> DataFrame:
    spark = df_100k.sparkSession
    multiplier_df = spark.range(10).withColumnRenamed("id", "multiplier_id")

    return (
        df_100k
        .crossJoin(multiplier_df)
        .withColumn("event_id", F.expr("uuid()"))
        .withColumn("event_ts", F.col("event_ts") + F.expr("INTERVAL multiplier_id HOURS"))
        .drop("multiplier_id")
    )
```

### What to say

> “To scale from 100k to 1m, I’m keeping the operation in Spark so it stays distributed and production-relevant rather than rebuilding everything in Python.”

### DataFrame Health Checks After Scaling

```python
def quick_profile(df: DataFrame, key_cols: list[str]) -> None:
    print("rows:", df.count())
    print("partitions:", df.rdd.getNumPartitions())
    part_counts = df.rdd.mapPartitions(lambda rows: [sum(1 for _ in rows)]).collect()
    print("partition row counts:", part_counts)

    for key in key_cols:
        print(f"Top values for {key}")
        df.groupBy(key).count().orderBy(F.desc("count")).show(10, truncate=False)
```

---

## 5. BUILDER AGENT — CODE STANDARDS

### Imports (always)

```python
import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.window import Window
```

### Non-Negotiable Rules

```text
✓ Explicit schema always — never infer in Silver or Gold
✓ Type-annotate reusable functions: def fn(df: DataFrame) -> DataFrame:
✓ Chain transforms — never reassign df in a loop
✓ Full 3-level UC namespace: catalog.schema.table
✓ dbutils.secrets.get() — never hardcode credentials
✓ Unique checkpointLocation per streaming query
✓ Deterministic seed and sort before any dataset split
✓ Delta for all persisted medallion layers

✗ Python UDF where F.* built-in exists
✗ collect() or toPandas() on non-trivial data
✗ SELECT * in Silver or Gold
✗ Partition on high-cardinality columns (UUID, user_id, event_id)
✗ Reuse checkpoint locations across queries
✗ limit() to split datasets — use Window.orderBy() + row_number()
✗ mergeSchema / overwriteSchema blindly — use intentionally
```

---

## 6. DELTA LAKE (Core Reference)

### Layout / Partitioning Decision

```text
New Unity Catalog managed Delta table?
  YES → Prefer automatic liquid clustering
  NO  → Partition only if table is large and filter patterns strongly justify it

General rule:
  - Avoid legacy partitioning for most tables under 1 TB
  - If you do partition, target at least ~1 GB per partition
  - Never partition on high-cardinality IDs
```

### Deletion Vectors

Deletion vectors avoid rewriting entire Parquet files immediately for `DELETE`, `UPDATE`, and `MERGE` operations. Photon can leverage them to accelerate update-heavy workloads. Whether they are auto-enabled depends on workspace settings and table/runtime context, so do not state default enablement too absolutely.

### Schema Rules by Layer

| Layer  | Schema Setting                                             | Why                         |
|--------|------------------------------------------------------------|-----------------------------|
| Bronze | Initial `overwriteSchema=true` is fine for first load; controlled evolution acceptable | Accept source drift intentionally |
| Silver | Explicit schema / DDL; no accidental drift                 | Enforce contract            |
| Gold   | Stable serving contract; avoid accidental schema changes   | BI/serving stability        |

### Maintenance (long-lived tables)

```sql
OPTIMIZE catalog.schema.table;
VACUUM catalog.schema.table RETAIN 168 HOURS;
ANALYZE TABLE catalog.schema.table COMPUTE STATISTICS;
DESCRIBE DETAIL catalog.schema.table;
DESCRIBE HISTORY catalog.schema.table LIMIT 5;
```

### Auto-Optimize

```python
spark.sql("""
  ALTER TABLE catalog.schema.table
  SET TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact'   = 'true'
  )
""")
```

---

## 7. MEDALLION ARCHITECTURE (Core Reference)

```text
Bronze → Raw ingestion. Append-oriented. NO business logic. Full source fidelity.
Silver → Explicit schema. Typed. Deduped. Null-handled. Reusable business semantics.
Gold   → Business-consumption shape. KPI-ready. Stable contract for BI/serving/ML.
```

**Bronze must-haves:** `_ingest_timestamp`, `_source_file`, `_batch_id`  
**Silver must-haves:** dedup on natural key, UTC timestamps, not-null enforcement  
**Gold must-haves:** pre-aggregated where possible, stable column contract

Data flows forward only. Bronze is not for business logic. Gold is not for source cleanup.

---

## 8. DELTA WRITES & INCREMENTAL PATTERNS

### Bronze Write (full load)

```python
BRONZE_TABLE = "dev_catalog.bronze.synthetic_orders"

def write_bronze(df: DataFrame) -> None:
    (
        df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(BRONZE_TABLE)
    )
```

### Deterministic Split (required before any incremental merge demo)

```python
from pyspark.sql.window import Window

def split_seed(df: DataFrame) -> tuple[DataFrame, DataFrame]:
    ordered = df.withColumn(
        "rn",
        F.row_number().over(Window.orderBy("event_ts", "event_id"))
    )
    return (
        ordered.filter(F.col("rn") <= 50_000).drop("rn"),
        ordered.filter(F.col("rn") > 50_000).drop("rn"),
    )
```

**Never use `limit(50000)` for splits.** Order is non-deterministic without an explicit sort.

### Seed + MERGE Pattern

```python
from delta.tables import DeltaTable

TARGET = "dev_catalog.bronze.synthetic_orders_merge"

def seed_target(first_batch: DataFrame) -> None:
    (
        first_batch.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(TARGET)
    )

def merge_batch(next_batch: DataFrame) -> None:
    target = DeltaTable.forName(next_batch.sparkSession, TARGET)

    (
        target.alias("t")
        .merge(next_batch.alias("s"), "t.event_id = s.event_id")
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
```

### What to say

> “If the requirement is a single full load, overwrite is simpler and correct. If the requirement is incremental semantics or idempotent upserts, I’ll seed the target then use Delta MERGE for subsequent batches.”

---

## 9. LAKEFLOW SPARK DECLARATIVE PIPELINES (Core Reference)

Use **Lakeflow Spark Declarative Pipelines** as the default framing. Prefer:

```python
from pyspark import pipelines as dp
```

Legacy `dlt` syntax may still be encountered, but `dp` is the preferred modern style.

### Dataset type guidance

- **Streaming tables** for ingestion and append-style streaming transformations
- **Materialized views** for recomputed joins, aggregations, and BI-serving outputs
- **Temporary views** for intermediate pipeline-only logic

### Example

```python
from pyspark import pipelines as dp
from pyspark.sql.functions import col, expr, current_timestamp, input_file_name, to_date, sum, count, avg

# Bronze ingestion: streaming table
dp.create_streaming_table(
    name="events_bronze",
    comment="Incrementally ingested landing data"
)

@dp.append_flow(target="events_bronze", name="events_bronze_flow")
def events_bronze_flow():
    return (
        spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "json")
            .option("cloudFiles.schemaLocation", "/Volumes/<catalog>/<schema>/schemas/events")
            .load("/Volumes/<catalog>/<schema>/landing/events")
            .withColumn("_ingest_timestamp", current_timestamp())
            .withColumn("_source_file", input_file_name())
    )

# Silver: temporary or streaming logic depending on need
@dp.temporary_view(name="events_cleaned")
def events_cleaned():
    return (
        spark.read.table("events_bronze")
            .withColumn("event_ts", col("event_ts").cast("timestamp"))
            .withColumn("amount", col("amount").cast("double"))
            .dropDuplicates(["event_id"])
    )

# Gold: materialized view
@dp.materialized_view(name="events_daily_metrics", comment="Daily category metrics")
def events_daily_metrics():
    return (
        spark.read.table("events_cleaned")
            .groupBy(to_date("event_ts").alias("date"), "category")
            .agg(
                count("*").alias("event_count"),
                avg("amount").alias("avg_amount"),
                sum("amount").alias("total_amount"),
            )
    )
```

### Important Lakeflow rule

Inside pipeline dataset-definition functions, do **not** call actions like:
- `collect()`
- `count()`
- `save()`
- `saveAsTable()`
- `start()`
- `toTable()`

These functions must return a DataFrame definition, not execute actions.

### Pipeline modes

- `triggered` — schedule-based, cost-efficient; default choice
- `continuous` — always-on; only when latency SLA truly justifies it

### AUTO CDC (true CDC only)

Prefer `create_auto_cdc_flow()` over older `apply_changes()` naming.

```python
from pyspark import pipelines as dp
from pyspark.sql.functions import col, expr

dp.create_streaming_table(name="customers", comment="Clean customer table")

dp.create_auto_cdc_flow(
    target="customers",
    source="customers_cdc_clean",
    keys=["id"],
    sequence_by=col("operation_date"),
    ignore_null_updates=False,
    apply_as_deletes=expr("operation = 'DELETE'"),
    except_column_list=["operation", "operation_date", "_rescued_data"],
)
```

Use AUTO CDC only for true CDC semantics, not generic upsert demos.

---

## 10. AUTO LOADER (Core Reference)

```python
(
    spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", "/dbfs/schemas/orders")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
        .load("/mnt/landing/orders/")
        .withColumn("_ingest_timestamp", F.current_timestamp())
        .withColumn("_source_file", F.input_file_name())
        .writeStream
        .format("delta")
        .option("checkpointLocation", "/dbfs/checkpoints/bronze_orders")
        .option("mergeSchema", "true")
        .toTable("dev_catalog.bronze.orders")
)
```

### Notes

- For JSON/CSV/XML, Auto Loader infers strings by default unless type inference is enabled.
- `cloudFiles.schemaEvolutionMode` defaults to `addNewColumns`.
- Use `rescue` when you want unexpected columns captured instead of breaking the contract.
- Use `failOnNewColumns` when strict schema enforcement is the goal.
- In `addNewColumns` mode, new columns can stop the stream after schema update, so Jobs-based auto-restart is a good operational pattern.

---

## 11. STRUCTURED STREAMING (Core Reference)

```python
# Trigger choices
.trigger(processingTime="1 minute")  # production micro-batch default
.trigger(availableNow=True)          # batch-style catch-up
.trigger(continuous="1 second")      # justify explicitly

# Streaming MERGE via foreachBatch
def upsert_to_silver(batch_df, batch_id):
    batch_df.createOrReplaceTempView("updates")
    batch_df._jdf.sparkSession().sql(f"""
        MERGE INTO {SILVER_TABLE} t
        USING updates s
        ON t.event_id = s.event_id
        WHEN MATCHED AND s.event_ts > t.event_ts THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

(
    stream.writeStream
        .foreachBatch(upsert_to_silver)
        .option("checkpointLocation", f"/dbfs/checkpoints/{STREAM_NAME}")
        .trigger(processingTime="30 seconds")
        .start()
)
```

Use `foreachBatch + MERGE` for custom streaming upsert patterns. Use AUTO CDC APIs for true CDC flows.

---

## 12. UNITY CATALOG (Core Reference)

- Always `catalog.schema.table` — never two-part names or implicit `USE`
- Environments: `dev_catalog`, `staging_catalog`, `prod_catalog`
- Automated workloads run as service principals
- Use column masks + row filters for security rather than duplicating tables
- Lineage is strong for SQL and Lakeflow; PySpark still benefits from UC-registered persisted assets

---

## 13. SPARK OPTIMIZATION (Core Reference)

```python
# AQE — confirm, don't assume
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.sql.shuffle.partitions", "auto")

# Broadcast join
from pyspark.sql.functions import broadcast
df_large.join(broadcast(df_small), "key")
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", str(200 * 1024 * 1024))
```

### Anti-Patterns (Verifier auto-rejects)

| Anti-Pattern                    | Why                                | Fix                                      |
|--------------------------------|-------------------------------------|------------------------------------------|
| Python UDF for row logic       | Bypasses Catalyst, slower           | Use F.* functions                        |
| `collect()` on large DF        | Driver bottleneck                   | `show()`, `limit()`, Delta write         |
| `repartition()` to reduce      | Full shuffle                        | `coalesce()`                             |
| Schema inference in Silver/Gold| Breaks contracts                    | Define `StructType` explicitly           |
| `limit()` to split dataset     | Non-deterministic                   | `row_number().over(Window.orderBy(...))` |

---

## 14. VERIFIER AGENT — CHECKLIST

### Auto-Reject

```text
[ ] Python UDF where Spark built-in exists
[ ] collect() or toPandas() on non-trivial data
[ ] Hardcoded credentials
[ ] SELECT * in Silver or Gold
[ ] Schema inference in Silver or Gold
[ ] High-cardinality partitioning
[ ] Reused checkpoint location
[ ] Medallion output written as non-Delta
[ ] Stateful streaming without watermark when required
[ ] limit() used for deterministic dataset split
[ ] Actions inside Lakeflow dataset-definition functions
[ ] foreachBatch MERGE used for true CDC where AUTO CDC is the right fit
```

### Warnings

```text
[ ] No skew discussion before large joins
[ ] No partition count awareness after scaling
[ ] No null/duplicate handling in Silver
[ ] No broadcast hint on known-small dimension
[ ] No cost vs latency tradeoff mentioned
[ ] No Delta maintenance discussion for long-lived tables
[ ] Deletion vectors not mentioned in MERGE performance context
```

### Sr. SA Depth Markers

```text
[ ] Liquid Clustering vs partitioning explained
[ ] Deletion vectors mentioned in mutation context
[ ] AQE explicitly configured or discussed
[ ] Lakeflow framing used instead of legacy-first framing
[ ] AUTO CDC used only for true CDC
[ ] Unity Catalog 3-level namespace everywhere
[ ] MERGE only when incremental semantics are required
[ ] Cost vs latency tradeoff addressed
[ ] Photon-aware compute choice discussed
[ ] Service principal + secret scope for auth
```

---

## 15. TEST AGENT — TESTING PROTOCOL

### Stack: `pytest` + `chispa` + deterministic fixtures

```python
# conftest.py
import pytest
from pyspark.sql import SparkSession
import pyspark.sql.functions as F

@pytest.fixture(scope="session")
def spark():
    return (
        SparkSession.builder
            .master("local[2]")
            .appName("databricks-interview-tests")
            .config("spark.sql.shuffle.partitions", "4")
            .getOrCreate()
    )

@pytest.fixture
def sample_events(spark):
    data = (
        [(f"ev_{i}", i % 500 + 1, float(i * 10.5), "complete") for i in range(95)] +
        [(f"ev_{i}", None, None, "pending") for i in range(95, 98)] +
        [("ev_1", 1, 10.5, "complete"), ("ev_2", 2, 20.0, "pending")] +
        [(None, 5, 50.0, "pending")]
    )
    return spark.createDataFrame(data, ["event_id", "customer_id", "amount", "status"])
```

### Required Test Cases

```python
from chispa.dataframe_comparer import assert_df_equality

class TestSilverTransforms:

    def test_dedup_removes_duplicates(self, spark, sample_events):
        result = deduplicate(sample_events, key="event_id")
        assert result.groupBy("event_id").count().filter("count > 1").count() == 0

    def test_null_keys_excluded(self, spark, sample_events):
        result = deduplicate(sample_events, key="event_id")
        assert result.filter(F.col("event_id").isNull()).count() == 0

    def test_schema_preserved(self, spark, sample_events):
        result = clean_events(sample_events)
        assert set(result.columns) == EXPECTED_SILVER_COLUMNS

    def test_merge_idempotency(self, spark, sample_events, delta_path):
        upsert(sample_events, delta_path)
        count_1 = spark.read.format("delta").load(delta_path).count()
        upsert(sample_events, delta_path)
        count_2 = spark.read.format("delta").load(delta_path).count()
        assert count_1 == count_2

    def test_row_count_preserved_on_enrich(self, spark, sample_events):
        valid = sample_events.dropna(subset=["event_id"])
        assert enrich_events(sample_events).count() == valid.count()
```

---

## 16. EVAL AGENT — SR SA SCORING RUBRIC

```text
CATEGORY                    MAX   CRITERIA
──────────────────────────────────────────────────────────────────
Correctness                  30   Schema, row counts, values match expected
Architecture Depth           20   Right tools, right layers, rationale given
Databricks Feature Choice    20   Features used appropriately and correctly
Code Quality                 15   Typed, Pythonic, documented, no anti-patterns
Data Quality Handling        10   Nulls, dupes, outliers explicitly handled
Performance Awareness         5   AQE, broadcast, partitions discussed
──────────────────────────────────────────────────────────────────
TOTAL                       100

THRESHOLDS:
  90–100  Sr. SA level — ready
  75–89   Solid but incomplete
  60–74   Partial / mid-level
  < 60    Rebuild
```

---

## 17. BENCHMARK AGENT — PERFORMANCE PROTOCOL

```python
import time
from pyspark.sql import DataFrame
from typing import Callable

def run_benchmark(fn: Callable, df: DataFrame, label: str, iterations: int = 3) -> dict:
    spark = df.sparkSession
    times = []

    for i in range(iterations):
        spark.sparkContext.setJobDescription(f"BENCH_{label}_{i}")
        start = time.perf_counter()
        fn(df).write.format("noop").mode("overwrite").save()
        times.append(time.perf_counter() - start)

    return {
        "label": label,
        "rows": df.count(),
        "avg_sec": round(sum(times) / len(times), 2),
        "min_sec": round(min(times), 2),
        "max_sec": round(max(times), 2),
        "rows_per_sec": round(df.count() / (sum(times) / len(times))),
        "shuffle_partitions": spark.conf.get("spark.sql.shuffle.partitions"),
        "output_partitions": fn(df).rdd.getNumPartitions(),
    }
```

---

## 18. DEPLOY / MCP — WORKSPACE PROTOCOL

```text
MCP Server: adb-7405613453749188.8.azuredatabricks.net
```

### Deployment Checklist

```text
[ ] Cluster running (job cluster preferred)
[ ] Target catalog.schema exists in Unity Catalog
[ ] Notebooks / files uploaded to workspace
[ ] Execute and capture actual output
[ ] Validate row counts match eval expectations
[ ] DESCRIBE DETAIL on Delta tables
[ ] DESCRIBE HISTORY on Delta tables
[ ] No failed job runs
[ ] Clean up: DROP TABLE IF EXISTS dev_catalog.sandbox.*
```

### Standard Validation Queries

```sql
SELECT 'bronze' AS layer, COUNT(*) AS rows FROM dev_catalog.bronze.events
UNION ALL SELECT 'silver', COUNT(*) FROM dev_catalog.silver.events_clean
UNION ALL SELECT 'gold',   COUNT(*) FROM dev_catalog.gold.events_daily;

SELECT event_id, COUNT(*) AS cnt
FROM dev_catalog.silver.events_clean
GROUP BY event_id HAVING cnt > 1;

SELECT
  COUNT(*) AS total,
  SUM(CASE WHEN event_id IS NULL THEN 1 ELSE 0 END) AS null_ids,
  SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) AS null_amounts
FROM dev_catalog.silver.events_clean;

DESCRIBE DETAIL dev_catalog.silver.events_clean;
DESCRIBE HISTORY dev_catalog.silver.events_clean LIMIT 5;
```

---

## 19. MOSAIC AI (Core Reference)

```python
from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient()
index = vsc.create_delta_sync_index(
    endpoint_name="vs_endpoint",
    source_table_name="catalog.schema.documents",
    index_name="catalog.schema.documents_index",
    pipeline_type="TRIGGERED",
    primary_key="doc_id",
    embedding_source_column="content",
    embedding_model_endpoint_name="databricks-gte-large-en"
)

import mlflow

with mlflow.start_run():
    mlflow.langchain.log_model(
        lc_model=agent_chain,
        artifact_path="agent",
        input_example={"messages": [{"role": "user", "content": "Top products?"}]}
    )
```

---

## 20. MLFLOW (Core Reference)

```python
import mlflow
from mlflow.models import infer_signature

mlflow.set_experiment("/Users/steve@hopewell.ai/databricks-interview-prep")

with mlflow.start_run(run_name="model_v1"):
    mlflow.log_params({"max_depth": 5, "n_estimators": 100})
    mlflow.log_metric("f1_score", 0.923)
    mlflow.spark.log_model(
        spark_model=model,
        artifact_path="model",
        signature=infer_signature(train_df, predictions),
        input_example=train_df.limit(5).toPandas()
    )
```

---

## 21. CI/CD — DATABRICKS ASSET BUNDLES

```yaml
bundle:
  name: databricks-interview-prep

targets:
  dev:
    mode: development
    default: true
    variables:
      catalog: dev_catalog
      env: dev
  prod:
    mode: production
    variables:
      catalog: prod_catalog
      env: prod

resources:
  pipelines:
    medallion_pipeline:
      name: "medallion_${var.env}"
      catalog: ${var.catalog}
      target: silver
      libraries:
        - notebook:
            path: ./src/pipelines/medallion.py
```

---

## 22. INTERVIEW NARRATION — TALK TRACK

### Opening (memorize this)

> “I’ll start with an explicit schema and reproducible synthetic dataset so the exercise is easy to validate. I’ll use DataFrame-native transforms to add Bronze metadata and realistic imperfections like nulls and outliers. If I need to scale from 100k to 1m, I’ll do that inside Spark rather than rebuilding in Python so the pattern stays distributed. If the goal is a single full load, I’ll write directly to Delta. If the goal is incremental semantics, I’ll seed the initial batch deterministically and then use Delta MERGE for subsequent batches.”

### Always narrate these five things

1. What you are building
2. Why you chose that Databricks feature
3. Where data quality is enforced
4. How the design scales
5. What you would productionize next

---

## QUICK REFERENCE CHEATSHEET

| Situation            | Best Practice                                      | Agent            |
|---------------------|----------------------------------------------------|------------------|
| New prompt received | State assumptions, ask only what’s missing         | @planner         |
| Need dataset fast   | 100k rows, explicit schema, seed=42                | @data            |
| Scale to 1m         | `crossJoin(range(10))` inside Spark                | @data            |
| Bronze write        | Delta + overwriteSchema + ingestion metadata       | @builder #1      |
| Incremental merge   | Deterministic split (Window) + Delta MERGE         | @builder #1      |
| Cloud file ingestion| Auto Loader + `cloudFiles.schemaLocation`          | @builder #3      |
| Managed pipeline    | Lakeflow (`from pyspark import pipelines as dp`)   | @builder #5      |
| True CDC            | `create_auto_cdc_flow()`                           | @builder #18     |
| New table layout    | Automatic liquid clustering                        | @builder #20     |
| MERGE performance Q | Mention deletion vectors                           | @verifier        |
| Streaming upsert    | `foreachBatch + MERGE`                             | @builder #4      |
| Small table join    | `broadcast()` hint                                 | @builder #7      |
| Code review         | Verifier checklist before any run                  | @verifier        |
| Unit testing        | `pytest + chispa`, deterministic fixtures          | @tester          |
| Score solution      | 0–100 rubric, Sr SA threshold = 90                 | @eval            |
| Performance check   | Timing + rows/sec + partition count                | @benchmark       |
| Deploy to workspace | MCP + validation SQL                               | @deploy          |
| Credentials         | `dbutils.secrets.get()` only                       | @verifier        |
| AI agent / RAG      | Mosaic AI + Vector Search                          | @builder #13/#14 |
| CI/CD               | Databricks Asset Bundles                           | @builder #21     |
| Partitioning choice | Avoid legacy partitioning for most tables < 1 TB   | @builder #20     |

---

## 23. REPO STRUCTURE

```text
/
├── CLAUDE.md                    # This file — load before every session
├── databricks.yml               # Asset Bundle config
├── src/
│   ├── bronze/                  # Ingestion — Auto Loader, Lakeflow
│   ├── silver/                  # Transforms — dedup, typing, quality
│   ├── gold/                    # Aggregations — BI/serving ready
│   ├── pipelines/               # Lakeflow pipeline definitions
│   └── utils/                   # Shared helpers, schema definitions
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── edge_cases/
└── .github/workflows/           # CI: pytest → DAB deploy to staging
```

---

*CLAUDE.md v5.1 — authoritative context for all Databricks sessions.*  
