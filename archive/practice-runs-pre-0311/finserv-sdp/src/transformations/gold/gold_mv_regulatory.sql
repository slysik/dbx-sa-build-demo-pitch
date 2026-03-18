-- =============================================================================
-- GOLD: Materialized Views — Regulatory & Executive Reporting Layer
-- Source : fact_transactions (Gold)
-- Pattern: Pre-aggregated MVs replace SSIS nightly summary jobs
--          Incremental refresh — only recomputes new partitions
--          Serverless SQL Warehouse (Photon + IWM) delivers <2s dashboard response
-- =============================================================================

-- ── 1. Daily Account Exposure (Basel IV capital adequacy) ──────────────────
CREATE OR REFRESH MATERIALIZED VIEW ${gold_schema}.mv_daily_account_exposure
  COMMENT "Daily risk-weighted exposure per account. Feeds Basel IV RWA capital adequacy report. Replaces nightly SSIS aggregate job."
  TBLPROPERTIES ('quality' = 'gold', 'compliance' = 'Basel-IV')
  CLUSTER BY (posting_date, account_id)
AS
SELECT
  posting_date,
  account_id,
  customer_segment,
  country_code,
  COUNT(*)                                          AS transaction_count,
  SUM(amount)                                       AS gross_exposure,
  SUM(risk_weighted_amount)                         AS risk_weighted_exposure,
  AVG(aml_risk_score)                               AS avg_aml_risk_score,
  MAX(aml_risk_score)                               AS max_aml_risk_score,
  -- Basel IV minimum capital requirement: 8% of RWA (Pillar 1)
  SUM(risk_weighted_amount) * 0.08                  AS min_capital_requirement,
  current_timestamp()                               AS mv_refreshed_at
FROM ${gold_schema}.fact_transactions
GROUP BY ALL;


-- ── 2. Monthly Regulatory Summary (SOX + Basel IV) ────────────────────────
CREATE OR REFRESH MATERIALIZED VIEW ${gold_schema}.mv_monthly_regulatory_summary
  COMMENT "Monthly cross-product regulatory summary. Submitted to regulators. Currently a 5-day manual process → target: automated daily refresh."
  TBLPROPERTIES ('quality' = 'gold', 'compliance' = 'SOX,Basel-IV,GDPR')
  CLUSTER BY (posting_year, posting_month)
AS
SELECT
  posting_year,
  posting_month,
  customer_segment,
  mcc_category,
  country_code,
  currency_code,
  COUNT(DISTINCT account_id)                        AS active_accounts,
  COUNT(*)                                          AS total_transactions,
  SUM(amount)                                       AS total_volume,
  SUM(risk_weighted_amount)                         AS total_rwa,
  SUM(risk_weighted_amount) * 0.08                  AS regulatory_capital_required,
  AVG(aml_risk_score)                               AS avg_aml_score,
  -- PCI-DSS: transaction count by channel for fraud monitoring
  SUM(CASE WHEN channel = 'online'  THEN 1 ELSE 0 END) AS online_count,
  SUM(CASE WHEN channel = 'branch'  THEN 1 ELSE 0 END) AS branch_count,
  SUM(CASE WHEN channel = 'mobile'  THEN 1 ELSE 0 END) AS mobile_count,
  current_timestamp()                               AS mv_refreshed_at
FROM ${gold_schema}.fact_transactions
GROUP BY ALL;


-- ── 3. Real-time KPI Dashboard (Executive Layer) ──────────────────────────
CREATE OR REFRESH MATERIALIZED VIEW ${gold_schema}.mv_executive_kpis
  COMMENT "Rolling 30-day executive KPIs. Power BI imports this MV. Replaces VB6 daily email reports. <2s query via Serverless SQL Warehouse + Photon."
  TBLPROPERTIES ('quality' = 'gold')
  CLUSTER BY (snapshot_date)
AS
SELECT
  current_date()                                    AS snapshot_date,
  customer_segment,
  COUNT(DISTINCT account_id)                        AS active_accounts,
  COUNT(*)                                          AS total_transactions_30d,
  SUM(amount)                                       AS total_volume_30d,
  SUM(amount) / COUNT(DISTINCT account_id)          AS avg_revenue_per_account,
  SUM(risk_weighted_amount)                         AS total_rwa_30d,
  -- High-risk flag: accounts with AML score > 7.5 (triggers enhanced monitoring)
  COUNT(DISTINCT CASE WHEN aml_risk_score > 7.5 THEN account_id END) AS high_risk_accounts,
  current_timestamp()                               AS mv_refreshed_at
FROM ${gold_schema}.fact_transactions
WHERE posting_date >= current_date() - 30
GROUP BY ALL;


-- ── 4. GDPR Erasure Compliance View ───────────────────────────────────────
-- Note: This MV supports the right-to-erasure workflow.
-- When a GDPR deletion request is processed in Silver (via DELETE CDC event),
-- fact_transactions must be refreshed — Delta Lake handles this via full MV refresh.
-- Legal hold flag prevents deletion during active regulatory investigation.
CREATE OR REFRESH MATERIALIZED VIEW ${gold_schema}.mv_gdpr_retention_status
  COMMENT "Tracks GDPR data retention status per customer. Supports right-to-erasure workflow and 7-year financial record retention under SOX."
  TBLPROPERTIES ('quality' = 'gold', 'compliance' = 'GDPR,SOX')
AS
SELECT
  customer_id,
  customer_sk,
  country_code,
  MIN(posting_date)                                 AS earliest_transaction_date,
  MAX(posting_date)                                 AS latest_transaction_date,
  COUNT(*)                                          AS total_transactions,
  -- SOX requires 7-year financial record retention
  CASE WHEN MIN(posting_date) < current_date() - (7 * 365)
       THEN 'eligible_for_review'
       ELSE 'within_retention'
  END                                               AS retention_status,
  -- GDPR: Flag EU customers (country_code in EU27)
  CASE WHEN country_code IN (
    'AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE',
    'GR','HU','IE','IT','LV','LT','LU','MT','NL','PL','PT',
    'RO','SK','SI','ES','SE'
  ) THEN TRUE ELSE FALSE END                        AS is_eu_subject,
  current_timestamp()                               AS mv_refreshed_at
FROM ${gold_schema}.fact_transactions
GROUP BY customer_id, customer_sk, country_code;
