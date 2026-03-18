-- ================================================================
-- FinServ Lakeflow Pipeline  |  Spark Declarative Pipelines (SDP)
-- Author  : Steve Lysik     |  SA Interview Prep — DW Spike
-- Target  : dbx_weg.dwprep  (set in pipeline configuration)
-- Source  : /Volumes/dbx_weg/dwprep/dwprep_files/sdp_source/
--
-- PIPELINE DAG
--   bronze_sdp_transactions          ← Auto Loader from CSV volume
--        │
--        ▼
--   silver_sdp_transactions          ← Dedup + MCC enrichment + DQ
--        │
--        ├──► gold_sdp_monthly_summary    ← Monthly cash flow MV
--        └──► gold_sdp_fraud_signals      ← Spend velocity flags MV
--
-- HOW TO RUN
--   1. Jobs & Pipelines → Create Pipeline
--   2. Set catalog = dbx_weg, schema = dwprep
--   3. Add this file as a source
--   4. Click Start (Triggered mode for demo)
--
-- INTERVIEW TALKING POINTS (inline throughout)
-- ================================================================


-- ================================================================
-- BRONZE : Streaming Table — Auto Loader from Unity Catalog Volume
-- ================================================================
-- 💬 SAY: "The STREAMING TABLE construct is what makes this
--   declarative. I describe WHAT I want — a table continuously
--   updated from this volume path — and SDP handles the how:
--   checkpoint management, exactly-once delivery, schema evolution,
--   retry on failure. On Netezza this was a custom ETL job,
--   a control table for file tracking, and a DBA on call at 2am.
--   Here it's 15 lines of SQL."
--
-- CONSTRAINT / EXPECT — SDP's built-in data quality layer:
--   ON VIOLATION DROP ROW  → silently drop bad rows, log to event log
--   ON VIOLATION WARN      → keep the row, emit a warning metric
--   ON VIOLATION FAIL UPDATE → halt the entire pipeline run
--
-- 💬 SAY: "These EXPECT constraints are data quality gates that
--   run at ingestion time. The pipeline UI shows a live pass/fail
--   metric for each constraint — no separate DQ framework needed.
--   Batch 3 in our demo has 2 intentional bad rows: one with a
--   null account_id (DROP ROW) and one with txn_type='INVALID'
--   (WARN). Watch what the event log shows."
-- ================================================================

CREATE OR REFRESH STREAMING TABLE bronze_sdp_transactions (

  -- ── Data Quality Gates ─────────────────────────────────────
  -- DROP ROW: row is silently removed + counted in event log
  CONSTRAINT valid_account_id
    EXPECT (account_id IS NOT NULL)
    ON VIOLATION DROP ROW,

  CONSTRAINT valid_amount
    EXPECT (amount IS NOT NULL)
    ON VIOLATION DROP ROW,

  -- No ON VIOLATION clause = WARN (default) — row kept, violation logged
  CONSTRAINT valid_txn_type
    EXPECT (txn_type IN ('DEBIT', 'CREDIT')),

  CONSTRAINT valid_mcc_code
    EXPECT (mcc_code IS NOT NULL AND LENGTH(mcc_code) = 4)
)
COMMENT "Bronze: raw transactions — Auto Loader from ADLS landing volume. Append-only."
TBLPROPERTIES (
  'layer'                      = 'bronze',
  'delta.enableChangeDataFeed' = 'true',
  'pipelines.reset.allowed'    = 'true'
)
AS SELECT
  transaction_id,
  account_id,
  customer_id,
  CAST(txn_date AS DATE)          AS txn_date,
  CAST(txn_ts   AS TIMESTAMP)     AS txn_ts,
  CAST(amount   AS DECIMAL(15,2)) AS amount,
  txn_type,
  merchant_name,
  mcc_code,
  current_timestamp()             AS _ingest_ts,
  _metadata.file_name             AS _source_file    -- Auto Loader metadata
FROM STREAM read_files(
  '/Volumes/dbx_weg/dwprep/dwprep_files/sdp_source/',
  format      => 'csv',
  header      => 'true',
  inferSchema => 'false',
  -- Explicit schema prevents type inference failures on bad data
  schema      => 'transaction_id STRING, account_id STRING, customer_id STRING,
                  txn_date STRING, txn_ts STRING, amount STRING,
                  txn_type STRING, merchant_name STRING, mcc_code STRING'
);


-- ================================================================
-- SILVER : Materialized View — Dedup + Enrich + Clean
-- ================================================================
-- 💬 SAY: "Silver is a MATERIALIZED VIEW, not a Streaming Table.
--   The difference: Streaming Tables are append-only, updated
--   incrementally as new files arrive. Materialized Views are
--   recomputed when upstream data changes — SDP figures out the
--   minimal recomputation needed. Silver reads from Bronze via
--   LIVE.bronze_sdp_transactions — that LIVE. prefix tells SDP
--   this is an intra-pipeline dependency, so it builds the DAG
--   automatically and guarantees Bronze runs before Silver."
--
-- 💬 SAY: "Three things happen in Silver:
--   1. ROW_NUMBER dedup — batch2 re-sent TXN-B2-003, Silver
--      keeps only one copy. Bronze keeps both for audit.
--   2. WARN rows (txn_type=INVALID) are filtered out here —
--      they passed Bronze because WARN keeps the row, but Silver
--      applies business logic and drops non-standard types.
--   3. MCC enrichment — human-readable category derived inline.
--      No separate lookup table join needed at this volume."
-- ================================================================

CREATE OR REFRESH MATERIALIZED VIEW silver_sdp_transactions
COMMENT "Silver: deduped clean transactions — DQ enforced, MCC enriched, Photon-optimised"
TBLPROPERTIES (
  'layer'                      = 'silver',
  'delta.enableChangeDataFeed' = 'true'
)
AS
WITH deduped AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY transaction_id
      ORDER BY _ingest_ts DESC       -- latest re-send wins
    ) AS _rn
  FROM LIVE.bronze_sdp_transactions
  WHERE txn_type IN ('DEBIT', 'CREDIT')   -- drop WARN violations
)
SELECT
  transaction_id,
  account_id,
  customer_id,
  txn_date,
  txn_ts,
  amount,
  txn_type,
  merchant_name,
  mcc_code,

  -- MCC enrichment — replaces lookup table join
  CASE mcc_code
    WHEN '0000' THEN 'Payroll / Internal'
    WHEN '4511' THEN 'Airlines'
    WHEN '5200' THEN 'Home Improvement'
    WHEN '5411' THEN 'Grocery Stores'
    WHEN '5541' THEN 'Service Stations / Fuel'
    WHEN '5734' THEN 'Electronics / Software'
    WHEN '5732' THEN 'Electronics Stores'
    WHEN '5912' THEN 'Drug Stores / Pharmacies'
    WHEN '5944' THEN 'Jewelry Stores'
    WHEN '5999' THEN 'Online Retail / Misc'
    WHEN '6012' THEN 'Financial Institutions / Transfers'
    WHEN '6552' THEN 'Real Estate / Mortgage'
    ELSE              'Other (' || mcc_code || ')'
  END                                      AS mcc_category,

  -- Pre-computed columns — Photon avoids re-evaluating at query time
  txn_type = 'DEBIT'                       AS is_debit,
  ABS(amount)                              AS abs_amount,
  DATE_FORMAT(txn_date, 'yyyy-MM')         AS txn_month,

  _ingest_ts,
  _source_file
FROM deduped
WHERE _rn = 1;                             -- deduplicated


-- ================================================================
-- GOLD : Monthly Cash Flow Summary — Replaces Netezza summary table
-- ================================================================
-- 💬 SAY: "This Materialized View replaces the nightly summary
--   table refresh job that Netezza teams typically schedule.
--   On Netezza: a cron job runs CREATE TABLE AS SELECT at 2am,
--   overwrites the summary table, analysts query stale data if
--   the job fails or runs late. Here the MV auto-refreshes when
--   Silver changes — analysts always see consistent, fresh data.
--   No scheduler, no failure mode, no stale dashboard."
-- ================================================================

CREATE OR REFRESH MATERIALIZED VIEW gold_sdp_monthly_summary
COMMENT "Gold: monthly cash flow per account — auto-refreshed, replaces Netezza nightly summary job"
TBLPROPERTIES ('layer' = 'gold')
AS
SELECT
  customer_id,
  account_id,
  txn_month,
  COUNT(*)                                              AS txn_count,
  SUM(CASE WHEN is_debit     THEN abs_amount END)       AS total_debits,
  SUM(CASE WHEN NOT is_debit THEN abs_amount END)       AS total_credits,
  SUM(CASE WHEN is_debit THEN -abs_amount
           ELSE abs_amount END)                         AS net_flow,
  ROUND(AVG(abs_amount), 2)                             AS avg_txn_amount,
  MAX(abs_amount)                                       AS largest_txn,
  COUNT(DISTINCT mcc_category)                          AS unique_categories

  -- NOTE: LAG() MoM removed from MV — window + GROUP BY unsupported in SDP MVs.
  -- Run this at query time in DBSQL:
  --   SELECT *, LAG(net_flow) OVER (PARTITION BY account_id ORDER BY txn_month)
  --   FROM gold_sdp_monthly_summary

FROM LIVE.silver_sdp_transactions
GROUP BY customer_id, account_id, txn_month;


-- ================================================================
-- GOLD : Fraud Signals — Spend Velocity Flags
-- ================================================================
-- 💬 SAY: "This is a classic Basel/AML pattern: flag any
--   transaction that exceeds 2x or 3x the customer's average
--   spend in the same merchant category. In Netezza you'd run
--   this as a nightly batch job and the fraud team would review
--   yesterday's flags. Here the MV refreshes continuously —
--   the fraud dashboard is always current.
--
--   Watch TXN-B3-004 in the output: C003 did an $8,500
--   international wire transfer. Their average in that category
--   is much lower — it will flag as HIGH velocity."
-- ================================================================

CREATE OR REFRESH MATERIALIZED VIEW gold_sdp_fraud_signals
COMMENT "Gold: spend velocity fraud flags — HIGH/MEDIUM/NORMAL per transaction"
TBLPROPERTIES ('layer' = 'gold')
AS
SELECT
  transaction_id,
  customer_id,
  account_id,
  txn_date,
  txn_month,
  merchant_name,
  mcc_category,
  abs_amount,
  _source_file,

  -- Window: average spend per customer per MCC (all-time baseline)
  ROUND(AVG(abs_amount) OVER (
    PARTITION BY customer_id, mcc_code
  ), 2)                                                AS avg_spend_this_mcc,

  -- Ratio: how many multiples above average is this transaction?
  ROUND(abs_amount / NULLIF(AVG(abs_amount) OVER (
    PARTITION BY customer_id, mcc_code), 0), 1)        AS spend_ratio,

  CASE
    WHEN abs_amount > 3 * AVG(abs_amount) OVER (
           PARTITION BY customer_id, mcc_code)
    THEN '🚨 HIGH'
    WHEN abs_amount > 2 * AVG(abs_amount) OVER (
           PARTITION BY customer_id, mcc_code)
    THEN '⚠️  MEDIUM'
    ELSE '✅ NORMAL'
  END                                                  AS velocity_flag

FROM LIVE.silver_sdp_transactions
WHERE is_debit = TRUE;
-- NOTE: ORDER BY with window functions removed — not supported in SDP MVs.
-- Sort at query time: ORDER BY velocity_flag, abs_amount DESC
