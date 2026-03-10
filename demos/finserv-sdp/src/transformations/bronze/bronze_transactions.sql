-- =============================================================================
-- BRONZE: Raw Financial Transactions
-- Source : ADLS Gen2 landing zone (Temenos core banking CDC export)
-- Pattern: Auto Loader streaming table — append-only, schema-on-read
-- =============================================================================

CREATE OR REFRESH STREAMING TABLE bronze_transactions
  COMMENT "Raw transaction events from Temenos core banking. Append-only. PII unmasked — restrict access via Unity Catalog."
  TBLPROPERTIES (
    'quality'           = 'bronze',
    'pii'               = 'true',           -- UC column masks apply downstream
    'source_system'     = 'temenos',
    'delta.enableChangeDataFeed' = 'true'   -- required for downstream Silver MV refresh
  )
  CLUSTER BY (ingestion_date, source_system)    -- Liquid Clustering for time-windowed audit queries
AS
SELECT
  -- Raw business columns (schema hints enforce critical types; rest inferred)
  transaction_id,
  account_id,
  customer_id,
  transaction_type,
  amount,
  currency_code,
  merchant_id,
  merchant_category_code,    -- MCC — critical for PCI-DSS and fraud scoring
  card_last4,                -- PCI-DSS: store only last 4 digits
  transaction_ts,
  posting_date,
  channel,
  status,
  reference_number,
  -- Auto Loader metadata — essential for debugging and lineage
  _metadata.file_path        AS _source_file,
  _metadata.file_modification_time AS _file_ts,
  current_timestamp()        AS _ingested_at,
  current_date()             AS ingestion_date,
  'temenos'                  AS source_system
FROM STREAM read_files(
  '${transactions_landing}',
  format        => 'parquet',
  -- Explicit schema hints for critical financial fields — prevents type drift
  schemaHints   => '
    transaction_id    STRING,
    account_id        STRING,
    customer_id       STRING,
    transaction_type  STRING,
    amount            DECIMAL(18, 4),
    currency_code     STRING,
    merchant_id       STRING,
    merchant_category_code STRING,
    card_last4        STRING,
    transaction_ts    TIMESTAMP,
    posting_date      DATE,
    channel           STRING,
    status            STRING,
    reference_number  STRING
  ',
  mode          => 'PERMISSIVE'    -- Rescues malformed records to _rescued_data
);

-- =============================================================================
-- BRONZE: Quarantine — malformed / rescued records
-- Ops team investigates; never blocks the main pipeline
-- =============================================================================

CREATE OR REFRESH STREAMING TABLE bronze_transactions_quarantine
  COMMENT "Malformed transaction records rescued by Auto Loader. Ops team investigates."
  TBLPROPERTIES ('quality' = 'quarantine')
AS
SELECT *
FROM STREAM bronze_transactions
WHERE _rescued_data IS NOT NULL;
