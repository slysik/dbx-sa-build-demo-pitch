-- ================================================================
-- steve-sql.sql  |  Databricks SQL — DW Interview Deep Dive
-- Author  : Steve Lysik  |  SA Interview Prep — DW Spike
-- Catalog : dw           |  Schema: dwprep
-- Runs on : Databricks SQL Serverless Warehouse
--
-- INTERVIEW WALK-THROUGH FORMAT
--   Explain each section as if presenting to an interviewer.
--   Comments written as "say this out loud" coaching notes.
--   Netezza / Yellowbrick comparisons on every major feature.
--
-- SECTIONS
--   0  Setup & schema
--   1  Bronze  — raw landing, CONSTRAINTS, Change Data Feed
--   2  Silver  — SCD Type 2 MERGE, FOREIGN KEYS, dedup
--   3  Gold    — Liquid Clustering, Materialized Views, Photon
--   4  Performance deep dive — LC vs Zone Maps, MV vs agg tables
--   5  Advanced features — CLONE, STREAMING TABLES, APPLY CHANGES INTO
--   6  Time Travel & audit trail
--   7  Interview challenge queries (window fns, fraud signals, SCD)
--   8  Cheat sheet
--
-- REPEATABILITY
--   Script uses CREATE OR REPLACE TABLE throughout.
--   Safe to run top-to-bottom multiple times — cleans up first.
-- ================================================================


-- ================================================================
-- SECTION 0 : SETUP
-- ================================================================
-- 💬 SAY: "I always start with the catalog and schema context
--   so every object is created in exactly the right place.
--   In a production deployment this would be parameterised
--   through a Databricks Asset Bundle variable."
-- ================================================================

-- ── Catalog — create if it doesn't exist ─────────────────────
-- 💬 SAY: "In Unity Catalog, a catalog is the top-level
--   namespace — the equivalent of a database in Netezza or
--   Snowflake. I create a dedicated catalog per domain or
--   environment (dev/prod) so governance policies, RBAC, and
--   storage are fully isolated at the catalog boundary."
--
-- NETEZZA: no catalog concept — all databases are peers in a
--   flat namespace. Security is at the database + schema level.
-- SNOWFLAKE: same three-level namespace (database.schema.table)
--   but no unified governance layer like Unity Catalog.

CREATE CATALOG IF NOT EXISTS dw
  COMMENT 'DW interview demo catalog — FinServ Medallion architecture';

USE CATALOG dw;

-- ── Schema ────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS dwprep
  COMMENT 'DW interview practice — Medallion architecture, FinServ scenario';

USE SCHEMA dwprep;

-- ── Clean up for repeatability ────────────────────────────────
-- DROP ORDER matters: MVs reference tables, drop MVs first
DROP MATERIALIZED VIEW  IF EXISTS gold_mv_monthly_summary;
DROP MATERIALIZED VIEW  IF EXISTS gold_mv_mcc_spend_summary;
DROP TABLE              IF EXISTS gold_fact_transaction;
DROP TABLE              IF EXISTS gold_dim_account;
DROP TABLE              IF EXISTS gold_dim_customer;
DROP TABLE              IF EXISTS silver_fact_transaction;
DROP TABLE              IF EXISTS silver_dim_account;
DROP TABLE              IF EXISTS silver_dim_customer;
DROP TABLE              IF EXISTS bronze_raw_transactions;
DROP TABLE              IF EXISTS bronze_raw_accounts;
DROP TABLE              IF EXISTS bronze_raw_customers;


-- ================================================================
-- SECTION 1 : BRONZE LAYER  — "Land everything, change nothing"
-- ================================================================
-- 💬 SAY: "Bronze is my raw landing zone. I preserve source
--   schema exactly — no transforms, no business logic. If a
--   source system sends garbage, I want to see the original
--   garbage in Bronze so I can debug upstream. Every table
--   gets two audit columns: _ingest_ts and _source.
--   I also enable Change Data Feed here so Silver can consume
--   only the delta on each pipeline run instead of a full scan."
--
-- NETEZZA COMPARISON:
--   Netezza has no staging concept like Bronze — data lands
--   directly into the EDW in its final modelled form.
--   Result: you lose the raw record forever after a transform.
--   Delta Bronze gives you RESTORE and TIME TRAVEL — Netezza
--   requires a separate archive/backup strategy for that.
--
-- YELLOWBRICK COMPARISON:
--   Yellowbrick is an in-memory MPP warehouse — not designed
--   for raw landing of semi-structured or dirty data.
--   You'd typically land to S3/ADLS first, then COPY INTO
--   Yellowbrick. Delta Bronze replaces that S3 staging layer
--   with governance, versioning, and queryability.
-- ================================================================

-- ── 1A : Customers ───────────────────────────────────────────

CREATE OR REPLACE TABLE bronze_raw_customers (
  customer_id     STRING         NOT NULL  COMMENT 'Natural key from core banking',
  first_name      STRING         NOT NULL,
  last_name       STRING         NOT NULL,
  email           STRING,
  city            STRING,
  state           STRING,
  credit_score    INT,
  annual_income   DECIMAL(15,2),
  _ingest_ts      TIMESTAMP      NOT NULL  COMMENT 'Row arrival time — set by pipeline',
  _source         STRING         NOT NULL  COMMENT 'Source system identifier (audit)',
  -- ────────────────────────────────────────────────────────────
  -- CONSTRAINTS — enforced at write time (Delta checks on INSERT/MERGE)
  --
  -- 💬 SAY: "Databricks CHECK constraints are enforced — any row
  --   that violates them is rejected with an error at write time,
  --   not silently passed through. That's a data quality gate
  --   without needing a separate DQ framework."
  --
  -- NETEZZA: CHECK constraints exist but are INFORMATIONAL ONLY —
  --   Netezza optimizer uses them for query planning but never
  --   rejects a bad row. You'd discover bad data at report time.
  --
  -- YELLOWBRICK: Same as Netezza — constraints are informational.
  --   Yellowbrick relies on ETL pipelines to enforce quality.
  -- ────────────────────────────────────────────────────────────
  CONSTRAINT chk_credit_score   CHECK (credit_score BETWEEN 300 AND 850),
  CONSTRAINT chk_annual_income  CHECK (annual_income >= 0),
  CONSTRAINT chk_state_len      CHECK (LENGTH(state) = 2)
)
USING DELTA
COMMENT 'Bronze: raw customer CDC feed from core banking mainframe'
TBLPROPERTIES (
  -- appendOnly prevents accidental UPDATE/DELETE on Bronze
  -- Interviewer question: "why not just use permissions?" →
  -- BOTH: permissions prevent human error, appendOnly prevents
  -- pipeline code bugs from silently corrupting history.
  'delta.appendOnly'             = 'true',
  -- Change Data Feed (CDF): tracks row-level changes (insert/update/delete)
  -- Silver queries _change_type and _commit_version to process only deltas
  'delta.enableChangeDataFeed'   = 'true',
  'layer'                        = 'bronze'
);

-- ── 1B : Accounts ────────────────────────────────────────────

CREATE OR REPLACE TABLE bronze_raw_accounts (
  account_id      STRING        NOT NULL,
  customer_id     STRING        NOT NULL,
  account_type    STRING        NOT NULL  COMMENT 'CHECKING | SAVINGS | CREDIT | LOAN',
  open_date       DATE          NOT NULL,
  credit_limit    DECIMAL(15,2)           COMMENT 'NULL for non-revolving accounts',
  interest_rate   DECIMAL(6,4),
  status          STRING        NOT NULL  COMMENT 'ACTIVE | CLOSED | FROZEN',
  _ingest_ts      TIMESTAMP     NOT NULL,
  _source         STRING        NOT NULL,
  CONSTRAINT chk_account_type  CHECK (account_type IN ('CHECKING','SAVINGS','CREDIT','LOAN')),
  CONSTRAINT chk_status        CHECK (status IN ('ACTIVE','CLOSED','FROZEN')),
  CONSTRAINT chk_interest_rate CHECK (interest_rate BETWEEN 0 AND 1)
)
USING DELTA
COMMENT 'Bronze: raw account records from core banking'
TBLPROPERTIES (
  'delta.appendOnly'           = 'true',
  'delta.enableChangeDataFeed' = 'true',
  'layer'                      = 'bronze'
);

-- ── 1C : Transactions — high-volume fact source ───────────────
-- 💬 SAY: "Transactions are the highest-volume Bronze table.
--   I'm NOT applying Liquid Clustering here because Bronze is
--   append-only — clustering benefits reads, and Bronze is
--   write-optimised. Clustering happens at Gold, where the
--   analytical query patterns are known."

CREATE OR REPLACE TABLE bronze_raw_transactions (
  transaction_id  STRING        NOT NULL,
  account_id      STRING        NOT NULL,
  txn_date        DATE          NOT NULL,
  txn_ts          TIMESTAMP     NOT NULL,
  amount          DECIMAL(15,2) NOT NULL  COMMENT 'Negative=debit, Positive=credit',
  txn_type        STRING        NOT NULL  COMMENT 'DEBIT | CREDIT',
  merchant_name   STRING,
  mcc_code        STRING                  COMMENT 'ISO 18245 — 4-digit Merchant Category Code',
  status          STRING        NOT NULL  COMMENT 'POSTED | PENDING | REVERSED',
  _ingest_ts      TIMESTAMP     NOT NULL,
  _source         STRING        NOT NULL,
  CONSTRAINT chk_txn_type   CHECK (txn_type IN ('DEBIT','CREDIT')),
  CONSTRAINT chk_txn_status CHECK (status IN ('POSTED','PENDING','REVERSED')),
  CONSTRAINT chk_mcc_len    CHECK (mcc_code IS NULL OR LENGTH(mcc_code) = 4)
)
USING DELTA
COMMENT 'Bronze: raw transactions — append-only, includes duplicates and reversals'
TBLPROPERTIES (
  'delta.appendOnly'           = 'true',
  'delta.enableChangeDataFeed' = 'true',
  'layer'                      = 'bronze'
);

-- ── Load Bronze sample data ───────────────────────────────────
-- Batch 1: initial load
INSERT INTO bronze_raw_customers VALUES
  ('C001','Alice',  'Johnson', 'alice@bank.com', 'Chicago', 'IL', 760, 125000.00, current_timestamp(),'core_banking_v1'),
  ('C002','Bob',    'Smith',   'bob@bank.com',   'New York','NY', 680,  85000.00, current_timestamp(),'core_banking_v1'),
  ('C003','Carol',  'Davis',   'carol@bank.com', 'Dallas',  'TX', 720,  98000.00, current_timestamp(),'core_banking_v1'),
  ('C004','David',  'Wilson',  'david@bank.com', 'Seattle', 'WA', 800, 210000.00, current_timestamp(),'core_banking_v1'),
  ('C005','Eva',  'Martinez',  'eva@bank.com',   'Miami',   'FL', 640,  62000.00, current_timestamp(),'core_banking_v1');

-- Batch 2: C002 credit score improved (SCD Type 2 will version this)
INSERT INTO bronze_raw_customers VALUES
  ('C002','Bob','Smith','bob@bank.com','New York','NY', 710, 85000.00, current_timestamp(),'core_banking_v2');

INSERT INTO bronze_raw_accounts VALUES
  ('A001','C001','CHECKING', DATE'2020-01-15', NULL,       0.0000,'ACTIVE', current_timestamp(),'core_banking_v1'),
  ('A002','C001','CREDIT',   DATE'2020-03-01', 10000.00,   0.1999,'ACTIVE', current_timestamp(),'core_banking_v1'),
  ('A003','C002','SAVINGS',  DATE'2019-06-20', NULL,       0.0475,'ACTIVE', current_timestamp(),'core_banking_v1'),
  ('A004','C003','CHECKING', DATE'2021-11-01', NULL,       0.0000,'ACTIVE', current_timestamp(),'core_banking_v1'),
  ('A005','C004','LOAN',     DATE'2022-05-15', 250000.00,  0.0625,'ACTIVE', current_timestamp(),'core_banking_v1'),
  ('A006','C005','CREDIT',   DATE'2023-02-28', 5000.00,    0.2399,'CLOSED', current_timestamp(),'core_banking_v1');

INSERT INTO bronze_raw_transactions VALUES
  -- MCC 5411 = Grocery  |  MCC 6552 = Mortgage/Real Estate
  -- MCC 4511 = Airlines |  MCC 5912 = Pharmacies
  -- MCC 6012 = Financial Institutions  |  MCC 0000 = Payroll
  ('T0001','A001',DATE'2024-01-10',TIMESTAMP'2024-01-10 09:15:00', -250.00,'DEBIT', 'Whole Foods Market','5411','POSTED',  current_timestamp(),'core_banking_v1'),
  ('T0002','A001',DATE'2024-01-11',TIMESTAMP'2024-01-11 14:22:00', 3500.00,'CREDIT','PAYROLL DIRECT DEP', '0000','POSTED',  current_timestamp(),'core_banking_v1'),
  ('T0003','A002',DATE'2024-01-12',TIMESTAMP'2024-01-12 18:45:00',  -89.99,'DEBIT', 'Amazon.com',         '5999','POSTED',  current_timestamp(),'core_banking_v1'),
  -- ⚠️  Intentional duplicate: T0003 re-sent by source system.
  --     Silver ROW_NUMBER() dedup removes this. Classic EDW problem.
  ('T0003','A002',DATE'2024-01-12',TIMESTAMP'2024-01-12 18:45:00',  -89.99,'DEBIT', 'Amazon.com',         '5999','POSTED',  current_timestamp(),'core_banking_v1'),
  ('T0004','A003',DATE'2024-01-13',TIMESTAMP'2024-01-13 10:00:00',  500.00,'CREDIT','TRANSFER IN',         '6012','POSTED',  current_timestamp(),'core_banking_v1'),
  ('T0005','A004',DATE'2024-01-14',TIMESTAMP'2024-01-14 12:30:00',  -45.00,'DEBIT', 'Shell Oil',           '5541','POSTED',  current_timestamp(),'core_banking_v1'),
  ('T0006','A001',DATE'2024-01-15',TIMESTAMP'2024-01-15 08:00:00',-1200.00,'DEBIT', 'Rent Payment',        '6552','POSTED',  current_timestamp(),'core_banking_v1'),
  ('T0007','A002',DATE'2024-01-16',TIMESTAMP'2024-01-16 19:10:00', -350.00,'DEBIT', 'Delta Airlines',      '4511','PENDING', current_timestamp(),'core_banking_v1'),
  ('T0008','A005',DATE'2024-01-17',TIMESTAMP'2024-01-17 06:00:00',-1875.00,'DEBIT', 'MORTGAGE PAYMENT',    '6552','POSTED',  current_timestamp(),'core_banking_v1'),
  ('T0009','A001',DATE'2024-01-18',TIMESTAMP'2024-01-18 11:30:00',  -75.50,'DEBIT', 'CVS Pharmacy',        '5912','POSTED',  current_timestamp(),'core_banking_v1'),
  ('T0010','A003',DATE'2024-01-19',TIMESTAMP'2024-01-19 16:45:00', 1000.00,'CREDIT','TRANSFER IN',          '6012','POSTED',  current_timestamp(),'core_banking_v1'),
  ('T0011','A002',DATE'2024-01-31',TIMESTAMP'2024-01-31 23:59:00',  -25.00,'DEBIT', 'INTEREST CHARGE',     '6012','POSTED',  current_timestamp(),'core_banking_v1'),
  -- ⚠️  Intentional REVERSED: T0012 posted then reversed same day.
  --     Silver excludes REVERSED from clean fact. Bronze keeps it for audit.
  ('T0012','A005',DATE'2024-01-31',TIMESTAMP'2024-01-31 06:00:00',-1875.00,'DEBIT', 'MORTGAGE PAYMENT',    '6552','REVERSED',current_timestamp(),'core_banking_v1'),
  ('T0013','A001',DATE'2024-02-05',TIMESTAMP'2024-02-05 09:00:00', 3500.00,'CREDIT','PAYROLL DIRECT DEP',  '0000','POSTED',  current_timestamp(),'core_banking_v2'),
  ('T0014','A004',DATE'2024-02-10',TIMESTAMP'2024-02-10 13:15:00', -120.00,'DEBIT', 'Home Depot',          '5200','POSTED',  current_timestamp(),'core_banking_v2'),
  ('T0015','A001',DATE'2024-02-15',TIMESTAMP'2024-02-15 08:00:00',-1200.00,'DEBIT', 'Rent Payment',        '6552','POSTED',  current_timestamp(),'core_banking_v2');

-- ── Verify Bronze ─────────────────────────────────────────────
SELECT 'bronze_raw_customers'   AS tbl, count(*) AS rows FROM bronze_raw_customers
UNION ALL
SELECT 'bronze_raw_accounts',          count(*)          FROM bronze_raw_accounts
UNION ALL
SELECT 'bronze_raw_transactions',      count(*)          FROM bronze_raw_transactions;
-- Expected: customers=6 (5 orig + 1 update row for C002)
--           accounts=6, transactions=16 (15 + 1 duplicate T0003)


-- ================================================================
-- SECTION 2 : SILVER LAYER  — "Make it trusted and integrated"
-- ================================================================
-- 💬 SAY: "Silver is where I apply all business rules. Three
--   things happen here: deduplication, SCD Type 2 versioning
--   for slowly-changing dimensions, and MCC code enrichment.
--   I also add informational FOREIGN KEYS — not enforced, but
--   Power BI and Tableau read them to auto-detect relationships,
--   and Unity Catalog uses them for column-level lineage."
--
-- NETEZZA COMPARISON:
--   Netezza has MERGE but it's limited — only INSERT+UPDATE,
--   no WHEN NOT MATCHED BY SOURCE clause. SCD Type 2 on Netezza
--   typically required a staging table + two separate DML passes.
--   Delta MERGE handles INSERT + UPDATE + DELETE in a single
--   atomic operation with full ACID guarantees.
--
-- YELLOWBRICK COMPARISON:
--   Yellowbrick supports MERGE with similar syntax to Databricks.
--   The key difference: Yellowbrick MERGE is not ACID — concurrent
--   reads can see partial merge results. Delta MERGE is fully
--   ACID; readers always see a complete consistent snapshot.
-- ================================================================

-- ── 2A : Silver Dim Customer — SCD Type 2 ────────────────────
-- 💬 SAY: "I use a row_hash to detect changes without comparing
--   every column individually. md5(concat_ws) is deterministic
--   and fast — Photon vectorises it across millions of rows.
--   The surrogate key is a deterministic hash of natural key +
--   effective start date, so it's reproducible on re-run."

CREATE OR REPLACE TABLE silver_dim_customer (
  customer_sk   STRING        NOT NULL  COMMENT 'Surrogate key — md5(customer_id|eff_start_dt)',
  customer_id   STRING        NOT NULL  COMMENT 'Natural key from Bronze',
  first_name    STRING        NOT NULL,
  last_name     STRING        NOT NULL,
  email         STRING                  COMMENT 'PII — Unity Catalog column mask applied',
  city          STRING,
  state         STRING,
  credit_score  INT,
  annual_income DECIMAL(15,2)           COMMENT 'PII — Unity Catalog column mask applied',
  eff_start_dt  DATE          NOT NULL  COMMENT 'SCD2: version valid from (inclusive)',
  eff_end_dt    DATE          NOT NULL  COMMENT 'SCD2: 9999-12-31 = current version',
  is_current    BOOLEAN       NOT NULL  COMMENT 'SCD2: shortcut flag — avoids date range join',
  row_hash      STRING        NOT NULL  COMMENT 'md5 of all business cols — change detection'
)
USING DELTA
COMMENT 'Silver: SCD Type 2 customer dimension — full version history preserved'
TBLPROPERTIES ('layer' = 'silver');

-- ── 2B : Silver Dim Account ───────────────────────────────────
CREATE OR REPLACE TABLE silver_dim_account (
  account_sk    STRING        NOT NULL,
  account_id    STRING        NOT NULL,
  customer_id   STRING        NOT NULL,
  account_type  STRING        NOT NULL,
  open_date     DATE          NOT NULL,
  credit_limit  DECIMAL(15,2),
  interest_rate DECIMAL(6,4),
  status        STRING        NOT NULL
)
USING DELTA
COMMENT 'Silver: account dimension — current state'
TBLPROPERTIES ('layer' = 'silver');

-- ── 2C : Silver Fact Transaction — Liquid Clustering debut ────
-- ─────────────────────────────────────────────────────────────
-- LIQUID CLUSTERING EXPLAINED (say this to an interviewer)
-- ─────────────────────────────────────────────────────────────
-- 💬 SAY: "In Netezza, the optimizer relies on Zone Maps —
--   automatic min/max statistics per 8MB data slice. They work
--   well when data is loaded in order, but drift over time as
--   you append out-of-order records. You can't control which
--   columns drive zone map pruning without reloading the table.
--
--   Yellowbrick uses DISTRIBUTE ON + SORT ON at table creation.
--   Effective, but changing the sort key requires a full table
--   rebuild — expensive on multi-TB facts.
--
--   Databricks Liquid Clustering replaces BOTH with CLUSTER BY.
--   It co-locates rows sharing cluster key values into the same
--   Parquet files. OPTIMIZE runs incrementally — only newly
--   written files are clustered, not the entire table. You can
--   change cluster keys with ALTER TABLE and no data rewrite.
--   That's the key advantage over both Netezza and Yellowbrick."
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE silver_fact_transaction (
  transaction_id  STRING        NOT NULL,
  account_id      STRING        NOT NULL,
  customer_id     STRING        NOT NULL,
  txn_date        DATE          NOT NULL,
  txn_ts          TIMESTAMP     NOT NULL,
  amount          DECIMAL(15,2) NOT NULL,
  txn_type        STRING        NOT NULL,
  merchant_name   STRING,
  mcc_code        STRING,
  mcc_category    STRING        COMMENT 'Human-readable — lookup applied in Silver',
  status          STRING        NOT NULL,
  _silver_ts      TIMESTAMP     NOT NULL  COMMENT 'Pipeline processing timestamp'
)
USING DELTA
-- Cluster by the columns that appear most in WHERE/JOIN clauses
CLUSTER BY (txn_date, account_id)
COMMENT 'Silver: deduped clean transactions — REVERSED and duplicate rows removed'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'layer'                      = 'silver'
);

-- ── FOREIGN KEYS — informational, not enforced ────────────────
-- 💬 SAY: "These FKs are not enforced — Databricks doesn't
--   reject a row if the FK is missing, just like Netezza.
--   Their value is metadata: Power BI reads them to auto-detect
--   relationships in the semantic model, Tableau uses them for
--   join suggestions, and Unity Catalog lineage tracks them for
--   column-level impact analysis. Think of them as machine-
--   readable documentation, not a runtime check."
--
-- NETEZZA: FK constraints exist, informational, optimizer uses
--   them for join elimination (same as Databricks).
-- YELLOWBRICK: FK constraints informational only. Same value
--   proposition — BI tool integration and documentation.
ALTER TABLE silver_fact_transaction
  ADD CONSTRAINT fk_fact_account
  FOREIGN KEY (account_id) REFERENCES silver_dim_account(account_id);

ALTER TABLE silver_fact_transaction
  ADD CONSTRAINT fk_fact_customer
  FOREIGN KEY (customer_id) REFERENCES silver_dim_customer(customer_id);

-- ── MERGE : SCD Type 2 — Step 1 (close changed records) ───────
-- 💬 SAY: "SCD Type 2 in two steps: first MERGE closes the
--   old version by setting is_current=FALSE and stamping
--   eff_end_dt. Second INSERT opens the new version. I use
--   row_hash to detect changes — one md5 comparison is faster
--   than comparing eight individual columns, especially at
--   10M+ row scale on a Netezza-sized customer table."

MERGE INTO silver_dim_customer AS tgt
USING (
  -- Latest version of each customer from Bronze
  -- ROW_NUMBER handles multiple CDC events for same customer in one batch
  SELECT
    customer_id, first_name, last_name, email,
    city, state, credit_score, annual_income,
    md5(concat_ws('|',
          customer_id, first_name, last_name, email, city, state,
          CAST(credit_score   AS STRING),
          CAST(annual_income  AS STRING))) AS row_hash
  FROM (
    SELECT *,
      ROW_NUMBER() OVER (
        PARTITION BY customer_id
        ORDER BY _ingest_ts DESC        -- latest CDC event wins
      ) AS rn
    FROM bronze_raw_customers
  )
  WHERE rn = 1
) AS src
ON  tgt.customer_id = src.customer_id
AND tgt.is_current  = TRUE
AND tgt.row_hash   != src.row_hash      -- only process actual changes
WHEN MATCHED THEN
  UPDATE SET
    tgt.is_current = FALSE,
    -- Close eff_end_dt to yesterday so new version starts today
    -- with no gap and no overlap in the date range
    tgt.eff_end_dt = CURRENT_DATE() - INTERVAL 1 DAY;

-- SCD Type 2 — Step 2: open new version for changed + new customers
INSERT INTO silver_dim_customer
SELECT
  md5(concat_ws('|', src.customer_id, CAST(CURRENT_DATE() AS STRING))) AS customer_sk,
  src.customer_id, src.first_name, src.last_name, src.email,
  src.city, src.state, src.credit_score, src.annual_income,
  CURRENT_DATE()   AS eff_start_dt,
  DATE'9999-12-31' AS eff_end_dt,
  TRUE             AS is_current,
  src.row_hash
FROM (
  SELECT
    customer_id, first_name, last_name, email, city, state,
    credit_score, annual_income,
    md5(concat_ws('|',
          customer_id, first_name, last_name, email, city, state,
          CAST(credit_score AS STRING), CAST(annual_income AS STRING))) AS row_hash,
    ROW_NUMBER() OVER (
      PARTITION BY customer_id ORDER BY _ingest_ts DESC
    ) AS rn
  FROM bronze_raw_customers
) AS src
WHERE src.rn = 1
  AND NOT EXISTS (                      -- skip if we already have this exact version
    SELECT 1 FROM silver_dim_customer t
    WHERE t.customer_id = src.customer_id
      AND t.is_current  = TRUE
      AND t.row_hash    = src.row_hash
  );

-- ── Insert Silver Dim Account ─────────────────────────────────
INSERT INTO silver_dim_account
SELECT
  md5(account_id) AS account_sk,
  account_id, customer_id, account_type,
  open_date, credit_limit, interest_rate, status
FROM bronze_raw_accounts;

-- ── Insert Silver Fact — dedup + REVERSED exclusion + MCC ─────
-- 💬 SAY: "Three transforms in one query:
--   1. ROW_NUMBER removes duplicates (T0003 re-send case)
--   2. WHERE status != REVERSED excludes voided transactions
--   3. CASE on mcc_code enriches the category inline —
--      no separate lookup table join needed at this volume"
INSERT INTO silver_fact_transaction
SELECT
  t.transaction_id, t.account_id, a.customer_id,
  t.txn_date, t.txn_ts, t.amount, t.txn_type,
  t.merchant_name, t.mcc_code,
  CASE t.mcc_code
    WHEN '0000' THEN 'Payroll / Internal'
    WHEN '4511' THEN 'Airlines'
    WHEN '5200' THEN 'Home Improvement'
    WHEN '5411' THEN 'Grocery Stores'
    WHEN '5541' THEN 'Service Stations / Fuel'
    WHEN '5912' THEN 'Drug Stores / Pharmacies'
    WHEN '5999' THEN 'Online Retail / Misc'
    WHEN '6012' THEN 'Financial Institutions / Transfers'
    WHEN '6552' THEN 'Real Estate / Mortgage'
    ELSE              'Other (' || t.mcc_code || ')'
  END              AS mcc_category,
  t.status,
  current_timestamp() AS _silver_ts
FROM (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY transaction_id
      ORDER BY _ingest_ts DESC          -- latest re-send wins
    ) AS rn
  FROM bronze_raw_transactions
  WHERE status != 'REVERSED'           -- REVERSED excluded from clean fact
) t
JOIN bronze_raw_accounts a ON t.account_id = a.account_id
WHERE t.rn = 1;                        -- deduplicated

-- ── Verify Silver ─────────────────────────────────────────────
SELECT
  'silver_dim_customer'   AS tbl,
  count(*)                AS total_rows,
  count(CASE WHEN is_current THEN 1 END) AS current_versions
FROM silver_dim_customer
UNION ALL
SELECT 'silver_fact_transaction', count(*), NULL
FROM silver_fact_transaction;
-- Expected dim_customer: 6 rows total, 5 current (C002 has 2 versions)
-- Expected fact:         14 rows (16 - 1 dup T0003 - 1 REVERSED T0012)


-- ================================================================
-- SECTION 3 : GOLD LAYER  — "Optimised for consumption"
-- ================================================================
-- 💬 SAY: "Gold is where the business lives. I model Kimball
--   star schema here — conformed dimensions that every BI tool
--   already understands, plus fact tables tuned for the actual
--   query patterns I captured in discovery. PII is stripped
--   or banded at this layer — analysts get credit_band and
--   income_band, not raw scores and salaries."
-- ================================================================

-- ── 3A : Gold Dim Customer ────────────────────────────────────
CREATE OR REPLACE TABLE gold_dim_customer (
  customer_sk   STRING   NOT NULL,
  customer_id   STRING   NOT NULL,
  full_name     STRING             COMMENT 'first + last — derived in Gold',
  city          STRING,
  state         STRING,
  -- Derived bands replace raw PII fields in Gold
  credit_band   STRING             COMMENT 'EXCELLENT ≥750 | GOOD ≥700 | FAIR ≥650 | POOR',
  income_band   STRING             COMMENT 'HIGH ≥150K | MID ≥75K | LOW'
)
USING DELTA
CLUSTER BY (customer_id)
COMMENT 'Gold: conformed customer dimension — PII removed, bands applied'
TBLPROPERTIES ('layer' = 'gold');

-- ── 3B : Gold Dim Account ─────────────────────────────────────
CREATE OR REPLACE TABLE gold_dim_account (
  account_sk    STRING   NOT NULL,
  account_id    STRING   NOT NULL,
  customer_id   STRING   NOT NULL,
  account_type  STRING   NOT NULL,
  open_date     DATE     NOT NULL,
  credit_limit  DECIMAL(15,2),
  interest_rate DECIMAL(6,4),
  status        STRING   NOT NULL
)
USING DELTA
CLUSTER BY (account_id)
COMMENT 'Gold: account dimension'
TBLPROPERTIES ('layer' = 'gold');

-- ── 3C : Gold Fact Transaction — full Liquid Clustering demo ──
-- ─────────────────────────────────────────────────────────────
-- LIQUID CLUSTERING KEY SELECTION — interview question answer:
-- "How do you choose cluster keys?"
--
-- 💬 SAY: "I choose based on WHERE clause frequency across the
--   top 10 queries. For a banking transaction fact: txn_date
--   is in virtually every report filter. account_id is the
--   primary join key to dims. mcc_code drives fraud and spend
--   category analysis. Three keys cover ~85% of query patterns.
--
--   Rule of thumb: 1-4 columns, highest cardinality columns
--   that appear in WHERE clauses most frequently. Avoid columns
--   used only in SELECT or GROUP BY — clustering doesn't help those.
--
--   Netezza zone maps prune on the physical sort order.
--   Liquid Clustering prunes on any combination of cluster keys
--   simultaneously — no fixed sort order required."
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE gold_fact_transaction (
  transaction_id  STRING        NOT NULL,
  txn_date        DATE          NOT NULL,
  txn_month       STRING        NOT NULL  COMMENT 'Pre-computed YYYY-MM — avoids DATE_FORMAT at query',
  account_id      STRING        NOT NULL,
  customer_id     STRING        NOT NULL,
  customer_sk     STRING                  COMMENT 'FK to gold_dim_customer',
  amount          DECIMAL(15,2) NOT NULL,
  txn_type        STRING        NOT NULL,
  mcc_code        STRING,
  mcc_category    STRING,
  -- Pre-computed booleans avoid expression evaluation at query time
  -- 💬 SAY: "is_debit as a stored boolean is faster than
  --   evaluating txn_type = 'DEBIT' across 500M rows at query time.
  --   Same principle as Netezza pre-aggregating into base tables."
  is_debit        BOOLEAN       NOT NULL,
  abs_amount      DECIMAL(15,2) NOT NULL  COMMENT 'Pre-computed ABS(amount) — Photon avoids re-computing'
)
USING DELTA
CLUSTER BY (txn_date, account_id, mcc_code)
COMMENT 'Gold: Kimball fact table — Liquid Clustered, Photon-optimised'
TBLPROPERTIES (
  -- autoOptimize: compact small files from streaming/micro-batch writes
  -- 💬 SAY: "Auto-compaction is what Netezza GROOM TABLE does —
  --   except GROOM requires a scheduled maintenance window.
  --   Delta does it automatically in the background."
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact'   = 'true',
  'layer'                            = 'gold'
);

-- ── FOREIGN KEYS on Gold ──────────────────────────────────────
ALTER TABLE gold_fact_transaction
  ADD CONSTRAINT fk_gold_customer
  FOREIGN KEY (customer_sk) REFERENCES gold_dim_customer(customer_sk);

ALTER TABLE gold_fact_transaction
  ADD CONSTRAINT fk_gold_account
  FOREIGN KEY (account_id) REFERENCES gold_dim_account(account_id);

-- ── Populate Gold Dims ────────────────────────────────────────
INSERT INTO gold_dim_customer
SELECT
  customer_sk,
  customer_id,
  first_name || ' ' || last_name    AS full_name,
  city, state,
  CASE
    WHEN credit_score >= 750 THEN 'EXCELLENT'
    WHEN credit_score >= 700 THEN 'GOOD'
    WHEN credit_score >= 650 THEN 'FAIR'
    ELSE                          'POOR'
  END AS credit_band,
  CASE
    WHEN annual_income >= 150000 THEN 'HIGH'
    WHEN annual_income >=  75000 THEN 'MID'
    ELSE                              'LOW'
  END AS income_band
FROM silver_dim_customer
WHERE is_current = TRUE;             -- Gold: current state only

INSERT INTO gold_dim_account
SELECT account_sk, account_id, customer_id,
       account_type, open_date, credit_limit, interest_rate, status
FROM silver_dim_account;

-- ── Populate Gold Fact ────────────────────────────────────────
INSERT INTO gold_fact_transaction
SELECT
  t.transaction_id,
  t.txn_date,
  DATE_FORMAT(t.txn_date, 'yyyy-MM') AS txn_month,
  t.account_id,
  t.customer_id,
  c.customer_sk,
  t.amount,
  t.txn_type,
  t.mcc_code,
  t.mcc_category,
  t.txn_type = 'DEBIT'               AS is_debit,
  ABS(t.amount)                      AS abs_amount
FROM silver_fact_transaction t
LEFT JOIN silver_dim_customer c
  ON  t.customer_id = c.customer_id
  AND c.is_current  = TRUE;


-- ================================================================
-- SECTION 4 : PERFORMANCE DEEP DIVE
-- ================================================================

-- ── 4A : OPTIMIZE — trigger Liquid Clustering ─────────────────
-- 💬 SAY: "OPTIMIZE is the equivalent of Netezza GROOM TABLE
--   or Yellowbrick VACUUM. It compacts small files and applies
--   Liquid Clustering to newly written data. Unlike Z-ORDER
--   (the old Databricks approach), OPTIMIZE with Liquid
--   Clustering is INCREMENTAL — it only re-clusters files that
--   haven't been clustered yet. Full table recompaction not needed."
OPTIMIZE gold_fact_transaction;

-- Inspect clustering effectiveness
-- Look at clustering_information.average_depth — target ≤ 2
-- average_depth = 1 means perfect: every file contains rows for
-- exactly one cluster key value combination
DESCRIBE DETAIL gold_fact_transaction;

-- Update statistics so Photon's Cost-Based Optimizer (CBO)
-- picks the right join strategy and predicate pushdown order.
-- 💬 SAY: "Same as Netezza GENERATE STATISTICS or Yellowbrick
--   ANALYZE. Without current stats, the optimizer defaults to
--   conservative (slow) join strategies."
ANALYZE TABLE gold_fact_transaction COMPUTE STATISTICS FOR ALL COLUMNS;
ANALYZE TABLE gold_dim_customer     COMPUTE STATISTICS FOR ALL COLUMNS;
ANALYZE TABLE gold_dim_account      COMPUTE STATISTICS FOR ALL COLUMNS;


-- ── 4B : MATERIALIZED VIEWS — replace Netezza summary tables ──
-- 💬 SAY: "Netezza customers typically maintain manual summary
--   tables — a nightly job runs CREATE TABLE AS SELECT and
--   refreshes the aggregate. If the job fails, analysts query
--   stale data and don't know it.
--
--   Yellowbrick has no native MVs — same manual pattern.
--
--   Databricks Materialized Views auto-refresh. When the
--   underlying gold_fact_transaction changes, Databricks
--   incrementally refreshes only the affected partitions of
--   the MV. Analysts always get consistent, fresh results
--   without a separate refresh job."
-- ─────────────────────────────────────────────────────────────
DROP MATERIALIZED VIEW IF EXISTS gold_mv_monthly_summary;
CREATE MATERIALIZED VIEW gold_mv_monthly_summary
COMMENT 'Pre-computed monthly account cash flow — replaces Netezza nightly summary table job'
AS
SELECT
  txn_month,
  account_id,
  customer_id,
  COUNT(*)                                        AS txn_count,
  SUM(CASE WHEN is_debit     THEN abs_amount END) AS total_debits,
  SUM(CASE WHEN NOT is_debit THEN abs_amount END) AS total_credits,
  SUM(CASE WHEN is_debit THEN -abs_amount
           ELSE abs_amount END)                   AS net_flow,
  AVG(abs_amount)                                 AS avg_txn_amount,
  MAX(abs_amount)                                 AS largest_txn
FROM gold_fact_transaction
GROUP BY txn_month, account_id, customer_id;

DROP MATERIALIZED VIEW IF EXISTS gold_mv_mcc_spend_summary;
CREATE MATERIALIZED VIEW gold_mv_mcc_spend_summary
COMMENT 'Spend by MCC category per customer — feeds fraud monitoring and spend profiling dashboards'
AS
SELECT
  c.full_name, c.credit_band, c.state,
  f.mcc_code, f.mcc_category, f.txn_month,
  COUNT(*)          AS txn_count,
  SUM(f.abs_amount) AS total_spend,
  AVG(f.abs_amount) AS avg_spend,
  MAX(f.abs_amount) AS max_single_txn
FROM gold_fact_transaction f
JOIN gold_dim_customer c ON f.customer_sk = c.customer_sk
WHERE f.is_debit = TRUE
GROUP BY c.full_name, c.credit_band, c.state,
         f.mcc_code, f.mcc_category, f.txn_month;

-- ── 4C : PHOTON — what to say and what to avoid ───────────────
-- 💬 SAY: "Photon is Databricks' vectorised execution engine
--   written in C++. It's always on for Serverless SQL Warehouses
--   — there's nothing to enable. It's the reason Databricks
--   beats Netezza on TPC-DS at 10TB scale by 2.7x at 3.6x
--   lower cost per query. It excels at columnar scans,
--   vectorised aggregations, and hash joins.
--
--   What you want to AVOID to stay on the Photon path:
--     ❌ Python UDFs — force a JVM/Python context switch
--     ❌ Scalar subqueries inside SELECT — use CTEs
--     ✅ Use SQL expressions: is_debit = TRUE not UDF
--     ✅ Pre-compute abs_amount at write time not query time
--     ✅ CLUSTER BY to enable file skipping before Photon scans"

-- Photon-friendly: vectorised window function — running balance
SELECT
  account_id,
  txn_date, txn_ts, merchant_name, amount,
  -- Running balance — Photon vectorises OVER() natively
  SUM(amount) OVER (
    PARTITION BY account_id
    ORDER BY txn_ts
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  )                                        AS running_balance,
  -- Rank transactions by size this month — fraud signal baseline
  RANK() OVER (
    PARTITION BY account_id, txn_month
    ORDER BY abs_amount DESC
  )                                        AS rank_by_size_in_month
FROM gold_fact_transaction
ORDER BY account_id, txn_ts;


-- ================================================================
-- SECTION 5 : ADVANCED DELTA / DATABRICKS FEATURES
-- ================================================================

-- ── 5A : CLONE — zero-copy dev/test environments ──────────────
-- 💬 SAY: "SHALLOW CLONE creates a new table that references
--   the same underlying Parquet files — no data is copied.
--   It's instant regardless of table size. I use this to give
--   every developer their own 'copy' of a 5TB fact table for
--   testing without duplicating storage.
--
--   DEEP CLONE copies both data and metadata — creates a fully
--   independent table. I use this for regulatory snapshots:
--   'here is the exact state of our risk tables as of quarter-end,
--    frozen in place for the auditor.'
--
--   NETEZZA: no equivalent. Creating a dev copy means
--   CREATE TABLE AS SELECT * — full data copy, full storage cost,
--   takes hours on large tables.
--
--   YELLOWBRICK: no equivalent. Same problem."

-- Shallow Clone: instant reference copy for dev/test
-- 💬 SAY: "Dev environment gets an instant 'copy' of prod.
--   Writes to the clone go to new files — the source table
--   is never touched."
CREATE TABLE IF NOT EXISTS gold_fact_transaction_dev
  SHALLOW CLONE gold_fact_transaction;

-- Deep Clone: independent snapshot for regulatory audit freeze
-- 💬 SAY: "I clone before a major migration or a regulatory
--   reporting cycle. If something goes wrong, the clone is
--   my point-in-time restore target."
CREATE TABLE IF NOT EXISTS gold_fact_transaction_q1_2024_snapshot
  DEEP CLONE gold_fact_transaction;

-- Verify the clone shows same row count as source
SELECT
  'source'   AS tbl, count(*) AS rows FROM gold_fact_transaction
UNION ALL
SELECT 'shallow_clone',          count(*) FROM gold_fact_transaction_dev
UNION ALL
SELECT 'deep_clone_snapshot',    count(*) FROM gold_fact_transaction_q1_2024_snapshot;

-- Cleanup clones (drop when done with demo)
DROP TABLE IF EXISTS gold_fact_transaction_dev;
DROP TABLE IF EXISTS gold_fact_transaction_q1_2024_snapshot;


-- ── 5B : STREAMING TABLES — continuously updated Bronze ───────
-- 💬 SAY: "A Streaming Table is a Delta table that's
--   continuously updated by a Lakeflow Declarative Pipeline.
--   The DDL looks like a normal CREATE TABLE but the engine
--   auto-processes new arriving data — no polling loop, no
--   scheduled job, no lag from batch windows.
--
--   NETEZZA: no equivalent. Netezza is a static warehouse —
--   all ingestion is batch. Real-time data required an external
--   Kafka/Flink layer feeding a staging table via JDBC.
--
--   YELLOWBRICK: no equivalent. Same batch-only constraint.
--
--   NOTE: The CREATE STREAMING TABLE statement below defines
--   the table schema and pipeline intent. To activate it,
--   attach it to a Lakeflow Declarative Pipeline in the UI
--   or via a Databricks Asset Bundle. It will NOT stream data
--   if you simply run it in a SQL warehouse — it creates the
--   table object only."

CREATE STREAMING TABLE IF NOT EXISTS bronze_streaming_transactions
  (
    transaction_id  STRING,
    account_id      STRING,
    txn_ts          TIMESTAMP,
    amount          DECIMAL(15,2),
    txn_type        STRING,
    merchant_name   STRING,
    mcc_code        STRING,
    status          STRING,
    _ingest_ts      TIMESTAMP,
    _source         STRING
  )
  COMMENT 'Streaming table: continuously updated from Kafka/Event Hub CDC feed (requires Lakeflow pipeline)'
  TBLPROPERTIES (
    'pipelines.channel' = 'CURRENT',   -- use production Lakeflow channel
    'layer'             = 'bronze'
  );


-- ── 5C : APPLY CHANGES INTO — automatic SCD without MERGE ─────
-- 💬 SAY: "APPLY CHANGES INTO is what replaces the hand-rolled
--   SCD Type 2 MERGE I wrote in Section 2 for most teams.
--   You declare your key, sequence column, and SCD type — the
--   pipeline handles the MERGE, the versioning, the hash
--   comparison, and out-of-order event handling automatically.
--
--   The critical advantage over hand-rolled MERGE:
--   out-of-order CDC events. If Kafka delivers event at t=5
--   before event at t=3, a naive MERGE gets the wrong current
--   version. APPLY CHANGES INTO uses the SEQUENCE BY column to
--   always reconstruct the correct version regardless of
--   delivery order.
--
--   NETEZZA: no equivalent. You'd need a separate CDC tool
--   (IBM InfoSphere CDC, Attunity) + a complex staging procedure.
--
--   NOTE: APPLY CHANGES INTO only runs inside a Lakeflow
--   Declarative Pipeline — not in a SQL warehouse. Shown here
--   for syntax reference and interview explanation.
--
--   Uncomment and run in a Lakeflow pipeline definition:
--
-- APPLY CHANGES INTO silver_dim_customer_streaming
-- FROM STREAM(bronze_raw_customers)
-- KEYS (customer_id)
-- SEQUENCE BY _ingest_ts           -- handles out-of-order delivery
-- COLUMNS * EXCEPT (_source)       -- exclude pipeline metadata
-- STORED AS SCD TYPE 2;            -- auto version history

-- The equivalent STORED AS SCD TYPE 1 (overwrite, no history):
-- APPLY CHANGES INTO silver_dim_account_streaming
-- FROM STREAM(bronze_raw_accounts)
-- KEYS (account_id)
-- SEQUENCE BY _ingest_ts
-- STORED AS SCD TYPE 1;
"


-- ================================================================
-- SECTION 6 : TIME TRAVEL & AUDIT TRAIL
-- ================================================================
-- 💬 SAY: "Delta Lake maintains a _delta_log transaction log
--   for every table. Every operation — INSERT, MERGE, OPTIMIZE,
--   even DESCRIBE — is a versioned commit with timestamp,
--   user, and operation type. This is the SOX/Basel audit trail
--   your compliance team needs. On Netezza, once you MERGE a
--   table, the prior state is gone unless you maintained a
--   separate archive table manually."
-- ================================================================

-- Full audit trail — every operation on Bronze transactions
DESCRIBE HISTORY bronze_raw_transactions;

-- Time Travel by version number
-- Version 0 = immediately after CREATE TABLE (before any INSERTs)
SELECT count(*) AS rows_at_version_0
FROM bronze_raw_transactions VERSION AS OF 0;

-- Version 1 = after first INSERT batch
SELECT count(*) AS rows_after_first_batch
FROM bronze_raw_transactions VERSION AS OF 1;

-- Time Travel by timestamp — answer: "what data did the 9am report see?"
-- 💬 SAY: "This answers the auditor question exactly.
--   No separate audit table. No log parsing. One SQL statement."
SELECT count(*) AS rows_at_open_of_business
FROM bronze_raw_transactions
TIMESTAMP AS OF (current_timestamp() - INTERVAL 1 HOUR);

-- RESTORE: undo a bad ETL run — roll table back to a prior version
-- 💬 SAY: "RESTORE is what replaces the Netezza backup restore
--   procedure that takes 4 hours. On Delta it's seconds — it
--   rewrites the transaction log pointer, not the data files."
-- RESTORE TABLE bronze_raw_transactions VERSION AS OF 1;  -- ← uncomment carefully


-- ================================================================
-- SECTION 7 : INTERVIEW CHALLENGE QUERIES
-- ================================================================
-- These are the queries interviewers ask you to write on a
-- whiteboard. Know the pattern, know WHY each piece is there.
-- ================================================================

-- ── Q1 : Top 3 merchants by spend per customer (RANK + CTE) ───
-- 💬 SAY: "Classic window function question. I use RANK not
--   DENSE_RANK because I want gaps — if two merchants tie for
--   2nd, the next is 4th, not 3rd. CTE makes it readable and
--   avoids a subquery that confuses the optimizer."
WITH merchant_spend AS (
  SELECT
    customer_id,
    merchant_name,
    mcc_category,
    SUM(abs_amount)   AS total_spend,
    RANK() OVER (
      PARTITION BY customer_id
      ORDER BY SUM(abs_amount) DESC
    )                 AS spend_rank
  FROM gold_fact_transaction
  WHERE is_debit = TRUE
  GROUP BY customer_id, merchant_name, mcc_category
)
SELECT
  c.full_name,
  c.credit_band,
  m.merchant_name,
  m.mcc_category,
  ROUND(m.total_spend, 2)  AS total_spend,
  m.spend_rank
FROM merchant_spend m
JOIN gold_dim_customer c USING (customer_id)
WHERE m.spend_rank <= 3
ORDER BY c.full_name, m.spend_rank;

-- ── Q2 : Customers whose credit score changed — SCD Type 2 ────
-- 💬 SAY: "This is THE SCD Type 2 validation query. Self-join
--   on the dimension with two role aliases: v_old (expired)
--   and v_new (current). Proves the version history works."
SELECT
  v_old.customer_id,
  v_old.first_name || ' ' || v_old.last_name   AS customer_name,
  v_old.credit_score                            AS old_score,
  v_new.credit_score                            AS new_score,
  v_new.credit_score - v_old.credit_score       AS score_delta,
  v_old.eff_start_dt                            AS old_version_from,
  v_new.eff_start_dt                            AS new_version_from
FROM silver_dim_customer v_old
JOIN silver_dim_customer v_new
  ON  v_old.customer_id   = v_new.customer_id
  AND v_old.is_current    = FALSE
  AND v_new.is_current    = TRUE
  AND v_old.credit_score != v_new.credit_score
ORDER BY ABS(score_delta) DESC;

-- ── Q3 : Monthly cash flow with MoM change (LAG) ─────────────
-- 💬 SAY: "LAG is the Basel IV staple — regulators want to
--   see month-over-month change, not just the absolute number.
--   I'm querying the Materialized View here — this is instant
--   regardless of how large the underlying fact table is."
SELECT
  account_id, txn_month, total_debits, total_credits, net_flow,
  LAG(net_flow) OVER (
    PARTITION BY account_id ORDER BY txn_month
  )                             AS prior_month_net,
  net_flow - LAG(net_flow) OVER (
    PARTITION BY account_id ORDER BY txn_month
  )                             AS mom_change
FROM gold_mv_monthly_summary   -- querying the pre-computed MV
ORDER BY account_id, txn_month;

-- ── Q4 : Spend velocity flag — simple fraud signal ────────────
-- 💬 SAY: "This is a classic fraud rule: flag any transaction
--   that's more than 2x this customer's average spend in the
--   same MCC. I use a window AVG, not a subquery, so it's one
--   pass over the data — Photon handles this in vectorised mode."
SELECT
  f.customer_id,
  c.full_name,
  c.credit_band,
  f.mcc_category,
  f.txn_date,
  f.merchant_name,
  f.abs_amount,
  ROUND(AVG(f.abs_amount) OVER (
    PARTITION BY f.customer_id, f.mcc_code
  ), 2)                          AS avg_spend_this_mcc,
  CASE
    WHEN f.abs_amount > 2 * AVG(f.abs_amount) OVER (
           PARTITION BY f.customer_id, f.mcc_code
         )
    THEN '🚨 VELOCITY FLAG'
    ELSE '✅ normal'
  END                            AS flag
FROM gold_fact_transaction f
JOIN gold_dim_customer c USING (customer_sk)
WHERE f.is_debit = TRUE
ORDER BY flag DESC, f.abs_amount DESC;

-- ── Q5 : Running balance per account (UNBOUNDED PRECEDING) ────
SELECT
  account_id, txn_date, txn_ts, merchant_name, amount,
  SUM(amount) OVER (
    PARTITION BY account_id
    ORDER BY txn_ts
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  )                              AS running_balance
FROM silver_fact_transaction
ORDER BY account_id, txn_ts;


-- ================================================================
-- SECTION 8 : CHEAT SHEET  — Feature Reference
-- ================================================================
-- LIQUID CLUSTERING
--   Create  : CLUSTER BY (col1, col2, col3) in CREATE TABLE DDL
--   Trigger : OPTIMIZE tablename               (incremental)
--   Full    : OPTIMIZE tablename FULL          (recompact all files)
--   Inspect : DESCRIBE DETAIL tablename        → clustering_information
--   Change  : ALTER TABLE t CLUSTER BY (new_col)  (no data rewrite)
--   Drop    : ALTER TABLE t CLUSTER BY NONE
--   vs NZ   : Netezza Zone Maps = automatic, no user control
--   vs YB   : Yellowbrick SORT ON = fixed at creation, full rebuild to change
--
-- MATERIALIZED VIEWS
--   Create  : CREATE MATERIALIZED VIEW mv AS SELECT ...
--   Refresh : automatic on query; or REFRESH MATERIALIZED VIEW mv
--   Drop    : DROP MATERIALIZED VIEW mv
--   Limit   : read-only — cannot INSERT/UPDATE/DELETE into MV
--   vs NZ   : Netezza MV = manual GROOM + refresh, no auto-refresh
--   vs YB   : Yellowbrick has no native MV — use scheduled agg tables
--
-- CLONE
--   Shallow : CREATE TABLE new SHALLOW CLONE source   (zero copy, instant)
--   Deep    : CREATE TABLE new DEEP CLONE source       (full copy)
--   Use     : dev/test environments, regulatory snapshots, pre-migration backup
--   vs NZ   : no equivalent — CTAS = full copy
--   vs YB   : no equivalent
--
-- STREAMING TABLES
--   Create  : CREATE STREAMING TABLE t (schema...)
--   Activate: attach to Lakeflow Declarative Pipeline
--   vs NZ   : no equivalent — static warehouse only
--   vs YB   : no equivalent
--
-- APPLY CHANGES INTO (pipeline only)
--   SCD1    : APPLY CHANGES INTO target FROM STREAM(src) KEYS(k) SEQUENCE BY ts STORED AS SCD TYPE 1
--   SCD2    : APPLY CHANGES INTO target FROM STREAM(src) KEYS(k) SEQUENCE BY ts STORED AS SCD TYPE 2
--   Benefit : out-of-order event handling, no hand-rolled MERGE
--   vs NZ   : requires external CDC tool + manual staging procedure
--   vs YB   : same
--
-- FOREIGN KEYS
--   Add     : ALTER TABLE t ADD CONSTRAINT fk FOREIGN KEY (col) REFERENCES other(col)
--   Enforce : NOT enforced at write time — informational only
--   Value   : Power BI / Tableau auto-detect joins; UC lineage tracking
--   vs NZ   : same — informational, optimizer uses for join elimination
--   vs YB   : same
--
-- CONSTRAINTS (enforced)
--   NOT NULL: enforced at write — rejecting row on violation
--   CHECK   : CHECK (expr) — enforced; row rejected if false
--   vs NZ   : NOT NULL enforced; CHECK informational only
--   vs YB   : same as Netezza
--
-- TIME TRAVEL
--   Version : SELECT * FROM t VERSION AS OF 3
--   Stamp   : SELECT * FROM t TIMESTAMP AS OF '2024-01-15 09:00:00'
--   History : DESCRIBE HISTORY tablename
--   Restore : RESTORE TABLE t TO VERSION AS OF 3
--   Retain  : default 30 days (delta.logRetentionDuration)
--   vs NZ   : no equivalent — data is gone after DML
--   vs YB   : no equivalent
--
-- PHOTON
--   Enable  : automatic on Serverless SQL Warehouses
--   Fast    : vectorised aggs (SUM/COUNT/AVG), columnar scans, hash joins
--   Avoid   : Python UDFs, scalar subqueries in SELECT
--   Tip     : pre-compute abs_amount / is_debit at write time
--   vs NZ   : Netezza FPGA-accelerated columnar scan (AMPU) — similar concept
--   vs YB   : Yellowbrick in-memory MPP — fast but no elasticity
--
-- SCD TYPE 2 PATTERN
--   Step 1  : MERGE → close old version (is_current=FALSE, stamp eff_end_dt)
--   Step 2  : INSERT → open new version (is_current=TRUE, eff_end_dt=9999-12-31)
--   Key     : row_hash = md5(concat_ws('|', all_business_cols)) — change detection
--   Query   : WHERE is_current = TRUE  → current state
--             self-join v_old(is_current=FALSE) v_new(is_current=TRUE) → changes
-- ================================================================


-- ================================================================
-- SECTION 9 : UNITY CATALOG — RBAC & GOVERNANCE
-- ================================================================
-- 💬 SAY: "Unity Catalog is the governance layer that sits
--   above Delta Lake. It provides three things Netezza and
--   Snowflake can't match simultaneously: a three-level
--   namespace (catalog.schema.table), attribute-based access
--   control (ABAC) with tag propagation, and automatic
--   column-level lineage captured from SQL execution — no
--   manual tagging required.
--
--   The GRANT model follows ANSI SQL privilege syntax so it
--   feels familiar to any DBA, but the scope is unified across
--   tables, views, models, volumes, and dashboards in one place."
--
-- PRIVILEGE HIERARCHY (outer → inner, inherits downward)
--   CATALOG  →  SCHEMA  →  TABLE / VIEW / FUNCTION / VOLUME
--   Granting at catalog level gives access to all schemas below.
--   Granting at schema level scopes to that schema only.
--   Granting at table level is the most restrictive scope.
--
-- NETEZZA COMPARISON:
--   Netezza security: database → schema → table/view.
--   No catalog layer. No ABAC. No row filters or column masks
--   at the engine level — you'd build them as views manually.
--   No cross-system lineage.
--
-- SNOWFLAKE COMPARISON:
--   Snowflake has database.schema.table — structurally similar.
--   Snowflake Dynamic Data Masking ≈ Unity Catalog column masks.
--   Snowflake Row Access Policies ≈ Unity Catalog row filters.
--   Key difference: Unity Catalog also governs ML models,
--   notebooks, volumes (files), and dashboards in the same
--   namespace. Snowflake governance is SQL objects only.
-- ================================================================


-- ────────────────────────────────────────────────────────────────
-- 9A : PRINCIPALS — users, service principals, groups
-- ────────────────────────────────────────────────────────────────
-- 💬 SAY: "Unity Catalog RBAC operates on three principal types:
--   users (humans), service principals (pipelines/apps), and
--   groups (collections of either). Best practice: always GRANT
--   to groups, never to individual users — makes onboarding and
--   offboarding a group membership change, not a privilege audit."

-- View all principals currently visible to you
SHOW USERS;
-- SHOW GROUPS;          -- list all groups in the account
-- SHOW PRINCIPALS IN GROUP analysts;   -- members of a group


-- ────────────────────────────────────────────────────────────────
-- 9B : CATALOG-LEVEL GRANTS
-- ────────────────────────────────────────────────────────────────
-- 💬 SAY: "USE CATALOG lets a principal see the catalog exists.
--   Without it, the catalog is invisible. This is the outer
--   gate — you need it before any schema or table grant works."

-- Allow analysts to see and use the dw catalog
GRANT USE CATALOG ON CATALOG dw TO `analysts`;

-- Allow the ETL pipeline service principal to write to the catalog
GRANT USE CATALOG ON CATALOG dw TO `etl-pipeline-sp`;

-- Allow data engineers full control of the catalog
-- 💬 SAY: "ALL PRIVILEGES on catalog includes CREATE SCHEMA,
--   CREATE TABLE, MODIFY — everything except GRANT (metastore admin only)."
GRANT ALL PRIVILEGES ON CATALOG dw TO `data-engineers`;

-- Inspect what's been granted at the catalog level
SHOW GRANTS ON CATALOG dw;


-- ────────────────────────────────────────────────────────────────
-- 9C : SCHEMA-LEVEL GRANTS
-- ────────────────────────────────────────────────────────────────
-- 💬 SAY: "USE SCHEMA lets a principal enter a schema and
--   see its tables. Without it, GRANT SELECT on a table below
--   has no effect — the user can't get to the table to use it.
--   This is a common gotcha when setting up RBAC for the first time."

GRANT USE SCHEMA ON SCHEMA dw.dwprep TO `analysts`;
GRANT USE SCHEMA ON SCHEMA dw.dwprep TO `etl-pipeline-sp`;

-- Allow ETL service principal to create tables in dwprep
GRANT CREATE TABLE ON SCHEMA dw.dwprep TO `etl-pipeline-sp`;

SHOW GRANTS ON SCHEMA dw.dwprep;


-- ────────────────────────────────────────────────────────────────
-- 9D : TABLE-LEVEL GRANTS — read vs write separation
-- ────────────────────────────────────────────────────────────────
-- 💬 SAY: "This is the most common pattern in a FinServ lakehouse:
--   analysts get SELECT on Gold only — they never touch Bronze or
--   Silver directly. The ETL service principal gets MODIFY on
--   Bronze (append) and Silver/Gold (MERGE writes). No human
--   ever gets MODIFY on production Gold — changes go through
--   the pipeline."

-- Analysts: read Gold layer only (star schema + MVs)
GRANT SELECT ON TABLE dw.dwprep.gold_fact_transaction  TO `analysts`;
GRANT SELECT ON TABLE dw.dwprep.gold_dim_customer      TO `analysts`;
GRANT SELECT ON TABLE dw.dwprep.gold_dim_account       TO `analysts`;

-- Analysts can also query Materialized Views (same SELECT grant)
GRANT SELECT ON TABLE dw.dwprep.gold_mv_monthly_summary    TO `analysts`;
GRANT SELECT ON TABLE dw.dwprep.gold_mv_mcc_spend_summary  TO `analysts`;

-- Risk team: Gold + Silver (for model feature access)
GRANT SELECT ON TABLE dw.dwprep.silver_fact_transaction TO `risk-analysts`;
GRANT SELECT ON TABLE dw.dwprep.silver_dim_customer     TO `risk-analysts`;

-- ETL service principal: write access to all layers
-- MODIFY covers INSERT, UPDATE, DELETE, MERGE, TRUNCATE
GRANT MODIFY ON TABLE dw.dwprep.bronze_raw_customers     TO `etl-pipeline-sp`;
GRANT MODIFY ON TABLE dw.dwprep.bronze_raw_accounts      TO `etl-pipeline-sp`;
GRANT MODIFY ON TABLE dw.dwprep.bronze_raw_transactions  TO `etl-pipeline-sp`;
GRANT MODIFY ON TABLE dw.dwprep.silver_dim_customer      TO `etl-pipeline-sp`;
GRANT MODIFY ON TABLE dw.dwprep.silver_dim_account       TO `etl-pipeline-sp`;
GRANT MODIFY ON TABLE dw.dwprep.silver_fact_transaction  TO `etl-pipeline-sp`;
GRANT MODIFY ON TABLE dw.dwprep.gold_fact_transaction    TO `etl-pipeline-sp`;

-- Inspect table-level grants
SHOW GRANTS ON TABLE dw.dwprep.gold_fact_transaction;


-- ────────────────────────────────────────────────────────────────
-- 9E : COLUMN MASKS — PII protection at the engine level
-- ────────────────────────────────────────────────────────────────
-- 💬 SAY: "Column masks let me store real PII in Silver and
--   serve a masked version to analysts — without maintaining
--   two copies of the table. The mask is a SQL function that
--   runs at query time. Analysts in the 'pii-approved' group
--   see the real value; everyone else sees the masked value.
--   This is how you pass GDPR and PCI audits without forking
--   the data model."
--
-- NETEZZA: no engine-level column masking. You'd build a view
--   with CASE expressions and grant on the view — brittle, and
--   bypassed if someone gets direct table access.
-- SNOWFLAKE: Dynamic Data Masking — same concept, similar syntax.
--   Unity Catalog version is unified across catalogs and enforced
--   even on direct table access (no view bypass).

-- Step 1: create the masking function
-- The function receives the real value and returns masked or real
-- based on current_user()'s group membership
CREATE OR REPLACE FUNCTION dw.dwprep.mask_email(email STRING)
  RETURNS STRING
  RETURN
    CASE
      WHEN is_account_group_member('pii-approved') THEN email
      ELSE regexp_replace(email, '(^[^@]{2})([^@]*)(@.*)', '$1***$3')
      -- e.g.  alice@bank.com  →  al***@bank.com
    END;

CREATE OR REPLACE FUNCTION dw.dwprep.mask_income(income DECIMAL(15,2))
  RETURNS DECIMAL(15,2)
  RETURN
    CASE
      WHEN is_account_group_member('pii-approved') THEN income
      ELSE NULL   -- non-approved users see NULL, not the actual income
    END;

-- Step 2: apply the mask to the Silver table column
-- 💬 SAY: "The mask is attached to the column — it fires on
--   every query, even if someone queries Bronze directly via
--   Unity Catalog. There's no way to bypass it short of
--   metastore admin privileges."
ALTER TABLE dw.dwprep.silver_dim_customer
  ALTER COLUMN email         SET MASK dw.dwprep.mask_email;

ALTER TABLE dw.dwprep.silver_dim_customer
  ALTER COLUMN annual_income SET MASK dw.dwprep.mask_income;

-- Verify: query the table — non-pii-approved users see masked values
SELECT customer_id, first_name, email, annual_income
FROM dw.dwprep.silver_dim_customer
WHERE is_current = TRUE;

-- Remove a mask (if you need to drop the column mask for testing)
-- ALTER TABLE dw.dwprep.silver_dim_customer ALTER COLUMN email DROP MASK;


-- ────────────────────────────────────────────────────────────────
-- 9F : ROW FILTERS — multi-jurisdiction, GDPR, regional scoping
-- ────────────────────────────────────────────────────────────────
-- 💬 SAY: "Row filters are the GDPR and Basel IV answer for
--   multi-jurisdiction data. I store all regions in one table
--   but each regional analyst only sees their own rows — the
--   filter runs at the storage layer, not in application code.
--   Compliance teams love this because it's centralised and
--   auditable. A rogue BI query can't accidentally return
--   EU customer data to a US analyst."
--
-- NETEZZA: no engine-level row filtering. You'd partition by
--   region and grant schema-level access — coarse-grained and
--   hard to audit across thousands of tables.
-- SNOWFLAKE: Row Access Policies — same concept, same value.
--   Unity Catalog version applies across all compute types
--   (SQL warehouses, notebooks, jobs) in one policy.

-- Row filter function: restrict to rows matching the user's region
CREATE OR REPLACE FUNCTION dw.dwprep.filter_by_state(state STRING)
  RETURNS BOOLEAN
  RETURN
    CASE
      -- Metastore admins and pii-approved see all rows
      WHEN is_account_group_member('pii-approved')  THEN TRUE
      -- Regional groups see only their state(s)
      WHEN is_account_group_member('region-northeast')
           AND state IN ('NY','NJ','CT','MA','PA')  THEN TRUE
      WHEN is_account_group_member('region-south')
           AND state IN ('TX','FL','GA','NC')       THEN TRUE
      WHEN is_account_group_member('region-west')
           AND state IN ('WA','CA','OR','NV')       THEN TRUE
      ELSE FALSE
    END;

-- Apply row filter to Gold dim customer
ALTER TABLE dw.dwprep.gold_dim_customer
  SET ROW FILTER dw.dwprep.filter_by_state ON (state);

-- Verify: run as a regional analyst — should only see their state rows
SELECT customer_id, full_name, state, credit_band
FROM dw.dwprep.gold_dim_customer;

-- Remove a row filter (for testing)
-- ALTER TABLE dw.dwprep.gold_dim_customer DROP ROW FILTER;


-- ────────────────────────────────────────────────────────────────
-- 9G : TAGS — ABAC (Attribute-Based Access Control)
-- ────────────────────────────────────────────────────────────────
-- 💬 SAY: "Tags in Unity Catalog propagate from catalog →
--   schema → table → column. Once I tag a column as PII,
--   every downstream view and materialized view that references
--   that column inherits the PII tag automatically. This is
--   ABAC — policies can then be written against tag values
--   instead of enumerating every table individually.
--   At scale — 50,000 tables — this is the only manageable
--   governance model."

-- Tag the catalog (inherited by all schemas + tables inside)
ALTER CATALOG dw
  SET TAGS ('environment' = 'dev', 'domain' = 'finserv');

-- Tag the schema
ALTER SCHEMA dw.dwprep
  SET TAGS ('layer' = 'multi-layer', 'team' = 'data-engineering');

-- Tag sensitive columns (PII classification)
ALTER TABLE dw.dwprep.silver_dim_customer
  ALTER COLUMN email         SET TAGS ('pii' = 'true', 'pii_type' = 'email');

ALTER TABLE dw.dwprep.silver_dim_customer
  ALTER COLUMN annual_income SET TAGS ('pii' = 'true', 'pii_type' = 'financial');

ALTER TABLE dw.dwprep.silver_dim_customer
  ALTER COLUMN credit_score  SET TAGS ('pii' = 'true', 'pii_type' = 'financial');

-- Query the system catalog to find ALL PII-tagged columns
-- across the entire catalog — this is the GDPR data mapping report
SELECT
  table_catalog,
  table_schema,
  table_name,
  column_name,
  tag_name,
  tag_value
FROM system.information_schema.column_tags
WHERE tag_name = 'pii'
  AND tag_value = 'true'
  AND table_catalog = 'dw'
ORDER BY table_name, column_name;


-- ────────────────────────────────────────────────────────────────
-- 9H : LINEAGE — automatic, no manual tagging
-- ────────────────────────────────────────────────────────────────
-- 💬 SAY: "Unity Catalog captures column-level lineage from
--   SQL execution automatically. Every INSERT, MERGE, and
--   CREATE TABLE AS SELECT is tracked. I can answer: which
--   upstream column does gold_fact_transaction.amount derive
--   from? The answer traces back through Silver all the way
--   to bronze_raw_transactions.amount. This is what satisfies
--   Basel IV BCBS 239 data lineage requirements."

-- Query lineage from Unity Catalog system tables
-- (system.access.table_lineage available in Databricks)
SELECT
  source_table_full_name,
  source_column_name,
  target_table_full_name,
  target_column_name,
  created_by
FROM system.access.column_lineage
WHERE target_table_full_name LIKE 'dw.dwprep.%'
ORDER BY target_table_full_name, target_column_name;


-- ────────────────────────────────────────────────────────────────
-- 9I : REVOKE — removing access
-- ────────────────────────────────────────────────────────────────
-- 💬 SAY: "REVOKE is the mirror of GRANT. In a FinServ context
--   this is the offboarding path — when an analyst leaves,
--   you remove them from the group and every GRANT to that
--   group is revoked automatically. That's why best practice
--   is always grant to groups, never individuals."

-- Remove select on Gold from analysts (e.g. project ended)
REVOKE SELECT ON TABLE dw.dwprep.gold_fact_transaction FROM `analysts`;

-- Verify the revoke took effect
SHOW GRANTS ON TABLE dw.dwprep.gold_fact_transaction;

-- Restore it for continued demo use
GRANT SELECT ON TABLE dw.dwprep.gold_fact_transaction TO `analysts`;


-- ────────────────────────────────────────────────────────────────
-- 9J : RBAC CHEAT SHEET
-- ────────────────────────────────────────────────────────────────
-- PRIVILEGE SUMMARY
--   USE CATALOG   : see the catalog exists — required outer gate
--   USE SCHEMA    : enter a schema — required before table access
--   SELECT        : read rows from table/view/MV
--   MODIFY        : INSERT, UPDATE, DELETE, MERGE, TRUNCATE
--   CREATE TABLE  : create new tables in a schema
--   ALL PRIVILEGES: all of the above (typically for data engineers)
--
-- GRANT PATTERN (always three steps: catalog → schema → object)
--   GRANT USE CATALOG  ON CATALOG  mycat      TO `group`;
--   GRANT USE SCHEMA   ON SCHEMA   mycat.mysc TO `group`;
--   GRANT SELECT       ON TABLE    mycat.mysc.mytable TO `group`;
--
-- COLUMN MASKS
--   Create  : CREATE OR REPLACE FUNCTION cat.sc.fn(col TYPE) RETURNS TYPE
--   Apply   : ALTER TABLE t ALTER COLUMN c SET MASK cat.sc.fn
--   Remove  : ALTER TABLE t ALTER COLUMN c DROP MASK
--   Logic   : use is_account_group_member('group') in RETURN
--
-- ROW FILTERS
--   Create  : CREATE OR REPLACE FUNCTION cat.sc.fn(col TYPE) RETURNS BOOLEAN
--   Apply   : ALTER TABLE t SET ROW FILTER cat.sc.fn ON (col)
--   Remove  : ALTER TABLE t DROP ROW FILTER
--   Logic   : return TRUE = show row, FALSE = hide row
--
-- TAGS (ABAC)
--   Catalog : ALTER CATALOG c SET TAGS ('k' = 'v')
--   Schema  : ALTER SCHEMA s SET TAGS ('k' = 'v')
--   Table   : ALTER TABLE t SET TAGS ('k' = 'v')
--   Column  : ALTER TABLE t ALTER COLUMN c SET TAGS ('k' = 'v')
--   Query   : SELECT * FROM system.information_schema.column_tags
--
-- vs NETEZZA : no masks, no row filters, no ABAC, no lineage
-- vs SNOWFLAKE: Dynamic Masking ≈ column masks (similar)
--               Row Access Policies ≈ row filters (similar)
--               No equivalent to tag-propagated ABAC
--               No cross-object lineage (SQL objects only)
-- ================================================================
