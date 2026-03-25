"""
Churn Intervention UI — Real-Time Customer Service Dashboard

Streamlit app for customer service reps to:
1. View real-time at-risk customers ranked by risk score
2. See engagement signals that triggered the risk alert
3. Log intervention (call, email, discount offer, etc.)
4. Track effectiveness (did customer stay or churn?)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from databricks.sdk import WorkspaceClient

# ── Configuration ──────────────────────────────────────────────────────────

CATALOG = "finserv"
SCHEMA = "churn_demo"

# Initialize Databricks client (OAuth auto-auth in Databricks Apps)
ws = WorkspaceClient()

st.set_page_config(
    page_title="🏦 Churn Intervention Command Center",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Sidebar: Filters ───────────────────────────────────────────────────────

st.sidebar.title("⚙️ Filters")
risk_filter = st.sidebar.multiselect(
    "Risk Tier",
    ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
    default=["CRITICAL", "HIGH"]
)
action_filter = st.sidebar.selectbox(
    "Recommended Action",
    ["ALL", "WIN_BACK_CAMPAIGN", "TECH_SUPPORT", "INCENTIVE_OFFER", "VIP_SUPPORT", "MONITOR"]
)

# ── Main: At-Risk Customers ────────────────────────────────────────────────

st.title("🏦 Real-Time Churn Intervention Command Center")
st.markdown("**Live dashboard for customer retention.** Identify at-risk customers, log interventions, track outcomes.")

# Fetch at-risk customers from gold_churn_risk
query_risk = f"""
SELECT
  user_id,
  risk_tier,
  rule_based_score,
  recommended_action,
  weekly_app_opens,
  weekly_transactions,
  weekly_risk_signals,
  weekly_failed_logins,
  weekly_crashes,
  weekly_support_calls,
  engagement_health,
  score_date
FROM {CATALOG}.{SCHEMA}.gold_churn_risk
WHERE risk_tier IN ({','.join([f"'{t}'" for t in risk_filter])})
"""

if action_filter != "ALL":
    query_risk += f" AND recommended_action = '{action_filter}'"

query_risk += " ORDER BY rule_based_score DESC LIMIT 50"

try:
    at_risk_df = ws.sql.execute(query_risk).result().as_pandas()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🚨 At-Risk Customers", len(at_risk_df))
    col2.metric("CRITICAL", len(at_risk_df[at_risk_df["risk_tier"] == "CRITICAL"]))
    col3.metric("HIGH", len(at_risk_df[at_risk_df["risk_tier"] == "HIGH"]))
    col4.metric("MEDIUM", len(at_risk_df[at_risk_df["risk_tier"] == "MEDIUM"]))
    
    st.divider()
    
    # ── Interactive Customer Selection ─────────────────────────────────────
    
    st.subheader("👥 At-Risk Customers")
    
    # Format for display
    display_df = at_risk_df[[
        "user_id", "risk_tier", "rule_based_score", "recommended_action",
        "weekly_app_opens", "weekly_transactions", "weekly_risk_signals",
        "engagement_health"
    ]].copy()
    
    display_df.columns = [
        "User ID", "Risk", "Score", "Recommended Action",
        "App Opens", "Transactions", "Risk Signals", "Engagement"
    ]
    
    st.dataframe(display_df, use_container_width=True, height=400)
    
    # ── Intervention Logging ───────────────────────────────────────────────
    
    st.divider()
    st.subheader("✍️ Log Intervention")
    
    col_user, col_action, col_result = st.columns(3)
    
    selected_user = col_user.selectbox(
        "Select Customer",
        at_risk_df["user_id"].tolist()
    )
    
    intervention_type = col_action.selectbox(
        "Intervention Type",
        ["CALL", "EMAIL", "SMS", "IN_APP_MESSAGE", "DISCOUNT_OFFER", "TECH_SUPPORT", "ESCALATE_TO_VIP"]
    )
    
    intervention_result = col_result.selectbox(
        "Result",
        ["PENDING", "ACCEPTED", "DECLINED", "IN_PROGRESS"]
    )
    
    # Intervention notes
    notes = st.text_area(
        "Notes (optional)",
        placeholder="E.g., 'Called customer, app crashing on login. Offered reset + $20 credit.'"
    )
    
    if st.button("📤 Log Intervention", type="primary"):
        # Insert intervention into gold_interventions table
        insert_sql = f"""
        INSERT INTO {CATALOG}.{SCHEMA}.gold_interventions 
        (intervention_id, user_id, intervention_type, intervention_result, intervention_ts, outcome_ts)
        VALUES (
          CONCAT('INT-', DATE_FORMAT(CURRENT_TIMESTAMP(), 'yyyyMMddHHmmss'), '-', CAST(ABS(HASH('{selected_user}')) AS STRING)),
          '{selected_user}',
          '{intervention_type}',
          '{intervention_result}',
          CURRENT_TIMESTAMP(),
          CURRENT_TIMESTAMP()
        )
        """
        
        ws.sql.execute(insert_sql)
        st.success(f"✅ Intervention logged for {selected_user}")
        st.balloons()
    
    # ── Intervention History ───────────────────────────────────────────────
    
    st.divider()
    st.subheader("📋 Recent Interventions (Last 30 Days)")
    
    query_interventions = f"""
    SELECT
      intervention_id,
      user_id,
      intervention_type,
      intervention_result,
      intervention_ts,
      retained_after_intervention
    FROM {CATALOG}.{SCHEMA}.gold_interventions
    WHERE intervention_ts >= CURRENT_TIMESTAMP() - INTERVAL 30 DAYS
    ORDER BY intervention_ts DESC
    LIMIT 25
    """
    
    interventions_df = ws.sql.execute(query_interventions).result().as_pandas()
    
    if len(interventions_df) > 0:
        st.dataframe(interventions_df, use_container_width=True)
        
        # Intervention effectiveness
        st.metric(
            "Intervention Success Rate",
            f"{100 * interventions_df['retained_after_intervention'].sum() / len(interventions_df):.1f}%"
        )
    else:
        st.info("No recent interventions logged.")
    
    # ── Engagement Trends ──────────────────────────────────────────────────
    
    st.divider()
    st.subheader("📈 Engagement Trends")
    
    query_trends = f"""
    SELECT
      DATE_TRUNC('DAY', event_timestamp) AS date,
      COUNT(CASE WHEN event_type = 'app_open' THEN 1 END) AS app_opens,
      COUNT(CASE WHEN event_type = 'transaction' THEN 1 END) AS transactions,
      COUNT(CASE WHEN is_risk_signal THEN 1 END) AS risk_signals
    FROM {CATALOG}.{SCHEMA}.silver_user_events
    WHERE event_timestamp >= CURRENT_TIMESTAMP() - INTERVAL 30 DAYS
    GROUP BY DATE_TRUNC('DAY', event_timestamp)
    ORDER BY date DESC
    """
    
    trends_df = ws.sql.execute(query_trends).result().as_pandas()
    st.line_chart(trends_df.set_index("date"))
    
except Exception as e:
    st.error(f"❌ Data fetch error: {e}")
    st.info("Make sure the SDP pipeline has run and tables are populated.")

# ── Footer ─────────────────────────────────────────────────────────────────

st.divider()
st.caption("🏦 Banking Churn Detection Platform | Real-time dashboa using Databricks SDP + ML | Data updated every 5 minutes")
