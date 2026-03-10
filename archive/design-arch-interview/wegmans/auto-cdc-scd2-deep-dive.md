# AUTO CDC with SCD TYPE 2 — Complete Syntax Reference
## The Single Feature That Replaces Teradata's PK Enforcement + History Tracking

---

## Why This Matters

In Teradata, you get three things for free:
1. **PK enforcement** — duplicate INSERT rejected
2. **Identity guarantee** — one row per business key
3. **Audit history** — via temporal tables or manual SCD MERGE

In Databricks, **AUTO CDC with SCD TYPE 2 gives you all three in ~4 lines of code.**

```
KEYS          → replaces PK enforcement (defines what makes a record unique)
SEQUENCE BY   → replaces duplicate rejection (latest wins, handles out-of-order)
SCD TYPE 2    → replaces manual history tracking (__START_AT / __END_AT)
```

Without AUTO CDC, you'd write 50+ lines of MERGE logic. With it: 4 lines.

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SYNTAX: SQL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Minimal Example (SQL)

```sql
-- Step 1: Declare the target table
CREATE OR REFRESH STREAMING TABLE gold.dim_customer;

-- Step 2: Create the AUTO CDC flow (4 lines that replace 50 lines of MERGE)
CREATE FLOW customer_scd2 AS
AUTO CDC INTO gold.dim_customer
FROM STREAM silver.customers_clean
KEYS (customer_id)
SEQUENCE BY updated_timestamp
STORED AS SCD TYPE 2;
```

**That's it.** This:
- Rejects duplicates by `customer_id` (KEYS)
- Handles late-arriving data by `updated_timestamp` (SEQUENCE BY)
- Creates `__START_AT` / `__END_AT` columns automatically (SCD TYPE 2)
- Guarantees exactly ONE active row per `customer_id` at any point in time

---

## Full Production Example (SQL) — FinServ Customer Dimension

### Bronze: Raw CDC Feed from Source System

```sql
CREATE OR REPLACE STREAMING TABLE bronze.customers_cdc_raw
CLUSTER BY (ingestion_date)
COMMENT 'Raw CDC feed from core banking system. Contains INSERT/UPDATE/DELETE operations.'
AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  _metadata.file_path AS _source_file,
  CAST(current_date() AS DATE) AS ingestion_date
FROM STREAM read_files(
  '/Volumes/finserv/landing/customers_cdc/',
  format => 'json',
  schemaHints => '
    customer_id STRING,
    legal_name STRING,
    email STRING,
    phone STRING,
    address_line1 STRING,
    city STRING,
    state STRING,
    zip_code STRING,
    country STRING,
    segment STRING,
    risk_rating STRING,
    kyc_status STRING,
    relationship_manager STRING,
    operation STRING,
    updated_timestamp TIMESTAMP
  '
);
```

### Silver: Clean + Validate + Type-Cast

```sql
CREATE OR REPLACE STREAMING TABLE silver.customers_clean (
  -- Data quality expectations (these ARE enforced)
  CONSTRAINT valid_id EXPECT (customer_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_name EXPECT (legal_name IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_timestamp EXPECT (updated_timestamp IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_operation EXPECT (operation IN ('INSERT','UPDATE','DELETE')) ON VIOLATION DROP ROW
)
CLUSTER BY (customer_id)
COMMENT 'Cleaned customer CDC data. Quality-validated. Ready for AUTO CDC.'
AS
SELECT
  customer_id,
  legal_name,
  LOWER(email) AS email,
  phone,
  address_line1,
  city,
  state,
  zip_code,
  country,
  segment,
  risk_rating,
  kyc_status,
  relationship_manager,
  operation,
  CAST(updated_timestamp AS TIMESTAMP) AS updated_timestamp,
  _ingested_at,
  _source_file
FROM STREAM bronze.customers_cdc_raw;
```

### Gold: AUTO CDC — SCD Type 2 with All Options

```sql
-- Step 1: Declare target with clustering for query performance
CREATE OR REFRESH STREAMING TABLE gold.dim_customer
CLUSTER BY (customer_id)
COMMENT 'Customer dimension with full SCD Type 2 history. '
        'Columns: __START_AT (effective from), __END_AT (expired at, NULL=current). '
        'KEYS: customer_id. SEQUENCE: updated_timestamp.';

-- Step 2: The AUTO CDC flow
CREATE FLOW customer_history_flow AS
AUTO CDC INTO gold.dim_customer
FROM STREAM silver.customers_clean
KEYS (customer_id)
APPLY AS DELETE WHEN operation = 'DELETE'
SEQUENCE BY updated_timestamp
COLUMNS * EXCEPT (operation, _ingested_at, _source_file)
STORED AS SCD TYPE 2;
```

### What Each Clause Does

```sql
AUTO CDC INTO gold.dim_customer          -- Target table (auto-adds __START_AT, __END_AT)
FROM STREAM silver.customers_clean       -- Source: streaming table from Silver
KEYS (customer_id)                       -- ← REPLACES PK ENFORCEMENT
                                         --   Defines uniqueness. One active row per key.
                                         --   Multiple keys: KEYS (account_id, sub_account_id)
APPLY AS DELETE WHEN operation = 'DELETE' -- ← HANDLES DELETES
                                         --   When source says DELETE, close out the record
                                         --   (__END_AT set, no active row remains)
SEQUENCE BY updated_timestamp            -- ← REPLACES DUPLICATE REJECTION
                                         --   If two records arrive for same key,
                                         --   the one with LATER timestamp wins.
                                         --   Handles out-of-order streaming data.
COLUMNS * EXCEPT (operation, ...)        -- ← EXCLUDE pipeline metadata columns
                                         --   Don't store operation/ingestion cols in dim
STORED AS SCD TYPE 2                     -- ← REPLACES MANUAL HISTORY TRACKING
                                         --   Auto-creates __START_AT, __END_AT
                                         --   Current row: __END_AT IS NULL
                                         --   Historical row: __END_AT IS NOT NULL
```

---

## Resulting Table Structure

```
gold.dim_customer
┌─────────────┬────────────┬────────────────┬─────────┬───────────────┬─────────────────────┬─────────────────────┐
│ customer_id │ legal_name │ email          │ segment │ risk_rating   │ __START_AT           │ __END_AT            │
├─────────────┼────────────┼────────────────┼─────────┼───────────────┼─────────────────────┼─────────────────────┤
│ C001        │ Alice Smith│ alice@bank.com │ Premium │ Low           │ 2023-01-15 09:00:00 │ 2024-03-20 14:30:00 │ ← expired
│ C001        │ Alice Jones│ alice@bank.com │ Premium │ Low           │ 2024-03-20 14:30:00 │ 2024-11-01 10:00:00 │ ← expired (name change: married)
│ C001        │ Alice Jones│ alice@bank.com │ Private │ Medium        │ 2024-11-01 10:00:00 │ NULL                │ ← CURRENT (segment + risk change)
│ C002        │ Bob Chen   │ bob@corp.com   │ Retail  │ Low           │ 2023-06-01 08:00:00 │ NULL                │ ← CURRENT (never changed)
└─────────────┴────────────┴────────────────┴─────────┴───────────────┴─────────────────────┴─────────────────────┘

Key guarantees:
  ✓ Exactly ONE row per customer_id where __END_AT IS NULL (current state)
  ✓ Full audit trail of every change (when, what changed)
  ✓ Late-arriving data handled correctly (SEQUENCE BY)
  ✓ No manual MERGE logic required
```

---

## Selective History Tracking

Don't create a new version for EVERY column change — only track what matters:

```sql
CREATE OR REFRESH STREAMING TABLE gold.dim_customer_selective;

CREATE FLOW customer_selective_flow AS
AUTO CDC INTO gold.dim_customer_selective
FROM STREAM silver.customers_clean
KEYS (customer_id)
APPLY AS DELETE WHEN operation = 'DELETE'
SEQUENCE BY updated_timestamp
COLUMNS * EXCEPT (operation, _ingested_at, _source_file)
STORED AS SCD TYPE 2
TRACK HISTORY ON segment, risk_rating, kyc_status;
-- ↑ Only these 3 columns trigger a new historical version
-- Other changes (email, phone, address) update in-place silently
```

**Why this matters for FinServ:**
- Risk rating change? → New version (auditors need to see when it changed)
- KYC status change? → New version (compliance requirement)
- Phone number change? → In-place update (no audit requirement)
- Reduces table size by 60-80% vs tracking everything

---

## Composite Keys

When identity requires multiple columns:

```sql
-- Account dimension: unique by account_id + sub_account_id
CREATE OR REFRESH STREAMING TABLE gold.dim_account;

CREATE FLOW account_history_flow AS
AUTO CDC INTO gold.dim_account
FROM STREAM silver.accounts_clean
KEYS (account_id, sub_account_id)
SEQUENCE BY modified_timestamp
COLUMNS * EXCEPT (operation, _ingested_at)
STORED AS SCD TYPE 2;
```

---

## Handling Deletes (Soft Delete Pattern)

```sql
-- When source sends operation = 'DELETE':
-- The current row gets __END_AT set to the delete timestamp
-- No active row remains for that customer_id
-- Full history is preserved (never physically deleted)

-- Query: Find deleted customers
SELECT customer_id, legal_name, __START_AT, __END_AT
FROM gold.dim_customer
WHERE customer_id NOT IN (
  SELECT customer_id FROM gold.dim_customer WHERE __END_AT IS NULL
);
-- These customers existed but were deleted — all history preserved
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SYNTAX: Python
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Minimal Example (Python)

```python
from pyspark import pipelines as dp
from pyspark.sql.functions import col

# Step 1: Declare target
dp.create_streaming_table("gold.dim_customer")

# Step 2: Create AUTO CDC flow
dp.create_auto_cdc_flow(
    target="gold.dim_customer",
    source="silver.customers_clean",
    keys=["customer_id"],
    sequence_by=col("updated_timestamp"),
    stored_as_scd_type=2                       # Integer for Type 2
)
```

---

## Full Production Example (Python) — FinServ Customer Dimension

```python
from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.functions import col

# ─── Config ───
schema_location = spark.conf.get("schema_location_base")
gold_schema = spark.conf.get("gold_schema", "gold")
silver_schema = spark.conf.get("silver_schema", "silver")


# ━━━ BRONZE: Raw CDC Ingest ━━━

@dp.table(
    name="bronze.customers_cdc_raw",
    cluster_by=["ingestion_date"],
    comment="Raw CDC feed from core banking. May contain dupes and out-of-order events."
)
def bronze_customers():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", f"{schema_location}/customers_raw")
        .option("cloudFiles.inferColumnTypes", "true")
        .load("/Volumes/finserv/landing/customers_cdc/")
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.col("_metadata.file_path"))
        .withColumn("ingestion_date", F.current_date())
    )


# ━━━ SILVER: Clean + Validate ━━━

@dp.table(
    name=f"{silver_schema}.customers_clean",
    cluster_by=["customer_id"],
    comment="Validated customer CDC. Quality-checked. Ready for AUTO CDC."
)
@dp.expect_or_drop("valid_id", "customer_id IS NOT NULL")
@dp.expect_or_drop("valid_name", "legal_name IS NOT NULL")
@dp.expect_or_drop("valid_timestamp", "updated_timestamp IS NOT NULL")
@dp.expect_or_fail("valid_operation", "operation IN ('INSERT','UPDATE','DELETE')")
def silver_customers():
    return (
        spark.readStream.table("bronze.customers_cdc_raw")
        .withColumn("updated_timestamp", F.to_timestamp("updated_timestamp"))
        .withColumn("email", F.lower(F.col("email")))
        .withColumn("zip_code", F.trim(F.col("zip_code")))
        .select(
            "customer_id", "legal_name", "email", "phone",
            "address_line1", "city", "state", "zip_code", "country",
            "segment", "risk_rating", "kyc_status", "relationship_manager",
            "operation", "updated_timestamp",
            "_ingested_at", "_source_file"
        )
    )


# ━━━ GOLD: AUTO CDC — SCD Type 2 (Full History) ━━━

# Step 1: Declare the target
dp.create_streaming_table(
    name=f"{gold_schema}.dim_customer",
    comment=(
        "Customer dimension with SCD Type 2 history. "
        "KEYS: customer_id. SEQUENCE: updated_timestamp. "
        "Query current: WHERE __END_AT IS NULL. "
        "Point-in-time: WHERE __START_AT <= date AND (__END_AT > date OR __END_AT IS NULL)."
    )
)

# Step 2: Create the AUTO CDC flow
dp.create_auto_cdc_flow(
    target=f"{gold_schema}.dim_customer",
    source=f"{silver_schema}.customers_clean",
    keys=["customer_id"],                              # ← PK enforcement
    sequence_by=col("updated_timestamp"),               # ← Dedup / ordering
    stored_as_scd_type=2,                               # ← History tracking (integer!)
    apply_as_deletes=col("operation") == "DELETE",      # ← Handle deletes
    except_column_list=[                                # ← Exclude metadata
        "operation", "_ingested_at", "_source_file"
    ]
)


# ━━━ GOLD: AUTO CDC — Selective History ━━━

dp.create_streaming_table(
    name=f"{gold_schema}.dim_customer_selective",
    comment="Customer dim with selective SCD2. Only segment/risk/kyc changes create versions."
)

dp.create_auto_cdc_flow(
    target=f"{gold_schema}.dim_customer_selective",
    source=f"{silver_schema}.customers_clean",
    keys=["customer_id"],
    sequence_by=col("updated_timestamp"),
    stored_as_scd_type=2,
    apply_as_deletes=col("operation") == "DELETE",
    except_column_list=["operation", "_ingested_at", "_source_file"],
    track_history_column_list=["segment", "risk_rating", "kyc_status"]
    # ↑ ONLY these columns trigger new history rows
    # Phone/email/address changes update in-place
)


# ━━━ GOLD: AUTO CDC — SCD Type 1 (Reference Data, No History) ━━━

dp.create_streaming_table(
    name=f"{gold_schema}.dim_branch",
    comment="Branch dimension. SCD Type 1 — current state only, no history."
)

dp.create_auto_cdc_flow(
    target=f"{gold_schema}.dim_branch",
    source=f"{silver_schema}.branches_clean",
    keys=["branch_id"],
    sequence_by=col("modified_timestamp"),
    stored_as_scd_type="1",                   # ← String for Type 1!
    except_column_list=["operation", "_ingested_at"]
)
```

---

## ⚠️ Critical Syntax Gotcha

```python
# SCD Type 2: integer
stored_as_scd_type=2          # ✅ integer → history tracking

# SCD Type 1: STRING  
stored_as_scd_type="1"        # ✅ string → in-place updates

# WRONG:
stored_as_scd_type="2"        # ❌ string "2" → ERROR
stored_as_scd_type=1           # ❌ integer 1 → ERROR
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QUERYING SCD TYPE 2: The 5 Essential Patterns
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Pattern 1: Current State (Most Common)

```sql
-- "Who is this customer RIGHT NOW?"
-- This is what 90% of queries need
SELECT *
FROM gold.dim_customer
WHERE __END_AT IS NULL;

-- Pro tip: Create a materialized view for this
CREATE OR REPLACE MATERIALIZED VIEW gold.dim_customer_current
  CLUSTER BY (customer_id)
  TRIGGER ON UPDATE
  COMMENT 'Current-state customer dimension. Auto-refreshes when dim_customer changes.'
AS
SELECT
  customer_id,
  legal_name,
  email,
  segment,
  risk_rating,
  kyc_status,
  relationship_manager,
  __START_AT AS effective_since
FROM gold.dim_customer
WHERE __END_AT IS NULL;
```

## Pattern 2: Point-in-Time ("As-Of" Query)

```sql
-- "What was this customer's risk rating on June 30, 2024?"
-- Critical for: regulatory snapshots, audit queries, historical reporting
SELECT
  customer_id,
  legal_name,
  risk_rating,
  segment,
  __START_AT AS effective_from,
  __END_AT AS effective_to
FROM gold.dim_customer
WHERE customer_id = 'C001'
  AND __START_AT <= '2024-06-30'
  AND (__END_AT > '2024-06-30' OR __END_AT IS NULL);
-- Returns exactly ONE row: the version that was active on that date

-- Bulk point-in-time: All customers as of quarter-end
CREATE OR REPLACE MATERIALIZED VIEW gold.customers_q2_2024_snapshot AS
SELECT *
FROM gold.dim_customer
WHERE __START_AT <= '2024-06-30'
  AND (__END_AT > '2024-06-30' OR __END_AT IS NULL);
```

## Pattern 3: Temporal Join — Fact with Historical Dimension

```sql
-- "What was the customer's segment AT THE TIME of each trade?"
-- This is THE killer query for FinServ — audit trail for every transaction
CREATE OR REPLACE MATERIALIZED VIEW gold.trades_with_customer_at_trade_time
  CLUSTER BY (trade_business_date)
  SCHEDULE EVERY 1 HOUR
AS
SELECT
  t.trade_id,
  t.trade_business_date,
  t.trade_ts_utc,
  t.security_id,
  CAST(t.trade_amount AS DECIMAL(38,10)) AS trade_amount,
  
  -- Customer attributes AS OF THE TRADE DATE (not current!)
  c.legal_name AS customer_name_at_trade,
  c.segment AS customer_segment_at_trade,
  c.risk_rating AS customer_risk_at_trade,
  c.relationship_manager AS rm_at_trade,
  c.__START_AT AS customer_version_from,
  c.__END_AT AS customer_version_to

FROM gold.fact_trades t

-- TEMPORAL JOIN: match the dimension version active at trade time
INNER JOIN gold.dim_customer c
  ON t.customer_id = c.customer_id
  AND t.trade_ts_utc >= c.__START_AT
  AND (t.trade_ts_utc < c.__END_AT OR c.__END_AT IS NULL);

-- Result: Every trade shows what the customer LOOKED LIKE when the trade happened
-- Customer was "Retail" when they traded on Jan 15, then "Premium" on March 20
-- Both rows show the CORRECT segment at the time — not today's segment
```

### Same in Python (for notebook exploration)

```python
trades = spark.table("gold.fact_trades")
customers = spark.table("gold.dim_customer")

# Temporal join
trades_enriched = (
    trades.alias("t")
    .join(
        customers.alias("c"),
        (F.col("t.customer_id") == F.col("c.customer_id")) &
        (F.col("t.trade_ts_utc") >= F.col("c.__START_AT")) &
        (
            (F.col("t.trade_ts_utc") < F.col("c.__END_AT")) |
            F.col("c.__END_AT").isNull()
        ),
        "inner"
    )
    .select(
        "t.trade_id", "t.trade_business_date", "t.trade_amount",
        "c.legal_name", "c.segment", "c.risk_rating",
        "c.__START_AT", "c.__END_AT"
    )
)
```

## Pattern 4: Change History & Audit Trail

```sql
-- "Show me every change to customer C001, in order"
SELECT
  customer_id,
  legal_name,
  segment,
  risk_rating,
  kyc_status,
  __START_AT AS effective_from,
  __END_AT AS effective_to,
  CASE 
    WHEN __END_AT IS NULL THEN '→ CURRENT'
    ELSE '  expired'
  END AS status,
  COALESCE(
    DATEDIFF(DAY, __START_AT, __END_AT),
    DATEDIFF(DAY, __START_AT, current_timestamp())
  ) AS days_in_this_version
FROM gold.dim_customer
WHERE customer_id = 'C001'
ORDER BY __START_AT;

/*
Result:
customer_id | legal_name  | segment | risk_rating | effective_from      | effective_to        | status     | days
C001        | Alice Smith | Retail  | Low         | 2023-01-15 09:00:00 | 2024-03-20 14:30:00 |   expired  | 430
C001        | Alice Jones | Retail  | Low         | 2024-03-20 14:30:00 | 2024-06-01 10:00:00 |   expired  |  73
C001        | Alice Jones | Premium | Low         | 2024-06-01 10:00:00 | 2024-11-01 10:00:00 |   expired  | 153
C001        | Alice Jones | Premium | Medium      | 2024-11-01 10:00:00 | NULL                | → CURRENT  | 114
*/

-- "What changed between versions?" (diff query)
WITH versioned AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY __START_AT) AS version_num,
    LAG(legal_name) OVER (PARTITION BY customer_id ORDER BY __START_AT) AS prev_name,
    LAG(segment) OVER (PARTITION BY customer_id ORDER BY __START_AT) AS prev_segment,
    LAG(risk_rating) OVER (PARTITION BY customer_id ORDER BY __START_AT) AS prev_risk
  FROM gold.dim_customer
  WHERE customer_id = 'C001'
)
SELECT
  customer_id,
  version_num,
  __START_AT AS change_timestamp,
  CASE WHEN legal_name != prev_name THEN concat(prev_name, ' → ', legal_name) END AS name_changed,
  CASE WHEN segment != prev_segment THEN concat(prev_segment, ' → ', segment) END AS segment_changed,
  CASE WHEN risk_rating != prev_risk THEN concat(prev_risk, ' → ', risk_rating) END AS risk_changed
FROM versioned
WHERE version_num > 1
ORDER BY __START_AT;

/*
version | change_timestamp    | name_changed              | segment_changed    | risk_changed
2       | 2024-03-20 14:30:00 | Alice Smith → Alice Jones | NULL               | NULL
3       | 2024-06-01 10:00:00 | NULL                      | Retail → Premium   | NULL
4       | 2024-11-01 10:00:00 | NULL                      | NULL               | Low → Medium
*/
```

## Pattern 5: Regulatory Snapshot (End-of-Period)

```sql
-- "Give me every customer's state at end of each quarter"
-- Required for: Basel III reporting, CCAR, DFAST stress tests
CREATE OR REPLACE MATERIALIZED VIEW gold.customer_quarterly_snapshots AS
WITH quarter_ends AS (
  SELECT explode(array(
    '2024-03-31', '2024-06-30', '2024-09-30', '2024-12-31'
  )) AS quarter_end_date
)
SELECT
  CAST(q.quarter_end_date AS DATE) AS reporting_date,
  c.customer_id,
  c.legal_name,
  c.segment,
  c.risk_rating,
  c.kyc_status,
  c.__START_AT AS version_effective
FROM quarter_ends q
INNER JOIN gold.dim_customer c
  ON CAST(q.quarter_end_date AS TIMESTAMP) >= c.__START_AT
  AND (CAST(q.quarter_end_date AS TIMESTAMP) < c.__END_AT OR c.__END_AT IS NULL);

-- Result: 4 rows per customer (one per quarter), each showing
-- the EXACT state of the customer at that quarter-end
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WHAT THIS REPLACES: Teradata Manual MERGE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## The Old Way (Teradata / Manual Databricks)

```sql
-- 50+ lines of manual SCD Type 2 MERGE logic
-- Error-prone, hard to maintain, doesn't handle late data

-- Step 1: Expire existing current records that have changes
MERGE INTO gold.dim_customer AS target
USING (
  SELECT s.* 
  FROM silver.customers_clean s
  JOIN gold.dim_customer t 
    ON s.customer_id = t.customer_id 
    AND t.__END_AT IS NULL
  WHERE s.legal_name != t.legal_name 
     OR s.segment != t.segment
     OR s.risk_rating != t.risk_rating
     -- ... check every column ...
) AS source
ON target.customer_id = source.customer_id 
  AND target.__END_AT IS NULL
WHEN MATCHED THEN UPDATE SET
  __END_AT = source.updated_timestamp;

-- Step 2: Insert new versions for changed records
INSERT INTO gold.dim_customer
SELECT 
  customer_id, legal_name, email, segment, risk_rating,
  updated_timestamp AS __START_AT,
  NULL AS __END_AT
FROM silver.customers_clean s
WHERE EXISTS (
  SELECT 1 FROM gold.dim_customer t
  WHERE t.customer_id = s.customer_id
    AND t.__END_AT = s.updated_timestamp  -- just expired above
);

-- Step 3: Insert brand new records
INSERT INTO gold.dim_customer
SELECT 
  customer_id, legal_name, email, segment, risk_rating,
  updated_timestamp AS __START_AT,
  NULL AS __END_AT
FROM silver.customers_clean s
WHERE NOT EXISTS (
  SELECT 1 FROM gold.dim_customer t
  WHERE t.customer_id = s.customer_id
);

-- Step 4: Handle deletes...
-- Step 5: Handle out-of-order arrivals...
-- Step 6: Handle multiple changes in same batch...
-- 😱 This is fragile, slow, and nobody wants to debug it at 3 AM
```

## The New Way (AUTO CDC)

```sql
CREATE OR REFRESH STREAMING TABLE gold.dim_customer;

CREATE FLOW customer_history AS
AUTO CDC INTO gold.dim_customer
FROM STREAM silver.customers_clean
KEYS (customer_id)
APPLY AS DELETE WHEN operation = 'DELETE'
SEQUENCE BY updated_timestamp
COLUMNS * EXCEPT (operation, _ingested_at, _source_file)
STORED AS SCD TYPE 2;

-- Done. Handles all of the above. Plus late data. Plus idempotent reruns.
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PARAMETER REFERENCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## SQL Syntax — Full Clause Reference

```sql
CREATE FLOW <flow_name> AS
AUTO CDC INTO <target_table>
FROM STREAM <source_table>
KEYS (<col1> [, <col2>, ...])                          -- REQUIRED: business key columns
[APPLY AS DELETE WHEN <boolean_expression>]             -- OPTIONAL: soft-delete condition
[APPLY AS TRUNCATE WHEN <boolean_expression>]           -- OPTIONAL: truncate condition  
SEQUENCE BY <timestamp_column>                          -- REQUIRED: ordering column
[COLUMNS <column_list>]                                 -- OPTIONAL: select specific columns
[COLUMNS * EXCEPT (<col1>, <col2>)]                     -- OPTIONAL: exclude columns
STORED AS SCD TYPE <1|2>                                -- REQUIRED: 1 or 2
[TRACK HISTORY ON <col1> [, <col2>, ...]];             -- OPTIONAL: selective tracking (Type 2 only)
```

## Python Syntax — Full Parameter Reference

```python
dp.create_auto_cdc_flow(
    target="catalog.schema.table",                      # REQUIRED: target table name
    source="catalog.schema.source",                     # REQUIRED: source table/view name
    keys=["col1", "col2"],                              # REQUIRED: business key column(s)
    sequence_by=col("timestamp_col"),                   # REQUIRED: ordering column (Column object)
    stored_as_scd_type=2,                               # REQUIRED: 2 (int) or "1" (str)
    apply_as_deletes=col("op") == "DELETE",             # OPTIONAL: delete condition (Column expr)
    apply_as_truncates=col("op") == "TRUNCATE",         # OPTIONAL: truncate condition
    except_column_list=["col1", "col2"],                # OPTIONAL: columns to exclude
    track_history_column_list=["col1", "col2"],         # OPTIONAL: selective tracking (Type 2)
    # Note: column_list parameter also exists for explicit include
)
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTERVIEW QUICK REFERENCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
┌─────────────────────────────────────────────────────────────────────┐
│  AUTO CDC with SCD TYPE 2 replaces THREE Teradata features:        │
│                                                                     │
│  ┌─────────────────┬──────────────────┬───────────────────────┐    │
│  │ Teradata         │ AUTO CDC Clause  │ What It Does           │    │
│  ├─────────────────┼──────────────────┼───────────────────────┤    │
│  │ PRIMARY KEY      │ KEYS (col)       │ Defines uniqueness     │    │
│  │ (enforced)       │                  │ One active row per key │    │
│  ├─────────────────┼──────────────────┼───────────────────────┤    │
│  │ SET table /      │ SEQUENCE BY ts   │ Latest timestamp wins  │    │
│  │ dupe rejection   │                  │ Handles late arrivals  │    │
│  ├─────────────────┼──────────────────┼───────────────────────┤    │
│  │ Temporal table / │ STORED AS        │ __START_AT / __END_AT  │    │
│  │ manual MERGE SCD │ SCD TYPE 2       │ Full audit history     │    │
│  └─────────────────┴──────────────────┴───────────────────────┘    │
│                                                                     │
│  5 Query Patterns to Know:                                          │
│  1. Current state:    WHERE __END_AT IS NULL                        │
│  2. Point-in-time:    __START_AT <= date AND (__END_AT > date       │
│                       OR __END_AT IS NULL)                          │
│  3. Temporal join:    fact.ts >= dim.__START_AT AND                  │
│                       (fact.ts < dim.__END_AT OR __END_AT IS NULL)  │
│  4. Change history:   ORDER BY __START_AT (full audit trail)        │
│  5. Regulatory snap:  Point-in-time for each quarter-end            │
│                                                                     │
│  Syntax gotcha: Type 2 = integer 2, Type 1 = string "1"           │
│  Column gotcha: __START_AT / __END_AT (double underscore!)          │
└─────────────────────────────────────────────────────────────────────┘
```
