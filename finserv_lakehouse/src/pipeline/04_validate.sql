-- FinServ Lakehouse — Post-Pipeline Validation Queries
-- Run via SQL Warehouse after SDP pipeline completes
-- One query at a time (Statements API requirement)

-- ── LAYER ROW COUNTS ────────────────────────────────────────────────────────
SELECT 'bronze_fact_transactions' AS layer_table, COUNT(*) AS row_count FROM workspace.finserv.bronze_fact_transactions
UNION ALL
SELECT 'silver_transactions',  COUNT(*) FROM workspace.finserv.silver_transactions
UNION ALL
SELECT 'gold_txn_by_category', COUNT(*) FROM workspace.finserv.gold_txn_by_category
UNION ALL
SELECT 'gold_segment_risk',    COUNT(*) FROM workspace.finserv.gold_segment_risk
UNION ALL
SELECT 'gold_daily_risk',      COUNT(*) FROM workspace.finserv.gold_daily_risk
ORDER BY layer_table;

-- ── SILVER DEDUP CHECK ──────────────────────────────────────────────────────
SELECT txn_id, COUNT(*) AS cnt
FROM workspace.finserv.silver_transactions
GROUP BY txn_id
HAVING cnt > 1
LIMIT 5;

-- ── NULL AUDIT (Silver) ─────────────────────────────────────────────────────
SELECT
  COUNT(*) AS total,
  SUM(CASE WHEN txn_id IS NULL     THEN 1 ELSE 0 END) AS null_txn_id,
  SUM(CASE WHEN account_id IS NULL THEN 1 ELSE 0 END) AS null_account_id,
  SUM(CASE WHEN amount IS NULL     THEN 1 ELSE 0 END) AS null_amount,
  SUM(CASE WHEN risk_score IS NULL THEN 1 ELSE 0 END) AS null_risk_score
FROM workspace.finserv.silver_transactions;

-- ── REVENUE RECONCILIATION ──────────────────────────────────────────────────
SELECT
  SUM(amount) AS silver_total_revenue
FROM workspace.finserv.silver_transactions;

SELECT
  SUM(total_revenue) AS gold_category_total
FROM workspace.finserv.gold_txn_by_category
WHERE txn_status = 'Approved';

-- ── RISK DISTRIBUTION CHECK ─────────────────────────────────────────────────
SELECT
  txn_status,
  COUNT(*) AS cnt,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct,
  ROUND(AVG(risk_score), 2) AS avg_risk
FROM workspace.finserv.silver_transactions
GROUP BY txn_status
ORDER BY cnt DESC;
