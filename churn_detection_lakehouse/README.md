# 🏦 Real-Time Banking Churn Detection Platform

**Use Case:** BOA iOS app users showing signs of dissatisfaction → Real-time detection + intervention → Customer retention

**Architecture:**
```
BOA App (2K JSON events/batch)
    ↓ Zerobus gRPC (real-time stream)
    ↓
Bronze (raw JSON ingestion)
    ↓ SDP Pipeline
    ↓
Silver (parsed, enriched with engagement metrics)
    ↓ SDP Pipeline  
    ↓
Gold (churn scores, ML predictions, intervention tracking)
    ↓
├─ Dashboard (at-risk customers, trends)
├─ Genie Space (Q&A on churn data)
├─ Web App (intervention UI for reps)
└─ SQL Alerts (escalation on high-risk spikes)
```

---

## Data Model

### Bronze Layer (Raw JSON from Zerobus)
```json
{
  "event_id": "EVT-xxx",
  "user_id": "USER-xxx",
  "timestamp": "2026-03-21T17:00:00Z",
  "event_type": "app_open|transaction|failed_login|app_crash|support_call",
  "metadata": {...}
}
```

### Silver Layer (Enriched)
- Deduped events
- Engagement metrics (app opens/week, transaction frequency)
- Behavioral flags (failed logins, crashes, support calls)
- RFM scoring (Recency, Frequency, Monetary)

### Gold Layer (ML-Ready)
- Churn risk score (0-100, from LogisticRegression)
- Risk tier (LOW, MEDIUM, HIGH, CRITICAL)
- Recommended action (discount, call, proactive message)
- Intervention tracking (what we tried, when, effectiveness)

---

## Key Tables

| Layer | Table | Purpose |
|-------|-------|---------|
| Bronze | `bronze_banking_events` | Raw JSON stream from Zerobus |
| Silver | `silver_user_events` | Deduped, parsed events |
| Silver | `silver_user_metrics` | Weekly engagement + RFM |
| Gold | `gold_churn_risk` | ML predictions + risk scores |
| Gold | `gold_interventions` | Intervention log + results |

---

## Deployment

```bash
# Validate
databricks bundle validate

# Deploy pipeline + job to workspace
databricks bundle deploy

# Run producer (generates 2K events/batch, pushes to Zerobus every 30s)
python3 src/app/produce_banking_events.py

# Run SDP pipeline
databricks bundle run churn_pipeline

# Start web app (real-time intervention UI)
python3 -m databricks.sdk.core app start src/app/churn_intervention_app.py

# Deploy dashboard
python3 scripts/deploy_dashboard.py

# Create Genie Space
python3 scripts/create_genie_space.py
```

---

## Alerts

SQL Alerts trigger when:
- High-risk VIP customers detected (churn_score > 75 AND account_value > $100K)
- Churn spike in region (weekly increase > 20%)
- Critical customer engagement drop (no activity for 7 days)

---

## Files

```
src/
├── notebooks/
│   ├── 01_produce_banking_events.py   ← Zerobus producer
│   ├── 02_train_churn_model.py        ← LogisticRegression + MLflow
│   └── 03_validate_gold_layer.py      ← Final validation
├── pipeline/
│   ├── 02_silver_transforms.sql       ← Parse + enrich
│   ├── 03_gold_churn_scores.sql       ← ML predictions
│   └── 04_interventions.sql           ← Tracking
├── app/
│   └── churn_intervention_app.py       ← Streamlit UI
└── dashboard/
    └── churn_dashboard.json            ← Lakeview dashboard

docs/
├── architecture.md
└── intervention_playbook.md

tests/
└── README.md
```

---

## Next Steps

1. Run producer → generates 2K events
2. SDP pipeline processes in real-time
3. Dashboard shows at-risk customers
4. Genie answers questions about churn
5. Web app lets reps intervene
6. Alerts notify on escalations
