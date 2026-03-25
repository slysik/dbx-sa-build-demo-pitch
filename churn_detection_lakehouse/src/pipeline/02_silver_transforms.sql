-- Databricks notebook source

-- Silver Layer: Parse + Enrich Banking Events
-- Dedup raw events, add engagement metrics, compute RFM

CREATE OR REFRESH MATERIALIZED VIEW silver_user_events AS
SELECT DISTINCT
  event_id,
  user_id,
  event_type,
  CAST(timestamp AS TIMESTAMP) AS event_timestamp,
  is_risk_signal,
  CAST(metadata_json AS STRING) AS metadata,
  ingest_ts,
  CURRENT_TIMESTAMP() AS processed_at
FROM bronze_banking_events
WHERE event_id IS NOT NULL AND user_id IS NOT NULL
  AND CAST(timestamp AS TIMESTAMP) >= CURRENT_TIMESTAMP() - INTERVAL 7 DAYS
CLUSTER BY (user_id);

-- Silver Layer: User Engagement Metrics (Weekly RFM)
CREATE OR REFRESH MATERIALIZED VIEW silver_user_metrics AS
SELECT
  user_id,
  DATE_TRUNC('WEEK', event_timestamp) AS metric_week,
  
  -- Recency: Days since last event
  DATEDIFF(CURRENT_DATE(), MAX(CAST(event_timestamp AS DATE))) AS days_since_last_event,
  
  -- Frequency: Events this week by type
  COUNT(CASE WHEN event_type = 'app_open' THEN 1 END) AS weekly_app_opens,
  COUNT(CASE WHEN event_type = 'transaction' THEN 1 END) AS weekly_transactions,
  
  -- Risk signals: Count of warning events
  COUNT(CASE WHEN is_risk_signal THEN 1 END) AS weekly_risk_signals,
  COUNT(CASE WHEN event_type = 'failed_login' THEN 1 END) AS weekly_failed_logins,
  COUNT(CASE WHEN event_type = 'app_crash' THEN 1 END) AS weekly_crashes,
  COUNT(CASE WHEN event_type = 'support_call' THEN 1 END) AS weekly_support_calls,
  
  -- Engagement health
  CASE 
    WHEN COUNT(CASE WHEN event_type = 'app_open' THEN 1 END) = 0 THEN 'DORMANT'
    WHEN COUNT(CASE WHEN is_risk_signal THEN 1 END) > 3 THEN 'AT_RISK'
    WHEN COUNT(CASE WHEN event_type = 'transaction' THEN 1 END) > 0 THEN 'ACTIVE'
    ELSE 'LOW_ACTIVITY'
  END AS engagement_health,
  
  CURRENT_TIMESTAMP() AS metric_timestamp
  
FROM silver_user_events
GROUP BY user_id, DATE_TRUNC('WEEK', event_timestamp)
CLUSTER BY (user_id);

print("✅ Silver layer: raw events parsed + metrics computed")
