-- ============================================================
-- steve-cc.sql  |  Change Data Capture (CDC) Patterns
-- Author  : Steve Lysik  |  SA Interview Prep — DW Spike
-- Catalog : dw            |  Schema: dwprep
-- Run in  : Databricks SQL Serverless Warehouse
--
-- Covers  : CDC ingest patterns  |  MERGE INTO (upsert)
--           SCD Type 1 (overwrite)  |  SCD Type 2 (history)
--           Change Data Feed (CDF)  |  Incremental reads
--           APPLY CHANGES (Spark Declarative Pipelines context)
--           Delete propagation  |  Late-arriving data
--
-- Prereq  : Run after steve-sql.sql (shares dw catalog + dwprep schema)
-- TIP     : Run one SECTION at a time in DBSQL query editor.
-- ============================================================


-- ============================================================
-- SECTION 0 : SETUP
-- ============================================================

CREATE CATALOG IF NOT EXISTS dw
  COMMENT 'Data Warehouse interview prep catalog';

USE CATALOG dw;

-- Reuse the same schema as steve-sql.sql — all practice tables in one place
CREATE SCHEMA IF NOT EXISTS dwprep
  COMMENT 'DW interview practice — Medallion + CDC patterns';

USE SCHEMA dwprep;

-- Clean slate
DROP TABLE IF EXISTS cdc_landing;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_product_scd2;
DROP TABLE IF EXISTS fact_balance;
DROP TABLE IF EXISTS audit_cdc_log;


-- ============================================================
-- SECTION 1 : CDC LANDING TABLE — Simulating a CDC Feed
-- ============================================================
-- In production, CDC events arrive from:
--   • Debezium / Kafka (streaming)
--   • AWS DMS / Azure DMS (batch)
--   • Oracle GoldenGate, Attunity, Fivetran (managed)
--
-- Each CDC record includes:
--   _op       : I(nsert), U(pdate), D(elete) — the operation type
--   _ts       : When the change happened in the source system
--   _seq      : Ordering sequence (handles out-of-order delivery)
--
-- DW CONCEPT: The landing table is append-only. We never delete
-- from it. It's the "journal" — every change ever made to the
-- source system is preserved here for audit and replay.
-- ============================================================

CREATE TABLE cdc_landing (
  -- Business columns (from source system)
  product_id      STRING        COMMENT 'Natural key from OLTP',
  product_name    STRING,
  category        STRING,
  price           DECIMAL(10,2),
  is_active       BOOLEAN,
  -- CDC metadata columns
  _op             STRING        COMMENT 'I=Insert, U=Update, D=Delete',
  _ts             TIMESTAMP     COMMENT 'Source system change timestamp',
  _seq            BIGINT        COMMENT 'Monotonic sequence for ordering',
  _ingest_ts      TIMESTAMP DEFAULT current_timestamp()
)
USING DELTA
COMMENT 'CDC landing: append-only journal of all source changes'
TBLPROPERTIES (
  'delta.appendOnly'           = 'true',
  'delta.enableChangeDataFeed' = 'true'
);


-- ── Load Batch 1: Initial load (5 products) ────────────────
-- Simulates the first full extract from the source system.
-- All operations are 'I' (Insert).

INSERT INTO cdc_landing VALUES
  ('P001', 'High-Yield Savings',    'Deposits',    0.00,  TRUE,  'I', TIMESTAMP'2024-01-01 08:00:00', 1, current_timestamp()),
  ('P002', 'Platinum Credit Card',  'Credit',    199.00,  TRUE,  'I', TIMESTAMP'2024-01-01 08:00:00', 2, current_timestamp()),
  ('P003', 'Auto Loan 60-Month',    'Lending',     0.00,  TRUE,  'I', TIMESTAMP'2024-01-01 08:00:00', 3, current_timestamp()),
  ('P004', 'Basic Checking',        'Deposits',    0.00,  TRUE,  'I', TIMESTAMP'2024-01-01 08:00:00', 4, current_timestamp()),
  ('P005', 'Home Mortgage 30yr',    'Lending',     0.00,  TRUE,  'I', TIMESTAMP'2024-01-01 08:00:00', 5, current_timestamp());

SELECT 'Batch 1 loaded' AS status, COUNT(*) AS rows FROM cdc_landing;


-- ============================================================
-- SECTION 2 : SCD TYPE 1 — MERGE (Overwrite in Place)
-- ============================================================
-- SCD Type 1: "I only care about the current state."
--   • Updates overwrite existing values
--   • Deletes remove (or soft-delete) the row
--   • No history preserved in the target table
--   • Simplest pattern — good for reference/lookup dimensions
--
-- MERGE INTO is the SQL workhorse for CDC processing.
-- It handles INSERT, UPDATE, and DELETE in a single statement.
--
-- DW TALKING POINT: "MERGE on Delta Lake is ACID-compliant.
-- In Netezza we had to do this with staged temp tables and
-- manual INSERT/UPDATE/DELETE sequences. Delta MERGE is one
-- atomic operation — either all changes apply or none do."
-- ============================================================

-- Create the SCD1 target dimension
CREATE TABLE dim_product (
  product_id      STRING,
  product_name    STRING,
  category        STRING,
  price           DECIMAL(10,2),
  is_active       BOOLEAN,
  last_updated_ts TIMESTAMP     COMMENT 'When this row was last modified',
  _cdc_op         STRING        COMMENT 'Last CDC operation applied'
)
USING DELTA
CLUSTER BY (category)
COMMENT 'SCD Type 1: current-state product dimension — history not preserved';


-- ── MERGE: Apply Batch 1 (Initial Load) ─────────────────────
-- Since the target is empty, all rows will be INSERTed.

MERGE INTO dim_product AS tgt
USING (
  -- Get the LATEST version of each product from the CDC landing.
  -- If the same product_id appears multiple times in a batch,
  -- we only want the most recent change (_seq DESC).
  SELECT *
  FROM (
    SELECT *,
      ROW_NUMBER() OVER (
        PARTITION BY product_id
        ORDER BY _seq DESC
      ) AS rn
    FROM cdc_landing
  )
  WHERE rn = 1
) AS src
ON tgt.product_id = src.product_id

-- MATCHED + DELETE operation → remove the row (or soft-delete)
WHEN MATCHED AND src._op = 'D' THEN
  DELETE

-- MATCHED + INSERT or UPDATE → overwrite all columns
WHEN MATCHED AND src._op IN ('I', 'U') THEN
  UPDATE SET
    tgt.product_name    = src.product_name,
    tgt.category        = src.category,
    tgt.price           = src.price,
    tgt.is_active       = src.is_active,
    tgt.last_updated_ts = src._ts,
    tgt._cdc_op         = src._op

-- NOT MATCHED → new product, insert it
WHEN NOT MATCHED AND src._op IN ('I', 'U') THEN
  INSERT (product_id, product_name, category, price, is_active, last_updated_ts, _cdc_op)
  VALUES (src.product_id, src.product_name, src.category, src.price, src.is_active, src._ts, src._op);


-- Verify: should have 5 products, all with _cdc_op = 'I'
SELECT * FROM dim_product ORDER BY product_id;


-- ── Load Batch 2: Updates, a new product, and a delete ──────
-- This simulates the next CDC batch arriving.

INSERT INTO cdc_landing VALUES
  -- Price change on Platinum Credit Card (annual fee increase)
  ('P002', 'Platinum Credit Card',  'Credit',    249.00,  TRUE,  'U', TIMESTAMP'2024-02-01 10:00:00', 6, current_timestamp()),
  -- Discontinue Basic Checking (soft delete)
  ('P004', 'Basic Checking',        'Deposits',    0.00,  FALSE, 'D', TIMESTAMP'2024-02-01 12:00:00', 7, current_timestamp()),
  -- New product launch
  ('P006', 'Student Checking',      'Deposits',    0.00,  TRUE,  'I', TIMESTAMP'2024-02-15 09:00:00', 8, current_timestamp()),
  -- Name change on Home Mortgage (rebranding)
  ('P005', 'HomeFirst Mortgage 30yr','Lending',    0.00,  TRUE,  'U', TIMESTAMP'2024-02-20 14:00:00', 9, current_timestamp());


-- ── MERGE: Apply Batch 2 ────────────────────────────────────
-- Same MERGE statement works for every batch — idempotent pattern.
-- DW NOTE: This is why MERGE is the gold standard for CDC.
-- The same SQL handles inserts, updates, and deletes.

MERGE INTO dim_product AS tgt
USING (
  SELECT *
  FROM (
    SELECT *,
      ROW_NUMBER() OVER (
        PARTITION BY product_id
        ORDER BY _seq DESC
      ) AS rn
    FROM cdc_landing
  )
  WHERE rn = 1
) AS src
ON tgt.product_id = src.product_id
WHEN MATCHED AND src._op = 'D' THEN
  DELETE
WHEN MATCHED AND src._op IN ('I', 'U') THEN
  UPDATE SET
    tgt.product_name    = src.product_name,
    tgt.category        = src.category,
    tgt.price           = src.price,
    tgt.is_active       = src.is_active,
    tgt.last_updated_ts = src._ts,
    tgt._cdc_op         = src._op
WHEN NOT MATCHED AND src._op IN ('I', 'U') THEN
  INSERT (product_id, product_name, category, price, is_active, last_updated_ts, _cdc_op)
  VALUES (src.product_id, src.product_name, src.category, src.price, src.is_active, src._ts, src._op);


-- Verify Batch 2 results:
--   P002 price should be 249.00, _cdc_op = 'U'
--   P004 should be GONE (hard deleted by MERGE)
--   P005 should be renamed to 'HomeFirst Mortgage 30yr'
--   P006 should be new
SELECT * FROM dim_product ORDER BY product_id;


-- ============================================================
-- SECTION 3 : SCD TYPE 2 — Full Version History
-- ============================================================
-- SCD Type 2: "I need to see every historical state."
--   • Updates create a NEW row (new version) and close the old one
--   • Deletes close the current row (eff_end_dt set, is_current=FALSE)
--   • Full audit trail preserved — required for FinServ compliance
--
-- Pattern: Two-step MERGE
--   Step 1: MERGE to CLOSE changed rows (set is_current = FALSE)
--   Step 2: INSERT to ADD new versions
--
-- DW TALKING POINT: "SCD2 is the regulatory backbone. Auditors
-- ask 'what was the customer's credit score on March 31?' and
-- we can answer that with a simple date-range filter. In the old
-- Netezza world this was a multi-join nightmare. With Delta's
-- MERGE and versioning, it's clean and atomic."
-- ============================================================

CREATE TABLE dim_product_scd2 (
  product_sk      BIGINT GENERATED ALWAYS AS IDENTITY
                  COMMENT 'Surrogate key — auto-incremented',
  product_id      STRING        COMMENT 'Natural key from source',
  product_name    STRING,
  category        STRING,
  price           DECIMAL(10,2),
  is_active       BOOLEAN,
  -- SCD2 tracking columns
  eff_start_dt    DATE          COMMENT 'Version effective from (inclusive)',
  eff_end_dt      DATE          COMMENT '9999-12-31 = current version',
  is_current      BOOLEAN       COMMENT 'TRUE = latest version',
  row_hash        STRING        COMMENT 'MD5 of business cols — change detection',
  _cdc_op         STRING
)
USING DELTA
COMMENT 'SCD Type 2: full version history — every change creates a new row';


-- ── Step 1: Initial load into SCD2 ──────────────────────────
-- For the initial load, we pull the current state from Batch 1
-- CDC events (only _op = 'I' from the first batch).

INSERT INTO dim_product_scd2 (product_id, product_name, category, price, is_active, eff_start_dt, eff_end_dt, is_current, row_hash, _cdc_op)
SELECT
  product_id,
  product_name,
  category,
  price,
  is_active,
  CAST(_ts AS DATE)           AS eff_start_dt,
  DATE'9999-12-31'            AS eff_end_dt,
  TRUE                        AS is_current,
  MD5(CONCAT_WS('|',
    product_id, product_name, category,
    CAST(price AS STRING), CAST(is_active AS STRING)
  ))                          AS row_hash,
  _op                         AS _cdc_op
FROM cdc_landing
WHERE _seq <= 5;              -- Batch 1 only

SELECT * FROM dim_product_scd2 ORDER BY product_id;


-- ── Step 2: Apply Batch 2 changes with SCD2 pattern ─────────
-- Two operations:
--   (A) MERGE to CLOSE rows where business data changed
--   (B) INSERT to create NEW versions for changed/new rows

-- (A) CLOSE changed rows
MERGE INTO dim_product_scd2 AS tgt
USING (
  -- Batch 2 changes: seq 6-9
  SELECT
    product_id,
    product_name,
    category,
    price,
    is_active,
    _op,
    _ts,
    MD5(CONCAT_WS('|',
      product_id, product_name, category,
      CAST(price AS STRING), CAST(is_active AS STRING)
    )) AS row_hash
  FROM (
    SELECT *,
      ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY _seq DESC) AS rn
    FROM cdc_landing
    WHERE _seq > 5              -- Batch 2 only
  )
  WHERE rn = 1
) AS src
ON  tgt.product_id = src.product_id
AND tgt.is_current = TRUE
AND tgt.row_hash  != src.row_hash   -- Only close if data actually changed

WHEN MATCHED THEN
  UPDATE SET
    tgt.is_current = FALSE,
    tgt.eff_end_dt = DATEADD(DAY, -1, CAST(src._ts AS DATE));
    -- Close the old version the day before the new one starts


-- (B) INSERT new versions for changed rows + brand new products
INSERT INTO dim_product_scd2 (product_id, product_name, category, price, is_active, eff_start_dt, eff_end_dt, is_current, row_hash, _cdc_op)
SELECT
  src.product_id,
  src.product_name,
  src.category,
  src.price,
  src.is_active,
  CAST(src._ts AS DATE)       AS eff_start_dt,
  -- If _op = 'D', close immediately (end date = start date)
  CASE WHEN src._op = 'D' THEN CAST(src._ts AS DATE)
       ELSE DATE'9999-12-31'
  END                         AS eff_end_dt,
  -- If _op = 'D', this version is NOT current
  src._op != 'D'              AS is_current,
  src.row_hash,
  src._op                     AS _cdc_op
FROM (
  SELECT
    product_id, product_name, category, price, is_active, _op, _ts,
    MD5(CONCAT_WS('|',
      product_id, product_name, category,
      CAST(price AS STRING), CAST(is_active AS STRING)
    )) AS row_hash
  FROM (
    SELECT *,
      ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY _seq DESC) AS rn
    FROM cdc_landing
    WHERE _seq > 5
  )
  WHERE rn = 1
) AS src
WHERE NOT EXISTS (
  -- Don't insert if current version already matches (idempotency)
  SELECT 1 FROM dim_product_scd2 t
  WHERE t.product_id = src.product_id
    AND t.is_current = TRUE
    AND t.row_hash   = src.row_hash
);


-- ── Verify SCD2 results ─────────────────────────────────────
-- P002 should have 2 rows: old ($199) closed, new ($249) current
-- P004 should have 2 rows: original + deleted version (is_current=FALSE)
-- P005 should have 2 rows: old name closed, new name current
-- P006 should have 1 row: brand new, is_current=TRUE

SELECT
  product_sk,
  product_id,
  product_name,
  price,
  is_active,
  eff_start_dt,
  eff_end_dt,
  is_current,
  _cdc_op
FROM dim_product_scd2
ORDER BY product_id, eff_start_dt;


-- ── SCD2 Querying Patterns ──────────────────────────────────

-- Current state (most common query)
SELECT * FROM dim_product_scd2
WHERE is_current = TRUE
ORDER BY product_id;

-- Historical state: "What was the product catalog on Jan 15, 2024?"
-- This is the auditor's favorite question.
SELECT * FROM dim_product_scd2
WHERE eff_start_dt <= DATE'2024-01-15'
  AND eff_end_dt   >= DATE'2024-01-15'
ORDER BY product_id;

-- Change detection: which products changed between Batch 1 and 2?
SELECT
  product_id,
  product_name,
  _cdc_op,
  eff_start_dt,
  eff_end_dt,
  is_current
FROM dim_product_scd2
WHERE _cdc_op IN ('U', 'D')
ORDER BY product_id, eff_start_dt;


-- ============================================================
-- SECTION 4 : CHANGE DATA FEED (CDF) — Delta's Built-in CDC
-- ============================================================
-- CHANGE DATA FEED (CDF) is Delta Lake's native CDC mechanism.
-- When enabled on a table (delta.enableChangeDataFeed = true),
-- Delta automatically tracks all changes and makes them readable
-- via table_changes() function.
--
-- This is different from source-system CDC (Debezium/DMS).
-- CDF captures changes WITHIN Databricks — useful for:
--   • Feeding downstream Silver/Gold tables incrementally
--   • Audit logging ("what changed in this table and when?")
--   • Replicating Delta tables to other systems
--   • Triggering notifications on data changes
--
-- DW TALKING POINT: "CDF is the lakehouse equivalent of Oracle
-- Streams or DB2 CDC. But it's built into the storage format,
-- not bolted on. Any Delta table can expose its change feed
-- with a single table property."
-- ============================================================

-- CDF is already enabled on cdc_landing (set in TBLPROPERTIES above).
-- Let's also enable it on dim_product for downstream tracking.

ALTER TABLE dim_product
SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

-- ── Read the change feed ─────────────────────────────────────
-- table_changes() returns every row that was inserted, updated, or deleted,
-- along with metadata columns:
--   _change_type    : insert, update_preimage, update_postimage, delete
--   _commit_version : Delta version number
--   _commit_timestamp: When the commit happened

-- See all changes to dim_product since version 0
SELECT
  _change_type,
  _commit_version,
  _commit_timestamp,
  product_id,
  product_name,
  price,
  _cdc_op
FROM table_changes('dim_product', 0)
ORDER BY _commit_version, product_id;

-- ── Incremental read: changes since last processed version ───
-- In production you'd track the last processed version in a checkpoint table.
-- This pattern reads only new changes since version 1.

-- Simulated: "Give me only what changed after the initial load"
SELECT
  _change_type,
  product_id,
  product_name,
  price
FROM table_changes('dim_product', 2)   -- version 2 = after Batch 2 MERGE
ORDER BY product_id;

-- ── CDF for audit: show before/after for updates ────────────
-- update_preimage = the row BEFORE the update
-- update_postimage = the row AFTER the update
-- This is gold for audit trails.

SELECT
  _change_type,
  product_id,
  product_name,
  price,
  _commit_timestamp
FROM table_changes('dim_product', 0)
WHERE _change_type IN ('update_preimage', 'update_postimage')
ORDER BY product_id, _commit_timestamp, _change_type;


-- ============================================================
-- SECTION 5 : INCREMENTAL MERGE PATTERN — Production-Grade
-- ============================================================
-- In production, you don't re-MERGE the entire CDC landing table
-- every run. Instead, you use a WATERMARK (high-water mark) to
-- track the last processed _seq, and only MERGE new rows.
--
-- This is the incremental pattern:
--   1. Read the last processed _seq from a control table
--   2. MERGE only rows where _seq > last_processed
--   3. Update the control table with the new high-water mark
--
-- DW TALKING POINT: "This is the same pattern as Netezza's
-- incremental loads, but with ACID guarantees. If the MERGE fails
-- partway through, nothing is committed. No partial loads, no
-- orphaned rows, no manual cleanup."
-- ============================================================

-- Control table for tracking processing state
CREATE TABLE audit_cdc_log (
  table_name          STRING,
  last_processed_seq  BIGINT,
  last_processed_ts   TIMESTAMP,
  rows_processed      INT,
  run_ts              TIMESTAMP DEFAULT current_timestamp()
)
USING DELTA
COMMENT 'CDC control table — tracks incremental processing watermarks';

-- Record that we've processed through seq 9
INSERT INTO audit_cdc_log (table_name, last_processed_seq, last_processed_ts, rows_processed)
VALUES ('dim_product', 9, current_timestamp(), 9);


-- ── Load Batch 3: More changes ──────────────────────────────
INSERT INTO cdc_landing VALUES
  -- Another price change on P002
  ('P002', 'Platinum Credit Card',  'Credit',  299.00, TRUE,  'U', TIMESTAMP'2024-03-01 10:00:00', 10, current_timestamp()),
  -- P006 gets deactivated
  ('P006', 'Student Checking',      'Deposits',  0.00, FALSE, 'U', TIMESTAMP'2024-03-15 11:00:00', 11, current_timestamp()),
  -- Brand new product
  ('P007', 'Premium Money Market',  'Deposits', 0.00,  TRUE,  'I', TIMESTAMP'2024-03-20 09:00:00', 12, current_timestamp());


-- ── Incremental MERGE: Only process new rows ─────────────────
-- This is the production pattern. No scanning of already-processed rows.

MERGE INTO dim_product AS tgt
USING (
  SELECT *
  FROM (
    SELECT *,
      ROW_NUMBER() OVER (
        PARTITION BY product_id
        ORDER BY _seq DESC
      ) AS rn
    FROM cdc_landing
    WHERE _seq > (
      -- High-water mark: only rows newer than last processed
      SELECT COALESCE(MAX(last_processed_seq), 0)
      FROM audit_cdc_log
      WHERE table_name = 'dim_product'
    )
  )
  WHERE rn = 1
) AS src
ON tgt.product_id = src.product_id
WHEN MATCHED AND src._op = 'D' THEN
  DELETE
WHEN MATCHED AND src._op IN ('I', 'U') THEN
  UPDATE SET
    tgt.product_name    = src.product_name,
    tgt.category        = src.category,
    tgt.price           = src.price,
    tgt.is_active       = src.is_active,
    tgt.last_updated_ts = src._ts,
    tgt._cdc_op         = src._op
WHEN NOT MATCHED AND src._op IN ('I', 'U') THEN
  INSERT (product_id, product_name, category, price, is_active, last_updated_ts, _cdc_op)
  VALUES (src.product_id, src.product_name, src.category, src.price, src.is_active, src._ts, src._op);

-- Update the control table
INSERT INTO audit_cdc_log (table_name, last_processed_seq, last_processed_ts, rows_processed)
VALUES ('dim_product', 12, current_timestamp(), 3);

-- Verify
SELECT * FROM dim_product ORDER BY product_id;
SELECT * FROM audit_cdc_log ORDER BY run_ts;


-- ============================================================
-- SECTION 6 : LATE-ARRIVING DATA — A DW Classic Problem
-- ============================================================
-- Late-arriving data: a CDC event arrives out of order.
-- E.g., Batch 4 arrives with a change timestamped BEFORE Batch 3.
-- The _seq ensures correct ordering even if timestamps overlap.
--
-- DW TALKING POINT: "Late-arriving data was the bane of our
-- Netezza ETL. We had to re-run entire daily loads. With Delta
-- MERGE, we simply process the late event — it upserts correctly
-- because we use _seq ordering, not arrival time."
-- ============================================================

-- Simulate late arrival: this event happened on Feb 10 but arrives now
INSERT INTO cdc_landing VALUES
  ('P003', 'Auto Loan 48-Month',   'Lending', 0.00, TRUE, 'U', TIMESTAMP'2024-02-10 08:00:00', 13, current_timestamp());
  -- Note: _seq 13 is higher than 12, so it will be picked up
  -- by incremental processing, even though _ts is older

-- Process the late arrival (same incremental MERGE)
MERGE INTO dim_product AS tgt
USING (
  SELECT *
  FROM (
    SELECT *,
      ROW_NUMBER() OVER (
        PARTITION BY product_id
        ORDER BY _seq DESC
      ) AS rn
    FROM cdc_landing
    WHERE _seq > (
      SELECT COALESCE(MAX(last_processed_seq), 0)
      FROM audit_cdc_log
      WHERE table_name = 'dim_product'
    )
  )
  WHERE rn = 1
) AS src
ON tgt.product_id = src.product_id
WHEN MATCHED AND src._op = 'D' THEN DELETE
WHEN MATCHED AND src._op IN ('I', 'U') THEN
  UPDATE SET
    tgt.product_name = src.product_name, tgt.category = src.category,
    tgt.price = src.price, tgt.is_active = src.is_active,
    tgt.last_updated_ts = src._ts, tgt._cdc_op = src._op
WHEN NOT MATCHED AND src._op IN ('I', 'U') THEN
  INSERT (product_id, product_name, category, price, is_active, last_updated_ts, _cdc_op)
  VALUES (src.product_id, src.product_name, src.category, src.price, src.is_active, src._ts, src._op);

INSERT INTO audit_cdc_log (table_name, last_processed_seq, last_processed_ts, rows_processed)
VALUES ('dim_product', 13, current_timestamp(), 1);

-- P003 should now be 'Auto Loan 48-Month' (was 'Auto Loan 60-Month')
SELECT * FROM dim_product WHERE product_id = 'P003';


-- ============================================================
-- SECTION 7 : FACT TABLE INCREMENTAL LOAD — Running Balance
-- ============================================================
-- Not all CDC targets are dimensions. Fact tables also need
-- incremental loads. Here we show an append-only fact pattern
-- with running balance computation.
-- ============================================================

CREATE TABLE fact_balance (
  snapshot_date   DATE,
  product_id      STRING,
  product_name    STRING,
  category        STRING,
  daily_change    DECIMAL(15,2)   COMMENT 'Net change on this date',
  running_total   DECIMAL(15,2)   COMMENT 'Cumulative total as of snapshot_date'
)
USING DELTA
CLUSTER BY (snapshot_date, category)
COMMENT 'Fact: daily balance snapshots derived from CDC events';

-- Build fact from the CDC journal using window functions
INSERT INTO fact_balance
SELECT
  CAST(_ts AS DATE)           AS snapshot_date,
  product_id,
  product_name,
  category,
  price                       AS daily_change,
  -- Running total per product, ordered by event sequence
  SUM(price) OVER (
    PARTITION BY product_id
    ORDER BY _seq
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  )                           AS running_total
FROM (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY product_id, _seq ORDER BY _ingest_ts DESC) AS rn
  FROM cdc_landing
)
WHERE rn = 1
ORDER BY product_id, _seq;

SELECT * FROM fact_balance ORDER BY product_id, snapshot_date;


-- ============================================================
-- SECTION 8 : APPLY CHANGES — Declarative CDC (SDP Context)
-- ============================================================
-- APPLY CHANGES is the declarative CDC syntax used in Spark
-- Declarative Pipelines (SDP, formerly DLT). It automates the
-- MERGE logic we wrote manually above.
--
-- You can't run APPLY CHANGES in a SQL worksheet — it requires
-- an SDP pipeline context. But knowing the syntax is essential
-- for the interview because it shows you understand Databricks'
-- recommended production pattern.
--
-- The equivalent of our manual SCD1 MERGE above in SDP:
-- ────────────────────────────────────────────────────────────
-- NOTE: This is pseudocode for interview discussion — won't execute here.
--
-- CREATE OR REFRESH STREAMING TABLE dim_product_sdp;
--
-- APPLY CHANGES INTO dim_product_sdp
-- FROM STREAM(cdc_landing)
-- KEYS (product_id)
-- APPLY AS DELETE WHEN _op = 'D'
-- SEQUENCE BY _seq
-- COLUMNS * EXCEPT (_op, _ts, _seq, _ingest_ts)
-- STORED AS SCD TYPE 1;
--
-- For SCD2, change the last line to:
-- STORED AS SCD TYPE 2;
-- ────────────────────────────────────────────────────────────
--
-- DW TALKING POINT: "APPLY CHANGES is Databricks' answer to
-- Informatica PowerCenter's SCD wizard. But it's declarative SQL,
-- not a GUI tool. It handles dedup, ordering, delete propagation,
-- and SCD versioning automatically. For production pipelines,
-- this is what I'd recommend over hand-rolled MERGE."


-- ============================================================
-- SECTION 9 : VERIFY & SUMMARISE
-- ============================================================

-- Final state of all tables
SELECT '1. cdc_landing'      AS step, COUNT(*) AS rows FROM cdc_landing
UNION ALL
SELECT '2. dim_product (SCD1)',        COUNT(*) FROM dim_product
UNION ALL
SELECT '3. dim_product_scd2 (SCD2)',   COUNT(*) FROM dim_product_scd2
UNION ALL
SELECT '4. fact_balance',              COUNT(*) FROM fact_balance
UNION ALL
SELECT '5. audit_cdc_log',            COUNT(*) FROM audit_cdc_log;

-- Full audit trail
SELECT * FROM audit_cdc_log ORDER BY run_ts;

-- SCD2 version summary
SELECT
  product_id,
  COUNT(*) AS total_versions,
  SUM(CASE WHEN is_current THEN 1 ELSE 0 END) AS current_versions
FROM dim_product_scd2
GROUP BY product_id
ORDER BY product_id;


-- ============================================================
-- SECTION 10 : CLEANUP (Optional)
-- ============================================================
-- Uncomment to drop everything:
--
-- DROP TABLE IF EXISTS fact_balance;
-- DROP TABLE IF EXISTS audit_cdc_log;
-- DROP TABLE IF EXISTS dim_product_scd2;
-- DROP TABLE IF EXISTS dim_product;
-- DROP TABLE IF EXISTS cdc_landing;
-- DROP SCHEMA IF EXISTS dwprep;  -- careful: shared with steve-sql.sql


-- ============================================================
-- QUICK REFERENCE — CDC Patterns Cheat Sheet
-- ============================================================
--
-- | Pattern           | When to Use                                | Key SQL                         |
-- |-------------------|--------------------------------------------|---------------------------------|
-- | SCD Type 1        | Current state only, no history needed      | MERGE INTO ... UPDATE/DELETE    |
-- | SCD Type 2        | Full history required (regulatory/audit)   | MERGE to close + INSERT new    |
-- | CDF (table_changes)| Read Delta changes downstream             | SELECT * FROM table_changes()  |
-- | Incremental MERGE | Production loads (avoid full table scan)   | WHERE _seq > last_processed    |
-- | Late-arriving     | Out-of-order events from source            | _seq ordering, not _ts         |
-- | APPLY CHANGES     | SDP pipelines (declarative, production)    | APPLY CHANGES INTO ... KEYS()  |
--
-- KEY DELTA PROPERTIES:
--   delta.appendOnly           = true   → Bronze tables (prevent accidental DML)
--   delta.enableChangeDataFeed = true   → Enable CDF for downstream consumers
--   delta.autoOptimize.*       = true   → Auto-compact small files on write
--
-- INTERVIEW TIPS:
--   • Always mention ACID guarantees when discussing MERGE
--   • Contrast with Netezza: "staged temp table + 3 DML statements"
--   • Mention APPLY CHANGES as the recommended production pattern
--   • Bring up CDF when asked "how do downstream tables know what changed?"
--   • Late-arriving data: "_seq ordering is the solution, not timestamps"
-- ============================================================
