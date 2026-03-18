-- Silver: Transactions
-- Deduped on txn_id, typed, null-guarded, explicit columns only
-- Source: workspace.retail.bronze_transactions (already broadcast-joined with dims)

CREATE OR REFRESH MATERIALIZED VIEW workspace.retail.silver_transactions
TBLPROPERTIES (
  "quality" = "silver",
  "layer"   = "silver"
)
AS
SELECT
  txn_id,
  product_id,
  store_id,
  CAST(txn_date        AS DATE)           AS txn_date,
  CAST(quantity        AS INT)            AS quantity,
  CAST(unit_price_sold AS DECIMAL(10, 2)) AS unit_price_sold,
  CAST(discount_pct    AS DECIMAL(5, 2))  AS discount_pct,
  CAST(amount          AS DECIMAL(12, 2)) AS amount,
  -- Dim attributes denormalized for easy Gold aggregation
  COALESCE(category,     'Unknown')       AS category,
  COALESCE(brand,        'Unknown')       AS brand,
  COALESCE(region,       'Unknown')       AS region,
  COALESCE(store_format, 'Unknown')       AS store_format,
  COALESCE(city,         'Unknown')       AS city,
  -- Bronze metadata passthrough
  ingest_ts,
  source_system,
  batch_id
FROM (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY txn_id ORDER BY ingest_ts DESC) AS rn
  FROM workspace.retail.bronze_transactions
  WHERE txn_id IS NOT NULL
    AND amount  IS NOT NULL
    AND amount  > 0
) deduped
WHERE rn = 1
