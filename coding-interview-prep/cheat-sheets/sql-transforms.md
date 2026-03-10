# SQL Transform Patterns for Databricks

> Your strength is SQL — lean into it! Generate data in Python, then do ALL transforms in SQL.

## Bronze → Silver Patterns

### Deduplication
```sql
-- Remove exact duplicates by keeping the latest record
-- NARRATE: "I'm deduplicating on transaction_id, keeping the most recent record.
--           ROW_NUMBER partitions by the key and orders by timestamp descending,
--           so row_num = 1 is always the latest version of each record."

CREATE OR REPLACE TABLE silver.transactions AS
SELECT * FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY transaction_id 
            ORDER BY ingestion_timestamp DESC
        ) as row_num
    FROM bronze.transactions_raw
)
WHERE row_num = 1;
```

### Data Type Casting & Cleaning
```sql
-- Cast strings to proper types, handle nulls
-- NARRATE: "Silver is where I enforce data quality. I'm casting amount from string
--           to decimal for precision with money — never use float for financial data."

CREATE OR REPLACE TABLE silver.transactions AS
SELECT
    transaction_id,
    customer_id,
    CAST(amount AS DECIMAL(12,2)) AS amount,         -- Precise decimal for money
    CAST(transaction_date AS TIMESTAMP) AS transaction_date,
    UPPER(TRIM(merchant_category)) AS merchant_category,  -- Normalize strings
    COALESCE(channel, 'unknown') AS channel,              -- Handle nulls
    is_fraud
FROM bronze.transactions_raw
WHERE transaction_id IS NOT NULL                          -- Drop records with no key
  AND amount IS NOT NULL;
```

### Data Quality Constraints
```sql
-- Add Delta table constraints for ongoing quality
-- NARRATE: "Delta Lake constraints act as guardrails — any future INSERT that 
--           violates these rules will fail, protecting data quality downstream."

ALTER TABLE silver.transactions ADD CONSTRAINT valid_amount CHECK (amount > 0);
ALTER TABLE silver.transactions ADD CONSTRAINT valid_id CHECK (transaction_id IS NOT NULL);
```

## Silver → Gold Patterns

### Customer Aggregation (common interview pattern)
```sql
-- Customer-level aggregated metrics
-- NARRATE: "This Gold table is a customer 360 view — one row per customer with 
--           all their key metrics. The business team can query this directly.
--           Under the hood, this GROUP BY triggers a shuffle — Spark redistributes 
--           all rows for each customer_id to the same partition for aggregation."

CREATE OR REPLACE TABLE gold.customer_360 AS
SELECT
    c.customer_id,
    c.first_name,
    c.last_name,
    c.customer_segment,
    c.credit_score,
    COUNT(t.transaction_id) AS total_transactions,
    SUM(t.amount) AS total_spend,
    AVG(t.amount) AS avg_transaction_amount,
    MAX(t.amount) AS largest_transaction,
    MIN(t.transaction_date) AS first_transaction_date,
    MAX(t.transaction_date) AS last_transaction_date,
    DATEDIFF(day, MAX(t.transaction_date), CURRENT_DATE()) AS days_since_last_txn,
    SUM(CASE WHEN t.is_fraud THEN 1 ELSE 0 END) AS fraud_count,
    ROUND(SUM(CASE WHEN t.is_fraud THEN 1 ELSE 0 END) * 100.0 
          / COUNT(*), 2) AS fraud_rate_pct
FROM silver.customers c
LEFT JOIN silver.transactions t ON c.customer_id = t.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name, c.customer_segment, c.credit_score;
```

### Time-Series Aggregation (daily/monthly summary)
```sql
-- Daily transaction summary
-- NARRATE: "This creates a time-series Gold table — one row per day per category.
--           Perfect for dashboards and trend analysis. I'm using DATE_TRUNC
--           to bucket timestamps into days."

CREATE OR REPLACE TABLE gold.daily_summary AS
SELECT
    DATE_TRUNC('day', transaction_date) AS txn_date,
    merchant_category,
    channel,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS avg_amount,
    SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) AS fraud_count,
    SUM(CASE WHEN is_fraud THEN amount ELSE 0 END) AS fraud_amount
FROM silver.transactions
GROUP BY DATE_TRUNC('day', transaction_date), merchant_category, channel
ORDER BY txn_date DESC;
```

### Window Functions (powerful for feature engineering)
```sql
-- Customer transaction patterns using window functions
-- NARRATE: "Window functions let me compute per-customer metrics WITHOUT 
--           collapsing rows. The PARTITION BY keeps each customer's data together,
--           and ORDER BY defines the window frame for running calculations."

CREATE OR REPLACE TABLE gold.transaction_features AS
SELECT
    transaction_id,
    customer_id,
    amount,
    transaction_date,
    
    -- Running average of last 5 transactions per customer
    AVG(amount) OVER (
        PARTITION BY customer_id 
        ORDER BY transaction_date 
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ) AS rolling_avg_5_txn,
    
    -- Transaction count in last 24 hours (possible velocity feature for fraud)
    COUNT(*) OVER (
        PARTITION BY customer_id 
        ORDER BY UNIX_TIMESTAMP(transaction_date)
        RANGE BETWEEN 86400 PRECEDING AND CURRENT ROW
    ) AS txn_count_24h,
    
    -- Rank by spend per customer
    RANK() OVER (
        PARTITION BY customer_id 
        ORDER BY amount DESC
    ) AS spend_rank,
    
    -- Deviation from customer's average
    amount - AVG(amount) OVER (PARTITION BY customer_id) AS deviation_from_avg,
    
    is_fraud
FROM silver.transactions;
```

### Pivot / Cross-Tab
```sql
-- Spend by category pivot
-- NARRATE: "This pivot creates a wide table — one row per customer with a column 
--           for each merchant category showing their total spend. Useful for 
--           segmentation analysis."

CREATE OR REPLACE TABLE gold.customer_category_spend AS
SELECT * FROM (
    SELECT customer_id, merchant_category, amount
    FROM silver.transactions
)
PIVOT (
    SUM(amount) 
    FOR merchant_category IN ('Grocery', 'Gas', 'Restaurant', 'Online', 'Travel', 'Healthcare', 'Entertainment')
);
```

## Useful SQL Functions Reference

| Function | Use Case | Example |
|----------|----------|---------|
| `COALESCE(a, b)` | Replace nulls | `COALESCE(city, 'Unknown')` |
| `NULLIF(a, b)` | Convert value to null | `NULLIF(status, '')` |
| `DATE_TRUNC('month', col)` | Truncate timestamp | Time-series grouping |
| `DATEDIFF(day, start, end)` | Days between dates | Recency calculation |
| `DATE_ADD(date, n)` | Add days | Date math |
| `REGEXP_REPLACE(col, pat, rep)` | Regex clean | `REGEXP_REPLACE(phone, '[^0-9]', '')` |
| `EXPLODE(array_col)` | Flatten arrays | One row per array element |
| `COLLECT_LIST(col)` | Aggregate into array | Group values into list |
| `PERCENTILE_APPROX(col, 0.5)` | Approximate median | Stats without exact sort |
