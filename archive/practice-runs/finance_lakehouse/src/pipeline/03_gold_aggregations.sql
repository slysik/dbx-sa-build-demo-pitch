-- ─────────────────────────────────────────────────────────────────────────────
-- Gold Layer: Risk & Fraud Analytics Aggregations
-- Three materialized views shaped for the AI/BI Dashboard + Genie
-- ─────────────────────────────────────────────────────────────────────────────

-- ── Gold 1: Daily Transaction Volume + Risk Metrics ──────────────────────────
-- Powers: KPI cards, trend line chart, channel breakdown bar chart
CREATE OR REFRESH MATERIALIZED VIEW workspace.finance.gold_daily_risk_summary
COMMENT "Daily transaction volume and risk metrics by channel — primary dashboard dataset"
TBLPROPERTIES ("quality" = "gold", "layer" = "gold")
AS
SELECT
  txn_date,
  channel,
  COUNT(*)                                              AS total_transactions,
  ROUND(SUM(amount), 2)                                 AS total_amount,
  COUNT(CASE WHEN risk_bucket = 'HIGH'  THEN 1 END)     AS high_risk_count,
  COUNT(CASE WHEN risk_bucket = 'MEDIUM' THEN 1 END)    AS medium_risk_count,
  ROUND(SUM(CASE WHEN risk_bucket = 'HIGH' THEN amount ELSE 0 END), 2)
                                                        AS high_risk_amount,
  ROUND(
    COUNT(CASE WHEN risk_bucket = 'HIGH' THEN 1 END) * 100.0 / COUNT(*),
  2)                                                    AS fraud_rate_pct,
  ROUND(AVG(risk_score), 1)                             AS avg_risk_score,
  COUNT(CASE WHEN rules_engine_flag = true THEN 1 END)  AS rules_flagged_count
FROM workspace.finance.silver_transactions
GROUP BY txn_date, channel;


-- ── Gold 2: Risk Profile by Customer Segment ─────────────────────────────────
-- Powers: segment heatmap, portfolio risk bar chart
CREATE OR REFRESH MATERIALIZED VIEW workspace.finance.gold_risk_by_segment
COMMENT "Risk and fraud exposure by customer segment and risk tier"
TBLPROPERTIES ("quality" = "gold", "layer" = "gold")
AS
SELECT
  customer_segment,
  customer_risk_tier,
  customer_country,
  COUNT(*)                                              AS transaction_count,
  COUNT(DISTINCT customer_id)                           AS unique_customers,
  ROUND(SUM(amount), 2)                                 AS total_amount,
  ROUND(AVG(risk_score), 1)                             AS avg_risk_score,
  COUNT(CASE WHEN risk_bucket = 'HIGH'  THEN 1 END)     AS high_risk_txns,
  COUNT(CASE WHEN risk_bucket = 'MEDIUM' THEN 1 END)    AS medium_risk_txns,
  ROUND(
    COUNT(CASE WHEN risk_bucket = 'HIGH' THEN 1 END) * 100.0 / COUNT(*),
  2)                                                    AS high_risk_rate_pct
FROM workspace.finance.silver_transactions
GROUP BY customer_segment, customer_risk_tier, customer_country;


-- ── Gold 3: Merchant Risk Exposure ───────────────────────────────────────────
-- Powers: top high-risk merchants table, category breakdown
CREATE OR REFRESH MATERIALIZED VIEW workspace.finance.gold_merchant_risk
COMMENT "Merchant-level risk exposure — flags high-risk merchant categories"
TBLPROPERTIES ("quality" = "gold", "layer" = "gold")
AS
SELECT
  merchant_id,
  merchant_category,
  mcc_code,
  merchant_is_high_risk,
  COUNT(*)                                              AS transaction_count,
  ROUND(SUM(amount), 2)                                 AS total_exposure,
  ROUND(AVG(risk_score), 1)                             AS avg_risk_score,
  COUNT(CASE WHEN risk_bucket = 'HIGH'  THEN 1 END)     AS high_risk_txns,
  ROUND(
    COUNT(CASE WHEN risk_bucket = 'HIGH' THEN 1 END) * 100.0 / COUNT(*),
  2)                                                    AS fraud_rate_pct,
  MAX(txn_date)                                         AS last_transaction_date
FROM workspace.finance.silver_transactions
GROUP BY merchant_id, merchant_category, mcc_code, merchant_is_high_risk;
