-- =============================================================================
-- GOLD: dim_customer — Conformed Customer Dimension
-- Source : silver_customers (SCD Type 2 history table)
-- Pattern: Materialized View — current-state view for BI tools
--          __END_AT IS NULL = currently active version of each customer
--          PBI / Tableau users always see present state; analysts query Silver for history
-- =============================================================================

CREATE OR REFRESH MATERIALIZED VIEW ${gold_schema}.dim_customer
  COMMENT "Current-state customer dimension for BI tools. One row per customer. PII masked via Unity Catalog column masks."
  TBLPROPERTIES (
    'quality' = 'gold',
    'layer'   = 'gold'
  )
AS
SELECT
  -- Surrogate key (use monotonically_increasing_id or hash for deterministic SK)
  hash(customer_id)                     AS customer_sk,

  -- Business / natural key
  customer_id,

  -- PII fields — Unity Catalog column masks enforce masking for non-privileged roles:
  --   • Compliance analysts: full value
  --   • BI developers: SHA-256 hash  
  --   • All others: '***MASKED***'
  first_name,
  last_name,
  email,
  phone_number,
  date_of_birth,
  national_id,

  -- Geography — used by GDPR row filter policy (EU customers: country_code IN EU set)
  address_line1,
  city,
  state_province,
  postal_code,
  country_code,

  -- Segmentation & risk
  customer_segment,
  relationship_manager_id,
  kyc_status,
  aml_risk_score,

  -- Dates
  onboarded_date,
  __START_AT                            AS effective_from,   -- When this version became active
  last_updated_ts,

  -- SCD metadata (useful for BI tools doing incremental refresh)
  TRUE                                  AS is_current

FROM ${silver_schema}.silver_customers
WHERE __END_AT IS NULL;   -- Current active version only (SCD Type 2 pattern)
