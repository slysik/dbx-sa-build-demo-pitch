-- ============================================================================
-- BRONZE LAYER — Raw ingestion from Volume. No business logic. Append metadata.
-- ============================================================================

-- Bronze: Customers
CREATE OR REFRESH MATERIALIZED VIEW bronze_customers
CLUSTER BY (customer_id)
COMMENT 'Raw customer dimension from landing zone'
AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  'raw_data/customers' AS _source
FROM read_files(
  '/Volumes/interview/retail/raw_data/customers',
  format => 'parquet'
);

-- Bronze: Products
CREATE OR REFRESH MATERIALIZED VIEW bronze_products
CLUSTER BY (product_id)
COMMENT 'Raw product dimension from landing zone'
AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  'raw_data/products' AS _source
FROM read_files(
  '/Volumes/interview/retail/raw_data/products',
  format => 'parquet'
);

-- Bronze: Orders (1M rows)
CREATE OR REFRESH MATERIALIZED VIEW bronze_orders
CLUSTER BY (order_timestamp)
COMMENT 'Raw order facts from landing zone — 1M rows'
AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  'raw_data/orders' AS _source
FROM read_files(
  '/Volumes/interview/retail/raw_data/orders',
  format => 'parquet'
);

-- Bronze: Order Items
CREATE OR REFRESH MATERIALIZED VIEW bronze_order_items
CLUSTER BY (order_id)
COMMENT 'Raw order line items from landing zone'
AS
SELECT
  *,
  current_timestamp() AS _ingested_at,
  'raw_data/order_items' AS _source
FROM read_files(
  '/Volumes/interview/retail/raw_data/order_items',
  format => 'parquet'
);
