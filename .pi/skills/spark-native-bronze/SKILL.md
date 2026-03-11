---
name: spark-native-bronze
description: "End-to-end Databricks interview demo: spark.range() Bronze generation, SDP Silver/Gold, metric views, AI/BI dashboards, Asset Bundles, and job orchestration. ALWAYS read this skill FIRST for any synthetic data, medallion pipeline, dashboard, or bundle task. Supersedes Faker/Pandas patterns. See sdp-and-dashboard-patterns.md for Silver/Gold/Dashboard/Bundle gotchas."
---

# Spark-Native Bronze Generation — Canonical Patterns

**Priority:** This skill OVERRIDES `.agents/skills/synthetic-data-generation/SKILL.md` for all synthetic data tasks.

## When to Use
- ANY synthetic data generation for Databricks
- ANY Bronze table creation from generated data
- ANY interview demo dataset (retail, media, IoT, SaaS, FinServ — domain-neutral)
- Scaling datasets from 100 to 1M+ rows

## Core Rules (Non-Negotiable)

1. **`spark.range(N)` for ALL row generation** — distributed, no driver pressure
2. **No Faker, no Pandas, no Python loops** for fact tables (ever)
3. **Dims ≤ 6 columns** — lean, fast to talk through
4. **Direct to Bronze Delta** — no parquet/Volume intermediate (unless demoing Auto Loader)
5. **Broadcast join** tiny dims into fact — no shuffle, no skew
6. **Same code, any scale** — change `N_EVENTS` only, zero logic changes
7. **Less is more** — concise comments, 8 cells max, fast to generate
8. **SQL for Silver/Gold** — PySpark owns generation + Bronze; SDP/SQL owns everything after
9. **Bronze metadata:** `ingest_ts`, `source_system`, `batch_id` (not underscore-prefixed)
10. **One validation pass** at end — no repeated `count()` after each step

## Architecture Flow

```
spark.range(N) → Spark-native columns → broadcast join dims → Bronze Delta
                                                                   ↓
                                                          SQL-based Silver (SDP)
                                                                   ↓
                                                          SQL-based Gold (SDP)
```

## Anti-Patterns — NEVER DO THESE

| ❌ Never | ✅ Always |
|----------|----------|
| Python `for i in range(N): rows.append(...)` | `spark.range(N).withColumn(...)` |
| `pd.DataFrame(rows)` → `spark.createDataFrame(pdf)` | Spark-native column expressions |
| Faker for large datasets | Deterministic `F.concat`, `F.rand`, modulo |
| Write parquet → Volume → read back → Delta | Direct `.saveAsTable()` |
| Repeated `count()` after each step | One validation loop at end |
| Dims with 7+ columns | Max 6 columns per dim table |
| `StructType` schema on Bronze write | Let Spark infer from the DataFrame it just built |
| Complex `%md` essays in notebooks | Short punchy comments, talk the rest |
| `_ingest_timestamp`, `_source_file`, `_batch_id` | `ingest_ts`, `source_system`, `batch_id` |

## Categorical Column Patterns

### Weighted distribution (use for important business segmentation)
```python
.withColumn("_r", F.rand(seed=1))
.withColumn("plan_type",
    F.when(F.col("_r") < 0.40, "free")
     .when(F.col("_r") < 0.65, "basic")
     .when(F.col("_r") < 0.85, "standard")
     .otherwise("premium"))
.drop("_r")
```

### Deterministic / uniform (use for simple categories)
```python
.withColumn("region",
    F.when(F.col("id") % 4 == 0, "North")
     .when(F.col("id") % 4 == 1, "South")
     .when(F.col("id") % 4 == 2, "East")
     .otherwise("West"))
```

## Dimension Template (≤ 6 cols)

```python
dim = (
    spark.range(N_DIM)
    .withColumn("dim_id", F.concat(F.lit("PFX-"), F.lpad(F.col("id").cast("string"), 5, "0")))
    .withColumn("col_a", ...)   # weighted via rand()
    .withColumn("col_b", ...)   # modulo-based
    .withColumn("col_c", ...)   # derived date or numeric
    .withColumn("col_d", ...)   # simple category
    .withColumn("col_e", ...)   # optional 6th col
    .drop("id", "_r")           # clean up helper cols
)
```

## Fact Table Template

```python
fact = (
    spark.range(N_EVENTS)
    .withColumnRenamed("id", "event_seq")
    .withColumn("event_id", F.concat(F.lit("EVT-"), F.lpad(F.col("event_seq").cast("string"), 8, "0")))
    # Foreign keys — modulo guarantees valid dim references
    .withColumn("dim1_id", F.concat(F.lit("PFX1-"), F.lpad((F.col("event_seq") % N_DIM1).cast("string"), 5, "0")))
    .withColumn("dim2_id", F.concat(F.lit("PFX2-"), F.lpad((F.col("event_seq") % N_DIM2).cast("string"), 6, "0")))
    # Date spread across range
    .withColumn("event_date", F.date_add(F.lit(START_DATE), (F.rand(seed=42) * DAYS_SPAN).cast("int")))
    # Timestamp with random hour
    .withColumn("event_ts", F.to_timestamp(
        F.concat(F.col("event_date").cast("string"), F.lit(" "),
                 F.lpad((F.rand(seed=7) * 24).cast("int").cast("string"), 2, "0"), F.lit(":"),
                 F.lpad((F.rand(seed=13) * 60).cast("int").cast("string"), 2, "0"), F.lit(":00"))))
    # Measures
    .withColumn("amount", F.round(F.rand(seed=99) * 500 + 10, 2))
    .withColumn("quantity", (F.col("event_seq") % 5 + 1).cast("int"))
    .drop("event_seq")
)
```

## Broadcast Join + Bronze Metadata + Write

```python
# Enrich fact with dim attributes
bronze = (
    fact
    .join(F.broadcast(dim1), "dim1_id", "left")
    .join(F.broadcast(dim2), "dim2_id", "left")
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("source_system", F.lit("synthetic_generator"))
    .withColumn("batch_id", F.lit(BATCH_ID))
)

# Write dims (small — no repartition)
dim1.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_dim1")
dim2.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_dim2")

# Write fact (repartition for file sizing)
(bronze.repartition(8).write.format("delta")
    .mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_fact"))
```

## Scaling — The Quality Bar

```python
N_EVENTS = 100         # dev/debug
N_EVENTS = 100_000     # interview demo
N_EVENTS = 1_000_000   # scale test
```

**Zero code changes.** If scaling requires different code, the design is wrong.

## Interview Day Execution Order (CRITICAL)

**Notebook-first, pipeline-in-parallel.** The user walks through Bronze while backend deploys SDP.

```
1. Upload notebook → hand URL immediately (user starts walking through on warm cluster)
2. IN PARALLEL: create/update SDP pipeline, upload Silver/Gold SQL, trigger pipeline
3. IN PARALLEL: deploy dashboard JSON, publish with embed_credentials=false
4. By the time user finishes cell 8 → SDP pipeline is COMPLETED, ready for walkthrough
5. Dashboard live → user clicks through after Gold narration
```

**Pre-warm cluster 10 min before interview.** Notebook must be on warm cluster instantly.

## Notebook Structure (8 cells max)

| Cell | Content |
|------|---------|
| 1 | `%md` — Title, table summary (3-line table), pattern note |
| 2 | Config — imports, `CATALOG`, `SCHEMA`, `N_*`, `START_DATE`, `BATCH_ID` |
| 3 | Create schema — `CREATE SCHEMA IF NOT EXISTS` |
| 4 | Dim 1 — `spark.range()` + `display(dim.limit(5))` |
| 5 | Dim 2 — same pattern |
| 6 | Fact — `spark.range(N_EVENTS)` + FK modulo + dates + measures |
| 7 | Broadcast join + metadata + write all 3 tables |
| 8 | Validate — one loop for counts, one `groupBy` distribution check |

## Validation (Single Pass)

```python
for tbl in ["bronze_dim1", "bronze_dim2", "bronze_fact"]:
    cnt = spark.table(f"{CATALOG}.{SCHEMA}.{tbl}").count()
    print(f"  {tbl}: {cnt:,}")

spark.table(f"{CATALOG}.{SCHEMA}.bronze_fact").groupBy("category").count().orderBy(F.desc("count")).show()
```

## Responsibility Split

| Layer | Language | Where |
|-------|----------|-------|
| Synthetic gen + Bronze | PySpark (`spark.range`) | Notebook |
| Silver (clean/dedup/type) | SQL | SDP pipeline |
| Gold (aggregate/mart) | SQL | SDP pipeline |
| Dashboard | SQL queries | AI/BI Dashboard |

## Domain Adaptation — Same Pattern, Different Names

| Domain | Dim 1 | Dim 2 | Fact |
|--------|-------|-------|------|
| **Media** | content (genre, type, duration) | subscribers (plan, country, age) | stream_events |
| **Retail** | products (category, brand, price) | stores (region, format, size) | transactions |
| **SaaS** | accounts (tier, industry, size) | features (module, category) | usage_events |
| **IoT** | devices (type, location, firmware) | sensors (metric, unit) | readings |
| **FinServ** | accounts (type, branch, status) | customers (segment, risk) | transactions |

The code structure is identical — only column names and categories change.

## Interview Talking Points (Memorize These)

1. "spark.range gives us distributed generation — no driver bottleneck at any scale"
2. "Broadcast join because dims are tiny — sent to every executor, zero shuffle"
3. "Same code works at 100 rows or 1M — I just change one parameter"
4. "Direct to Delta Bronze — no wasted I/O landing files we'll just re-read"
5. "Bronze is source-shaped with metadata — Silver handles all business logic in SQL"
6. "Modulo on foreign keys guarantees referential integrity without maintaining lookup maps"
7. "rand() with seed for reproducibility — same data every run for debugging"
8. "repartition(8) before write sizes files for downstream reads"

## Dashboard Deployment Learnings

1. **`embed_credentials: false`** — Always publish dashboards without embedded credentials on this workspace. The personal MS account (@gmail.com via live.com) intermittently loses active status, causing `Principal is not an active member` errors on embedded-credential dashboards.
2. **Test ALL SQL queries via SQL Statements API before building dashboard JSON** — broken queries = broken widgets with no useful error.
3. **Metric view queries in dashboards** — Use `MEASURE()` syntax in the dataset `queryLines`. The dashboard dataset is just a SQL query; metric views work as any other table source.
4. **Field name matching is exact** — `name` in `query.fields` MUST equal `fieldName` in `encodings`. For aggregations: both must be `"sum(col)"`.
5. **Widget versions** — counter=2, table=2, filters=2, bar/line/pie=3. Text widgets have NO spec block.
6. **Text title + subtitle** — Use SEPARATE text widgets at different y positions. Multiple `lines` array items concatenate on one line.
7. **Global filters** — Put on a `PAGE_TYPE_GLOBAL_FILTERS` page. Filter only affects datasets containing the filter column.

## Interview Workflow — Complete Sequence (MUST FOLLOW)

**Every run follows this exact sequence. No shortcuts.**

```
PHASE 1: CLEAN SLATE
  1. Clean workspace: delete old notebooks, pipelines, jobs, dashboards from previous runs
  2. Clean schema: DROP orphaned __materialization_* tables, silver_*, gold_* tables
  3. Keep Bronze tables ONLY if reusing data (otherwise drop everything)

PHASE 2: BUILD + DEPLOY
  4. Generate code: notebook, SDP SQL, dashboard JSON, bundle YAML
  5. ALL code in ONE flat folder: retail_workflow/ (numbered 01_, 02_, 03_, 04_)
  6. bundle validate → bundle deploy → creates pipeline + job in workspace
  7. Upload notebooks to retail_workflow/ for UI viewing

PHASE 3: VALIDATE (MANDATORY — DO NOT SKIP)
  8. Run Bronze notebook on cluster → verify 4 Bronze tables created with correct counts
  9. Start SDP pipeline (full refresh) → poll until IDLE → verify Silver/Gold tables
  10. Test ALL dashboard SQL queries via SQL Statements API → all must return rows
  11. Update/publish dashboard (embed_credentials=false)
  12. Verify job DAG wiring: Bronze → SDP → Validate task chain

PHASE 4: HAND TO USER
  13. Provide ALL URLs: folder, notebook, pipeline, job, dashboard
  14. Use ?o={ws_id}#notebook/{object_id} format for notebook URLs
  15. Commit code to git repo and push as final step
```

**If ANY validation fails → FIX AND RE-VALIDATE before handing URLs.**

## Deployment Fixes — Lessons from Practice Runs (2026-03-10)

### Notebook Format
1. **`# ruff: noqa` must NOT be in the `%md` cell.** It renders as raw text. Put lint suppressions in a separate Python cell, or omit entirely — notebooks don't need ruff directives.
2. **Always verify notebook renders in UI after upload.** Use `workspace import --overwrite` and open the URL before handing to user.

### SDP Pipeline
3. **Silver/Gold SQL files for SDP must be raw SQL — no `-- Databricks notebook source` header.** Use `file:` in pipeline YAML for raw SQL. If the file has notebook markers, bundle validate fails: `expected a file but got a notebook`.
4. **`CREATE OR REFRESH MATERIALIZED VIEW` + `EXPECT` constraints are SDP-only syntax.** They CANNOT run on standalone compute (serverless SQL, cluster, warehouse). Error: `DLT_EXPECTATIONS_NOT_SUPPORTED`. Upload SDP SQL to workspace as notebooks for **viewing only** — run via pipeline Start button.
5. **Old pipeline materialization tables block new pipelines.** If a previous SDP pipeline was deleted but its `__materialization_*` tables remain in the schema, the new pipeline may conflict. Clean up orphaned tables: query `information_schema.tables WHERE table_name LIKE '__materialization%'` and DROP them.
6. **Pipeline + Job must be deployed to workspace (not just YAML on disk).** `bundle deploy` creates them in the UI. Without deploy, Jobs & Pipelines page shows nothing. Always run `bundle validate` then `bundle deploy`.

### Job / DAG
7. **`sql_task.query` requires `query_id` (a saved query), NOT `query_text`.** Inline SQL doesn't work in job YAML. Use a `notebook_task` for validation instead.

### Dashboard
8. **Dashboard `display_name` collision**: If a dashboard with the same name exists, `POST` fails. Use `PATCH /api/2.0/lakeview/dashboards/{id}` to update instead. Always check for existing dashboards first.
9. **Dashboard shows empty widgets until Gold tables have data.** Run Bronze notebook + SDP pipeline first, THEN open dashboard.

### URL Format
10. **Workspace notebook URLs**: Use `?o={workspace_id}#notebook/{object_id}` format. The `/browse/` format is for folders only. Always get `object_id` from `workspace list` and construct URL with it.

### Cleanup Before Each Run
11. **Delete old pipelines before creating new ones.** Old pipeline owns Silver/Gold MVs → new pipeline gets `TABLE_ALREADY_MANAGED_BY_OTHER_PIPELINE`. Fix: delete old pipeline, DROP its silver_*/gold_* tables, DROP __materialization_* tables.
12. **When dropping materialization tables, only drop tables from DELETED pipelines.** Check pipeline ID in table name (`__materialization_mat_{pipeline_id}_*`). Do NOT drop tables belonging to the active pipeline — that corrupts its state and causes "Pipeline initialization failed".
13. **Clean workspace of old notebooks/folders before uploading.** Stale files confuse the user during interview. One folder, numbered files, nothing else.

### Git Integration
14. **Push to git repo as LAST step** after all validation passes. Code in repo = tested code. Never push untested code.
15. **All code in one flat `src/` folder** — notebook + SQL + validate. Numbered for sort order: 01_, 02_, 03_, 04_.

### Execution Order for Full Validation
```
1. Clean workspace + schema  → remove stale artifacts
2. bundle validate           → catch YAML errors
3. bundle deploy             → creates pipeline + job in workspace
4. Upload notebooks          → retail_workflow/ for UI viewing
5. Run Bronze notebook       → verify Bronze Delta tables
6. Start SDP pipeline        → verify Silver/Gold MVs (~3-5 min)
7. Test dashboard queries    → ALL 6 must return rows
8. Deploy/update dashboard   → PATCH if exists, POST if new
9. Publish dashboard         → embed_credentials=false ALWAYS
10. Verify job DAG wiring    → 3 tasks chained correctly
11. Provide ALL URLs         → folder, notebook, pipeline, job, dashboard
12. git commit + push        → tested code to repo
```

## Supplemental References

- **[sdp-and-dashboard-patterns.md](sdp-and-dashboard-patterns.md)** — SDP gotchas, metric view patterns, dashboard REST API, auth/workspace issues. Read when building Silver/Gold/Dashboard.

## Complete Config Block (Copy-Paste Start)

```python
from pyspark.sql import functions as F

CATALOG  = "interview"
SCHEMA   = "my_schema"
BATCH_ID = "batch_001"

N_DIM1   = 200
N_DIM2   = 2_000
N_EVENTS = 100_000    # ← change this to scale

START_DATE = "2025-09-12"
DAYS_SPAN  = 180

print(f"Target: {CATALOG}.{SCHEMA} | Events: {N_EVENTS:,}")
```
