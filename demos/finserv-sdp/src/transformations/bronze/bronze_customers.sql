-- =============================================================================
-- BRONZE: Raw Customer Records
-- Source : ADLS Gen2 landing zone (Temenos + Fiserv loan origination CDC)
-- Pattern: Auto Loader streaming table — append-only
-- =============================================================================

CREATE OR REFRESH STREAMING TABLE bronze_customers
  COMMENT "Raw customer master records from core banking. PII present — downstream Silver applies column masks."
  TBLPROPERTIES (
    'quality'           = 'bronze',
    'pii'               = 'true',
    'source_system'     = 'temenos',
    'delta.enableChangeDataFeed' = 'true'
  )
  CLUSTER BY (ingestion_date)
AS
SELECT
  customer_id,
  first_name,
  last_name,
  email,
  phone_number,
  date_of_birth,
  national_id,                -- GDPR: highly sensitive — masked at Silver
  address_line1,
  address_line2,
  city,
  state_province,
  postal_code,
  country_code,               -- Drives row-filter policy by region (GDPR EU, etc.)
  customer_segment,
  relationship_manager_id,
  kyc_status,
  aml_risk_score,
  onboarded_date,
  last_updated_ts,            -- Sequence key for SCD Type 2 in Silver
  operation_type,             -- INSERT / UPDATE / DELETE from CDC
  -- Metadata
  _metadata.file_path        AS _source_file,
  current_timestamp()        AS _ingested_at,
  current_date()             AS ingestion_date
FROM STREAM read_files(
  '${customers_landing}',
  format      => 'parquet',
  schemaHints => '
    customer_id            STRING,
    first_name             STRING,
    last_name              STRING,
    email                  STRING,
    phone_number           STRING,
    date_of_birth          DATE,
    national_id            STRING,
    address_line1          STRING,
    address_line2          STRING,
    city                   STRING,
    state_province         STRING,
    postal_code            STRING,
    country_code           STRING,
    customer_segment       STRING,
    relationship_manager_id STRING,
    kyc_status             STRING,
    aml_risk_score         DOUBLE,
    onboarded_date         DATE,
    last_updated_ts        TIMESTAMP,
    operation_type         STRING
  ',
  mode => 'PERMISSIVE'
);
