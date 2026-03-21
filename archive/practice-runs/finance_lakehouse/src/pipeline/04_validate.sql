-- ─────────────────────────────────────────────────────────────────────────────
-- Validation Queries — run after pipeline completes
-- Each query should return rows. Zero rows = pipeline or data issue.
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Row counts across all layers
SELECT 'bronze_dim_customers'       AS table_name, COUNT(*) AS row_count FROM workspace.finance.bronze_dim_customers
UNION ALL
SELECT 'bronze_dim_merchants',       COUNT(*) FROM workspace.finance.bronze_dim_merchants
UNION ALL
SELECT 'bronze_fact_transactions',   COUNT(*) FROM workspace.finance.bronze_fact_transactions
UNION ALL
SELECT 'silver_transactions',        COUNT(*) FROM workspace.finance.silver_transactions
UNION ALL
SELECT 'gold_daily_risk_summary',    COUNT(*) FROM workspace.finance.gold_daily_risk_summary
UNION ALL
SELECT 'gold_risk_by_segment',       COUNT(*) FROM workspace.finance.gold_risk_by_segment
UNION ALL
SELECT 'gold_merchant_risk',         COUNT(*) FROM workspace.finance.gold_merchant_risk
ORDER BY table_name;

-- 2. Silver dedup check — zero rows = no duplicates
SELECT txn_id, COUNT(*) AS cnt
FROM workspace.finance.silver_transactions
GROUP BY txn_id
HAVING cnt > 1;

-- 3. Risk score distribution (should show all 3 buckets)
SELECT risk_bucket, COUNT(*) AS txn_count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
FROM workspace.finance.silver_transactions
GROUP BY risk_bucket
ORDER BY risk_bucket;

-- 4. Overall fraud metrics (what the dashboard will show)
SELECT
  SUM(total_transactions)                    AS total_txns,
  ROUND(SUM(total_amount), 0)                AS total_amount_usd,
  SUM(high_risk_count)                       AS total_high_risk,
  ROUND(SUM(high_risk_amount), 0)            AS total_at_risk_usd,
  ROUND(AVG(fraud_rate_pct), 2)              AS avg_fraud_rate_pct
FROM workspace.finance.gold_daily_risk_summary;

-- 5. Delta table health — Bronze fact
DESCRIBE DETAIL workspace.finance.bronze_fact_transactions;
