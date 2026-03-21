#!/usr/bin/env python3
"""Deploy Apex Banking AI/BI Dashboard via Lakeview REST API."""
import json, subprocess, sys

HOST       = "https://dbc-61514402-8451.cloud.databricks.com"
PROFILE    = "slysik-aws-sp"
WH_ID      = "4bbaafe9538467a0"
PARENT     = "/Users/5d54409d-304c-42aa-8a21-8070a8879443/dashboards"
DASH_NAME  = "Apex Banking — Customer Attrition Intelligence"

# ── Dashboard JSON ───────────────────────────────────────────────────────────
dashboard = {
  "datasets": [
    {
      "name": "ds_kpis",
      "displayName": "Portfolio KPIs",
      "queryLines": [
        "SELECT",
        "  (SELECT COUNT(*) FROM finserv.banking.gold_churn_risk WHERE churn_risk_tier='HIGH') AS at_risk_customers,",
        "  (SELECT COUNT(*) FROM finserv.banking.gold_churn_risk WHERE segment='Premium' AND churn_risk_tier='HIGH') AS premium_high_risk,",
        "  (SELECT ROUND(SUM(f.total_amount)/1000,0) FROM finserv.banking.gold_rfm_features f JOIN finserv.banking.gold_churn_predictions p ON f.customer_id=p.customer_id WHERE p.churn_tier='HIGH') AS revenue_at_risk_k,",
        "  (SELECT ROUND(AVG(churn_score),1) FROM finserv.banking.gold_churn_risk) AS avg_portfolio_score"
      ]
    },
    {
      "name": "ds_risk_by_segment",
      "displayName": "Risk by Segment",
      "queryLines": [
        "SELECT segment, churn_risk_tier, COUNT(*) AS customers",
        "FROM finserv.banking.gold_churn_risk",
        "GROUP BY segment, churn_risk_tier",
        "ORDER BY segment, churn_risk_tier"
      ]
    },
    {
      "name": "ds_segment_kpis",
      "displayName": "Segment KPIs",
      "queryLines": [
        "SELECT segment,",
        "  SUM(customer_count)           AS customers,",
        "  ROUND(SUM(total_revenue)/1000,0) AS revenue_k,",
        "  ROUND(AVG(avg_churn_score),1) AS avg_churn_score,",
        "  SUM(high_risk_count)          AS high_risk_count,",
        "  ROUND(AVG(high_risk_pct),1)   AS high_risk_pct",
        "FROM finserv.banking.gold_segment_kpis",
        "GROUP BY segment ORDER BY customers DESC"
      ]
    },
    {
      "name": "ds_queue",
      "displayName": "At-Risk Customer Queue",
      "queryLines": [
        "SELECT",
        "  r.customer_id, r.segment, r.region,",
        "  r.churn_score, r.churn_risk_tier,",
        "  ROUND(p.churn_probability * 100, 0) AS ml_prob_pct,",
        "  r.complaint_count, r.escalation_count,",
        "  COALESCE(s.interaction_summary, 'No CRM history') AS ai_brief",
        "FROM finserv.banking.gold_churn_risk r",
        "JOIN finserv.banking.gold_churn_predictions p ON r.customer_id = p.customer_id",
        "LEFT JOIN finserv.banking.gold_customer_ai_summary s ON r.customer_id = s.customer_id",
        "WHERE r.churn_risk_tier = 'HIGH'",
        "ORDER BY r.segment, r.churn_score DESC"
      ]
    }
  ],
  "pages": [
    {
      "name": "pg_main",
      "displayName": "Customer Attrition Intelligence",
      "layout": [
        {"widget": {"name": "w_title"},        "position": {"x": 0, "y": 0,  "width": 6, "height": 2}},
        {"widget": {"name": "w_kpi_risk"},     "position": {"x": 0, "y": 2,  "width": 2, "height": 3}},
        {"widget": {"name": "w_kpi_premium"},  "position": {"x": 2, "y": 2,  "width": 2, "height": 3}},
        {"widget": {"name": "w_kpi_revenue"},  "position": {"x": 4, "y": 2,  "width": 2, "height": 3}},
        {"widget": {"name": "w_bar_segment"},  "position": {"x": 0, "y": 5,  "width": 3, "height": 9}},
        {"widget": {"name": "w_tbl_segment"},  "position": {"x": 3, "y": 5,  "width": 3, "height": 9}},
        {"widget": {"name": "w_queue_title"},  "position": {"x": 0, "y": 14, "width": 6, "height": 2}},
        {"widget": {"name": "w_tbl_queue"},    "position": {"x": 0, "y": 16, "width": 6, "height": 10}}
      ],
      "widgets": [
        # ── Title ────────────────────────────────────────────────────────────
        {
          "name": "w_title",
          "textbox_spec": "## 🏦 Apex Banking — Customer Attrition Intelligence\nTwo sources · ML churn model · AI-generated customer briefs"
        },
        # ── KPI: At-Risk Customers ────────────────────────────────────────────
        {
          "name": "w_kpi_risk",
          "queries": [{
            "name": "q_kpi_risk",
            "query": {
              "datasetName": "ds_kpis",
              "fields": [{"name": "at_risk_customers", "expression": "at_risk_customers"}]
            }
          }],
          "spec": {
            "version": 2,
            "widgetType": "counter",
            "encodings": {
              "value": {
                "fieldName": "at_risk_customers",
                "displayName": "At-Risk Customers",
                "aggType": "NONE"
              }
            }
          }
        },
        # ── KPI: Premium High-Risk ────────────────────────────────────────────
        {
          "name": "w_kpi_premium",
          "queries": [{
            "name": "q_kpi_premium",
            "query": {
              "datasetName": "ds_kpis",
              "fields": [{"name": "premium_high_risk", "expression": "premium_high_risk"}]
            }
          }],
          "spec": {
            "version": 2,
            "widgetType": "counter",
            "encodings": {
              "value": {
                "fieldName": "premium_high_risk",
                "displayName": "Premium At-Risk",
                "aggType": "NONE"
              }
            }
          }
        },
        # ── KPI: Revenue at Risk ──────────────────────────────────────────────
        {
          "name": "w_kpi_revenue",
          "queries": [{
            "name": "q_kpi_revenue",
            "query": {
              "datasetName": "ds_kpis",
              "fields": [{"name": "revenue_at_risk_k", "expression": "revenue_at_risk_k"}]
            }
          }],
          "spec": {
            "version": 2,
            "widgetType": "counter",
            "encodings": {
              "value": {
                "fieldName": "revenue_at_risk_k",
                "displayName": "Revenue at Risk ($K)",
                "aggType": "NONE"
              }
            }
          }
        },
        # ── Bar: Risk by Segment ──────────────────────────────────────────────
        {
          "name": "w_bar_segment",
          "queries": [{
            "name": "q_bar_segment",
            "query": {
              "datasetName": "ds_risk_by_segment",
              "fields": [
                {"name": "segment",         "expression": "segment"},
                {"name": "churn_risk_tier", "expression": "churn_risk_tier"},
                {"name": "customers",       "expression": "customers"}
              ]
            }
          }],
          "spec": {
            "version": 3,
            "widgetType": "bar",
            "encodings": {
              "x": {"fieldName": "segment",         "displayName": "Segment",    "scale": {"type": "categorical"}},
              "y": {"fieldName": "customers",       "displayName": "Customers",  "scale": {"type": "quantitative"}},
              "color": {"fieldName": "churn_risk_tier", "displayName": "Risk Tier", "scale": {"type": "categorical"}}
            },
            "frame": {"showTitle": True, "title": "Churn Risk by Segment"}
          }
        },
        # ── Table: Segment KPIs ───────────────────────────────────────────────
        {
          "name": "w_tbl_segment",
          "queries": [{
            "name": "q_tbl_segment",
            "query": {
              "datasetName": "ds_segment_kpis",
              "fields": [
                {"name": "segment",         "expression": "segment"},
                {"name": "customers",       "expression": "customers"},
                {"name": "revenue_k",       "expression": "revenue_k"},
                {"name": "avg_churn_score", "expression": "avg_churn_score"},
                {"name": "high_risk_count", "expression": "high_risk_count"},
                {"name": "high_risk_pct",   "expression": "high_risk_pct"}
              ]
            }
          }],
          "spec": {
            "version": 2,
            "widgetType": "table",
            "encodings": {
              "columns": [
                {"fieldName": "segment",         "displayName": "Segment"},
                {"fieldName": "customers",       "displayName": "Customers"},
                {"fieldName": "revenue_k",       "displayName": "Revenue ($K)"},
                {"fieldName": "avg_churn_score", "displayName": "Avg Risk Score"},
                {"fieldName": "high_risk_count", "displayName": "High-Risk"},
                {"fieldName": "high_risk_pct",   "displayName": "High-Risk %"}
              ]
            },
            "frame": {"showTitle": True, "title": "Segment Performance"}
          }
        },
        # ── Queue title ───────────────────────────────────────────────────────
        {
          "name": "w_queue_title",
          "textbox_spec": "## 🎯 Intervention Queue — High-Risk Customers\nML churn probability · AI-generated brief from CRM history · Prioritized for relationship manager outreach"
        },
        # ── Table: At-Risk Customer Queue ─────────────────────────────────────
        {
          "name": "w_tbl_queue",
          "queries": [{
            "name": "q_tbl_queue",
            "query": {
              "datasetName": "ds_queue",
              "fields": [
                {"name": "customer_id",    "expression": "customer_id"},
                {"name": "segment",        "expression": "segment"},
                {"name": "region",         "expression": "region"},
                {"name": "churn_score",    "expression": "churn_score"},
                {"name": "ml_prob_pct",    "expression": "ml_prob_pct"},
                {"name": "complaint_count","expression": "complaint_count"},
                {"name": "ai_brief",       "expression": "ai_brief"}
              ]
            }
          }],
          "spec": {
            "version": 2,
            "widgetType": "table",
            "encodings": {
              "columns": [
                {"fieldName": "customer_id",    "displayName": "Customer"},
                {"fieldName": "segment",        "displayName": "Segment"},
                {"fieldName": "region",         "displayName": "Region"},
                {"fieldName": "churn_score",    "displayName": "Risk Score"},
                {"fieldName": "ml_prob_pct",    "displayName": "ML Churn Prob %"},
                {"fieldName": "complaint_count","displayName": "Complaints"},
                {"fieldName": "ai_brief",       "displayName": "AI Customer Brief"}
              ]
            },
            "frame": {"showTitle": False}
          }
        }
      ]
    }
  ]
}

# ── Deploy ───────────────────────────────────────────────────────────────────
def cli(args, payload=None):
    cmd = ["databricks", "-p", PROFILE, "api"] + args
    if payload:
        cmd += ["--json", json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.stdout.strip():
        return json.loads(r.stdout)
    return {}

# Check for existing dashboard with same name
existing = cli(["get", "/api/2.0/lakeview/dashboards?page_size=50"])
dash_id = None
for d in existing.get("dashboards", []):
    if d.get("display_name") == DASH_NAME:
        dash_id = d["dashboard_id"]
        print(f"Found existing dashboard: {dash_id}")
        break

serialized = json.dumps(dashboard)

if dash_id:
    result = cli(["patch", f"/api/2.0/lakeview/dashboards/{dash_id}"], {
        "display_name":         DASH_NAME,
        "serialized_dashboard": serialized,
        "warehouse_id":         WH_ID,
    })
else:
    result = cli(["post", "/api/2.0/lakeview/dashboards"], {
        "display_name":         DASH_NAME,
        "parent_path":          PARENT,
        "serialized_dashboard": serialized,
        "warehouse_id":         WH_ID,
    })
    dash_id = result.get("dashboard_id", "")

print(f"Dashboard ID: {dash_id}")

# Publish
pub = cli(["post", f"/api/2.0/lakeview/dashboards/{dash_id}/published"], {
    "embed_credentials": False,
    "warehouse_id":      WH_ID,
})
print(f"Published: {pub.get('embed_credentials', '?')}")
print(f"\n✓ Dashboard URL:")
print(f"  {HOST}/dashboardsv3/{dash_id}?o=7474656067656578")
