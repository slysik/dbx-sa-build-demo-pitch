-- Silver: Clean, deduplicate, and type retail transactions
-- Reads from Bronze Delta → produces curated Silver MV
-- SDP Materialized View — runs inside Lakeflow pipeline only

CREATE OR REFRESH MATERIALIZED VIEW silver_transactions
COMMENT 'Cleaned retail transactions — deduped on transaction_id, nulls handled, typed'
AS
SELECT
  transaction_id,
  product_id,
  store_id,
  category,
  brand,
  product_name,
  region,
  store_format,
  city,
  transaction_date,
  transaction_ts,
  quantity,
  unit_price,
  total_amount,
  payment_method,
  ingest_ts,
  source_system,
  batch_id,
  -- Silver enrichment
  YEAR(transaction_date) AS txn_year,
  MONTH(transaction_date) AS txn_month,
  DAYOFWEEK(transaction_date) AS txn_dow,
  CASE
    WHEN total_amount >= 500 THEN 'High'
    WHEN total_amount >= 100 THEN 'Medium'
    ELSE 'Low'
  END AS spend_tier
FROM (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY ingest_ts DESC) AS rn
  FROM interview.retail.bronze_transactions
  WHERE transaction_id IS NOT NULL
    AND product_id IS NOT NULL
    AND store_id IS NOT NULL
    AND total_amount > 0
)
WHERE rn = 1;
