-- Validation queries — run after pipeline completes

-- 1. Row counts across layers
SELECT 'bronze_transactions' AS layer_table, COUNT(*) AS rows FROM workspace.retail.bronze_transactions
UNION ALL SELECT 'silver_transactions', COUNT(*) FROM workspace.retail.silver_transactions
UNION ALL SELECT 'gold_sales_by_category', COUNT(*) FROM workspace.retail.gold_sales_by_category
UNION ALL SELECT 'gold_sales_by_store', COUNT(*) FROM workspace.retail.gold_sales_by_store
UNION ALL SELECT 'gold_daily_revenue', COUNT(*) FROM workspace.retail.gold_daily_revenue;

-- 2. Duplicate check on Silver
SELECT txn_id, COUNT(*) AS cnt
FROM workspace.retail.silver_transactions
GROUP BY txn_id
HAVING cnt > 1;

-- 3. Revenue reconciliation: Bronze → Silver → Gold
SELECT
  'bronze_total'  AS source, ROUND(SUM(amount), 2) AS total_revenue FROM workspace.retail.bronze_transactions
UNION ALL
SELECT 'silver_total', ROUND(SUM(amount), 2) FROM workspace.retail.silver_transactions
UNION ALL
SELECT 'gold_category_total', ROUND(SUM(total_revenue), 2) FROM workspace.retail.gold_sales_by_category;

-- 4. Category distribution
SELECT category, COUNT(*) AS txn_count, ROUND(SUM(amount), 2) AS revenue
FROM workspace.retail.silver_transactions
GROUP BY category ORDER BY revenue DESC;
