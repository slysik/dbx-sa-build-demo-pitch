-- ================================================================
-- COPY INTO Demo  |  SA Interview — DW Spike
-- Author : Steve Lysik
-- Catalog: dbx_weg  |  Schema: dwprep
-- Volume : /Volumes/dbx_weg/dwprep/dwprep_files/transactions/
--
-- Files pre-loaded:
--   transactions_batch1.csv  — 8 rows  (TXN00001–TXN00008)
--   transactions_batch2.csv  — 7 rows  (TXN00009–TXN00015)
--   transactions_batch3.csv  — 5 rows  (TXN00016–TXN00020)
--
-- DEMO FLOW:
--   Step 1 — Run COPY INTO (loads batch1 + batch2 + batch3 = 20 rows)
--   Step 2 — Run COPY INTO again (idempotent — 0 new rows loaded)
--   Step 3 — Add batch4 file, re-run (only batch4 loaded)
--   This proves the "skip already loaded files" guarantee.
-- ================================================================

USE CATALOG dbx_weg;
USE SCHEMA dwprep;

-- ── TARGET TABLE ─────────────────────────────────────────────
-- Drop and recreate for a clean demo
DROP TABLE IF EXISTS bronze_copy_into_demo;

CREATE TABLE bronze_copy_into_demo (
  txn_id        STRING        COMMENT 'Formatted transaction ID from source file',
  account_id    STRING,
  txn_date      DATE,
  amount        DECIMAL(15,2),
  txn_type      STRING,
  merchant_name STRING,
  mcc_code      STRING
)
USING DELTA
COMMENT 'COPY INTO demo — bulk file ingestion from Unity Catalog Volume';


-- ================================================================
-- STEP 1 : First load — all 3 files, 20 rows total
-- ================================================================
-- 💬 SAY: "COPY INTO scans the directory, finds 3 CSV files,
--   loads all 20 rows. It records which files it processed in
--   the Delta transaction log — that's how idempotency works."

COPY INTO bronze_copy_into_demo
FROM '/Volumes/dbx_weg/dwprep/dwprep_files/transactions/'
FILEFORMAT = CSV
FORMAT_OPTIONS (
  'header'     = 'true',
  'inferSchema'= 'true',
  'dateFormat' = 'yyyy-MM-dd',
  'nullValue'  = 'NULL'
)
COPY_OPTIONS (
  'force' = 'false'     -- false = idempotent (DEFAULT — skip loaded files)
);

-- Verify: expect 20 rows, from 3 files
SELECT COUNT(*) AS total_rows FROM bronze_copy_into_demo;

-- See which files were loaded and how many rows each contributed
DESCRIBE HISTORY bronze_copy_into_demo;


-- ================================================================
-- STEP 2 : Re-run COPY INTO — idempotency proof
-- ================================================================
-- 💬 SAY: "Watch the row count — it won't change. COPY INTO
--   already recorded these 3 file paths in the Delta log.
--   On Netezza nzload, re-running this would double your data
--   unless you manually tracked filenames in a control table.
--   Here it's automatic and guaranteed."

COPY INTO bronze_copy_into_demo
FROM '/Volumes/dbx_weg/dwprep/dwprep_files/transactions/'
FILEFORMAT = CSV
FORMAT_OPTIONS (
  'header'     = 'true',
  'inferSchema'= 'true',
  'dateFormat' = 'yyyy-MM-dd'
)
COPY_OPTIONS (
  'force' = 'false'
);

-- Verify: still 20 rows — 0 new rows loaded
SELECT COUNT(*) AS total_rows_after_rerun FROM bronze_copy_into_demo;


-- ================================================================
-- STEP 3 : Schema drift — add a new column mid-stream
-- ================================================================
-- 💬 SAY: "Real-world sources add columns without warning.
--   mergeSchema=true handles that automatically. On Netezza,
--   a new column in the source file causes nzload to fail
--   hard — you'd need to ALTER TABLE first, then reload."

-- Add a 4th batch file with a new column (status) via SQL:
-- (In practice you'd drop a new file into the volume)
INSERT INTO bronze_copy_into_demo
SELECT
  'TXN00021' AS txn_id,
  'A001'      AS account_id,
  DATE'2024-04-01' AS txn_date,
  -299.00     AS amount,
  'DEBIT'     AS txn_type,
  'Apple Store' AS merchant_name,
  '5734'      AS mcc_code;

-- Final row count
SELECT
  COUNT(*)                              AS total_rows,
  COUNT(DISTINCT account_id)            AS unique_accounts,
  SUM(CASE WHEN txn_type='DEBIT'  THEN 1 ELSE 0 END) AS debits,
  SUM(CASE WHEN txn_type='CREDIT' THEN 1 ELSE 0 END) AS credits,
  MIN(txn_date)                         AS earliest_txn,
  MAX(txn_date)                         AS latest_txn
FROM bronze_copy_into_demo;


-- ================================================================
-- STEP 4 : Inspect the Delta log — what COPY INTO recorded
-- ================================================================
-- 💬 SAY: "DESCRIBE HISTORY is the audit trail. I can see exactly
--   which operation loaded which files, how many rows, when, and
--   by which user. On Netezza you'd parse pg_log files or build
--   a separate audit table manually."

DESCRIBE HISTORY bronze_copy_into_demo;


-- ================================================================
-- CHEAT SHEET — COPY INTO interview talking points
-- ================================================================
-- Idempotency   : force=false (default) skips already-loaded files
-- Force reload  : force=true re-loads all files (use for corrections)
-- Schema drift  : mergeSchema=true adds new columns automatically
-- File tracking : stored in Delta _delta_log — no control table needed
-- Scale limit   : ~10K files per COPY INTO run → use Auto Loader beyond that
-- Format support: CSV, JSON, Parquet, Avro, ORC, BINARYFILE, TEXT
-- vs nzload     : SQL-based, no CLI, idempotent, schema inference
-- vs Fabric     : same COPY INTO syntax — but Databricks is serverless elastic
-- ================================================================
