-- ================================================================
-- steve-dw.sql  |  MPP & DW Platform Features — Deep Dive
-- Author  : Steve Lysik  |  SA Interview Prep — DW Spike
-- Catalog : dw            |  Schema: dwprep
-- Runs on : Databricks SQL Serverless Warehouse
--
-- PURPOSE
--   Covers the DW platform-level features NOT in steve-sql.sql
--   or steve-cc.sql. These are the topics that come up when an
--   interviewer asks: "How does Databricks compare to the DW
--   appliances you've worked with?"
--
-- SECTIONS
--   0  Setup
--   1  COPY INTO — bulk file ingestion (≈ nzload / LOAD TABLE)
--   2  INSERT OVERWRITE — partition swap pattern
--   3  VACUUM & table maintenance lifecycle
--   4  EXPLAIN / query profiling
--   5  Data skipping & Predictive I/O
--   6  Schema evolution — ALTER TABLE ADD/DROP/RENAME COLUMN
--   7  Warehouse sizing, scaling & Workload Management
--   8  Temporary views & session-scoped objects
--   9  INFORMATION_SCHEMA — system catalog exploration
--  10  Platform comparison cheat sheet (NZ / YB / Fabric / DBX)
--
-- PREREQ: Run steve-sql.sql first (creates dw.dwprep schema
--         and the Bronze/Silver/Gold tables referenced here).
-- ================================================================


-- ================================================================
-- SECTION 0 : SETUP
-- ================================================================

USE CATALOG dw;
USE SCHEMA dwprep;


-- ================================================================
-- SECTION 1 : COPY INTO — Bulk File Ingestion
-- ================================================================
-- 💬 SAY: "COPY INTO is Databricks' bulk loader. It's idempotent
--   — if you run it twice on the same files, it skips already-loaded
--   files automatically. That's a huge improvement over Netezza
--   nzload, which would double-load if you didn't track filenames
--   manually in your ETL orchestrator."
--
-- NETEZZA:  nzload / nz_migrate — external utility, not SQL.
--           No built-in idempotency — you track files in a control table.
--           No schema inference — you define the DDL upfront.
--
-- YELLOWBRICK: LOAD TABLE ... FROM 's3://...' — SQL-based, parallel.
--              Supports S3/GCS. No idempotency (manual tracking).
--              No schema evolution support.
--
-- MS FABRIC: COPY INTO is the same syntax — Microsoft adopted it
--            from Synapse/Databricks. Fabric's version supports
--            CSV/Parquet/JSON. Key difference: Fabric COPY INTO runs
--            on a fixed-capacity CU pool, Databricks runs on elastic
--            serverless compute. Fabric has no schema inference.
--
-- DATABRICKS: COPY INTO ... FROM 'path' ... FILEFORMAT = ...
--             ✅ Idempotent by default (tracks loaded files)
--             ✅ Schema inference (COPY_OPTIONS 'mergeSchema' = 'true')
--             ✅ Supports CSV, JSON, Parquet, Avro, ORC, text, binary
--             ✅ Runs on any SQL warehouse or cluster
-- ================================================================

-- First, create a volume to hold sample files for COPY INTO demo.
-- Unity Catalog Volumes are managed storage locations — think of
-- them as governed S3/ADLS paths with ACLs.
CREATE VOLUME IF NOT EXISTS dwprep_files
  COMMENT 'Staging volume for COPY INTO demos';

-- ── 1A : Write sample CSV data to the volume ────────────────
-- In production these would be files from an external system
-- landing in cloud storage. We simulate with a CTAS + export.

-- Create a temp table to generate our CSV content, then use it as source
CREATE OR REPLACE TEMPORARY VIEW v_sample_csv AS
SELECT
  'TXN' || LPAD(CAST(ROW_NUMBER() OVER (ORDER BY transaction_id) AS STRING), 5, '0') AS txn_id,
  account_id,
  txn_date,
  amount,
  txn_type,
  merchant_name,
  mcc_code
FROM silver_fact_transaction;

-- ── 1B : COPY INTO — the actual bulk load syntax ────────────
-- 💬 SAY: "The key feature is idempotency. If this pipeline fails
--   after loading 3 of 5 files, I just re-run it — COPY INTO skips
--   the 3 already loaded and picks up the remaining 2. On Netezza,
--   I'd have to truncate and reload, or maintain a file-tracking
--   control table manually."

-- Demo: COPY INTO from a path (syntax reference)
-- This won't execute without actual files in the volume, but the
-- syntax is what you need to know for the interview.

-- CREATE OR REPLACE TABLE bronze_copy_into_demo (
--   txn_id        STRING,
--   account_id    STRING,
--   txn_date      DATE,
--   amount        DECIMAL(15,2),
--   txn_type      STRING,
--   merchant_name STRING,
--   mcc_code      STRING,
--   _metadata     STRUCT<file_path:STRING, file_name:STRING, file_size:BIGINT>
-- )
-- USING DELTA;
--
-- COPY INTO bronze_copy_into_demo
-- FROM '/Volumes/dw/dwprep/dwprep_files/transactions/'
-- FILEFORMAT = CSV
-- FORMAT_OPTIONS (
--   'header'          = 'true',
--   'inferSchema'     = 'true',
--   'mergeSchema'     = 'true',     -- handle schema drift across files
--   'dateFormat'      = 'yyyy-MM-dd',
--   'nullValue'       = 'NULL'
-- )
-- COPY_OPTIONS (
--   'mergeSchema'     = 'true',     -- add new columns automatically
--   'force'           = 'false'     -- false = idempotent (skip loaded files)
-- );

-- ── 1C : COPY INTO vs Auto Loader — when to use which ───────
-- 💬 SAY: "COPY INTO is for SQL-first batch ingestion —
--   thousands of files, scheduled runs, DBSQL warehouse.
--   Auto Loader (cloudFiles) is for streaming/micro-batch —
--   millions of files, continuous processing, Spark clusters.
--   Both are idempotent. COPY INTO is what I'd recommend for
--   a Netezza migration because the team already thinks in SQL
--   and scheduled batch jobs."
--
-- | Feature          | COPY INTO            | Auto Loader             |
-- |------------------|----------------------|-------------------------|
-- | Language         | SQL                  | PySpark / SQL (SDP)     |
-- | Compute          | SQL Warehouse        | Cluster / Job           |
-- | File discovery   | Directory listing    | Cloud notification      |
-- | Scale            | ~10K files/run       | Millions of files       |
-- | Idempotent       | ✅ Yes               | ✅ Yes                  |
-- | Schema evolution | mergeSchema option   | Auto-detect + evolve    |
-- | Best for         | Batch migration      | Streaming / continuous  |


-- ================================================================
-- SECTION 2 : INSERT OVERWRITE — Partition Swap Pattern
-- ================================================================
-- 💬 SAY: "INSERT OVERWRITE atomically replaces data matching the
--   partition predicate. It's the Delta Lake equivalent of Netezza
--   EXCHANGE PARTITION or Yellowbrick partition swap. The key
--   advantage: readers never see partial data — the swap is ACID."
--
-- NETEZZA:  EXCHANGE PARTITION — fast, but requires exact partition
--           alignment. Mismatch = error. Not ACID for concurrent readers.
--
-- YELLOWBRICK: ALTER TABLE ... EXCHANGE PARTITION — similar to Netezza.
--              Fast, but not ACID. Concurrent SELECT during swap
--              may see incomplete data.
--
-- MS FABRIC: Supports partition switching via ALTER TABLE SWITCH.
--            Similar to Synapse — must match filegroup/partition scheme.
--            More restrictive than Delta's INSERT OVERWRITE because
--            it requires pre-created partition structures.
--
-- DATABRICKS: INSERT OVERWRITE replaces matched data atomically.
--             No partition pre-creation needed. Works with Liquid Clustering.
--             ACID: concurrent readers see either old or new, never partial.
-- ================================================================

-- Overwrite a single month in the Gold fact table
-- 💬 SAY: "This is how I'd handle a late correction: overwrite just
--   January 2024 data without touching any other month. ACID means
--   a dashboard querying this table mid-overwrite sees complete,
--   consistent data."

INSERT OVERWRITE gold_fact_transaction
SELECT * FROM gold_fact_transaction
WHERE txn_month = '2024-01';
-- In a real scenario, the SELECT would pull from a corrected source,
-- not the same table. This demonstrates the syntax safely.

-- Verify the table still has all data
SELECT txn_month, COUNT(*) AS rows
FROM gold_fact_transaction
GROUP BY txn_month
ORDER BY txn_month;


-- ================================================================
-- SECTION 3 : VACUUM & Table Maintenance Lifecycle
-- ================================================================
-- 💬 SAY: "Delta Lake accumulates old data files as you write new
--   versions. VACUUM removes files no longer referenced by any
--   version within the retention window. OPTIMIZE compacts small
--   files and applies Liquid Clustering. Together they're the
--   equivalent of Netezza GROOM + GENERATE STATISTICS."
--
-- NETEZZA:  GROOM TABLE — reclaims space from deleted/updated rows.
--           GENERATE STATISTICS — refreshes optimizer stats.
--           Both are manual, scheduled operations. No versioning —
--           once GROOMed, old data is gone permanently.
--
-- YELLOWBRICK: VACUUM — similar to Netezza GROOM. Reclaims space.
--              ANALYZE — statistics refresh. Both manual.
--
-- MS FABRIC: Automatic — Fabric runs background optimization.
--            No user control over compaction timing. Pro: zero-admin.
--            Con: no control = no tuning when you need it.
--
-- DATABRICKS:
--   OPTIMIZE     — compact small files + apply Liquid Clustering
--   OPTIMIZE FULL — recompact entire table (rare, for major reorg)
--   VACUUM       — delete old files beyond retention period
--   ANALYZE      — refresh statistics for CBO
-- ================================================================

-- ── 3A : OPTIMIZE — compact + cluster ────────────────────────
-- 💬 SAY: "OPTIMIZE is incremental by default — it only touches
--   files that haven't been optimized yet. OPTIMIZE FULL recompacts
--   everything, which I'd use after a major bulk delete or a
--   cluster key change. On a 5TB fact table, incremental OPTIMIZE
--   takes seconds; FULL takes minutes. On Netezza, GROOM TABLE
--   always processes the entire table — there's no incremental mode."

OPTIMIZE silver_fact_transaction;

-- OPTIMIZE with predicate — only compact files in a date range
-- Useful for hot partitions that get frequent writes
OPTIMIZE gold_fact_transaction
WHERE txn_date >= '2024-02-01';

-- ── 3B : VACUUM — clean up old file versions ─────────────────
-- 💬 SAY: "VACUUM deletes data files that are no longer referenced
--   by any Delta version within the retention period. Default is
--   7 days. After VACUUM, you can't TIME TRAVEL to versions older
--   than the retention window."
--
-- IMPORTANT: VACUUM doesn't delete the Delta log — that's controlled
-- by delta.logRetentionDuration (default 30 days). Log vs data
-- retention are independent settings.

-- Check current retention settings
DESCRIBE DETAIL gold_fact_transaction;

-- DRY RUN: See what VACUUM would delete (no files actually removed)
-- VACUUM gold_fact_transaction RETAIN 168 HOURS DRY RUN;

-- Actual VACUUM (7-day retention = 168 hours)
-- VACUUM gold_fact_transaction RETAIN 168 HOURS;

-- 💬 SAY: "I always run DRY RUN first in production. And I set
--   retention to at least 7 days so the time travel SLA for
--   compliance is met. On Netezza, once you GROOM, it's gone —
--   there's no retention window concept."

-- ── 3C : Full maintenance cycle (the production pattern) ─────
-- 💬 SAY: "My standard nightly maintenance job runs this sequence:
--   1. OPTIMIZE — compact small files, apply Liquid Clustering
--   2. ANALYZE — refresh column statistics for CBO
--   3. VACUUM — remove files beyond retention window
--   This is the Databricks equivalent of the Netezza admin scripts
--   that every DBA ran weekly."

-- OPTIMIZE gold_fact_transaction;
-- ANALYZE TABLE gold_fact_transaction COMPUTE STATISTICS FOR ALL COLUMNS;
-- VACUUM gold_fact_transaction RETAIN 168 HOURS;


-- ================================================================
-- SECTION 4 : EXPLAIN / Query Profiling
-- ================================================================
-- 💬 SAY: "Every DW engineer's first instinct when a query is slow
--   is to check the execution plan. On Netezza it's EXPLAIN VERBOSE.
--   On Yellowbrick it's EXPLAIN ANALYZE. On Databricks it's EXPLAIN
--   plus the Query Profile UI in the SQL warehouse."
--
-- NETEZZA:  EXPLAIN VERBOSE — shows zone map elimination, snippet
--           distribution across SPUs, estimated rows per SPU.
--           Great for diagnosing data skew and redistribution costs.
--
-- YELLOWBRICK: EXPLAIN ANALYZE — shows actual vs estimated rows,
--              per-node execution metrics. Similar to PostgreSQL.
--
-- MS FABRIC: Query insights — DMV-based (sys.dm_exec_query_stats).
--            No EXPLAIN ANALYZE. Synapse-style query plan in the
--            monitoring hub. Less granular than Netezza/YB plans.
--
-- DATABRICKS: EXPLAIN [EXTENDED | FORMATTED | COST | CODEGEN]
--             Shows logical plan, physical plan, cost estimates.
--             The SQL Warehouse Query Profile UI shows actual I/O,
--             data skipping stats, Photon vs JVM execution path,
--             and per-operator timing — richer than any of the above.
-- ================================================================

-- ── 4A : Basic EXPLAIN ───────────────────────────────────────
-- Shows the physical execution plan — what operations Databricks
-- will actually perform, in what order.
EXPLAIN
SELECT
  c.full_name,
  c.credit_band,
  SUM(f.abs_amount) AS total_spend
FROM gold_fact_transaction f
JOIN gold_dim_customer c ON f.customer_sk = c.customer_sk
WHERE f.is_debit = TRUE
  AND f.txn_date >= '2024-01-01'
  AND f.txn_date < '2024-02-01'
GROUP BY c.full_name, c.credit_band
ORDER BY total_spend DESC;

-- ── 4B : EXPLAIN EXTENDED — includes logical + physical plan ──
-- 💬 SAY: "EXTENDED shows both the logical plan (what the optimizer
--   wanted to do) and the physical plan (what it actually does after
--   optimization). I look for BroadcastHashJoin on small dims and
--   SortMergeJoin on large facts — if it broadcasts a big table,
--   that's a performance red flag."
EXPLAIN EXTENDED
SELECT
  c.full_name,
  f.mcc_category,
  COUNT(*)          AS txn_count,
  SUM(f.abs_amount) AS total_spend
FROM gold_fact_transaction f
JOIN gold_dim_customer c ON f.customer_sk = c.customer_sk
WHERE f.is_debit = TRUE
GROUP BY c.full_name, f.mcc_category;

-- ── 4C : EXPLAIN FORMATTED — structured output ──────────────
-- 💬 SAY: "FORMATTED gives the plan in a tree structure that's
--   easier to read than the flat output. In an interview setting
--   I'd look for three things:
--     1. ColumnarToRow — means Photon handed off to JVM (bad)
--     2. Exchange (shuffle) — data redistribution cost
--     3. Filter pushdown — predicates pushed to scan level (good)"
EXPLAIN FORMATTED
SELECT
  account_id,
  txn_date,
  amount,
  SUM(amount) OVER (
    PARTITION BY account_id
    ORDER BY txn_ts
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS running_balance
FROM silver_fact_transaction
WHERE txn_date >= '2024-01-01';


-- ================================================================
-- SECTION 5 : Data Skipping & Predictive I/O
-- ================================================================
-- 💬 SAY: "Data skipping is how Databricks avoids reading files
--   that can't contain matching rows. It reads the min/max stats
--   from the Delta log — same concept as Netezza Zone Maps, but
--   at the file level instead of the extent level.
--
--   Liquid Clustering makes data skipping dramatically more effective
--   because co-located data means tighter min/max ranges per file.
--   Without clustering, a column like txn_date might span
--   2020-2024 in every file (no skipping possible). With clustering,
--   each file covers a narrow date range (high skip rate).
--
--   Predictive I/O is the next level: Databricks uses ML to predict
--   which files contain relevant data, even when min/max stats
--   alone aren't enough (e.g., string columns, low-cardinality
--   columns, skewed data). It's automatic — no config needed."
--
-- NETEZZA:  Zone Maps — min/max per 8MB data slice. Automatic.
--           Works well when data is loaded in order. Degrades
--           with random insert patterns. No ML-based skipping.
--
-- YELLOWBRICK: Zone Maps equivalent + sort keys. Better than
--              Netezza because sort keys ensure physical ordering.
--              But fixed at creation — can't change without rebuild.
--
-- MS FABRIC: Synapse inherited column-store segment elimination
--            from SQL Server. Works on min/max per row group (~1M rows).
--            No ML-based skipping. No user-controlled clustering.
-- ================================================================

-- ── 5A : Check data skipping stats ───────────────────────────
-- DESCRIBE DETAIL shows clustering information including:
--   • num_files_clustered / num_files_total — what % is clustered
--   • average_depth — how many files overlap per cluster key value
--     (1.0 = perfect, higher = more files scanned per query)

DESCRIBE DETAIL gold_fact_transaction;

-- ── 5B : Query with predicate to show file skipping ──────────
-- After running this query, check the Query Profile in the DBSQL UI.
-- Look for "files pruned" vs "files read" — the ratio shows how
-- effective data skipping + Liquid Clustering is.
SELECT COUNT(*), SUM(abs_amount)
FROM gold_fact_transaction
WHERE txn_date = DATE'2024-01-15'
  AND mcc_code = '5411';

-- 💬 SAY: "In the Query Profile, I'd expect to see something like
--   'files read: 1, files pruned: 12'. That means Liquid Clustering
--   let the engine skip 92% of the data. On Netezza, zone maps
--   would give similar pruning IF the data was loaded in order —
--   but after months of random inserts, zone map effectiveness
--   degrades. Liquid Clustering stays effective because OPTIMIZE
--   continuously re-clusters."


-- ================================================================
-- SECTION 6 : Schema Evolution
-- ================================================================
-- 💬 SAY: "Schema evolution is one of the biggest pain points in
--   traditional DW. On Netezza, adding a column to a 5TB table
--   requires ALTER TABLE ADD COLUMN — which is fast (metadata-only)
--   — but changing a column type requires CREATE TABLE AS SELECT
--   with the new type, then renaming. That's a full table rewrite
--   that takes hours and requires a maintenance window.
--
--   Delta Lake handles all of this as metadata operations:"
--
-- NETEZZA:  ADD COLUMN = fast (metadata). ALTER TYPE = full rewrite.
--           RENAME COLUMN = not supported. DROP COLUMN = not supported.
--           You'd CREATE TABLE ... AS SELECT without the column.
--
-- YELLOWBRICK: ADD COLUMN = fast. ALTER TYPE = full rewrite.
--              Same constraints as Netezza.
--
-- MS FABRIC: ADD COLUMN = fast. ALTER TYPE = limited (widening only,
--            e.g., INT→BIGINT). DROP COLUMN = not supported in
--            Synapse serverless. Must recreate table.
--
-- DATABRICKS: All schema operations are metadata-only.
--             No data rewrite for any of these.
-- ================================================================

-- ── 6A : ADD COLUMN — metadata-only, instant ─────────────────
ALTER TABLE gold_fact_transaction
  ADD COLUMN (
    txn_quarter STRING COMMENT 'Derived: YYYY-Qn — pre-computed for quarterly reports'
  );

-- Backfill the new column
UPDATE gold_fact_transaction
SET txn_quarter = CONCAT(
  YEAR(txn_date), '-Q', QUARTER(txn_date)
);

-- Verify
SELECT txn_date, txn_month, txn_quarter
FROM gold_fact_transaction
LIMIT 5;

-- ── 6B : RENAME COLUMN — metadata-only ──────────────────────
-- 💬 SAY: "On Netezza you literally cannot rename a column.
--   You'd create a view with the new column alias. Delta does it
--   as a metadata change — zero I/O."

-- ALTER TABLE gold_fact_transaction
--   RENAME COLUMN txn_quarter TO fiscal_quarter;
-- (Commented out to keep script re-runnable — you'd use this pattern)

-- ── 6C : SET/CHANGE column comment — metadata-only ──────────
ALTER TABLE gold_fact_transaction
  ALTER COLUMN txn_quarter COMMENT 'Fiscal quarter: YYYY-Qn (derived from txn_date)';

-- ── 6D : DROP COLUMN — metadata-only ─────────────────────────
-- 💬 SAY: "Netezza doesn't support DROP COLUMN at all. You'd have
--   to CTAS without the column, then rename. On a 5TB table that's
--   a multi-hour operation. Delta does it instantly."
ALTER TABLE gold_fact_transaction
  DROP COLUMN txn_quarter;

-- ── 6E : SET NOT NULL — add constraint to existing column ────
-- ALTER TABLE gold_fact_transaction
--   ALTER COLUMN customer_id SET NOT NULL;
-- (Already NOT NULL from DDL — shown for syntax reference)


-- ================================================================
-- SECTION 7 : Warehouse Sizing, Scaling & Workload Management
-- ================================================================
-- 💬 SAY: "This is where the Databricks model is fundamentally
--   different from appliance-based DW. Netezza and Yellowbrick are
--   fixed-capacity: you buy an appliance, you get N SPUs or N nodes.
--   When workload exceeds capacity, you either queue or fail.
--
--   Databricks SQL Warehouses are elastic. Serverless warehouses
--   scale automatically from 0 to your configured maximum. You pay
--   per query, not per hour of idle capacity."
--
-- NETEZZA:  Fixed SPU count. WLM uses Resource Groups to allocate
--           SPUs per user/group. Queries queue when SPU capacity is
--           exceeded. Scaling = buy a bigger appliance ($$$).
--
-- YELLOWBRICK: Fixed node count. WLM uses Workload Rules to
--              prioritize/queue queries. Scaling = add nodes (manual).
--
-- MS FABRIC: Capacity Units (CU) — fixed pool assigned to a workspace.
--            Workloads compete for CUs. "Smoothing" allows burst above
--            capacity but throttles after sustained overuse. No true
--            auto-scale — you pre-purchase CU tiers (F2, F4, F8...F2048).
--            Fabric Mirroring uses CUs too, competing with queries.
--
-- DATABRICKS:
--   Serverless SQL Warehouse:
--     • Starts in ~5s (no cold start lag)
--     • Auto-scales 0 → max clusters in seconds
--     • Scales DOWN to 0 when idle (true serverless)
--     • No WLM config needed — auto-queuing built in
--     • Pay per DBU consumed, not per hour provisioned
--
--   Pro SQL Warehouse:
--     • Manual scaling (set min/max cluster count)
--     • 10-30s startup time
--     • Good for predictable workloads with steady load
--
--   Classic SQL Warehouse:
--     • Legacy — being deprecated
--     • Avoid for new deployments
-- ================================================================

-- ── 7A : Inspect current warehouse config ────────────────────
-- These system functions show warehouse metadata at query time.

SELECT
  current_catalog()     AS catalog,
  current_schema()      AS schema,
  current_user()        AS user,
  current_timestamp()   AS ts;

-- ── 7B : Query routing with tags ─────────────────────────────
-- 💬 SAY: "In Netezza, WLM routes queries based on user groups
--   and estimated cost. In Databricks, I use query tags to
--   categorize workloads. Tags appear in the Query History and
--   billing — I can see exactly which team or pipeline is consuming
--   resources."

SET statement_tag = 'team=finserv;workload=monthly_close';

-- Run a query — it will be tagged in Query History
SELECT
  txn_month,
  SUM(CASE WHEN is_debit THEN abs_amount ELSE 0 END) AS total_debits,
  SUM(CASE WHEN NOT is_debit THEN abs_amount ELSE 0 END) AS total_credits
FROM gold_fact_transaction
GROUP BY txn_month
ORDER BY txn_month;

-- Clear the tag
RESET statement_tag;

-- ── 7C : Query watchdog — automatic kill for runaway queries ──
-- 💬 SAY: "Netezza WLM lets you set max query time per resource
--   group. Databricks has statement_timeout — same concept but
--   simpler. If a query exceeds the threshold, it's killed
--   automatically. No need for a DBA to watch for runaways."

-- Set a 5-minute timeout for this session
-- SET statement_timeout = 300;  -- seconds

-- ── 7D : Warehouse scaling comparison table ──────────────────
-- 💬 SAY: "Here's how I frame the scaling conversation:
--
-- | Platform     | Scale Up           | Scale Out          | Scale to Zero | Time     |
-- |--------------|--------------------|--------------------|---------------|----------|
-- | Netezza      | Bigger appliance   | N/A (single node)  | ❌ No         | Weeks    |
-- | Yellowbrick  | Bigger instance    | Add nodes           | ❌ No         | Hours    |
-- | MS Fabric    | Higher CU tier     | N/A (pool-based)   | ⚠️ Pause only | Minutes  |
-- | DBX Serverless| Auto (transparent)| Auto (multi-cluster)| ✅ Yes       | Seconds  |
-- | DBX Pro      | Change T-shirt size| Set max clusters   | ⚠️ Min 1     | Minutes  |
-- "


-- ================================================================
-- SECTION 8 : Temporary Views & Session-Scoped Objects
-- ================================================================
-- 💬 SAY: "Every DW engineer uses temp tables for staging complex
--   transformations. On Netezza it's CREATE TEMP TABLE. On Fabric
--   it's #temp_table. On Databricks, we use TEMPORARY VIEWs —
--   they're session-scoped and automatically dropped when the
--   session ends. No cleanup required."
--
-- NETEZZA:  CREATE TEMP TABLE — session-scoped, physically materialised.
--           Stored in the temp tablespace. Dropped at session end.
--
-- YELLOWBRICK: CREATE TEMP TABLE — same as Netezza.
--
-- MS FABRIC: #temp_table syntax from T-SQL. Session-scoped.
--            Stored in tempdb equivalent. Risk of tempdb contention
--            at scale — a classic SQL Server problem.
--
-- DATABRICKS: TEMPORARY VIEW — session-scoped, not materialised.
--             It's a named query, not a physical table. No storage
--             cost, no tempdb contention. For materialised temp
--             results, use CREATE TABLE in a temp schema and drop
--             after processing.
-- ================================================================

-- ── 8A : TEMPORARY VIEW — session-scoped named query ─────────
CREATE OR REPLACE TEMPORARY VIEW v_high_value_customers AS
SELECT
  c.customer_id,
  c.full_name,
  c.credit_band,
  SUM(f.abs_amount) AS total_spend
FROM gold_fact_transaction f
JOIN gold_dim_customer c ON f.customer_sk = c.customer_sk
WHERE f.is_debit = TRUE
GROUP BY c.customer_id, c.full_name, c.credit_band
HAVING SUM(f.abs_amount) > 1000;

-- Use the temp view in a downstream query
SELECT
  hvc.full_name,
  hvc.total_spend,
  ms.mcc_category,
  ms.total_spend AS category_spend
FROM v_high_value_customers hvc
JOIN gold_mv_mcc_spend_summary ms
  ON hvc.full_name = ms.full_name
ORDER BY hvc.total_spend DESC, ms.total_spend DESC;

-- ── 8B : CTE chain — the Databricks-idiomatic alternative ────
-- 💬 SAY: "For multi-step transformations, I prefer CTE chains
--   over temp views. CTEs are optimised as a single query — the
--   engine can push predicates through the entire chain. Temp views
--   are evaluated independently each time they're referenced."

WITH step1_account_totals AS (
  SELECT
    account_id,
    customer_id,
    SUM(abs_amount) AS total_spend,
    COUNT(*)        AS txn_count
  FROM gold_fact_transaction
  WHERE is_debit = TRUE
  GROUP BY account_id, customer_id
),
step2_customer_rollup AS (
  SELECT
    customer_id,
    COUNT(account_id)   AS num_accounts,
    SUM(total_spend)    AS total_customer_spend,
    SUM(txn_count)      AS total_txns,
    ROUND(SUM(total_spend) / SUM(txn_count), 2) AS avg_txn_size
  FROM step1_account_totals
  GROUP BY customer_id
)
SELECT
  c.full_name,
  c.credit_band,
  r.num_accounts,
  r.total_customer_spend,
  r.total_txns,
  r.avg_txn_size
FROM step2_customer_rollup r
JOIN gold_dim_customer c USING (customer_id)
ORDER BY r.total_customer_spend DESC;


-- ================================================================
-- SECTION 9 : INFORMATION_SCHEMA — System Catalog Exploration
-- ================================================================
-- 💬 SAY: "Every DW admin's first stop is the system catalog.
--   On Netezza it's _v_table, _v_relation_column, _v_table_dist_map.
--   On Yellowbrick it's pg_catalog. On Fabric it's INFORMATION_SCHEMA
--   (same as SQL Server). Databricks uses the SQL standard
--   INFORMATION_SCHEMA plus Unity Catalog system tables for deeper
--   audit, lineage, and billing data."
-- ================================================================

-- ── 9A : List all tables in the current schema ──────────────
SELECT
  table_catalog,
  table_schema,
  table_name,
  table_type,
  comment
FROM information_schema.tables
WHERE table_schema = 'dwprep'
ORDER BY table_name;

-- ── 9B : Column metadata — types, nullability, comments ─────
SELECT
  table_name,
  column_name,
  data_type,
  is_nullable,
  comment
FROM information_schema.columns
WHERE table_schema = 'dwprep'
  AND table_name = 'gold_fact_transaction'
ORDER BY ordinal_position;

-- ── 9C : Constraints — CHECK, FK, PK ────────────────────────
SELECT
  constraint_catalog,
  constraint_schema,
  constraint_name,
  table_name,
  constraint_type
FROM information_schema.table_constraints
WHERE table_schema = 'dwprep'
ORDER BY table_name, constraint_type;

-- ── 9D : Table properties and storage details ────────────────
-- DESCRIBE DETAIL shows physical storage info that
-- INFORMATION_SCHEMA doesn't: file count, size, clustering info
DESCRIBE DETAIL silver_fact_transaction;
DESCRIBE DETAIL gold_fact_transaction;

-- ── 9E : Table history — all operations on a table ───────────
-- 💬 SAY: "DESCRIBE HISTORY is the audit trail. It shows every
--   MERGE, INSERT, OPTIMIZE, ALTER — with user, timestamp, and
--   metrics. On Netezza, you'd need to parse pg_log files or
--   set up a separate audit database."
DESCRIBE HISTORY gold_fact_transaction;

-- ── 9F : Unity Catalog system tables (deeper telemetry) ──────
-- 💬 SAY: "Beyond INFORMATION_SCHEMA, Databricks has system tables
--   in the system.information_schema and system.access catalogs.
--   These give you audit logs, query history, billing, and lineage
--   at the workspace level. No equivalent in Netezza/YB/Fabric —
--   those require separate monitoring tools."
--
-- Example queries (require system.* access):
-- SELECT * FROM system.access.audit LIMIT 10;
-- SELECT * FROM system.billing.usage WHERE usage_date = current_date();
-- SELECT * FROM system.information_schema.table_lineage LIMIT 10;


-- ================================================================
-- SECTION 10 : Platform Comparison Cheat Sheet
-- ================================================================
--
-- ┌──────────────────────┬──────────────────┬──────────────────┬──────────────────┬──────────────────────┐
-- │ Feature              │ Netezza (NZ)     │ Yellowbrick (YB) │ MS Fabric        │ Databricks           │
-- ├──────────────────────┼──────────────────┼──────────────────┼──────────────────┼──────────────────────┤
-- │ Architecture         │ Fixed appliance  │ Fixed MPP nodes  │ CU pool (SaaS)   │ Serverless elastic   │
-- │ Scaling              │ Buy bigger box   │ Add nodes        │ Change CU tier   │ Auto-scale clusters  │
-- │ Scale to zero        │ ❌               │ ❌               │ ⚠️ Pause         │ ✅ Yes               │
-- │ Storage format       │ Proprietary      │ Proprietary      │ Delta + Parquet  │ Delta Lake (open)    │
-- │ ACID transactions    │ Row-level locks  │ MVCC             │ Yes (limited)    │ Full ACID (Delta)    │
-- │ MERGE (CDC)          │ Basic (no DELETE)│ Full             │ Full             │ Full + ACID          │
-- │ SCD Type 2           │ Manual 2-step    │ Manual 2-step    │ Manual           │ Manual + APPLY CHANGES│
-- │ Clustering           │ Zone Maps (auto) │ SORT ON (fixed)  │ Segment elim     │ Liquid Clustering    │
-- │ Change clustering    │ Reload table     │ Rebuild table    │ N/A              │ ALTER TABLE (instant)│
-- │ Materialized Views   │ Manual refresh   │ ❌ None          │ ❌ None          │ Auto-refresh MV      │
-- │ Time Travel          │ ❌ None          │ ❌ None          │ ⚠️ Limited       │ 30-day versioning    │
-- │ CLONE (zero-copy)    │ ❌ None          │ ❌ None          │ ❌ (Shortcut=link)│ SHALLOW + DEEP       │
-- │ Schema evolution     │ ADD only         │ ADD only         │ ADD, widen type  │ ADD/DROP/RENAME/TYPE │
-- │ Bulk ingest          │ nzload (CLI)     │ LOAD TABLE (SQL) │ COPY INTO (SQL)  │ COPY INTO (SQL)      │
-- │ Idempotent ingest    │ ❌ Manual        │ ❌ Manual        │ ❌ Manual        │ ✅ COPY INTO auto    │
-- │ Streaming ingest     │ ❌ None          │ ❌ None          │ ⚠️ Eventstream   │ Streaming Tables     │
-- │ WLM / query routing  │ Resource Groups  │ Workload Rules   │ CU smoothing     │ Auto + query tags    │
-- │ Query profiling      │ EXPLAIN VERBOSE  │ EXPLAIN ANALYZE  │ DMVs             │ EXPLAIN + Query UI   │
-- │ Statistics           │ GENERATE STATS   │ ANALYZE          │ Auto             │ ANALYZE TABLE        │
-- │ Temp tables          │ CREATE TEMP TABLE│ CREATE TEMP TABLE│ #temp_table      │ TEMPORARY VIEW       │
-- │ System catalog       │ _v_* views       │ pg_catalog       │ INFORMATION_SCHEMA│ INFORMATION_SCHEMA + │
-- │                      │                  │                  │                  │ system.* tables      │
-- │ Governance           │ Row/column sec   │ Row/column sec   │ Purview          │ Unity Catalog        │
-- │ Open format          │ ❌ Proprietary   │ ❌ Proprietary   │ ✅ Delta/Parquet │ ✅ Delta Lake (open) │
-- │ Multi-engine access  │ ❌ NZ only       │ ❌ YB only       │ ⚠️ OneLake share │ ✅ Any Delta reader  │
-- └──────────────────────┴──────────────────┴──────────────────┴──────────────────┴──────────────────────┘
--
-- KEY INTERVIEW TALKING POINTS:
--
-- 1. "Netezza was brilliant for its time — FPGA-accelerated zone maps,
--    asymmetric MPP, zero-tuning. But it's frozen in time: no streaming,
--    no schema evolution, no time travel, no open format."
--
-- 2. "Yellowbrick modernised the MPP appliance with flash storage and
--    cloud deployment options. But it's still a closed format with
--    fixed capacity. You can't scale to zero or share data with other
--    engines."
--
-- 3. "Fabric is Microsoft's bet on convergence — DW + lake + BI in
--    one SKU. The CU model is simpler to budget but harder to optimise.
--    No auto-scale, no MV auto-refresh, limited schema evolution.
--    Good for shops already deep in the Microsoft stack."
--
-- 4. "Databricks is the lakehouse: open format (Delta), elastic compute,
--    unified SQL + ML + streaming. For FinServ, the key differentiators
--    are: Liquid Clustering (adaptive, not fixed), ACID MERGE for CDC,
--    Time Travel for regulatory audit, and Streaming Tables for
--    real-time fraud detection. No other platform combines all four."
-- ================================================================
