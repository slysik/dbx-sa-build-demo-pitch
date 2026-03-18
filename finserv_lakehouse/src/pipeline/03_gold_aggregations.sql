-- Gold Layer: Pre-aggregated analytical marts
-- SDP Materialized Views — 3 marts for BI dashboard + Genie
-- All Gold tables read from Silver only (never Bronze)

-- ────────────────────────────────────────────────────────────────────────────
-- GOLD 1: Transaction Volume & Revenue by Category × Month
-- Use cases: Spend analytics dashboard, category performance, trend lines
-- ────────────────────────────────────────────────────────────────────────────
CREATE OR REFRESH MATERIALIZED VIEW workspace.finserv.gold_txn_by_category
COMMENT "Monthly transaction volume and revenue grouped by merchant category and customer segment."
TBLPROPERTIES ("quality" = "gold", "layer" = "gold")
AS
SELECT
  merchant_category,
  segment                             AS customer_segment,
  DATE_TRUNC('MONTH', txn_date)       AS txn_month,
  txn_status,

  COUNT(*)                            AS txn_count,
  SUM(amount)                         AS total_revenue,
  AVG(amount)                         AS avg_txn_amount,
  MAX(amount)                         AS max_txn_amount,
  SUM(CASE WHEN is_high_risk THEN 1 ELSE 0 END)  AS high_risk_count,
  AVG(risk_score)                     AS avg_risk_score

FROM workspace.finserv.silver_transactions
GROUP BY
  merchant_category,
  segment,
  DATE_TRUNC('MONTH', txn_date),
  txn_status;


-- ────────────────────────────────────────────────────────────────────────────
-- GOLD 2: Customer Segment Risk & Revenue Summary
-- Use cases: Risk management dashboard, credit exposure, segment P&L
-- ────────────────────────────────────────────────────────────────────────────
CREATE OR REFRESH MATERIALIZED VIEW workspace.finserv.gold_segment_risk
COMMENT "Risk and revenue rollup by customer segment and risk tier. Powers executive dashboards."
TBLPROPERTIES ("quality" = "gold", "layer" = "gold")
AS
SELECT
  segment,
  risk_tier,
  region,
  account_type,

  COUNT(DISTINCT customer_id)         AS unique_customers,
  COUNT(DISTINCT account_id)          AS unique_accounts,
  COUNT(*)                            AS txn_count,
  SUM(amount)                         AS total_volume,
  AVG(amount)                         AS avg_txn_amount,
  SUM(CASE WHEN is_high_risk THEN 1 ELSE 0 END)        AS high_risk_txns,
  SUM(CASE WHEN txn_status = 'Flagged' THEN 1 ELSE 0 END) AS flagged_txns,
  SUM(CASE WHEN txn_status = 'Declined' THEN 1 ELSE 0 END) AS declined_txns,
  ROUND(
    SUM(CASE WHEN is_high_risk THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2
  )                                   AS risk_rate_pct,
  AVG(risk_score)                     AS avg_risk_score

FROM workspace.finserv.silver_transactions
GROUP BY
  segment,
  risk_tier,
  region,
  account_type;


-- ────────────────────────────────────────────────────────────────────────────
-- GOLD 3: Daily Risk Intelligence
-- Use cases: Risk ops real-time view, daily briefing, anomaly detection
-- ────────────────────────────────────────────────────────────────────────────
CREATE OR REFRESH MATERIALIZED VIEW workspace.finserv.gold_daily_risk
COMMENT "Day-level transaction risk metrics. Ingested daily for risk operations."
TBLPROPERTIES ("quality" = "gold", "layer" = "gold")
AS
SELECT
  txn_date,
  region,
  risk_tier,

  COUNT(*)                            AS total_txns,
  SUM(amount)                         AS total_volume,
  SUM(CASE WHEN is_high_risk THEN 1 ELSE 0 END)        AS high_risk_count,
  SUM(CASE WHEN txn_status = 'Flagged' THEN amount ELSE 0 END) AS flagged_volume,
  SUM(CASE WHEN txn_status = 'Declined' THEN 1 ELSE 0 END) AS declined_count,
  AVG(risk_score)                     AS avg_risk_score,
  MAX(risk_score)                     AS peak_risk_score,
  ROUND(
    SUM(CASE WHEN is_high_risk THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2
  )                                   AS daily_risk_rate_pct

FROM workspace.finserv.silver_transactions
GROUP BY
  txn_date,
  region,
  risk_tier;
