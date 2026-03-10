# Data Profiling

Comprehensive reference for data profiling, statistics collection, metadata inspection, UC Monitors, and drift detection in Databricks.

## Overview

Data profiling in Databricks spans multiple capabilities:

| Capability | Purpose |
|-----------|---------|
| `ANALYZE TABLE` | Compute column-level statistics for query optimization |
| `DESCRIBE EXTENDED` | Inspect table metadata, properties, and storage info |
| `INFORMATION_SCHEMA` | Query UC metadata programmatically |
| SQL profiling queries | Null counts, distinct counts, min/max, percentiles |
| UC Monitors | Automated drift detection, data quality monitoring |

---

## ANALYZE TABLE

Compute statistics used by the query optimizer. Essential for accurate cost-based optimization.

```sql
-- Compute statistics for all columns
ANALYZE TABLE analytics.gold.customers COMPUTE STATISTICS;

-- Compute statistics for specific columns
ANALYZE TABLE analytics.gold.customers
COMPUTE STATISTICS FOR COLUMNS customer_id, total_orders, lifetime_value;

-- Compute statistics for all columns (explicit)
ANALYZE TABLE analytics.gold.customers COMPUTE STATISTICS FOR ALL COLUMNS;

-- Check existing statistics
DESCRIBE EXTENDED analytics.gold.customers customer_id;
```

**When to run ANALYZE:**
- After large batch loads or MERGE operations
- After significant deletes or updates
- When query plans show poor estimates (table scans on small result sets)
- As part of your Gold table build pipeline

---

## DESCRIBE EXTENDED

Inspect table metadata, column details, and storage properties.

```sql
-- Full table metadata
DESCRIBE EXTENDED analytics.gold.customers;

-- Single column detail (includes stats if computed)
DESCRIBE EXTENDED analytics.gold.customers customer_id;

-- Table properties only
SHOW TBLPROPERTIES analytics.gold.customers;

-- Delta table detail (history, file count, size)
DESCRIBE DETAIL analytics.gold.customers;

-- Delta history
DESCRIBE HISTORY analytics.gold.customers LIMIT 10;
```

---

## Information Schema Queries

Query UC metadata programmatically for data discovery and governance.

```sql
-- Column inventory for a table
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default,
    comment
FROM system.information_schema.columns
WHERE table_catalog = 'analytics'
  AND table_schema = 'gold'
  AND table_name = 'customers'
ORDER BY ordinal_position;

-- Find tables with a specific column name (data discovery)
SELECT DISTINCT
    table_catalog,
    table_schema,
    table_name
FROM system.information_schema.columns
WHERE column_name LIKE '%customer_id%'
  AND table_catalog NOT IN ('system', 'hive_metastore');

-- Tables without comments (governance gap)
SELECT
    table_catalog || '.' || table_schema || '.' || table_name AS full_name,
    table_type
FROM system.information_schema.tables
WHERE comment IS NULL
  AND table_catalog NOT IN ('system', 'hive_metastore')
ORDER BY full_name;

-- Column count per table (complexity indicator)
SELECT
    table_catalog || '.' || table_schema || '.' || table_name AS full_name,
    COUNT(*) AS column_count
FROM system.information_schema.columns
WHERE table_catalog = 'analytics'
GROUP BY 1
ORDER BY column_count DESC;
```

---

## Data Profiling Patterns

### Null Analysis

```sql
-- Null counts and percentages for all columns
SELECT
    COUNT(*) AS total_rows,
    COUNT(customer_id) AS customer_id_non_null,
    COUNT(*) - COUNT(customer_id) AS customer_id_nulls,
    ROUND(100.0 * (COUNT(*) - COUNT(customer_id)) / COUNT(*), 2) AS customer_id_null_pct,
    COUNT(*) - COUNT(email) AS email_nulls,
    ROUND(100.0 * (COUNT(*) - COUNT(email)) / COUNT(*), 2) AS email_null_pct
FROM analytics.gold.customers;
```

### Distinct Counts

```sql
-- Distinct value counts
SELECT
    COUNT(DISTINCT customer_id) AS distinct_customers,
    COUNT(DISTINCT region) AS distinct_regions,
    COUNT(DISTINCT status) AS distinct_statuses,
    COUNT(*) AS total_rows
FROM analytics.gold.customers;
```

### Min/Max/Avg Profile

```sql
-- Numeric column profile
SELECT
    MIN(order_amount) AS min_amount,
    MAX(order_amount) AS max_amount,
    AVG(order_amount) AS avg_amount,
    STDDEV(order_amount) AS stddev_amount,
    PERCENTILE(order_amount, 0.5) AS median_amount,
    PERCENTILE(order_amount, 0.95) AS p95_amount,
    PERCENTILE(order_amount, 0.99) AS p99_amount
FROM analytics.silver.orders;
```

### Percentile Distribution

```sql
-- Full percentile profile for a numeric column
SELECT
    PERCENTILE(amount, 0.01) AS p01,
    PERCENTILE(amount, 0.05) AS p05,
    PERCENTILE(amount, 0.10) AS p10,
    PERCENTILE(amount, 0.25) AS p25,
    PERCENTILE(amount, 0.50) AS p50,
    PERCENTILE(amount, 0.75) AS p75,
    PERCENTILE(amount, 0.90) AS p90,
    PERCENTILE(amount, 0.95) AS p95,
    PERCENTILE(amount, 0.99) AS p99
FROM analytics.silver.orders;
```

### Categorical Distribution

```sql
-- Top values for a categorical column
SELECT
    status,
    COUNT(*) AS cnt,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM analytics.gold.customers
GROUP BY status
ORDER BY cnt DESC;
```

### Freshness Check

```sql
-- Data freshness: latest record timestamps
SELECT
    MAX(updated_at) AS latest_update,
    MIN(updated_at) AS earliest_update,
    DATEDIFF(current_timestamp(), MAX(updated_at)) AS days_since_update
FROM analytics.gold.customers;
```

---

## UC Monitors

Lakehouse Monitoring provides automated data quality and drift detection on Delta tables.

### Create Monitor

```sql
-- Snapshot monitor (point-in-time quality)
CREATE MONITOR analytics.gold.customers
SCHEDULE CRON '0 0 * * *'
USING SNAPSHOT;

-- Time series monitor (tracks metrics over time)
CREATE MONITOR analytics.gold.daily_revenue
SCHEDULE CRON '0 6 * * *'
USING TIME_SERIES
  TIMESTAMP_COL order_date
  GRANULARITIES ('1 day', '1 week');

-- Inference monitor (ML model quality)
CREATE MONITOR analytics.ml.predictions
SCHEDULE CRON '0 8 * * *'
USING INFERENCE
  TIMESTAMP_COL prediction_time
  PREDICTION_COL predicted_label
  LABEL_COL actual_label
  PROBLEM_TYPE 'CLASSIFICATION'
  GRANULARITIES ('1 day');
```

### Monitor Options

```sql
-- Monitor with slicing and custom metrics
CREATE MONITOR analytics.gold.transactions
SCHEDULE CRON '0 0 * * *'
USING TIME_SERIES
  TIMESTAMP_COL event_date
  GRANULARITIES ('1 day')
  SLICING_EXPRS ('region', 'product_category')
  CUSTOM_METRICS (
    STRUCT(
      'high_value_ratio' AS name,
      'double' AS type,
      'SUM(CASE WHEN amount > 1000 THEN 1 ELSE 0 END) / COUNT(*)' AS definition,
      ARRAY('amount') AS input_columns,
      'aggregate' AS output_data_type
    )
  );
```

### Monitor Output Tables

Each monitor creates two output tables in the same schema:

| Output Table | Purpose |
|-------------|---------|
| `{table_name}_profile_metrics` | Per-column statistics (null count, distinct count, min, max, mean, percentiles) |
| `{table_name}_drift_metrics` | Statistical drift scores comparing current window to baseline |

```sql
-- Query profile metrics
SELECT
    column_name,
    null_count,
    distinct_count,
    min,
    max,
    mean,
    percentile_25,
    percentile_50,
    percentile_75
FROM analytics.gold.customers_profile_metrics
WHERE window_end = (SELECT MAX(window_end) FROM analytics.gold.customers_profile_metrics);

-- Query drift metrics
SELECT
    column_name,
    drift_type,
    statistic,
    drift_score,
    CASE WHEN drift_score > 0.1 THEN 'DRIFT DETECTED' ELSE 'STABLE' END AS status
FROM analytics.gold.customers_drift_metrics
WHERE window_end = (SELECT MAX(window_end) FROM analytics.gold.customers_drift_metrics)
ORDER BY drift_score DESC;
```

### Manage Monitors

```sql
-- Refresh monitor (run now)
REFRESH MONITOR analytics.gold.customers;

-- Describe monitor configuration
DESCRIBE MONITOR analytics.gold.customers;

-- Drop monitor (removes output tables too)
DROP MONITOR analytics.gold.customers;

-- Drop monitor but keep output tables
DROP MONITOR analytics.gold.customers KEEP OUTPUT TABLES;
```

### MCP Tool for Monitors

```python
# Create/manage monitors via MCP
manage_uc_monitors(
    action="create",
    table_name="analytics.gold.customers",
    monitor_type="SNAPSHOT",
    schedule="0 0 * * *"
)

# List monitors
manage_uc_monitors(action="list", schema_name="analytics.gold")

# Get monitor status
manage_uc_monitors(action="get", table_name="analytics.gold.customers")
```

---

## Drift Detection Patterns

### Chi-Square Test (Categorical Drift)

```sql
-- Compare categorical distributions across two time windows
WITH baseline AS (
    SELECT status, COUNT(*) AS cnt
    FROM analytics.gold.customers
    WHERE updated_at < '2024-06-01'
    GROUP BY status
),
current_window AS (
    SELECT status, COUNT(*) AS cnt
    FROM analytics.gold.customers
    WHERE updated_at >= '2024-06-01'
    GROUP BY status
)
SELECT
    COALESCE(b.status, c.status) AS status,
    COALESCE(b.cnt, 0) AS baseline_count,
    COALESCE(c.cnt, 0) AS current_count
FROM baseline b
FULL OUTER JOIN current_window c ON b.status = c.status
ORDER BY status;
```

### Numeric Distribution Shift

```sql
-- Compare numeric distributions (baseline vs current)
SELECT
    'baseline' AS period,
    AVG(amount) AS mean_amount,
    STDDEV(amount) AS stddev_amount,
    PERCENTILE(amount, 0.5) AS median
FROM analytics.silver.orders
WHERE order_date < '2024-06-01'

UNION ALL

SELECT
    'current' AS period,
    AVG(amount) AS mean_amount,
    STDDEV(amount) AS stddev_amount,
    PERCENTILE(amount, 0.5) AS median
FROM analytics.silver.orders
WHERE order_date >= '2024-06-01';
```

---

## Best Practices

1. **Run ANALYZE TABLE after large writes** -- keeps the query optimizer accurate, especially for Gold tables used in dashboards.
2. **Use UC Monitors for automated quality** -- set up snapshot monitors on critical Gold tables; review drift metrics weekly.
3. **Profile before and after migrations** -- capture null counts, distinct counts, and distributions before/after schema changes.
4. **Slice monitors by business dimensions** -- use `SLICING_EXPRS` to detect drift in specific segments (regions, product lines).
5. **Set alerts on drift scores** -- pipe monitor output tables to notification workflows when `drift_score > threshold`.
6. **Use INFORMATION_SCHEMA for governance audits** -- find tables without comments, columns without tags, or schemas with no access controls.
