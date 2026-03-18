-- ============================================================================
-- SILVER LAYER — Cleaned, typed, deduped, quality-enforced.
-- Reusable business semantics. Explicit column contracts.
--
-- Bronze tables are managed Delta tables written by the data gen notebook.
-- This SDP reads from bronze and applies:
--   1. Dedup via ROW_NUMBER (deterministic, idempotent)
--   2. Explicit CAST on every column (schema contract)
--   3. Expectations with ON VIOLATION DROP ROW (quality gate)
--   4. COALESCE for null handling
--   5. Liquid Clustering on query-aligned keys
--
-- LIQUID CLUSTERING strategy (Silver):
--   CLUSTER BY keys match downstream Gold join/filter patterns:
--     - silver_customers:    (region, loyalty_tier) → segmentation queries
--     - silver_products:     (category)             → category rollups
--     - silver_orders:       (order_date, channel)  → time-series + channel
--     - silver_order_items:  (order_id)             → co-locate for order join
--
--   Keys are MUTABLE if access patterns evolve:
--     ALTER TABLE interview.retail.silver_orders CLUSTER BY (customer_id, order_date);
--     -- New writes instantly use the new layout. No full rewrite.
-- ============================================================================


-- Silver: Customers — dedup on customer_id, null handling, type enforcement
CREATE OR REFRESH MATERIALIZED VIEW silver_customers(
  CONSTRAINT valid_customer_id EXPECT (customer_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_signup       EXPECT (signup_date IS NOT NULL) ON VIOLATION DROP ROW
)
CLUSTER BY (region, loyalty_tier)
COMMENT 'Cleaned customer dimension — deduped, nulls handled, schema enforced'
AS
SELECT
  CAST(customer_id AS STRING)    AS customer_id,
  CAST(first_name AS STRING)     AS first_name,
  CAST(last_name AS STRING)      AS last_name,
  COALESCE(email, 'unknown@missing.com') AS email,
  CAST(region AS STRING)         AS region,
  CAST(loyalty_tier AS STRING)   AS loyalty_tier,
  CAST(signup_date AS DATE)      AS signup_date
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY customer_id) AS _rn
  FROM interview.retail.bronze_customers
)
WHERE _rn = 1;


-- Silver: Products — dedup on product_id, enforce positive prices
CREATE OR REFRESH MATERIALIZED VIEW silver_products(
  CONSTRAINT valid_product_id EXPECT (product_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_price      EXPECT (unit_price > 0)         ON VIOLATION DROP ROW,
  CONSTRAINT valid_cost       EXPECT (cost_price > 0)         ON VIOLATION DROP ROW
)
CLUSTER BY (category)
COMMENT 'Cleaned product dimension — valid prices, deduped'
AS
SELECT
  CAST(product_id AS STRING)       AS product_id,
  CAST(product_name AS STRING)     AS product_name,
  CAST(category AS STRING)         AS category,
  CAST(unit_price AS DECIMAL(10,2))  AS unit_price,
  CAST(cost_price AS DECIMAL(10,2))  AS cost_price
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY product_id) AS _rn
  FROM interview.retail.bronze_products
)
WHERE _rn = 1;


-- Silver: Orders — deterministic dedup on order_id, derive order_date
CREATE OR REFRESH MATERIALIZED VIEW silver_orders(
  CONSTRAINT valid_order_id    EXPECT (order_id IS NOT NULL)        ON VIOLATION DROP ROW,
  CONSTRAINT valid_customer_id EXPECT (customer_id IS NOT NULL)     ON VIOLATION DROP ROW,
  CONSTRAINT valid_timestamp   EXPECT (order_timestamp IS NOT NULL) ON VIOLATION DROP ROW
)
CLUSTER BY (order_date, channel)
COMMENT 'Cleaned order facts — deduped on order_id, typed, ~1M rows'
AS
SELECT
  CAST(order_id AS STRING)            AS order_id,
  CAST(customer_id AS STRING)         AS customer_id,
  CAST(order_timestamp AS TIMESTAMP)  AS order_timestamp,
  CAST(order_timestamp AS DATE)       AS order_date,
  CAST(channel AS STRING)             AS channel,
  CAST(payment_method AS STRING)      AS payment_method,
  CAST(status AS STRING)              AS status,
  CAST(store_id AS STRING)            AS store_id
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY order_timestamp ASC) AS _rn
  FROM interview.retail.bronze_orders
)
WHERE _rn = 1;


-- Silver: Order Items — dedup on item_id, filter outliers, enforce positives
CREATE OR REFRESH MATERIALIZED VIEW silver_order_items(
  CONSTRAINT valid_item_id    EXPECT (item_id IS NOT NULL)                        ON VIOLATION DROP ROW,
  CONSTRAINT valid_order_id   EXPECT (order_id IS NOT NULL)                       ON VIOLATION DROP ROW,
  CONSTRAINT valid_product_id EXPECT (product_id IS NOT NULL)                     ON VIOLATION DROP ROW,
  CONSTRAINT positive_qty     EXPECT (quantity > 0)                               ON VIOLATION DROP ROW,
  CONSTRAINT valid_line_total EXPECT (line_total > 0 AND line_total < 50000)      ON VIOLATION DROP ROW
)
CLUSTER BY (order_id)
COMMENT 'Cleaned order line items — outliers filtered, typed, FK-safe'
AS
SELECT
  CAST(item_id AS STRING)              AS item_id,
  CAST(order_id AS STRING)             AS order_id,
  CAST(product_id AS STRING)           AS product_id,
  CAST(quantity AS INT)                AS quantity,
  CAST(unit_price AS DECIMAL(10,2))    AS unit_price,
  CAST(discount_pct AS DECIMAL(5,2))   AS discount_pct,
  CAST(line_total AS DECIMAL(12,2))    AS line_total
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY item_id ORDER BY item_id) AS _rn
  FROM interview.retail.bronze_order_items
)
WHERE _rn = 1;
