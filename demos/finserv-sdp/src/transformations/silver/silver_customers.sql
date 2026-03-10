-- =============================================================================
-- SILVER: Customer Dimension — SCD Type 2 (History Tracking)
-- Source : bronze_customers (CDC events with operation_type: INSERT/UPDATE/DELETE)
-- Pattern: AUTO CDC INTO with STORED AS SCD TYPE 2
--          - Tracks full address, segment, KYC, AML score history
--          - Handles out-of-order CDC events via SEQUENCE BY last_updated_ts
--          - __START_AT / __END_AT added automatically by SDP
-- =============================================================================

-- Step 1: Streaming table as AUTO CDC target (SDP requires explicit declaration)
CREATE OR REFRESH STREAMING TABLE ${silver_schema}.silver_customers
  COMMENT "Customer master with full SCD Type 2 history. PII masked via Unity Catalog column masks. GDPR row filter by country_code."
  TBLPROPERTIES (
    'quality'  = 'silver',
    'pii'      = 'true',
    'layer'    = 'silver'
  )
  CLUSTER BY (customer_id);     -- Business key — most common filter in joins

-- Step 2: AUTO CDC flow — replaces 500 lines of MERGE + watermark logic
CREATE FLOW silver_customers_cdc
AUTO CDC INTO ${silver_schema}.silver_customers
FROM STREAM bronze_customers
KEYS                (customer_id)
IGNORE NULL UPDATES
APPLY AS DELETE WHEN (operation_type = 'DELETE')
SEQUENCE BY         last_updated_ts        -- Handles late-arriving CDC events correctly
STORED AS SCD TYPE 2                       -- Adds __START_AT, __END_AT per version
TRACK HISTORY ON *                         -- Track all column changes (address, segment, KYC, AML)
COLUMNS * EXCEPT    (operation_type, _source_file, _ingested_at, ingestion_date);
-- ^ Strip pipeline-internal metadata from the history table; they don't represent business state

-- =============================================================================
-- INTERVIEWER TALKING POINT
-- =============================================================================
-- "The declarative AUTO CDC replaces complex MERGE + watermark logic.
--  SEQUENCE BY handles late-arriving records automatically — something you'd
--  need to build a stateful streaming job to manage manually in SSIS or Spark.
--  For a 30-year-old bank with address changes going back decades, SCD Type 2
--  means we can answer 'What was this customer's address on 2019-03-15?' with
--  a single WHERE __START_AT <= '2019-03-15' AND __END_AT > '2019-03-15'."
-- =============================================================================
