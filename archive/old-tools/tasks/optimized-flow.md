# Optimized End-to-End Flow for Next Practice Run

## Time Budget: ~15 min (down from ~75 min)

---

## Root Causes of Slowness in Practice Run #1

| Problem | Time Lost | Root Cause |
|---------|-----------|------------|
| Infrastructure setup | ~40 min | One-time — done now |
| Join key mismatch debug | ~15 min | Scaled orders but not order_items |
| Code generation iteration | ~15 min | Writing from scratch each time |
| Pipeline error debug | ~5 min | Path mismatches, SQL syntax |
| Dashboard field mismatches | ~5 min | Manual JSON construction |

---

## THE FIX: 3 Architectural Changes

### Change 1: Generate at 1M directly — eliminate scaling step entirely

**Why the scaling step was a mistake:**
- `crossJoin(spark.range(10))` appended `-0`..`-9` to order_id
- order_items still had original IDs → gold joins returned 0 rows
- Required `regexp_extract` hack in gold SQL to strip suffixes

**New approach:** `spark.range(1_000_000)` directly. order_items generated FROM `orders.select("order_id")` — FK integrity by construction.

### Change 2: Write directly to Bronze Delta tables — no Volume staging

**Before (v1):**
1. Generate DataFrames → persist parquet to Volumes as intermediate landing
2. SDP Bronze ingests from Volumes via `read_files()`
3. SDP Silver transforms from Bronze
4. SDP Gold aggregates from Silver

**After (v2):**
1. Generate DataFrames → persist directly to managed Bronze Delta tables
2. SDP Silver reads from Bronze Delta tables
3. SDP Gold reads from Silver

**Benefits:**
- Removes unnecessary intermediate landing step for notebook-generated data
- Eliminates redundant parquet write/read cycles
- Avoids parquet-to-Delta conversion overhead
- Simplifies storage and Volume lifecycle management
- Produces Delta-governed Bronze tables immediately
- Reduces pipeline complexity and improves developer velocity

**Architectural tradeoff:**
- We are intentionally replacing file-based Bronze ingestion with table-based Bronze persistence
- This is appropriate for synthetic/demo data generated inside Spark
- If raw file arrival, replay-from-files, or Auto Loader semantics are required, v1 may still be justified

**Bronze governance columns (every table, every row):**
- `_ingest_ts` — when this batch landed
- `_batch_id` — groups all tables in the same execution (trace/rollback)
- `_source_system` — origin system identifier
- `_source_type` — synthetic, streaming, batch, etc.
- `_generator_version` — pins the code version for downstream trust
- `_run_id` — unique execution ID for audit

**Bronze table properties:**
- `bronze.source_system`, `bronze.source_type`, `bronze.generator_version`
- `bronze.initial_batch_id`, `bronze.initial_run_id`
- `quality.tier = 'bronze'`
- Table COMMENT with data shape description

### Change 3: Clean gold SQL — direct joins, no regexp

With consistent order_ids across all tables:
```sql
FROM silver_orders o
INNER JOIN silver_order_items oi ON o.order_id = oi.order_id
```

### Change 4: Single-command deployment scripts

- `generate_retail_data_v2.py` → DataFrames + FK validation + Bronze Delta + governance
- `deploy_pipeline.py` → upload Silver+Gold SQL + create/trigger SDP + validate

---

## Step-by-Step Optimized Flow

### Step 1: Data Generation + Bronze Write (~3 min)

**What to change from v1:**

| v1 (Practice Run) | v2 (Optimized) |
|---|---|
| 100k orders + crossJoin scale to 1M | Generate 1M directly via `spark.range(1_000_000)` |
| order_items generated from 100k orders, never scaled | order_items generated FROM 1M orders |
| Write parquet to Volumes | Write Delta tables directly: `.saveAsTable("catalog.schema.bronze_*")` |
| SDP bronze reads from Volumes via `read_files()` | SDP starts at Silver, reads from bronze Delta tables |
| Separate scaling + saving scripts | Single script: generate + validate FK + write bronze Delta |
| No Delta features on bronze | Full Delta: time travel, DESCRIBE HISTORY, Liquid Clustering |

**Best practices:**
1. FK integrity by construction: child tables generated FROM parent.select("key")
2. Deterministic: every `F.hash()` uses a unique salt string
3. Imperfections included in base generation (not bolted on after)
4. Single script generates + validates FK + writes all 4 bronze Delta tables
5. Validate FK integrity BEFORE writing:
```python
orphans = order_items.join(orders.select("order_id"), "order_id", "left_anti")
assert orphans.count() == 0, "FK violation: orphan order_items"
```
6. Write directly to managed Delta tables:
```python
df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("catalog.schema.bronze_orders")
```
7. Apply Liquid Clustering to bronze tables via ALTER TABLE after write

**Speed tricks:**
- `spark.range(N)` is instant — don't overthink the scaffold
- `F.hash(col, lit("salt"))` is ~10x faster than any UDF approach
- `F.broadcast(products_df)` on the small dimension join
- Cache dimension tables (small), don't cache fact tables (large, written once)
- No Volume creation, no parquet staging — straight to Delta

### Step 2: SDP Pipeline SQL (~5 min)

**What to change from v1:**

| v1 (Practice Run) | v2 (Optimized) |
|---|---|
| 3 SQL files (bronze + silver + gold) | 2 SQL files (silver + gold) — bronze is Delta tables |
| Bronze SDP reads from Volumes via `read_files()` | No bronze SDP — Silver reads from bronze Delta tables |
| Gold SQL uses `regexp_extract()` for order_id join | Clean `ON o.order_id = oi.order_id` |
| Pipeline created via ad-hoc API call | Scripted: `scripts/deploy_pipeline.py` |

**Best practices — Silver:**
- Expectations with `ON VIOLATION DROP ROW` for nulls and range checks
- `ROW_NUMBER() OVER (PARTITION BY pk ORDER BY ts)` for dedup
- Explicit CAST on every column — never rely on inferred types
- CLUSTER BY business query pattern (date + dimension)
- COALESCE nulls with sensible defaults

**Best practices — Gold:**
- Direct joins — no regex, no workarounds
- Pre-aggregate to consumption grain
- CLUSTER BY the primary access pattern
- Use NULLIF to avoid division by zero
- DECIMAL types for all monetary aggregations

**Speed tricks:**
- Keep SQL files as templates with `{catalog}` and `{schema}` placeholders
- Upload all 3 files in parallel: `databricks workspace import` x3
- Pipeline creation is a single API call — script it

### Step 3: Validation (~2 min)

**What to change from v1:**

| v1 (Practice Run) | v2 (Optimized) |
|---|---|
| Checked row counts only after gold was empty | Validate before AND after pipeline |
| No FK integrity check pre-pipeline | FK check embedded in data gen |
| Manual SQL statements API calls | Single validation script |

**Best practices:**
1. Pre-pipeline: FK integrity assertion in data gen script
2. Post-pipeline: Row count validation across all 12 tables
3. Post-pipeline: Zero-dupe assertion on silver PKs
4. Post-pipeline: Gold row count > 0 assertion
5. Post-pipeline: Revenue reconciliation (bronze ≈ silver ≈ gold)

**Standard validation query (single call):**
```sql
SELECT 'bronze_orders' AS tbl, COUNT(*) AS rows FROM {cat}.{sch}.bronze_orders
UNION ALL SELECT 'silver_orders', COUNT(*) FROM {cat}.{sch}.silver_orders
UNION ALL SELECT 'gold_daily_sales', COUNT(*) FROM {cat}.{sch}.gold_daily_sales
-- ... all 12 tables
```

**Revenue reconciliation:**
```sql
SELECT
  (SELECT SUM(line_total) FROM silver_order_items) AS silver_revenue,
  (SELECT SUM(total_revenue) FROM gold_daily_sales) AS gold_revenue
-- These should match (gold aggregates silver)
```

### Step 4: Dashboard (~5 min)

**What to change from v1:**

| v1 (Practice Run) | v2 (Optimized) |
|---|---|
| Tested 6 queries individually | Still test, but use batch script |
| Built 14-widget JSON from scratch | Template JSON with table name placeholders |
| Manual directory creation | Pre-create in setup |
| Deploy script created mid-session | `deploy_dashboard.py` already exists |

**Best practices:**
1. Test ALL SQL queries before deployment (non-negotiable)
2. Field `name` in query.fields MUST match `fieldName` in encodings
3. Counter version=2, Table version=2, Charts version=3
4. Width=6 per row, no gaps
5. KPIs height=3, charts height=5-6
6. ≤8 categories per chart dimension
7. Separate text widgets for title vs subtitle
8. Global filters on `PAGE_TYPE_GLOBAL_FILTERS` page

**Speed tricks:**
- Dashboard JSON is already built — just verify queries still work
- `deploy_dashboard.py` handles everything in one command
- Pre-create `/Users/slysik@gmail.com/dashboards` in workspace setup

---

## Execution Timeline (Interview Day)

```
T-10min: Start cluster
         databricks -p slysik clusters start 0310-193517-r0u8giyo

T-0:     Interview starts. Receive prompt.

T+1min:  Open data gen script. Adapt to prompt vertical if different.
         Run on cluster (generates 1M orders + saves to Volumes).

T+4min:  Upload SDP SQL (3 files).
         Create + trigger pipeline.

T+5min:  Pipeline running on serverless (~30 sec).
         While waiting: narrate architecture decisions.

T+6min:  Pipeline complete. Run validation query.
         Confirm all 12 tables populated. Row counts make sense.

T+8min:  Deploy dashboard.
         Open in browser. Walk through visualizations.

T+10min: Narrate: scaling story, quality enforcement, cost tradeoffs.
         Show Delta DESCRIBE DETAIL / HISTORY if time.

T+12min: Questions / discussion phase.
```

---

## Pre-Built Artifacts Checklist

```
scripts/
  generate_retail_data_v2.py    ← 1M gen + FK validation + write bronze Delta tables
  deploy_pipeline.py            ← Upload Silver+Gold SQL + create + trigger pipeline
  deploy_dashboard.py           ← Deploy AI/BI dashboard

pipeline/
  silver.sql                    ← Reads from bronze Delta tables, dedup + type + expect
  gold_v2.sql                   ← Clean joins, Liquid Clustering narration, no regexp

dashboard/
  retail_dashboard.json         ← 14 widgets, 6 datasets, 2 global filters
```

---

## Anti-Pattern Prevention

| Anti-Pattern | Prevention |
|---|---|
| Scaling creates key mismatch | Generate at target scale directly |
| Gold joins return 0 rows | FK integrity by construction + pre-validation |
| Pipeline path mismatch | Script handles upload + reference |
| Dashboard field name mismatch | Template with verified field names |
| Cluster not ready | Start 10 min early |
| PAT token expired | Check auth first: `databricks -p slysik auth describe` |
| Notebook cell stuck "Waiting" | Detach/reattach if needed |
