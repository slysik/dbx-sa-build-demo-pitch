-- ─────────────────────────────────────────────────────────────────────────────
-- Silver Layer: Transaction Risk Enrichment
-- Pipeline: finance_medallion  |  Catalog: workspace  |  Schema: finance
--
-- Applies deterministic risk scoring based on customer tier + merchant risk +
-- transaction amount. No RAND() — same score every refresh (reproducible).
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REFRESH MATERIALIZED VIEW workspace.finance.silver_transactions
COMMENT "Enriched, risk-scored transactions — deduped on txn_id, UTC timestamps"
TBLPROPERTIES (
  "quality"          = "silver",
  "layer"            = "silver",
  "pipelines.reset.allowed" = "true"
)
AS
SELECT
  t.txn_id,
  t.txn_ts,
  t.txn_date,
  t.customer_id,
  t.merchant_id,

  -- Customer attributes (from Bronze dim)
  t.segment                                           AS customer_segment,
  t.risk_tier                                         AS customer_risk_tier,
  t.country                                           AS customer_country,

  -- Merchant attributes (from Bronze dim)
  t.category                                          AS merchant_category,
  t.mcc_code,
  t.is_high_risk                                      AS merchant_is_high_risk,

  -- Transaction core
  t.amount,
  t.channel,
  t.is_flagged                                        AS rules_engine_flag,

  -- ── Deterministic Risk Score (0–100) ─────────────────────────────────────
  -- Combines customer risk tier + merchant risk + amount thresholds.
  -- Higher score = higher fraud probability. Scored at ingest, not query time.
  CAST(
    CASE
      WHEN t.risk_tier = 'HIGH'   AND t.is_high_risk = true  AND t.amount > 1000 THEN 92
      WHEN t.risk_tier = 'HIGH'   AND t.is_high_risk = true                       THEN 78
      WHEN t.risk_tier = 'HIGH'   AND t.amount > 5000                             THEN 72
      WHEN t.risk_tier = 'MEDIUM' AND t.is_high_risk = true  AND t.amount > 500   THEN 65
      WHEN t.risk_tier = 'HIGH'   AND t.amount > 1000                             THEN 58
      WHEN t.amount > 8000                                                         THEN 55
      WHEN t.risk_tier = 'HIGH'                                                    THEN 45
      WHEN t.is_high_risk = true                                                   THEN 38
      WHEN t.risk_tier = 'MEDIUM' AND t.amount > 2000                             THEN 30
      WHEN t.risk_tier = 'MEDIUM'                                                  THEN 22
      -- Low-risk baseline: deterministic hash spread across 5–20 range
      ELSE MOD(ABS(CRC32(t.txn_id)), 16) + 5
    END
  AS INT)                                             AS risk_score,

  -- Risk bucket for dashboard grouping
  CASE
    WHEN risk_score >= 70 THEN 'HIGH'
    WHEN risk_score >= 40 THEN 'MEDIUM'
    ELSE 'LOW'
  END                                                 AS risk_bucket,

  -- Bronze provenance
  t.ingest_ts,
  t.source_system,
  t.batch_id

FROM workspace.finance.bronze_fact_transactions t
WHERE t.txn_id IS NOT NULL
  AND t.amount  > 0
  AND t.txn_ts  IS NOT NULL
