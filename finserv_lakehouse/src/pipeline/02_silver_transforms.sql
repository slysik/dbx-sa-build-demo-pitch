-- Silver: Transactions — Clean, Typed, Deduped
-- SDP Materialized View — serverless pipeline only
-- Reads from bronze_fact_transactions (already broadcast-joined with dims)

CREATE OR REFRESH MATERIALIZED VIEW workspace.finserv.silver_transactions
COMMENT "Cleansed transaction ledger with customer and account attributes."
TBLPROPERTIES ("quality" = "silver", "layer" = "silver")
CLUSTER BY (txn_date, merchant_category)
AS
SELECT
  txn_id,
  account_id,
  customer_id,
  CAST(txn_date          AS DATE)           AS txn_date,
  CAST(amount            AS DECIMAL(12, 2)) AS amount,
  merchant_category,
  txn_type,
  txn_status,
  CAST(risk_score        AS DECIMAL(5, 1))  AS risk_score,
  account_type,
  branch,
  account_status,
  segment,
  risk_tier,
  region,
  -- Derived: high-risk flag
  CASE WHEN risk_score > 60 OR txn_status = 'Flagged' THEN TRUE ELSE FALSE END AS is_high_risk,
  -- Derived: month bucket for time-series aggregation
  DATE_TRUNC('MONTH', txn_date) AS txn_month,
  ingest_ts,
  source_system,
  batch_id
FROM (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY txn_id ORDER BY ingest_ts DESC) AS rn
  FROM workspace.finserv.bronze_fact_transactions
  WHERE txn_id     IS NOT NULL
    AND account_id IS NOT NULL
    AND amount     IS NOT NULL
    AND amount     > 0
    AND txn_date   IS NOT NULL
) deduped
WHERE rn = 1
