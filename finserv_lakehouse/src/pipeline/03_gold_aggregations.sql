-- =============================================================================
-- Gold Layer — Apex Banking Customer 360
-- Pipeline: banking_medallion | finserv.banking
--
-- Key pattern: aggregate each source independently, then join aggregates.
-- Never join raw transactions to raw interactions — that creates row fanout.
-- =============================================================================


-- ── gold_rfm_features ─────────────────────────────────────────────────────────
-- Per-customer RFM feature store feeding the churn model.
-- Two CTEs aggregated separately, joined on customer_id — no fanout.

CREATE OR REFRESH MATERIALIZED VIEW finserv.banking.gold_rfm_features
  COMMENT "Per-customer RFM feature store. Aggregated from transactions and CRM interactions independently to avoid join fanout. Input to churn prediction model."
TBLPROPERTIES ("quality" = "gold", "layer" = "feature-store")
AS
WITH txn_agg AS (
  SELECT
    customer_id,
    MAX(txn_date)                                    AS last_txn_date,
    DATEDIFF(CURRENT_DATE(), MAX(txn_date))           AS days_since_last_txn,
    COUNT(DISTINCT txn_id)                            AS txn_count,
    COUNT(DISTINCT txn_month)                         AS active_months,
    COUNT(DISTINCT account_id)                        AS account_count,
    CAST(SUM(amount)  AS DECIMAL(18,2))               AS total_amount,
    CAST(AVG(amount)  AS DECIMAL(10,2))               AS avg_txn_amount,
    CAST(MAX(amount)  AS DECIMAL(10,2))               AS max_txn_amount,
    COUNT(CASE WHEN txn_status = 'FAILED' THEN 1 END) AS failed_txn_count,
    COUNT(DISTINCT channel)                           AS channel_diversity
  FROM finserv.banking.silver_transactions
  GROUP BY customer_id
),
int_agg AS (
  SELECT
    customer_id,
    COUNT(DISTINCT interaction_id)                                         AS interaction_count,
    SUM(CASE WHEN interaction_category = 'complaint'  THEN 1 ELSE 0 END)  AS complaint_count,
    SUM(CASE WHEN interaction_category = 'escalation' THEN 1 ELSE 0 END)  AS escalation_count,
    SUM(CASE WHEN interaction_category = 'praise'     THEN 1 ELSE 0 END)  AS praise_count,
    AVG(CASE
      WHEN sentiment = 'positive' THEN  1.0
      WHEN sentiment = 'negative' THEN -1.0
      WHEN sentiment = 'mixed'    THEN -0.3
      ELSE 0.0
    END)                                                                   AS avg_sentiment_score
  FROM finserv.banking.silver_interactions
  GROUP BY customer_id
)
SELECT
  t.customer_id,
  t.last_txn_date,
  t.days_since_last_txn,
  t.txn_count,
  t.active_months,
  t.account_count,
  t.total_amount,
  t.avg_txn_amount,
  t.max_txn_amount,
  t.failed_txn_count,
  t.channel_diversity,
  COALESCE(i.interaction_count,  0)    AS interaction_count,
  COALESCE(i.complaint_count,    0)    AS complaint_count,
  COALESCE(i.escalation_count,   0)    AS escalation_count,
  COALESCE(i.praise_count,       0)    AS praise_count,
  COALESCE(i.avg_sentiment_score, 0.0) AS avg_sentiment_score
FROM txn_agg t
LEFT JOIN int_agg i ON t.customer_id = i.customer_id;


-- ── gold_churn_risk ───────────────────────────────────────────────────────────
-- Churn score 0–100 and tier per customer.
-- Each scoring component is independently interpretable for relationship managers.

CREATE OR REFRESH MATERIALIZED VIEW finserv.banking.gold_churn_risk
  COMMENT "Customer churn risk score (0-100) and tier. Rule-based scoring in pipeline; production replaces with registered MLflow model invoked as SQL UDF."
TBLPROPERTIES ("quality" = "gold", "layer" = "ml-scoring")
AS
WITH scored AS (
  SELECT
    f.customer_id,
    c.segment,
    c.region,
    c.risk_tier          AS profile_risk_tier,
    c.tenure_years,
    c.age_band,
    f.txn_count,
    f.total_amount,
    f.avg_txn_amount,
    f.days_since_last_txn,
    f.active_months,
    f.failed_txn_count,
    f.complaint_count,
    f.escalation_count,
    f.interaction_count,
    f.avg_sentiment_score,
    LEAST(100, GREATEST(0, CAST(
      (CASE WHEN f.days_since_last_txn > 120 THEN 30
            WHEN f.days_since_last_txn >  90 THEN 22
            WHEN f.days_since_last_txn >  60 THEN 14
            WHEN f.days_since_last_txn >  30 THEN  6
            ELSE 0 END)
      + (CASE WHEN f.complaint_count >= 3 THEN 25
              WHEN f.complaint_count =  2 THEN 18
              WHEN f.complaint_count =  1 THEN 10
              ELSE 0 END)
      + (CASE WHEN f.escalation_count >= 2 THEN 20
              WHEN f.escalation_count =  1 THEN 12
              ELSE 0 END)
      + (CASE WHEN f.avg_sentiment_score < -0.6 THEN 15
              WHEN f.avg_sentiment_score < -0.3 THEN 10
              WHEN f.avg_sentiment_score <  0.0 THEN  5
              ELSE 0 END)
      + (CASE WHEN f.txn_count <  5 THEN 10
              WHEN f.txn_count < 15 THEN  5
              ELSE 0 END)
    AS DOUBLE))) AS churn_score
  FROM finserv.banking.gold_rfm_features f
  JOIN finserv.banking.bronze_dim_customers c ON f.customer_id = c.customer_id
)
SELECT
  *,
  CASE
    WHEN churn_score >= 65 THEN 'HIGH'
    WHEN churn_score >= 35 THEN 'MEDIUM'
    ELSE                        'LOW'
  END AS churn_risk_tier
FROM scored;


-- gold_customer_ai_summary is intentionally excluded from this pipeline.
-- ai_summarize is non-deterministic → invalid in Materialized Views.
-- The table is written as a plain Delta table by 04_train_churn_model.py
-- which runs after this pipeline completes (notebooks have no determinism constraint).


-- ── gold_segment_kpis ─────────────────────────────────────────────────────────
-- Join Gold aggregates, not raw Silver, to avoid fanout.

CREATE OR REFRESH MATERIALIZED VIEW finserv.banking.gold_segment_kpis
  COMMENT "Executive KPIs by segment and region. Joins Gold-level aggregates — no row fanout."
TBLPROPERTIES ("quality" = "gold", "layer" = "bi")
AS
SELECT
  c.segment,
  c.region,
  COUNT(DISTINCT r.customer_id)                                        AS customer_count,
  CAST(SUM(r.total_amount)  AS DECIMAL(18,2))                          AS total_revenue,
  CAST(AVG(r.avg_txn_amount) AS DECIMAL(10,2))                         AS avg_txn_amount,
  CAST(AVG(r.days_since_last_txn) AS DECIMAL(8,1))                     AS avg_days_inactive,
  CAST(AVG(cr.churn_score)  AS DECIMAL(5,1))                           AS avg_churn_score,
  SUM(CASE WHEN cr.churn_risk_tier = 'HIGH'   THEN 1 ELSE 0 END)       AS high_risk_count,
  SUM(CASE WHEN cr.churn_risk_tier = 'MEDIUM' THEN 1 ELSE 0 END)       AS medium_risk_count,
  SUM(CASE WHEN cr.churn_risk_tier = 'LOW'    THEN 1 ELSE 0 END)       AS low_risk_count,
  CAST(
    SUM(CASE WHEN cr.churn_risk_tier = 'HIGH' THEN 1 ELSE 0 END) * 100.0
    / NULLIF(COUNT(DISTINCT r.customer_id), 0)
  AS DECIMAL(5,1))                                                      AS high_risk_pct
FROM finserv.banking.gold_rfm_features r
JOIN finserv.banking.bronze_dim_customers c  ON r.customer_id = c.customer_id
JOIN finserv.banking.gold_churn_risk      cr ON r.customer_id = cr.customer_id
GROUP BY c.segment, c.region;
