-- =============================================================================
-- SILVER: Validated & Enriched Transactions
-- Source : bronze_transactions (streaming)
-- Pattern: Streaming table with EXPECT data quality constraints
--          Type-cast, clean, deduplicate, enrich MCC codes
--          PII column mask applied via Unity Catalog (not inline SQL)
-- =============================================================================

CREATE OR REFRESH STREAMING TABLE ${silver_schema}.silver_transactions (
  -- Data quality constraints — WARN keeps record, FAIL drops it
  CONSTRAINT valid_transaction_id   EXPECT (transaction_id IS NOT NULL)           ON VIOLATION DROP ROW,
  CONSTRAINT valid_account_id       EXPECT (account_id IS NOT NULL)                ON VIOLATION DROP ROW,
  CONSTRAINT positive_amount        EXPECT (amount > 0)                            ON VIOLATION DROP ROW,
  CONSTRAINT valid_currency         EXPECT (length(currency_code) = 3)             ON VIOLATION DROP ROW,
  CONSTRAINT valid_mcc              EXPECT (merchant_category_code RLIKE '^[0-9]{4}$') ON VIOLATION WARN,
  CONSTRAINT no_future_transactions EXPECT (transaction_ts <= current_timestamp()) ON VIOLATION WARN
)
COMMENT "Validated, type-cast, DQ-gated transactions. PII (card_last4) masked via Unity Catalog column mask."
TBLPROPERTIES (
  'quality'  = 'silver',
  'pii'      = 'true',           -- UC column mask policy still referenced here
  'layer'    = 'silver'
)
CLUSTER BY (posting_date, account_id)   -- Optimized for account-day grain queries
AS
SELECT
  -- Business keys
  transaction_id,
  account_id,
  customer_id,

  -- Typed & cleaned financial fields
  transaction_type,
  CAST(amount AS DECIMAL(18, 4))        AS amount,
  UPPER(currency_code)                  AS currency_code,
  merchant_id,
  merchant_category_code,
  -- PCI-DSS: UC Column Mask will replace this for non-privileged users
  -- Raw value preserved here for compliance team full-access role
  card_last4,

  -- Temporal
  CAST(transaction_ts AS TIMESTAMP)     AS transaction_ts,
  posting_date,
  YEAR(posting_date)                    AS posting_year,
  MONTH(posting_date)                   AS posting_month,

  -- Enrichments
  channel,
  UPPER(status)                         AS status,
  reference_number,

  -- MCC risk tier — drives Basel IV RWA bucket lookup in Gold
  CASE
    WHEN merchant_category_code IN ('5411','5912','5661') THEN 'retail'
    WHEN merchant_category_code IN ('5812','5813')        THEN 'hospitality'
    WHEN merchant_category_code IN ('4511','7011')        THEN 'travel'
    WHEN merchant_category_code IN ('5999','6011')        THEN 'high_risk'
    ELSE 'general'
  END                                   AS mcc_category,

  -- Lineage metadata
  source_system,
  _source_file,
  _ingested_at,
  current_timestamp()                   AS _silver_ts

FROM STREAM bronze_transactions    -- unqualified = pipeline default catalog/bronze schema
WHERE _rescued_data IS NULL;       -- quarantined records already separated at Bronze
