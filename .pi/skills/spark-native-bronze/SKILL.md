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

**If pi `dbx-tools` extension is loaded, use custom tools instead of raw CLI:**
- `dbx_auth_check` instead of `databricks auth describe`
- `dbx_run_notebook` instead of manual runs/submit + polling loop
- `dbx_poll_pipeline` instead of manual pipeline polling loop
- `dbx_validate_tables` instead of individual SQL count queries
- `dbx_deploy_dashboard` instead of manual POST/PATCH + publish
- `dbx_cleanup` instead of manual delete loops
- `dbx_sql` instead of raw SQL Statements API calls

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

## Architecture Slide Narration (4-Layer Databricks Platform)

When the interviewer shows the Databricks platform slide (Spark Compute → Data Lakehouse → Unity Catalog → Analytics & AI), map each layer to the live demo:

**What to say for each layer:**

| Slide Layer | What We Built | Narration |
|---|---|---|
| **Spark Compute** | Serverless notebooks + SDP | *"All compute is serverless — no cluster to manage, auto-scales to zero between runs"* |
| **Data Lakehouse** | Bronze → Silver → Gold → Delta | *"The medallion pattern — Bronze preserves raw fidelity, Silver enforces quality, Gold is consumption-shaped for BI and ML"* |
| **Streaming and batch** | Batch only in demo | *"In production this lands via Auto Loader on S3 or Zerobus for near-real-time ingest — I'm using spark.range() so we can run the full pipeline in under 2 min on serverless"* |
| **Unity Catalog** | `workspace.finserv.*` | *"Three-level namespace — catalog, schema, table. UC gives us column-level lineage, row filters, and audit logs out of the box"* |
| **SQL Warehouses** | PRO serverless WH | *"The Gold MVs are served by a PRO serverless warehouse — Photon-accelerated, no warmup time"* |
| **BI + AI Apps** | AI/BI Dashboard | *"The dashboard queries Gold directly — sub-second because the aggregation already happened in the pipeline"* |
| **Mosaic AI** | Not built — narrate | *"The risk_score and is_high_risk columns in Silver are engineered features — next step is ai_query() for LLM-based transaction classification or a served MLflow model"* |
| **UC Govern/Share/Audit** | Not built — narrate | *"UC system tables give us full query lineage and audit trail. Delta Sharing publishes these Gold tables to external consumers — no data copies, governed access"* |

## Dashboard Deployment Learnings

1. **`embed_credentials: false`** — Always publish dashboards without embedded credentials on this workspace. The personal MS account (@gmail.com via live.com) intermittently loses active status, causing `Principal is not an active member` errors on embedded-credential dashboards.
2. **Test ALL SQL queries via SQL Statements API before building dashboard JSON** — broken queries = broken widgets with no useful error.
3. **Metric view queries in dashboards** — Use `MEASURE()` syntax in the dataset `queryLines`. The dashboard dataset is just a SQL query; metric views work as any other table source.
4. **Field name matching is exact** — `name` in `query.fields` MUST equal `fieldName` in `encodings`. For aggregations: both must be `"sum(col)"`.
5. **Widget versions** — counter=2, table=2, filters=2, bar/line/pie=3. Text widgets have NO spec block.
6. **Text title + subtitle** — Use SEPARATE text widgets at different y positions. Multiple `lines` array items concatenate on one line.
7. **Global filters** — Put on a `PAGE_TYPE_GLOBAL_FILTERS` page. Filter only affects datasets containing the filter column.
8. **Dashboard datasets query ONLY Gold MVs — NEVER Silver or Bronze.** Gold tables are pre-aggregated (tens to hundreds of rows). Dashboard SQL re-aggregates Gold by collapsing time dims → single-digit row counts for charts. This two-stage pattern (SDP aggregates Silver→Gold, dashboard re-aggregates Gold→widget) is the key to dashboards that load instantly and render correctly.
9. **Counter widgets: use `disaggregated: true` with a 1-row pre-aggregated dataset.** Create a `ds_kpi` dataset that SELECT SUM/AVG/COUNT from Gold into one row. Counter fields reference bare column aliases (`"revenue"` not `"sum(revenue)"`).
10. **Auth fallback: generate Bronze via `dbx_sql` + `RANGE(N)` on serverless.** When cluster auth fails ("principal inactive"), `CREATE OR REPLACE TABLE ... AS SELECT ... FROM RANGE(N)` is identical to `spark.range(N)`. Same FK integrity via modulo, same distributions, zero code pattern changes.

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

## CLI Polling Patterns — MUST USE THESE (tested 2026-03-11)

### ❌ BROKEN: `--query` param with system Python 3.9
```bash
# This returns empty response → JSON parse error
databricks -p slysik api get /api/2.1/jobs/runs/get --query "run_id=$RUN_ID"
```

### ✅ WORKING: URL query params
```bash
# Notebook run polling
databricks -p slysik api get "/api/2.1/jobs/runs/get?run_id=$RUN_ID" 2>&1 | python3 -c "
import sys,json
d=json.load(sys.stdin)
state=d.get('state',{})
print(f'{state.get(\"life_cycle_state\",\"?\")}|{state.get(\"result_state\",\"\")}')"

# Pipeline state polling
databricks -p slysik api get "/api/2.0/pipelines/$PIPELINE_ID" 2>&1 | python3 -c "
import sys,json; d=json.load(sys.stdin); print(d.get('state','?'))"
```

### Complete polling loop (notebook run)
```bash
RUN_ID=<run_id>
for i in $(seq 1 30); do
  result=$(databricks -p slysik api get "/api/2.1/jobs/runs/get?run_id=$RUN_ID" 2>&1 | python3 -c "
import sys,json
d=json.load(sys.stdin)
s=d.get('state',{})
print(f'{s.get(\"life_cycle_state\",\"?\")}|{s.get(\"result_state\",\"\")}')" 2>&1)
  life=$(echo $result | cut -d'|' -f1)
  res=$(echo $result | cut -d'|' -f2)
  echo "  $(date '+%H:%M:%S') — $life $res"
  if [ "$life" = "TERMINATED" ] || [ "$life" = "INTERNAL_ERROR" ]; then break; fi
  sleep 10
done
```

### Complete polling loop (SDP pipeline)
```bash
PIPELINE_ID=<pipeline_id>
for i in $(seq 1 20); do
  state=$(databricks -p slysik api get "/api/2.0/pipelines/$PIPELINE_ID" 2>&1 | python3 -c "
import sys,json; d=json.load(sys.stdin); print(d.get('state','?'))" 2>&1)
  echo "  $(date '+%H:%M:%S') — $state"
  if [ "$state" = "IDLE" ] || [ "$state" = "FAILED" ]; then break; fi
  sleep 20
done
```

## Test Run Timing Benchmarks (2026-03-11)

| Phase | 100K rows | 10M rows | Notes |
|-------|-----------|----------|-------|
| Scaffold + code gen | ~2 min | ~2 min | Constant — no data dependency |
| Bundle validate + deploy | ~25 sec | ~25 sec | Constant |
| Upload notebooks | ~10 sec | ~10 sec | Constant |
| Run Bronze notebook | ~30 sec | ~5.5 min | **Main bottleneck at scale** |
| SDP pipeline (serverless) | ~50 sec | ~50 sec | Mostly provisioning time |
| Dashboard deploy + publish | ~30 sec | ~30 sec | Constant |
| **Total** | **~6-7 min** | **~11-12 min** | At 100K, fits interview easily |

### Speed Rules
- **Start at 100K** for initial demo — scale to 1M after showing it works
- **SDP serverless provisioning** is ~40 sec regardless of data size — it's fixed overhead
- **Bronze notebook** is the only variable-time step — scales linearly with N_EVENTS
- **4-core single node**: 100K = ~30s, 1M = ~1.5min, 10M = ~5.5min

## CDC Pattern — Bronze with APPLY CHANGES at Silver (2026-03-11 media_lakehouse)

### Bronze CDC Generation
35. **Three `spark.range()` unions for CDC: INSERT + UPDATE + DELETE.** Cleanest pattern for interview narration. Each block has identical schema. UPDATEs reuse same event_id (first N_UPDATES), DELETEs reuse next N_DELETES event_ids. Union all three → single Bronze table.
36. **`_commit_timestamp` ordering is critical for APPLY CHANGES.** INSERT rows use `event_ts` as commit time. UPDATE rows use a fixed date AFTER all INSERT dates. DELETE rows use the latest date. SEQUENCE BY resolves to the highest `_commit_timestamp` per key.
37. **SQL `RANGE(N)` is identical to `spark.range(N)` for serverless fallback.** Same FK integrity via modulo, same distributions, same UNION ALL pattern. Use `CREATE OR REPLACE TABLE ... AS SELECT ... FROM RANGE(N) UNION ALL ...` when cluster auth fails.

### SDP APPLY CHANGES (AUTO CDC)
38. **SDP APPLY CHANGES clause order: KEYS → APPLY AS DELETE WHEN → SEQUENCE BY → COLUMNS * EXCEPT → STORED AS SCD TYPE.** Getting this wrong causes parse errors.
39. **COLUMNS * EXCEPT must list only columns that exist in the source.** Exclude CDC columns (`_change_type`, `_commit_timestamp`) and Bronze metadata (`ingest_ts`, `source_system`, `batch_id`).
40. **SCD TYPE 1 = latest state only (no history). SCD TYPE 2 = full history with `__START_AT`/`__END_AT`.** Type 1 is correct for streaming events where corrections replace originals.
41. **Silver streaming table from APPLY CHANGES supports CLUSTER BY.** `CREATE OR REFRESH STREAMING TABLE ... CLUSTER BY (event_ts)` works.

### Pipeline Ownership & SCIM
42. **Pipeline `run_as_user_name` determines execution identity.** If that user is SCIM-inactive, pipeline FAILS silently — no error details in events, just `FAILED` state.
43. **Fix: delete pipeline, recreate as SP.** `DELETE /api/2.0/pipelines/{id}` then `POST /api/2.0/pipelines` with SP profile. SP-owned pipelines are SCIM-immune.
44. **`dbx_poll_pipeline` reports "completed" when pipeline reaches IDLE — but IDLE after FAILED is NOT success.** Always verify tables exist after pipeline "completes". Check `latest_updates[0].state` for actual result.
45. **SP needs explicit catalog grants before SQL access.** `GRANT USE_CATALOG, USE_SCHEMA, CREATE_SCHEMA, CREATE_TABLE, SELECT, MODIFY ON CATALOG ... TO SP_ID`. Also `GRANT ALL PRIVILEGES ON SCHEMA ... TO SP_ID` for table management.

### Metric View
46. **Metric view with star-schema joins works on streaming table source.** YAML `joins` reference Bronze dims by fully-qualified name. `source` is the Silver streaming table.
47. **Metric view is NOT SDP syntax — runs on SQL warehouse.** Don't include in pipeline libraries. Create via `dbx_sql` after pipeline completes.

### ML + GenAI Layer Patterns (learned 2026-03-19 finserv_lakehouse)
48. **Sklearn over Spark MLlib for < 1K rows.** 200-customer feature store → pandas + sklearn LogisticRegression. Narrate MLlib as the scale path ("same features, same MLflow tracking, just swap the estimator"). Avoids VectorAssembler/Pipeline complexity in a demo.
49. **Churn label temporal trap.** If Bronze data spans 2023-2025 and current date is 2026, `days_since_last_txn >= 90` labels 100% of customers as at-risk → LogisticRegression fails: `ValueError: needs at least 2 classes`. Always use complaint/escalation/sentiment signals for labels, OR set `START_DATE` close to current date so recency varies.
50. **MLflow unavailable on serverless (new AWS workspace).** `spark.mlflow.modelRegistryUri` config not available → `mlflow.set_experiment()` throws `[CONFIG_NOT_AVAILABLE]`. Remove all MLflow calls. Narrate: "wrap `pipe.fit()` in `mlflow.start_run()` — one context manager, full experiment tracking." Don't show broken MLflow in a demo.
51. **RAG in pure SQL — no Vector Search needed for small corpus.** For < 100 doc chunks stored in a Bronze Delta table, use `ai_similarity(question, chunk_text)` to score all chunks, `ORDER BY score DESC LIMIT 3` for retrieval, `ai_query(model, CONCAT(context, question))` for generation. All in one SQL query. In production: replace `ai_similarity` with Vector Search endpoint for sub-second retrieval at scale.
52. **Policy doc chunks as Bronze source.** Store internal documents as chunked text rows in `bronze_policy_docs` (columns: `doc_id`, `doc_name`, `doc_category`, `chunk_id`, `chunk_text`, `source_system`, `ingest_ts`). This makes them UC-governed, lineage-tracked, and queryable alongside structured data — exactly the "untapped asset" story.
53. **Separate architecture for non-deterministic AI enrichment.** SDP pipeline owns deterministic transforms (Silver quality gates, Gold RFM features, segment KPIs). Non-deterministic AI (ai_summarize, ai_query) runs in a notebook after the pipeline. Tables written by the notebook are plain Delta; tables written by SDP are MVs. Never mix — notebook can't overwrite SDP-managed MV.
54. **Genie shows tables + "Visualize" button.** Genie doesn't pre-build charts — it generates SQL and shows tabular results. After query runs, a "Visualize" button appears. Best chart-generating questions: group-by aggregations ("average churn score by segment" → bar chart). Best narrative moment: "Which Premium customers are at highest risk and what have they been calling about?" → table with `interaction_summary` column showing AI briefs inline.

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
