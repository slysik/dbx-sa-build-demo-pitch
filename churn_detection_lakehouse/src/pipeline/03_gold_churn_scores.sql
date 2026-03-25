-- Databricks notebook source

-- Gold Layer: Churn Risk Scoring + ML Integration
-- Rule-based scoring + ML model predictions

CREATE OR REFRESH MATERIALIZED VIEW gold_churn_risk AS
SELECT
  m.user_id,
  m.metric_week,
  
  -- Rule-based risk score (0-100)
  CASE
    WHEN m.days_since_last_event > 30 THEN 40  -- Dormant
    WHEN m.weekly_risk_signals >= 3 THEN 25     -- Multiple risk signals
    WHEN m.weekly_failed_logins >= 2 THEN 15    -- Auth issues
    WHEN m.weekly_crashes >= 2 THEN 10          -- App stability
    WHEN m.weekly_support_calls >= 1 THEN 10    -- Calling support
    ELSE 0
  END +
  -- Engagement-based adjustment
  CASE
    WHEN m.weekly_app_opens = 0 THEN 30         -- No app usage
    WHEN m.weekly_transactions = 0 AND m.weekly_app_opens > 0 THEN 20  -- Opens but no transactions
    ELSE 0
  END AS rule_based_score,
  
  -- Risk tier (will be overridden by ML model score when available)
  CASE
    WHEN m.days_since_last_event > 30 THEN 'CRITICAL'
    WHEN m.weekly_risk_signals >= 3 THEN 'HIGH'
    WHEN m.weekly_failed_logins >= 2 OR m.weekly_crashes >= 2 THEN 'MEDIUM'
    WHEN m.engagement_health = 'LOW_ACTIVITY' THEN 'MEDIUM'
    ELSE 'LOW'
  END AS risk_tier,
  
  -- Engagement metrics for intervention planning
  m.weekly_app_opens,
  m.weekly_transactions,
  m.weekly_risk_signals,
  m.engagement_health,
  
  -- Recommended intervention
  CASE
    WHEN m.days_since_last_event > 30 THEN 'WIN_BACK_CAMPAIGN'
    WHEN m.weekly_failed_logins >= 2 THEN 'TECH_SUPPORT'
    WHEN m.weekly_crashes >= 2 THEN 'UPGRADE_REMINDER'
    WHEN m.weekly_support_calls >= 1 THEN 'VIP_SUPPORT'
    WHEN m.weekly_app_opens > 0 AND m.weekly_transactions = 0 THEN 'INCENTIVE_OFFER'
    ELSE 'MONITOR'
  END AS recommended_action,
  
  CURRENT_TIMESTAMP() AS score_timestamp,
  CURRENT_DATE() AS score_date

FROM silver_user_metrics m
CLUSTER BY (user_id);

-- Gold Layer: Intervention Tracking
-- Log every outreach attempt and result
CREATE OR REFRESH MATERIALIZED VIEW gold_interventions AS
SELECT
  CONCAT('INT-', DATE_FORMAT(CURRENT_TIMESTAMP(), 'yyyyMMddHHmmss'), '-', CAST(ROW_NUMBER() OVER (ORDER BY user_id) AS STRING)) AS intervention_id,
  g.user_id,
  g.metric_week,
  g.risk_tier,
  g.recommended_action,
  CURRENT_TIMESTAMP() AS intervention_datetime,
  
  -- Placeholder for intervention result (to be updated by web app)
  CAST(NULL AS STRING) AS intervention_type,  -- 'CALL', 'EMAIL', 'OFFER', etc.
  CAST(NULL AS STRING) AS intervention_result, -- 'ACCEPTED', 'IGNORED', 'PENDING'
  CAST(NULL AS TIMESTAMP) AS intervention_ts,
  
  -- Outcome tracking
  CAST(FALSE AS BOOLEAN) AS retained_after_intervention,
  CAST(NULL AS TIMESTAMP) AS outcome_ts
  
FROM gold_churn_risk g
WHERE g.risk_tier IN ('HIGH', 'CRITICAL')
CLUSTER BY (user_id);

print("✅ Gold layer: churn scores + intervention tracking ready")
