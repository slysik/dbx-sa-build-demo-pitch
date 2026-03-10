# Databricks DW Architecture — Technical Deep Dive Reference

## SCD Implementation Patterns

### SCD Type 1 — LakeFlow AUTO CDC (Declarative, Recommended)
```sql
CREATE OR REFRESH STREAMING TABLE dim_customer;

CREATE FLOW customer_type1
AS AUTO CDC INTO dim_customer
FROM stream(bronze.customers_cdc)
KEYS (customer_id)
SEQUENCE BY seq_num
COLUMNS * EXCEPT (operation, seq_num)
STORED AS SCD TYPE 1;
```

### SCD Type 2 — LakeFlow AUTO CDC (Declarative, Recommended)
```sql
CREATE OR REFRESH STREAMING TABLE dim_customer_history;

CREATE FLOW customer_type2
AS AUTO CDC INTO dim_customer_history
FROM stream(bronze.customers_cdc)
KEYS (customer_id)
SEQUENCE BY sequenceNum
COLUMNS * EXCEPT (operation, sequenceNum)
STORED AS SCD TYPE 2
TRACK HISTORY ON * EXCEPT (last_login_date, updated_at);
-- Adds __START_AT and __END_AT columns automatically
-- Handles out-of-order records via SEQUENCE BY
```

### SCD Type 2 — Manual MERGE (When You Need Full Control)
```sql
-- Step 1: Create staged changes (two row types per changed record)
CREATE OR REPLACE TEMP VIEW staged_updates AS
SELECT customer_id AS merge_key, * FROM staging_customers
UNION ALL
-- Null merge_key = force INSERT (new version row)
SELECT NULL AS merge_key, * FROM staging_customers
WHERE customer_id IN (
  SELECT customer_id FROM dim_customer
  WHERE is_current = true
    AND (dim_customer.name != staging_customers.name
      OR dim_customer.city != staging_customers.city)
);

-- Step 2: MERGE
MERGE INTO dim_customer AS target
USING staged_updates AS source
ON target.customer_id = source.merge_key AND target.is_current = true
WHEN MATCHED AND (target.name != source.name OR target.city != source.city) THEN
  UPDATE SET
    target.is_current = false,
    target.effective_end_date = current_date()
WHEN NOT MATCHED THEN
  INSERT (customer_id, name, city, effective_start_date, effective_end_date, is_current)
  VALUES (source.customer_id, source.name, source.city, current_date(), '9999-12-31', true);
```

---

## Liquid Clustering Syntax

```sql
-- Create with clustering
CREATE TABLE fact_transactions (
  transaction_id BIGINT,
  transaction_date DATE,
  customer_id BIGINT,
  product_id BIGINT,
  amount DECIMAL(18,2)
) CLUSTER BY (transaction_date, customer_id);

-- Enable on existing table (no data rewrite needed)
ALTER TABLE fact_transactions CLUSTER BY (transaction_date, customer_id);

-- Let the platform choose automatically (DBR 15.4+)
ALTER TABLE fact_transactions CLUSTER BY AUTO;

-- Run incremental clustering
OPTIMIZE fact_transactions;

-- Run full recluster (after changing keys)
OPTIMIZE fact_transactions FULL;

-- Check clustering info
DESCRIBE DETAIL fact_transactions;
```

**Key Rules:**
- 1–4 clustering keys maximum
- Prefer high-cardinality columns that are frequently in WHERE clauses
- For FinServ: `(reporting_date, jurisdiction_code)` or `(trade_date, instrument_type)`
- For e-commerce: `(order_date, customer_id)` or `(event_date, product_category)`

---

## Materialized Views

```sql
-- Create MV with incremental refresh
CREATE MATERIALIZED VIEW gold.monthly_sales_summary
AS SELECT
  date_trunc('month', transaction_date) AS month,
  product_category,
  sum(amount) AS total_revenue,
  count(*) AS transaction_count
FROM silver.fact_transactions
GROUP BY 1, 2;

-- Requirement: row tracking on source table
ALTER TABLE silver.fact_transactions SET TBLPROPERTIES ('delta.enableRowTracking' = 'true');

-- Refresh on demand
REFRESH MATERIALIZED VIEW gold.monthly_sales_summary;

-- Check refresh metadata
DESCRIBE EXTENDED AS JSON gold.monthly_sales_summary;
```

---

## Lakehouse Federation — Query Legacy DW in Place

```sql
-- Step 1: Create connection to Teradata (Unity Catalog)
CREATE CONNECTION my_teradata_conn
TYPE teradata
OPTIONS (
  host 'teradata.example.com',
  port '1025',
  user secret ('<scope>', '<key>'),
  password secret ('<scope>', '<key>')
);

-- Step 2: Create foreign catalog
CREATE FOREIGN CATALOG teradata_legacy
USING CONNECTION my_teradata_conn
OPTIONS (database 'PROD_EDW');

-- Step 3: Query in place — no data movement
SELECT * FROM teradata_legacy.sales_mart.fact_daily_sales
WHERE report_date >= '2024-01-01';
```

---

## Unity Catalog — Security Patterns

### Row Filter (GA)
```sql
-- Create filter function
CREATE FUNCTION catalog.security.jurisdiction_filter(jurisdiction STRING)
RETURN is_member('admin') OR current_user() IN (
  SELECT user FROM catalog.security.jurisdiction_access
  WHERE jurisdiction_code = jurisdiction
);

-- Apply to table
ALTER TABLE silver.fact_risk_positions
SET ROW FILTER catalog.security.jurisdiction_filter ON (jurisdiction_code);
```

### Column Mask (GA)
```sql
-- Create mask function
CREATE FUNCTION catalog.security.mask_ssn(ssn STRING)
RETURN CASE
  WHEN is_member('pii_access') THEN ssn
  ELSE '***-**-' || right(ssn, 4)
END;

-- Apply to column
ALTER TABLE silver.dim_customer
ALTER COLUMN ssn SET MASK catalog.security.mask_ssn;
```

---

## SQL Warehouse Sizing Guide

| Workload | Recommended | Rationale |
|----------|-------------|-----------|
| Interactive BI / dashboards | **Serverless** | IWM auto-scales; no idle costs; 2–6s startup |
| Ad-hoc analytics | **Serverless** | PQE handles unpredictable query shapes |
| Scheduled batch reports | **Serverless or Pro** | Serverless for bursty; Pro for sustained |
| Streaming ingestion (DLT) | **Serverless DLT** | Auto-scaling; serverless billing |
| Heavy ETL / data engineering | **Classic or Jobs** | Sustained compute; lower DBU rate |

**Cluster sizing shortcut:**
- Start with `2X-Small` for development
- Use `Auto-stop` at 10 minutes for interactive
- `Cluster size × 2` when P50 query time > 5 minutes on serverless
