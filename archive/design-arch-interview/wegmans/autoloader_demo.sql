-- Auto Loader Demo: Ingest Parquet files from landing volume into Delta Lake
-- This uses read_files() (SQL Auto Loader) to incrementally process new files

CREATE OR REFRESH STREAMING TABLE bronze_retail_transactions
CLUSTER BY (transaction_date, department)
COMMENT 'Raw retail transactions ingested via Auto Loader from Parquet files'
AS
SELECT
  transaction_id,
  customer_id,
  store_name,
  department,
  amount,
  quantity,
  CAST(transaction_date AS DATE) AS transaction_date,
  payment_method,
  current_timestamp() AS _ingested_at,
  _metadata.file_path AS _source_file
FROM STREAM read_files(
  '/Volumes/dbx_weg/bronze/landing/transactions',
  format => 'parquet'
);
