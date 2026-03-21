-- Gold: Pre-aggregated business metrics for BI consumption
-- Reads from Silver MV → produces Gold MVs
-- SDP Materialized Views — runs inside Lakeflow pipeline only

-- Gold 1: Sales by Product Category
CREATE OR REFRESH MATERIALIZED VIEW gold_sales_by_category
COMMENT 'Revenue and volume by product category and month'
AS
SELECT
  category,
  txn_year,
  txn_month,
  COUNT(*) AS transaction_count,
  SUM(quantity) AS total_units,
  ROUND(SUM(total_amount), 2) AS total_revenue,
  ROUND(AVG(total_amount), 2) AS avg_transaction_value,
  COUNT(DISTINCT product_id) AS unique_products,
  COUNT(DISTINCT store_id) AS unique_stores
FROM interview.retail.silver_transactions
GROUP BY category, txn_year, txn_month;

-- Gold 2: Sales by Store Region
CREATE OR REFRESH MATERIALIZED VIEW gold_sales_by_store
COMMENT 'Revenue and performance by store region and format'
AS
SELECT
  region,
  store_format,
  city,
  txn_year,
  txn_month,
  COUNT(*) AS transaction_count,
  SUM(quantity) AS total_units,
  ROUND(SUM(total_amount), 2) AS total_revenue,
  ROUND(AVG(total_amount), 2) AS avg_transaction_value,
  COUNT(DISTINCT product_id) AS products_sold,
  ROUND(SUM(CASE WHEN spend_tier = 'High' THEN total_amount ELSE 0 END), 2) AS high_value_revenue
FROM interview.retail.silver_transactions
GROUP BY region, store_format, city, txn_year, txn_month;

-- Gold 3: Daily Revenue Trend
CREATE OR REFRESH MATERIALIZED VIEW gold_daily_revenue
COMMENT 'Daily revenue trend with running totals'
AS
SELECT
  transaction_date,
  txn_year,
  txn_month,
  txn_dow,
  COUNT(*) AS transaction_count,
  SUM(quantity) AS total_units,
  ROUND(SUM(total_amount), 2) AS daily_revenue,
  ROUND(AVG(total_amount), 2) AS avg_basket_size,
  COUNT(DISTINCT store_id) AS active_stores,
  COUNT(DISTINCT product_id) AS products_sold,
  -- Payment mix
  SUM(CASE WHEN payment_method = 'Credit Card' THEN 1 ELSE 0 END) AS credit_card_txns,
  SUM(CASE WHEN payment_method = 'Digital Wallet' THEN 1 ELSE 0 END) AS digital_wallet_txns
FROM interview.retail.silver_transactions
GROUP BY transaction_date, txn_year, txn_month, txn_dow;
