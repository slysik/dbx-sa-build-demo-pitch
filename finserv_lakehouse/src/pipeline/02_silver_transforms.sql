-- =============================================================================
-- Silver Layer — Apex Banking Customer 360
-- Pipeline: banking_medallion | finserv.banking
--
-- Two sources unified into a single governed layer:
--   1. Core Banking System (Postgres)  → silver_transactions
--   2. Salesforce CRM Export (SaaS)    → silver_interactions + AI enrichment
--
-- Data quality enforced via WHERE predicates (same effect as EXPECT constraints).
-- In production: add row-level access policies + column masking on top of Silver.
-- =============================================================================


-- ── silver_transactions ───────────────────────────────────────────────────────
-- Clean, typed transaction ledger. Single source of truth for all revenue and
-- activity analytics. WHERE clause drops nulls + negatives at write time.

CREATE OR REFRESH MATERIALIZED VIEW finserv.banking.silver_transactions
  COMMENT "Cleansed and typed transaction ledger from core banking system (Postgres source). Governed single source of truth for all transaction analytics."
TBLPROPERTIES (
  "quality"        = "silver",
  "source_system"  = "core_banking_postgres"
)
AS
SELECT
  txn_id,
  account_id,
  customer_id,
  CAST(txn_date AS DATE)                       AS txn_date,
  DATE_TRUNC('month', CAST(txn_date AS DATE))  AS txn_month,
  CAST(txn_ts AS TIMESTAMP)                    AS txn_ts,
  CAST(amount AS DECIMAL(18, 2))               AS amount,
  txn_category,
  txn_status,
  channel,
  account_type,
  branch,
  segment,
  region,
  risk_tier,
  CAST(ingest_ts AS TIMESTAMP)                 AS ingest_ts,
  source_system,
  batch_id
FROM finserv.banking.bronze_fact_transactions
WHERE txn_id IS NOT NULL   -- quality gate: drop orphan records
  AND amount  > 0;          -- quality gate: drop zero/negative amounts


-- ── silver_interactions ───────────────────────────────────────────────────────
-- CRM interaction notes enriched inline with AI functions.
-- ai_classify  → structured intent label  (complaint / inquiry / escalation / praise)
-- ai_analyze_sentiment → sentiment score  (positive / negative / mixed / neutral)
-- These two columns feed directly into the churn model's feature store.

CREATE OR REFRESH MATERIALIZED VIEW finserv.banking.silver_interactions
  COMMENT "CRM interaction records (Salesforce SaaS source) enriched with AI-classified intent and sentiment. Powers churn risk scoring and GenAI summarization."
TBLPROPERTIES (
  "quality"        = "silver",
  "source_system"  = "salesforce_crm_saas"
)
AS
SELECT
  interaction_id,
  customer_id,
  CAST(interaction_date AS DATE)  AS interaction_date,
  channel,
  note_text,

  -- GenAI: classify interaction intent from raw note text
  ai_classify(
    note_text,
    ARRAY('complaint', 'inquiry', 'escalation', 'praise')
  )                               AS interaction_category,

  -- GenAI: sentiment scoring — feeds avg_sentiment_score in the churn model
  ai_analyze_sentiment(note_text) AS sentiment,

  CAST(ingest_ts AS TIMESTAMP)    AS ingest_ts,
  source_system
FROM finserv.banking.bronze_crm_interactions
WHERE customer_id IS NOT NULL
  AND note_text   IS NOT NULL;
