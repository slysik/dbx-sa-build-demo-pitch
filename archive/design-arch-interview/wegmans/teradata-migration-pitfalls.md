# Teradata → Databricks Migration Pitfalls: Deep Dive

## The 4 Silent Killers

These are the pitfalls that don't cause errors — they cause **wrong answers**.
Nothing breaks. Numbers just quietly drift. Trust erodes.

---

## 1. COLLATION — The Join Killer

### The Trap
Teradata defaults to case-insensitive comparisons in many configurations.
Databricks defaults to **binary UTF-8** (case-sensitive, byte-by-byte).

### Real-World Scenario (FinServ)
```
-- Teradata: Customer matching across systems
-- Source A has: "JPMorgan Chase"
-- Source B has: "JPMORGAN CHASE"  
-- Source C has: "jpmorgan chase"
-- Teradata JOIN: All 3 match ✅
-- Databricks JOIN: 0 matches ❌ (3 separate customers!)
```

### Impact Chain
```
Wrong collation
  → Silent row drops in JOINs
    → Undercounted customers/accounts
      → Wrong KPIs on dashboards
        → Regulatory reporting errors (FinServ!)
          → Auditor findings
```

### The Wrong Fix
```sql
-- Sprinkling LOWER() everywhere — fragile, inconsistent, CPU overhead
SELECT * FROM a JOIN b ON LOWER(a.name) = LOWER(b.name);
-- Every developer must remember. Every query. Every time. They won't.
```

### The Right Fix (Databricks 2025+)
```sql
-- Collation strategy at table creation — enforced once, works everywhere
CREATE TABLE gold.dim_customer (
  customer_id BIGINT,
  legal_name STRING COLLATE UTF8_LCASE,       -- case-insensitive
  email STRING COLLATE UTF8_LCASE,            -- case-insensitive  
  account_number STRING,                       -- case-sensitive (exact match needed)
  tax_id STRING                                -- case-sensitive (regulatory)
);

-- JOINs automatically respect collation — no LOWER() needed
SELECT * FROM trades t
JOIN dim_customer c ON t.customer_name = c.legal_name;
-- "JPMorgan Chase" = "JPMORGAN CHASE" = "jpmorgan chase" ✅
```

### Migration Checklist — Collation
```
□ Audit all VARCHAR/CHAR columns in Teradata for collation settings
□ Classify columns: case-sensitive vs case-insensitive
□ Define collation strategy BEFORE migration (not after)
□ Apply UTF8_LCASE to: names, emails, descriptions, free-text
□ Keep binary for: account numbers, tax IDs, codes, hashes
□ Test JOIN row counts: Teradata vs Databricks (must match exactly)
□ Document collation decisions in Unity Catalog COMMENTs
```

---

## 2. PRECISION DRIFT — The Credibility Killer

### The Trap
Teradata DECIMAL(38,10) behaves predictably through aggregations.
Spark may implicitly promote types during computation, causing micro-drift.
0.01% drift in a $10B portfolio = $1M discrepancy.

### Real-World Scenario (FinServ)
```
-- Daily P&L reconciliation
-- Teradata:  Total portfolio value = $10,234,567,891.1234567890
-- Databricks: Total portfolio value = $10,234,567,891.1234560000
--                                                    ^^^^^^^^
-- Difference: $0.000789 — but the AUDITOR SEES A DIFFERENCE
-- "Which number is correct?" — the question that kills credibility
```

### Impact Chain
```
Implicit type promotion
  → Precision loss in aggregation
    → Micro-drift in totals
      → Reconciliation failures
        → "Which system is right?"
          → Nobody trusts the new platform
            → Migration declared a failure
```

### Where Drift Happens
```
1. SUM() over millions of rows — accumulated rounding
2. AVG() — division introduces floating-point artifacts  
3. JOIN + aggregate — intermediate results lose precision
4. CAST chains — DECIMAL → DOUBLE → DECIMAL loses bits
5. UDF boundaries — Python float ≠ Spark DECIMAL
```

### The Wrong Fix
```sql
-- Hoping it's "close enough"
-- Rounding at the end: ROUND(SUM(amount), 2)
-- This hides drift, doesn't prevent it
```

### The Right Fix
```sql
-- 1. Explicit DECIMAL everywhere — never implicit
CREATE TABLE gold.fact_positions (
  position_id BIGINT,
  notional_amount DECIMAL(38,10),    -- match Teradata precision exactly
  market_value DECIMAL(38,10),
  accrued_interest DECIMAL(38,10),
  fx_rate DECIMAL(20,10)
);

-- 2. Explicit CAST in every aggregation
SELECT 
  account_id,
  CAST(SUM(CAST(market_value AS DECIMAL(38,10))) AS DECIMAL(38,10)) AS total_mv
FROM gold.fact_positions
GROUP BY account_id;

-- 3. Reconciliation framework — run EVERY migration batch
CREATE TABLE reconciliation.precision_check AS
SELECT 
  'fact_positions' AS table_name,
  td_sum,
  dbx_sum,
  ABS(td_sum - dbx_sum) AS absolute_delta,
  ABS(td_sum - dbx_sum) / NULLIF(ABS(td_sum), 0) * 100 AS pct_delta,
  CASE 
    WHEN ABS(td_sum - dbx_sum) / NULLIF(ABS(td_sum), 0) * 100 > 0.0001 
    THEN 'FAIL' ELSE 'PASS' 
  END AS status
FROM (
  SELECT 
    (SELECT SUM(amount) FROM teradata_export.fact_positions) AS td_sum,
    (SELECT CAST(SUM(amount) AS DECIMAL(38,10)) FROM gold.fact_positions) AS dbx_sum
);
```

### Golden Row Testing
```sql
-- Test pathological cases BEFORE go-live
INSERT INTO test.precision_cases VALUES
  (1, CAST('99999999999999999999999999.9999999999' AS DECIMAL(38,10))),  -- max precision
  (2, CAST('-99999999999999999999999999.9999999999' AS DECIMAL(38,10))), -- max negative
  (3, CAST('0.0000000001' AS DECIMAL(38,10))),                          -- min precision
  (4, NULL),                                                             -- null handling
  (5, CAST('0' AS DECIMAL(38,10)));                                     -- zero

-- Verify SUM, AVG, COUNT, MIN, MAX all match Teradata exactly
```

### Migration Checklist — Precision
```
□ Build type-mapping matrix: every DECIMAL column, exact precision
□ Ban FLOAT/DOUBLE for financial data (use DECIMAL always)
□ Explicit CAST in all aggregation queries
□ Golden row test suite: max, min, negative, null, zero
□ Automated reconciliation: compare Teradata vs Databricks totals
□ Set tolerance threshold (e.g., 0.0001%) — anything above = FAIL
□ Test aggregation chains: SUM of SUMs, AVG of AVGs
□ Validate INTERVAL conversions (store as BIGINT seconds)
```

---

## 3. PK ENFORCEMENT — The Identity Killer

### The Trap
Teradata rejects duplicate PKs at INSERT time.
Databricks accepts them silently. Duplicates propagate downstream.

### Real-World Scenario (FinServ)
```
-- Customer onboarding from 3 source systems
-- System A: customer_id = 'C001', name = 'Alice Smith'
-- System B: customer_id = 'C001', name = 'Alice B. Smith'  (same person!)
-- System C: customer_id = 'C001', name = 'A. Smith'        (same person!)

-- Teradata with PK: Only first INSERT succeeds, forces resolution
-- Databricks without enforcement: All 3 rows land

-- Result: 
--   SELECT COUNT(DISTINCT customer_id) → 1 (looks right!)
--   SELECT COUNT(*) WHERE customer_id = 'C001' → 3 (actual rows: 3!)
--   Every fact table JOIN now triples the revenue for this customer
```

### Impact Chain
```
No PK enforcement
  → Duplicate dimension rows
    → Fact-dimension JOIN fan-out
      → Inflated metrics (3x revenue per duplicate!)
        → Wrong risk calculations
          → Regulatory exposure
```

### The Wrong Fix
```sql
-- Adding DISTINCT everywhere — band-aid, hides the real problem
SELECT DISTINCT customer_id, name FROM dim_customer;
-- Which "name" did DISTINCT keep? You don't know. Nobody knows.
```

### The Right Fix — Layered Defense

```
Layer 1: Bronze — Accept everything (raw, as-is)
Layer 2: Silver — Deduplicate with AUTO CDC
Layer 3: Gold — Enforce identity with star schema + declared PK
Layer 4: Quality — Monitor with expectations + alerts
```

```python
# Layer 2: Silver — AUTO CDC Type 1 (dedup, latest wins)
dp.create_streaming_table("silver.customers_deduped")
dp.create_auto_cdc_flow(
    target="silver.customers_deduped",
    source="bronze.customers_raw",
    keys=["customer_id"],           # enforces one row per key
    sequence_by="updated_timestamp", # latest version wins
    stored_as_scd_type="1"
)
```

```sql
-- Layer 3: Gold — Star schema with declared constraints
CREATE TABLE gold.dim_customer (
  customer_key BIGINT GENERATED ALWAYS AS IDENTITY,
  customer_id STRING NOT NULL,
  legal_name STRING COLLATE UTF8_LCASE,
  CONSTRAINT pk_customer PRIMARY KEY (customer_key)
) CLUSTER BY (customer_key);

-- Layer 4: Quality — Monitoring query (schedule as alert)
SELECT customer_id, COUNT(*) AS dupes
FROM gold.dim_customer
GROUP BY customer_id
HAVING COUNT(*) > 1;
-- Should return 0 rows. If not, pipeline is broken.
```

### Migration Checklist — PK Enforcement
```
□ Inventory all Teradata PKs and UNIQUE constraints
□ Map enforcement strategy: AUTO CDC for dims, MERGE for facts
□ Implement duplicate monitoring queries (scheduled alerts)
□ Add SDP Expectations for NOT NULL on key columns
□ Declare PK/FK in Gold tables (informational + optimizer)
□ Validate: COUNT(*) = COUNT(DISTINCT pk) for every Gold table
□ Build reconciliation: Teradata row counts vs Databricks row counts
□ Document identity rules in Unity Catalog COMMENTs
```

---

## 4. TIMEZONE SEMANTICS — The Temporal Killer

### The Trap
Teradata supports `TIMESTAMP WITH TIME ZONE` natively.
Spark interprets timestamps through `spark.sql.session.timeZone` — a session setting.
Same data, different session = different time = different day = different report.

### Real-World Scenario (FinServ)
```
-- Trade executed at 11:30 PM EST on March 31
-- Stored as: 2024-03-31 23:30:00 America/New_York
-- In UTC:    2024-04-01 03:30:00 UTC

-- Question: What day was this trade?
-- New York desk: March 31 ✅ (their business day)
-- London desk:   April 1 ✅ (their business day) 
-- UTC storage:   April 1 (technically correct)
-- Report grouped by DATE(trade_ts): depends on session timezone!

-- If session TZ = UTC:    trade lands in April 1 bucket
-- If session TZ = EST:    trade lands in March 31 bucket
-- End-of-month report: different totals depending on who runs it
```

### Impact Chain — DST Edition
```
No timezone strategy
  → Timestamps interpreted by session setting
    → DST shift: 2 AM → 3 AM (spring forward)
      → 1-hour gap: events "disappear" from hourly aggregates
      → Or 1-hour overlap: events counted twice (fall back)
        → Daily/hourly metrics jump or drop 
          → "The dashboard is broken" (it's not — timezone is wrong)
```

### The Wrong Fix
```sql
-- Storing local time without timezone context
trade_timestamp TIMESTAMP  -- 2024-03-31 23:30:00 ... but WHOSE 23:30?
-- Nobody knows 6 months later
```

### The Right Fix — Two-Column Pattern
```sql
CREATE TABLE gold.fact_trades (
  trade_id BIGINT,
  
  -- The instant (unambiguous, comparable, joinable)
  trade_ts_utc TIMESTAMP NOT NULL,
  
  -- The context (preserves business meaning)
  trade_tz STRING NOT NULL,           -- 'America/New_York'
  
  -- The business date (derived, explicit)
  trade_business_date DATE NOT NULL,  -- based on desk's local calendar
  
  -- Derived display columns
  trade_ts_local TIMESTAMP            -- GENERATED or in pipeline
    GENERATED ALWAYS AS (from_utc_timestamp(trade_ts_utc, trade_tz))
);

-- Pipeline-level setting (consistency across all jobs)
SET spark.sql.session.timeZone = 'UTC';
```

### The Conversion Pipeline
```sql
-- Bronze: Store raw (whatever source sends)
CREATE OR REPLACE STREAMING TABLE bronze_trades AS
SELECT *, current_timestamp() AS _ingested_at
FROM STREAM read_files('/Volumes/.../trades/', format => 'json');

-- Silver: Normalize to UTC + preserve original TZ
CREATE OR REPLACE STREAMING TABLE silver_trades AS
SELECT
  trade_id,
  to_utc_timestamp(trade_timestamp, source_timezone) AS trade_ts_utc,
  source_timezone AS trade_tz,
  -- Business date = local date at the trading desk
  CAST(from_utc_timestamp(
    to_utc_timestamp(trade_timestamp, source_timezone), 
    source_timezone
  ) AS DATE) AS trade_business_date,
  amount, currency, account_id
FROM STREAM bronze_trades;

-- Gold: Serve with both UTC and local
CREATE OR REPLACE MATERIALIZED VIEW gold_daily_trading_volume AS
SELECT
  trade_business_date,
  trade_tz AS desk_timezone,
  COUNT(*) AS trade_count,
  CAST(SUM(amount) AS DECIMAL(38,2)) AS total_volume
FROM silver_trades
GROUP BY trade_business_date, trade_tz;
```

### DST-Safe Hourly Aggregation
```sql
-- ❌ Dangerous: depends on session timezone
GROUP BY HOUR(trade_timestamp)

-- ✅ Safe: always UTC, convert for display only
GROUP BY HOUR(trade_ts_utc)

-- ✅ Safe: explicit local hour with timezone
GROUP BY HOUR(from_utc_timestamp(trade_ts_utc, trade_tz))
```

### Migration Checklist — Timezones
```
□ Audit all TIMESTAMP columns in Teradata: WITH/WITHOUT TIME ZONE
□ Determine business meaning: instant vs wall-clock vs business date
□ Define standard: UTC storage + original TZ preservation
□ Set spark.sql.session.timeZone = 'UTC' globally in all pipelines
□ Convert all timestamps to UTC in Silver layer
□ Add trade_business_date as explicit derived column
□ Test DST boundaries: spring forward (gap) and fall back (overlap)
□ Test year-end boundary: Dec 31 23:30 EST = Jan 1 04:30 UTC
□ Validate: GROUP BY DATE matches Teradata exactly across TZ boundaries
□ Document timezone rules in Unity Catalog COMMENTs
```

---

## Summary: Where Each Pitfall Is Caught

```
                    COLLATION    PRECISION    PK ENFORCE    TIMEZONE
                    ─────────    ─────────    ──────────    ────────
Table DDL           COLLATE      DECIMAL      CONSTRAINT    UTC + TZ cols
                    UTF8_LCASE   (38,10)      PRIMARY KEY   two-column

Pipeline            Automatic    Explicit     AUTO CDC      to_utc_timestamp
(SDP/ETL)           (collation   CAST in      MERGE INTO    + preserve TZ
                    propagates)  aggregations              

Quality Gate        JOIN count   Reconcile    COUNT(*) =    DST boundary
(Expectations)      validation   vs Teradata  COUNT(DIST)   tests

Monitoring          Row count    Drift %      Duplicate     Hourly count
(Alerts)            comparison   threshold    alert query   consistency
```
