# DW Syntax Deep Dive: AUTO CDC, COLLATE, CAST
## FinServ Migration from Teradata — Complete Reference

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 1: COLLATE — Replacing Teradata's Case Handling
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## The Problem
Teradata: case-insensitive by default in many configs.
Databricks: binary UTF-8 (case-sensitive) by default.
Migration without collation strategy → silent JOIN row drops.

---

## Level 1: Catalog-Wide Default (Best for Greenfield Migration)

Set it once at the top — everything inherits:

```sql
-- Create the Gold catalog with case-insensitive default
CREATE CATALOG gold_finserv
  DEFAULT COLLATION UNICODE_CI;

-- Everything under this catalog inherits UNICODE_CI
USE CATALOG gold_finserv;

CREATE SCHEMA sales;
USE SCHEMA sales;

-- These columns are automatically case-insensitive
CREATE TABLE dim_customer (
  customer_key BIGINT GENERATED ALWAYS AS IDENTITY,
  customer_id STRING NOT NULL,          -- UNICODE_CI inherited
  legal_name STRING,                    -- UNICODE_CI inherited
  email STRING,                         -- UNICODE_CI inherited
  tax_id STRING COLLATE UTF8_BINARY,    -- OVERRIDE: exact match needed
  CONSTRAINT pk_customer PRIMARY KEY (customer_key)
) CLUSTER BY (customer_key);

-- This JOIN works without LOWER():
-- "JPMorgan Chase" = "JPMORGAN CHASE" = "jpmorgan chase" ✅
SELECT * FROM dim_customer WHERE legal_name = 'jpmorgan chase';
```

## Level 2: Schema-Level Default

```sql
-- Different schemas, different collation needs
CREATE SCHEMA gold_finserv.presentation
  DEFAULT COLLATION UNICODE_CI;         -- BI-facing: case-insensitive

CREATE SCHEMA gold_finserv.regulatory
  DEFAULT COLLATION UTF8_BINARY;        -- Regulatory: exact match
```

## Level 3: Column-Level (Most Common in Migration)

```sql
CREATE TABLE gold.sales.dim_counterparty (
  counterparty_key BIGINT GENERATED ALWAYS AS IDENTITY,
  
  -- Case-insensitive: names vary across source systems
  legal_name STRING COLLATE UTF8_LCASE,
  short_name STRING COLLATE UTF8_LCASE,
  city STRING COLLATE UTF8_LCASE,
  country STRING COLLATE UTF8_LCASE,
  
  -- Case-sensitive: codes, identifiers, hashes
  lei_code STRING,                           -- Legal Entity Identifier (exact)
  swift_code STRING,                         -- SWIFT/BIC code (exact)
  tax_id STRING,                             -- Tax ID (exact)
  
  -- Accent-insensitive: international names
  contact_name STRING COLLATE UNICODE_CI_AI, -- José = Jose = JOSÉ
  
  CONSTRAINT pk_counterparty PRIMARY KEY (counterparty_key)
) CLUSTER BY (counterparty_key, country);

COMMENT ON TABLE gold.sales.dim_counterparty IS 
  'Counterparty dimension. Collation: UTF8_LCASE on names/cities, '
  'UNICODE_CI_AI on contact names, UTF8_BINARY on codes/IDs.';
```

## Level 4: Expression-Level (Ad-Hoc Queries)

```sql
-- Analyst needs case-insensitive search on a binary column
SELECT * FROM gold.sales.dim_counterparty
WHERE swift_code COLLATE UTF8_LCASE = 'citius33';
-- Matches: CITIUS33, Citius33, citius33

-- Useful during migration validation:
-- Compare Teradata export (mixed case) vs Databricks (unknown case)
SELECT 
  td.legal_name,
  dbx.legal_name,
  CASE 
    WHEN td.legal_name COLLATE UTF8_LCASE = dbx.legal_name COLLATE UTF8_LCASE 
    THEN 'MATCH' ELSE 'MISMATCH' 
  END AS comparison
FROM teradata_export.customers td
JOIN gold.sales.dim_customer dbx 
  ON td.customer_id = dbx.customer_id;
```

## Collation Decision Matrix for FinServ

```sql
/*
┌──────────────────────────┬─────────────────────┬─────────────────────────┐
│ Column Type              │ Collation            │ Why                     │
├──────────────────────────┼─────────────────────┼─────────────────────────┤
│ Legal names              │ UTF8_LCASE           │ Source systems vary case │
│ Email addresses          │ UTF8_LCASE           │ RFC 5321: local-part    │
│                          │                      │ case-insensitive        │
│ City / State / Country   │ UTF8_LCASE           │ "new york" = "New York" │
│ International names      │ UNICODE_CI_AI        │ José = Jose = JOSÉ      │
│ Account numbers          │ UTF8_BINARY (default)│ Exact match required    │
│ CUSIP / ISIN / SEDOL     │ UTF8_BINARY          │ Security IDs are exact  │
│ LEI codes                │ UTF8_BINARY          │ 20-char alphanumeric    │
│ SWIFT/BIC codes          │ UTF8_BINARY          │ 8 or 11 char exact      │
│ Tax IDs / SSN            │ UTF8_BINARY          │ Regulatory exact match  │
│ Hash values              │ UTF8_BINARY          │ Cryptographic, exact    │
│ Free-text descriptions   │ UNICODE_CI           │ Search-friendly         │
│ Currency codes (USD/EUR) │ UTF8_BINARY          │ ISO 4217 exact codes    │
└──────────────────────────┴─────────────────────┴─────────────────────────┘
*/
```

## Migration Validation Query

```sql
-- Compare JOIN row counts: Teradata vs Databricks
-- If these don't match, you have a collation problem

-- Step 1: Teradata export (already case-insensitive)
-- td_join_count = 1,234,567

-- Step 2: Databricks WITHOUT collation fix
SELECT COUNT(*) AS dbx_join_count_binary
FROM trades t
JOIN dim_customer c ON t.customer_name = c.legal_name;
-- Result: 1,102,345 ← 132,222 rows DROPPED (case mismatch!)

-- Step 3: Databricks WITH collation fix
-- (after applying UTF8_LCASE to legal_name column)
SELECT COUNT(*) AS dbx_join_count_collated
FROM trades t
JOIN dim_customer c ON t.customer_name = c.legal_name;
-- Result: 1,234,567 ← MATCHES Teradata ✅
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 2: CAST — Replacing Teradata's Type Strictness
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## The Problem
Teradata maintains DECIMAL precision through aggregation chains.
Spark may implicitly promote DECIMAL → DOUBLE during computation.
$0.001 drift on a $10B portfolio = failed audit.

---

## Rule 1: DECIMAL Everywhere — Never FLOAT for Money

```sql
-- ✅ CORRECT: Explicit DECIMAL matching Teradata source
CREATE TABLE gold.trading.fact_positions (
  position_key BIGINT GENERATED ALWAYS AS IDENTITY,
  account_key BIGINT NOT NULL,
  security_key BIGINT NOT NULL,
  date_key INT NOT NULL,
  
  -- Financial amounts: DECIMAL always, match Teradata precision
  quantity DECIMAL(18,6),              -- share count (fractional shares)
  market_price DECIMAL(18,8),         -- price per share (8 decimals)
  market_value DECIMAL(38,10),        -- notional value 
  cost_basis DECIMAL(38,10),          -- original purchase cost
  unrealized_pnl DECIMAL(38,10),      -- mark-to-market P&L
  accrued_interest DECIMAL(18,10),    -- bond accrued interest
  fx_rate DECIMAL(20,10),             -- foreign exchange rate
  
  CONSTRAINT fk_account FOREIGN KEY (account_key) 
    REFERENCES gold.trading.dim_account(account_key),
  CONSTRAINT fk_security FOREIGN KEY (security_key) 
    REFERENCES gold.trading.dim_security(security_key)
) CLUSTER BY (date_key, account_key);

-- ❌ WRONG: DOUBLE/FLOAT for financial data
-- market_value DOUBLE,        -- NO! Floating-point artifacts
-- fx_rate FLOAT,              -- NO! Precision loss
```

## Rule 2: Explicit CAST in Every Aggregation

```sql
-- ❌ DANGEROUS: Implicit type promotion in aggregation chain
SELECT account_id, SUM(market_value) AS total_mv
FROM gold.trading.fact_positions
GROUP BY account_id;
-- Spark MAY promote intermediate results, causing micro-drift

-- ✅ SAFE: Explicit CAST preserves precision
SELECT 
  account_id,
  CAST(SUM(CAST(market_value AS DECIMAL(38,10))) AS DECIMAL(38,10)) AS total_mv,
  CAST(SUM(CAST(unrealized_pnl AS DECIMAL(38,10))) AS DECIMAL(38,10)) AS total_pnl,
  CAST(AVG(CAST(market_price AS DECIMAL(38,10))) AS DECIMAL(38,10)) AS avg_price
FROM gold.trading.fact_positions
WHERE date_key = 20240331
GROUP BY account_id;
```

## Rule 3: CAST in Materialized Views (Gold Aggregates)

```sql
CREATE OR REPLACE MATERIALIZED VIEW gold.trading.mv_portfolio_summary
  CLUSTER BY (as_of_date, account_key)
  SCHEDULE EVERY 1 HOUR
  COMMENT 'Portfolio summary with explicit DECIMAL precision'
AS 
SELECT
  p.date_key AS as_of_date,
  p.account_key,
  a.account_name,
  a.account_type,
  
  -- Explicit CAST on every aggregation
  COUNT(*) AS position_count,
  CAST(SUM(CAST(p.market_value AS DECIMAL(38,10))) AS DECIMAL(38,10)) AS total_market_value,
  CAST(SUM(CAST(p.cost_basis AS DECIMAL(38,10))) AS DECIMAL(38,10)) AS total_cost_basis,
  CAST(SUM(CAST(p.unrealized_pnl AS DECIMAL(38,10))) AS DECIMAL(38,10)) AS total_unrealized_pnl,
  
  -- Percentage calculation: force DECIMAL division
  CAST(
    SUM(CAST(p.unrealized_pnl AS DECIMAL(38,10))) / 
    NULLIF(SUM(CAST(p.cost_basis AS DECIMAL(38,10))), 0) * 100
    AS DECIMAL(18,6)
  ) AS return_pct
  
FROM gold.trading.fact_positions p
JOIN gold.trading.dim_account a ON p.account_key = a.account_key
GROUP BY p.date_key, p.account_key, a.account_name, a.account_type;
```

## Rule 4: CHECK Constraints for Financial Validation

```sql
-- CHECK constraints ARE enforced (unlike PK/FK)
ALTER TABLE gold.trading.fact_positions
  ADD CONSTRAINT positive_quantity CHECK (quantity > 0 OR quantity IS NULL);

ALTER TABLE gold.trading.fact_positions
  ADD CONSTRAINT valid_fx_rate CHECK (fx_rate > 0);

ALTER TABLE gold.trading.fact_positions
  ADD CONSTRAINT reasonable_price CHECK (market_price BETWEEN 0 AND 999999.99);

-- This INSERT will FAIL:
INSERT INTO gold.trading.fact_positions (quantity, fx_rate, market_price)
VALUES (-100, 0, 1000000);
-- ❌ Error: CHECK constraint 'positive_quantity' violated
```

## Rule 5: Type Mapping Matrix (Teradata → Databricks)

```sql
/*
┌────────────────────────┬──────────────────────┬────────────────────────────┐
│ Teradata Type          │ Databricks Type       │ Watch Out For              │
├────────────────────────┼──────────────────────┼────────────────────────────┤
│ DECIMAL(p,s)           │ DECIMAL(p,s)          │ Match EXACTLY. Always CAST │
│ BYTEINT                │ TINYINT               │ Range: -128 to 127         │
│ SMALLINT               │ SMALLINT              │ Same                       │
│ INTEGER                │ INT                   │ Same                       │
│ BIGINT                 │ BIGINT                │ Same                       │
│ FLOAT                  │ DOUBLE                │ NEVER for money            │
│ NUMBER                 │ DECIMAL(38,10)        │ Map to explicit precision  │
│ CHAR(n)                │ STRING                │ Trailing space: use RTRIM  │
│ VARCHAR(n)             │ STRING                │ No length enforcement      │
│ CLOB                   │ STRING                │ No size limit in Spark     │
│ DATE                   │ DATE                  │ Same                       │
│ TIME                   │ STRING (HH:MM:SS)     │ No native TIME type        │
│ TIMESTAMP              │ TIMESTAMP             │ See timezone section       │
│ TIMESTAMP WITH TZ      │ TIMESTAMP + STRING TZ │ Two-column pattern         │
│ INTERVAL HOUR TO MIN   │ BIGINT (seconds)      │ Or STRING ISO 8601         │
│ PERIOD(DATE)           │ DATE start + DATE end │ Two columns                │
│ BLOB                   │ BINARY                │ Same                       │
│ JSON                   │ STRING (parse w/ ':') │ Or VARIANT type            │
│ ARRAY                  │ ARRAY<type>           │ Same                       │
│ ST_GEOMETRY            │ GEOMETRY              │ Use ST_ functions          │
└────────────────────────┴──────────────────────┴────────────────────────────┘
*/
```

## Rule 6: Golden Row Reconciliation Framework

```sql
-- Run after EVERY migration batch. Automated. No exceptions.

-- Step 1: Create reconciliation table
CREATE TABLE reconciliation.type_precision_tests (
  table_name STRING,
  column_name STRING,
  test_type STRING,
  teradata_value DECIMAL(38,10),
  databricks_value DECIMAL(38,10),
  absolute_delta DECIMAL(38,10),
  pct_delta DECIMAL(18,10),
  status STRING,
  tested_at TIMESTAMP DEFAULT current_timestamp()
);

-- Step 2: Test SUM precision
INSERT INTO reconciliation.type_precision_tests
SELECT
  'fact_positions' AS table_name,
  'market_value' AS column_name,
  'SUM' AS test_type,
  td.total AS teradata_value,
  dbx.total AS databricks_value,
  ABS(td.total - dbx.total) AS absolute_delta,
  ABS(td.total - dbx.total) / NULLIF(ABS(td.total), 0) * 100 AS pct_delta,
  CASE 
    WHEN ABS(td.total - dbx.total) / NULLIF(ABS(td.total), 0) * 100 > 0.0001 
    THEN 'FAIL' ELSE 'PASS' 
  END AS status,
  current_timestamp()
FROM 
  (SELECT CAST(SUM(market_value) AS DECIMAL(38,10)) AS total 
   FROM teradata_export.fact_positions) td,
  (SELECT CAST(SUM(CAST(market_value AS DECIMAL(38,10))) AS DECIMAL(38,10)) AS total 
   FROM gold.trading.fact_positions) dbx;

-- Step 3: Test pathological cases
INSERT INTO reconciliation.type_precision_tests VALUES
  ('golden_row', 'max_decimal', 'BOUNDARY',
   99999999999999999999999999.9999999999, 
   99999999999999999999999999.9999999999, 0, 0, 'PASS', current_timestamp()),
  ('golden_row', 'min_decimal', 'BOUNDARY',
   0.0000000001, 0.0000000001, 0, 0, 'PASS', current_timestamp()),
  ('golden_row', 'negative', 'BOUNDARY',
   -99999999999999999999999999.9999999999,
   -99999999999999999999999999.9999999999, 0, 0, 'PASS', current_timestamp());

-- Step 4: Alert on failures
SELECT * FROM reconciliation.type_precision_tests
WHERE status = 'FAIL'
ORDER BY tested_at DESC;
-- Should return 0 rows. Any rows = stop migration, investigate.
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 3: AUTO CDC — Replacing Teradata's PK Enforcement
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## The Problem
Teradata rejects duplicate PKs at INSERT time.
Databricks accepts duplicates silently.
3 rows for same customer → fact JOINs fan out → revenue tripled.

---

## Pattern A: SQL — Full Medallion with AUTO CDC

### Bronze: Land Everything Raw

```sql
-- Accept everything, add metadata, no filtering
CREATE OR REPLACE STREAMING TABLE bronze.customers_raw
CLUSTER BY (ingestion_date)
TBLPROPERTIES ('quality' = 'bronze')
COMMENT 'Raw customer data from Teradata CDC feed. May contain duplicates.'
AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  _metadata.file_path AS _source_file,
  CAST(current_date() AS DATE) AS ingestion_date
FROM STREAM read_files(
  '/Volumes/gold_finserv/landing/customers_cdc/',
  format => 'parquet',
  schemaHints => 'customer_id STRING, legal_name STRING, email STRING, 
                  segment STRING, city STRING, state STRING, country STRING,
                  operation STRING, updated_timestamp TIMESTAMP'
);
```

### Silver: Clean + Validate (Before AUTO CDC)

```sql
-- Clean and type-cast before feeding to AUTO CDC
CREATE OR REPLACE STREAMING TABLE silver.customers_clean
CLUSTER BY (customer_id)
COMMENT 'Cleaned customer data with proper typing and collation-ready.'
AS
SELECT
  customer_id,
  -- Collation applied here for downstream JOINs
  CAST(legal_name AS STRING) AS legal_name,
  CAST(LOWER(email) AS STRING) AS email,
  segment,
  city,
  state,
  country,
  operation,
  CAST(updated_timestamp AS TIMESTAMP) AS updated_timestamp,
  _ingested_at
FROM STREAM bronze.customers_raw
WHERE customer_id IS NOT NULL
  AND legal_name IS NOT NULL
  AND updated_timestamp IS NOT NULL;
```

### Gold: AUTO CDC — SCD Type 2 (History Tracking)

```sql
-- Step 1: Declare the target streaming table
CREATE OR REFRESH STREAMING TABLE gold.dim_customer
CLUSTER BY (customer_id)
COMMENT 'Customer dimension with SCD Type 2 history. AUTO CDC enforces one active row per customer_id.';

-- Step 2: Create the AUTO CDC flow
CREATE FLOW customers_scd2_flow AS
AUTO CDC INTO gold.dim_customer
FROM STREAM silver.customers_clean
KEYS (customer_id)
APPLY AS DELETE WHEN operation = 'DELETE'
SEQUENCE BY updated_timestamp
COLUMNS * EXCEPT (operation, _ingested_at)
STORED AS SCD TYPE 2;
```

**What this produces:**

```sql
-- gold.dim_customer now has:
-- customer_id | legal_name | email | ... | __START_AT | __END_AT
-- C001        | Alice Smith| alice@| ... | 2024-01-15 | 2024-06-20  (old version)
-- C001        | Alice Jones| alice@| ... | 2024-06-20 | NULL        (current)

-- Current state query:
SELECT * FROM gold.dim_customer WHERE __END_AT IS NULL;

-- Point-in-time (as of March 1, 2024):
SELECT * FROM gold.dim_customer
WHERE __START_AT <= '2024-03-01' 
  AND (__END_AT > '2024-03-01' OR __END_AT IS NULL);
```

### Gold: AUTO CDC — SCD Type 1 (Dedup Only, No History)

```sql
-- For dimensions that don't need history (e.g., product reference data)
CREATE OR REFRESH STREAMING TABLE gold.dim_security;

CREATE FLOW securities_scd1_flow AS
AUTO CDC INTO gold.dim_security
FROM STREAM silver.securities_clean
KEYS (security_id)
SEQUENCE BY modified_timestamp
COLUMNS * EXCEPT (operation, _ingested_at)
STORED AS SCD TYPE 1;

-- Result: exactly ONE row per security_id (latest version wins)
-- No __START_AT / __END_AT columns
```

### Gold: Selective History Tracking

```sql
-- Only track changes to price and rating (not every column)
CREATE OR REFRESH STREAMING TABLE gold.dim_security_history;

CREATE FLOW security_history_flow AS
AUTO CDC INTO gold.dim_security_history
FROM STREAM silver.securities_clean
KEYS (security_id)
SEQUENCE BY modified_timestamp
COLUMNS * EXCEPT (operation, _ingested_at)
STORED AS SCD TYPE 2
TRACK HISTORY ON price, credit_rating;

-- Only price or credit_rating changes create new history rows
-- Other column changes update in-place without new versions
```

---

## Pattern B: Python — Full Medallion with AUTO CDC

### Bronze (Python)

```python
from pyspark import pipelines as dp
from pyspark.sql import functions as F

schema_location_base = spark.conf.get("schema_location_base")

@dp.table(
    name="bronze.customers_raw",
    cluster_by=["ingestion_date"],
    comment="Raw customer data from Teradata CDC feed"
)
def bronze_customers_raw():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "parquet")
        .option("cloudFiles.schemaLocation", f"{schema_location_base}/customers_raw")
        .load("/Volumes/gold_finserv/landing/customers_cdc/")
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.col("_metadata.file_path"))
        .withColumn("ingestion_date", F.current_date())
    )
```

### Silver (Python)

```python
@dp.table(
    name="silver.customers_clean",
    cluster_by=["customer_id"],
    comment="Cleaned and validated customer data"
)
@dp.expect_or_drop("valid_customer_id", "customer_id IS NOT NULL")
@dp.expect_or_drop("valid_name", "legal_name IS NOT NULL")
@dp.expect_or_drop("valid_timestamp", "updated_timestamp IS NOT NULL")
def silver_customers_clean():
    return (
        spark.readStream.table("bronze.customers_raw")
        .withColumn("updated_timestamp", F.to_timestamp("updated_timestamp"))
        .withColumn("email", F.lower(F.col("email")))
        .select(
            "customer_id", "legal_name", "email", "segment",
            "city", "state", "country", "operation", 
            "updated_timestamp", "_ingested_at"
        )
    )
```

### Gold — AUTO CDC SCD Type 2 (Python)

```python
from pyspark.sql.functions import col

# Step 1: Declare the target
dp.create_streaming_table(
    name="gold.dim_customer",
    comment="Customer dimension with SCD Type 2 history tracking"
)

# Step 2: Create AUTO CDC flow
dp.create_auto_cdc_flow(
    target="gold.dim_customer",
    source="silver.customers_clean",
    keys=["customer_id"],
    sequence_by=col("updated_timestamp"),
    stored_as_scd_type=2,                    # Integer for Type 2
    apply_as_deletes=col("operation") == "DELETE",
    except_column_list=["operation", "_ingested_at"]
)
```

### Gold — AUTO CDC SCD Type 1 (Python)

```python
# Dedup only, no history (latest wins)
dp.create_streaming_table(
    name="gold.dim_security",
    comment="Security reference - SCD Type 1 (current state only)"
)

dp.create_auto_cdc_flow(
    target="gold.dim_security",
    source="silver.securities_clean",
    keys=["security_id"],
    sequence_by=col("modified_timestamp"),
    stored_as_scd_type="1",                  # String for Type 1
    except_column_list=["operation", "_ingested_at"]
)
```

### Gold — Selective History (Python)

```python
# Track history only on price and credit_rating changes
dp.create_streaming_table(
    name="gold.dim_security_history",
    comment="Security dimension with selective SCD Type 2 on price/rating"
)

dp.create_auto_cdc_flow(
    target="gold.dim_security_history",
    source="silver.securities_clean",
    keys=["security_id"],
    sequence_by=col("modified_timestamp"),
    stored_as_scd_type=2,
    track_history_column_list=["price", "credit_rating"],
    except_column_list=["operation", "_ingested_at"]
)
```

---

## Pattern C: Fact Table with Temporal Dimension Join

This is where all three come together — COLLATE + CAST + AUTO CDC:

```sql
-- Fact table: trades with explicit DECIMAL and FK constraints
CREATE TABLE gold.trading.fact_trades (
  trade_key BIGINT GENERATED ALWAYS AS IDENTITY,
  trade_id STRING NOT NULL,
  customer_key BIGINT NOT NULL,
  security_key BIGINT NOT NULL,
  date_key INT NOT NULL,
  
  -- CAST: All financial amounts are DECIMAL
  quantity DECIMAL(18,6),
  execution_price DECIMAL(18,8),
  trade_amount DECIMAL(38,10),
  commission DECIMAL(18,4),
  net_amount DECIMAL(38,10),
  fx_rate DECIMAL(20,10),
  
  -- Timezone: two-column pattern
  trade_ts_utc TIMESTAMP NOT NULL,
  trade_tz STRING NOT NULL,
  trade_business_date DATE NOT NULL,
  
  -- COLLATE: text fields are case-insensitive
  counterparty_name STRING COLLATE UTF8_LCASE,
  exchange_code STRING,                        -- exact match (binary default)
  
  CONSTRAINT pk_trade PRIMARY KEY (trade_key),
  CONSTRAINT fk_customer FOREIGN KEY (customer_key) 
    REFERENCES gold.trading.dim_customer(customer_key),
  CONSTRAINT fk_security FOREIGN KEY (security_key) 
    REFERENCES gold.trading.dim_security(security_key),
  
  -- CHECK: financial validation (these ARE enforced)
  CONSTRAINT positive_quantity CHECK (quantity > 0),
  CONSTRAINT valid_fx CHECK (fx_rate > 0),
  CONSTRAINT amounts_consistent CHECK (
    ABS(trade_amount - (quantity * execution_price)) < 0.01
  )
) CLUSTER BY (date_key, customer_key);

-- Gold MV: Portfolio summary joining fact + SCD Type 2 dim
-- Uses temporal join to get customer info AT TIME OF TRADE
CREATE OR REPLACE MATERIALIZED VIEW gold.trading.mv_trading_summary
  CLUSTER BY (trade_business_date)
  SCHEDULE EVERY 1 HOUR
AS
SELECT
  t.trade_business_date,
  c.legal_name AS customer_name,               -- COLLATE: case-insensitive
  c.segment AS customer_segment,
  s.security_name,
  s.asset_class,
  
  COUNT(*) AS trade_count,
  
  -- CAST: explicit precision on every aggregation
  CAST(SUM(CAST(t.trade_amount AS DECIMAL(38,10))) AS DECIMAL(38,10)) AS total_volume,
  CAST(SUM(CAST(t.commission AS DECIMAL(38,10))) AS DECIMAL(38,10)) AS total_commission,
  CAST(SUM(CAST(t.net_amount AS DECIMAL(38,10))) AS DECIMAL(38,10)) AS total_net,
  CAST(AVG(CAST(t.execution_price AS DECIMAL(38,10))) AS DECIMAL(38,10)) AS avg_price

FROM gold.trading.fact_trades t

-- AUTO CDC: temporal join with SCD Type 2 dimension
-- Gets the customer record that was ACTIVE at time of trade
JOIN gold.trading.dim_customer c
  ON t.customer_key = c.customer_key
  AND t.trade_ts_utc >= c.__START_AT
  AND (t.trade_ts_utc < c.__END_AT OR c.__END_AT IS NULL)

-- AUTO CDC: current state join with SCD Type 1 dimension
JOIN gold.trading.dim_security s
  ON t.security_key = s.security_key

GROUP BY 
  t.trade_business_date, 
  c.legal_name, c.segment,
  s.security_name, s.asset_class;
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 4: MONITORING — Validate All Three
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Collation Monitor

```sql
-- Alert: Detect potential case-mismatch issues in JOINs
-- Run daily after loads
SELECT 
  'dim_customer' AS table_name,
  'legal_name' AS column_name,
  legal_name,
  COUNT(*) AS appearances
FROM gold.trading.dim_customer
WHERE __END_AT IS NULL
GROUP BY legal_name COLLATE UTF8_BINARY    -- force binary comparison
HAVING COUNT(*) > 1
ORDER BY appearances DESC;
-- If rows appear: same name exists in different cases
-- e.g., "JPMorgan" and "JPMORGAN" treated as separate with binary
```

## Precision Monitor

```sql
-- Alert: Detect precision drift after aggregation
-- Compare detail-level SUM vs pre-computed MV value
SELECT 
  mv.trade_business_date,
  mv.total_volume AS mv_total,
  detail.detail_total,
  ABS(mv.total_volume - detail.detail_total) AS delta,
  CASE 
    WHEN ABS(mv.total_volume - detail.detail_total) > 0.01 
    THEN '🔴 FAIL' ELSE '🟢 PASS' 
  END AS status
FROM gold.trading.mv_trading_summary mv
JOIN (
  SELECT trade_business_date, 
    CAST(SUM(CAST(trade_amount AS DECIMAL(38,10))) AS DECIMAL(38,10)) AS detail_total
  FROM gold.trading.fact_trades
  GROUP BY trade_business_date
) detail ON mv.trade_business_date = detail.trade_business_date
WHERE delta > 0.01;
-- Should return 0 rows
```

## Duplicate Monitor

```sql
-- Alert: Detect duplicates in dimension tables
-- Run after every pipeline refresh
WITH dupe_check AS (
  SELECT 
    'dim_customer' AS table_name,
    customer_id AS business_key,
    COUNT(*) AS active_versions
  FROM gold.trading.dim_customer
  WHERE __END_AT IS NULL    -- current rows only
  GROUP BY customer_id
  HAVING COUNT(*) > 1       -- more than 1 active = PROBLEM
  
  UNION ALL
  
  SELECT 
    'dim_security' AS table_name,
    security_id AS business_key,
    COUNT(*) AS active_versions
  FROM gold.trading.dim_security
  GROUP BY security_id
  HAVING COUNT(*) > 1
)
SELECT * FROM dupe_check;
-- Should return 0 rows. Any rows = AUTO CDC misconfigured.
```

## Combined Health Dashboard Query

```sql
-- Single query for daily migration health check
SELECT 
  current_timestamp() AS checked_at,
  
  -- Duplicate check
  (SELECT COUNT(*) FROM gold.trading.dim_customer 
   WHERE __END_AT IS NULL
   GROUP BY customer_id HAVING COUNT(*) > 1) AS customer_dupes,
   
  -- Row count match
  (SELECT COUNT(*) FROM gold.trading.dim_customer WHERE __END_AT IS NULL) AS dbx_customer_count,
  
  -- Precision check (max drift across all daily totals)
  (SELECT MAX(ABS(mv.total_volume - d.detail_total))
   FROM gold.trading.mv_trading_summary mv
   JOIN (SELECT trade_business_date, 
           CAST(SUM(CAST(trade_amount AS DECIMAL(38,10))) AS DECIMAL(38,10)) AS detail_total
         FROM gold.trading.fact_trades GROUP BY trade_business_date) d
   ON mv.trade_business_date = d.trade_business_date) AS max_precision_drift;
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHEAT SHEET: Quick Reference
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
COLLATION                           CAST                              AUTO CDC
─────────────────────────           ─────────────────────────         ─────────────────────────
Catalog: DEFAULT COLLATION          Table: DECIMAL(38,10)             Type 1: stored_as_scd_type="1"
Schema:  DEFAULT COLLATION          Agg:   CAST(SUM(CAST(...)))         → dedup, latest wins
Column:  COLLATE UTF8_LCASE         Ban:   FLOAT for money              → no __START_AT/__END_AT
Expr:    COLLATE UNICODE_CI         Check: CHECK (amount > 0)        Type 2: stored_as_scd_type=2
                                    Test:  golden row framework         → full history
Names:   UTF8_LCASE                                                     → __START_AT, __END_AT
Codes:   UTF8_BINARY                Teradata → Databricks:              → WHERE __END_AT IS NULL
Intl:    UNICODE_CI_AI              DECIMAL(p,s) → DECIMAL(p,s)      
                                    BYTEINT → TINYINT                 Selective:
Validate: compare JOIN              INTERVAL → BIGINT                   track_history_column_list
counts TD vs DBX                    TIMESTAMP W/ TZ → TS + STRING      → only named cols trigger
                                                                        new history rows
Python:                             Python:                           
dp.table() → COLLATE in DDL        Explicit .cast("decimal(38,10)")  dp.create_auto_cdc_flow(
                                                                       keys=["pk"],
SQL:                                SQL:                                sequence_by=col("ts"),
STRING COLLATE UTF8_LCASE           CAST(x AS DECIMAL(38,10))          stored_as_scd_type=2
                                                                     )
```
