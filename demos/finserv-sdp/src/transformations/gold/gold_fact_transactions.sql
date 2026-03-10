-- =============================================================================
-- GOLD: fact_transactions — Core Transaction Fact Table
-- Source : silver_transactions + gold dim_customer (conformed dimension join)
-- Pattern: Materialized View with Liquid Clustering
--          Photon-optimized star-schema join
--          Basel IV: RWA bucket assigned at fact grain
-- =============================================================================

CREATE OR REFRESH MATERIALIZED VIEW ${gold_schema}.fact_transactions
  COMMENT "Transaction fact at atomic grain. Liquid Clustered on (posting_date, account_id) for time-range + account queries. Basel IV RWA bucket assigned."
  TBLPROPERTIES (
    'quality'        = 'gold',
    'layer'          = 'gold',
    'compliance'     = 'GDPR,PCI-DSS,Basel-IV',
    'photon_hint'    = 'true'
  )
  CLUSTER BY (posting_date, account_id)   -- Top query patterns: date range + account
AS
SELECT
  -- Surrogate keys (Kimball pattern)
  t.transaction_id,
  t.account_id,
  hash(t.customer_id)                   AS customer_sk,      -- FK → dim_customer
  to_date(t.posting_date)               AS date_id,          -- FK → dim_date (built separately)

  -- Measures
  t.amount,
  t.currency_code,

  -- Degenerate dimensions (high-cardinality, no separate dim table needed)
  t.transaction_type,
  t.merchant_id,
  t.merchant_category_code,
  t.mcc_category,
  t.channel,
  t.status,
  t.reference_number,

  -- Basel IV: Risk-Weighted Asset bucket (drives capital adequacy calc)
  -- RWA weight per BIS CRE20 standardised approach
  CASE
    WHEN t.mcc_category = 'high_risk'                THEN 1.50   -- 150% risk weight
    WHEN t.mcc_category IN ('retail','hospitality')  THEN 0.75   -- 75% retail exposure
    WHEN t.mcc_category = 'travel'                   THEN 1.00   -- 100% corporate exposure
    ELSE                                                   0.85   -- 85% general
  END                                                AS rwa_weight,

  t.amount * CASE
    WHEN t.mcc_category = 'high_risk'                THEN 1.50
    WHEN t.mcc_category IN ('retail','hospitality')  THEN 0.75
    WHEN t.mcc_category = 'travel'                   THEN 1.00
    ELSE                                                   0.85
  END                                                AS risk_weighted_amount,

  -- Denormalised customer attributes (avoid join at query time for BI tools)
  c.customer_segment,
  c.country_code,
  c.kyc_status,
  c.aml_risk_score,

  -- Temporal
  t.transaction_ts,
  t.posting_date,
  t.posting_year,
  t.posting_month,

  -- Lineage
  t.source_system,
  t._ingested_at

FROM ${silver_schema}.silver_transactions t

-- Point-in-time join: get the customer version that was active at transaction time
-- This prevents "retroactive update" problem where a customer address change
-- would alter the historical risk profile of old transactions
LEFT JOIN ${silver_schema}.silver_customers c
  ON  t.customer_id  = c.customer_id
  AND t.transaction_ts >= c.__START_AT
  AND (t.transaction_ts  < c.__END_AT OR c.__END_AT IS NULL);
