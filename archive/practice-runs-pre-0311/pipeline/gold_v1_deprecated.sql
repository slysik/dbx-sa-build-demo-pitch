-- ============================================================================
-- GOLD LAYER — Business-ready aggregations for BI/serving.
-- Pre-aggregated, stable contracts, consumption-shaped.
-- ============================================================================

-- Gold: Daily Sales Summary
-- KPI: revenue, order count, avg order value by date/channel
CREATE OR REFRESH MATERIALIZED VIEW gold_daily_sales
CLUSTER BY (order_date)
COMMENT 'Daily sales KPIs by date and channel — BI-ready'
AS
SELECT
  o.order_date,
  o.channel,
  COUNT(DISTINCT o.order_id)            AS order_count,
  COUNT(DISTINCT o.customer_id)         AS unique_customers,
  SUM(oi.line_total)                    AS total_revenue,
  ROUND(SUM(oi.line_total) / COUNT(DISTINCT o.order_id), 2) AS avg_order_value,
  SUM(oi.quantity)                      AS total_units_sold
FROM silver_orders o
INNER JOIN silver_order_items oi
  ON regexp_extract(o.order_id, '^(ORD-\\d+)', 1) = oi.order_id
GROUP BY o.order_date, o.channel;


-- Gold: Product Performance
-- KPI: revenue, units, margin by product and category
CREATE OR REFRESH MATERIALIZED VIEW gold_product_performance
CLUSTER BY (category)
COMMENT 'Product-level revenue, units, and margin — category rollup ready'
AS
SELECT
  p.product_id,
  p.product_name,
  p.category,
  p.unit_price                                          AS list_price,
  p.cost_price,
  COUNT(DISTINCT oi.order_id)                           AS order_count,
  SUM(oi.quantity)                                      AS total_units_sold,
  SUM(oi.line_total)                                    AS total_revenue,
  ROUND(SUM(oi.line_total) - SUM(oi.quantity * p.cost_price), 2) AS gross_margin,
  ROUND(
    (SUM(oi.line_total) - SUM(oi.quantity * p.cost_price))
    / NULLIF(SUM(oi.line_total), 0) * 100, 1
  )                                                     AS margin_pct
FROM silver_order_items oi
INNER JOIN silver_products p ON oi.product_id = p.product_id
INNER JOIN silver_orders o
  ON regexp_extract(o.order_id, '^(ORD-\\d+)', 1) = oi.order_id
GROUP BY p.product_id, p.product_name, p.category, p.unit_price, p.cost_price;


-- Gold: Customer Lifetime Value
-- KPI: spend, frequency, recency per customer
CREATE OR REFRESH MATERIALIZED VIEW gold_customer_ltv
CLUSTER BY (loyalty_tier, region)
COMMENT 'Customer lifetime value metrics — segmentation ready'
AS
SELECT
  c.customer_id,
  c.first_name,
  c.last_name,
  c.region,
  c.loyalty_tier,
  c.signup_date,
  COUNT(DISTINCT o.order_id)                            AS total_orders,
  SUM(oi.line_total)                                    AS total_spend,
  ROUND(SUM(oi.line_total) / NULLIF(COUNT(DISTINCT o.order_id), 0), 2) AS avg_order_value,
  MIN(o.order_date)                                     AS first_order_date,
  MAX(o.order_date)                                     AS last_order_date,
  DATEDIFF(CURRENT_DATE(), MAX(o.order_date))           AS days_since_last_order
FROM silver_customers c
LEFT JOIN silver_orders o ON c.customer_id = o.customer_id
LEFT JOIN silver_order_items oi
  ON regexp_extract(o.order_id, '^(ORD-\\d+)', 1) = oi.order_id
GROUP BY c.customer_id, c.first_name, c.last_name, c.region,
         c.loyalty_tier, c.signup_date;


-- Gold: Regional Summary
-- KPI: revenue, orders, customers by region — exec dashboard ready
CREATE OR REFRESH MATERIALIZED VIEW gold_regional_summary
CLUSTER BY (region)
COMMENT 'Regional performance summary — executive dashboard'
AS
SELECT
  c.region,
  o.order_date,
  COUNT(DISTINCT o.order_id)            AS order_count,
  COUNT(DISTINCT o.customer_id)         AS active_customers,
  SUM(oi.line_total)                    AS total_revenue,
  ROUND(AVG(oi.line_total), 2)          AS avg_item_value
FROM silver_orders o
INNER JOIN silver_customers c ON o.customer_id = c.customer_id
INNER JOIN silver_order_items oi
  ON regexp_extract(o.order_id, '^(ORD-\\d+)', 1) = oi.order_id
GROUP BY c.region, o.order_date;
