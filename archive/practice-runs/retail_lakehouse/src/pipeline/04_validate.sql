-- Validation Queries — Run after pipeline completes

-- 1. Row counts across layers
SELECT 'bronze_transactions' AS layer, COUNT(*) AS rows FROM interview.retail.bronze_transactions
UNION ALL
SELECT 'silver_transactions', COUNT(*) FROM interview.retail.silver_transactions
UNION ALL
SELECT 'gold_sales_by_category', COUNT(*) FROM interview.retail.gold_sales_by_category
UNION ALL
SELECT 'gold_sales_by_store', COUNT(*) FROM interview.retail.gold_sales_by_store
UNION ALL
SELECT 'gold_daily_revenue', COUNT(*) FROM interview.retail.gold_daily_revenue;

-- 2. Duplicate check (Silver)
SELECT transaction_id, COUNT(*) cnt
FROM interview.retail.silver_transactions
GROUP BY transaction_id HAVING cnt > 1;

-- 3. Null audit
SELECT
  COUNT(*) AS total_rows,
  SUM(CASE WHEN transaction_id IS NULL THEN 1 ELSE 0 END) AS null_txn_ids,
  SUM(CASE WHEN product_id IS NULL THEN 1 ELSE 0 END) AS null_product_ids,
  SUM(CASE WHEN total_amount IS NULL THEN 1 ELSE 0 END) AS null_amounts
FROM interview.retail.silver_transactions;
