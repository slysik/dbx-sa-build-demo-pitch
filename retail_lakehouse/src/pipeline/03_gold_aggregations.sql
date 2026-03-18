-- Gold: Sales by Category (pre-aggregated for BI)
-- ~72 rows (6 categories × 12 months)

CREATE OR REFRESH MATERIALIZED VIEW workspace.retail.gold_sales_by_category
TBLPROPERTIES (
  "quality" = "gold",
  "layer"   = "gold"
)
AS
SELECT
  category,
  YEAR(txn_date)                     AS txn_year,
  MONTH(txn_date)                    AS txn_month,
  COUNT(*)                           AS txn_count,
  SUM(quantity)                      AS total_units,
  ROUND(SUM(amount), 2)              AS total_revenue,
  ROUND(AVG(amount), 2)              AS avg_order_value,
  ROUND(AVG(discount_pct) * 100, 1) AS avg_discount_pct
FROM workspace.retail.silver_transactions
GROUP BY category, YEAR(txn_date), MONTH(txn_date)
;

-- Gold: Sales by Store (pre-aggregated for BI)
-- ~300 rows (50 stores × 12 months, or region/format × months)

CREATE OR REFRESH MATERIALIZED VIEW workspace.retail.gold_sales_by_store
TBLPROPERTIES (
  "quality" = "gold",
  "layer"   = "gold"
)
AS
SELECT
  store_id,
  region,
  store_format,
  city,
  YEAR(txn_date)                     AS txn_year,
  MONTH(txn_date)                    AS txn_month,
  COUNT(*)                           AS txn_count,
  SUM(quantity)                      AS total_units,
  ROUND(SUM(amount), 2)              AS total_revenue,
  ROUND(AVG(amount), 2)              AS avg_order_value
FROM workspace.retail.silver_transactions
GROUP BY store_id, region, store_format, city, YEAR(txn_date), MONTH(txn_date)
;

-- Gold: Daily Revenue (365 rows — one per day)

CREATE OR REFRESH MATERIALIZED VIEW workspace.retail.gold_daily_revenue
TBLPROPERTIES (
  "quality" = "gold",
  "layer"   = "gold"
)
AS
SELECT
  txn_date,
  COUNT(*)              AS txn_count,
  SUM(quantity)         AS total_units,
  ROUND(SUM(amount), 2) AS total_revenue,
  ROUND(AVG(amount), 2) AS avg_order_value
FROM workspace.retail.silver_transactions
GROUP BY txn_date
ORDER BY txn_date
