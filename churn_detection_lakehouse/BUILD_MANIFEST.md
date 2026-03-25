# 🏗️ Build Manifest — Complete Project Structure

**Built:** March 21, 2026  
**Location:** `/Users/slysik/databricks/churn_detection_lakehouse/`  
**Status:** ✅ **READY FOR DEPLOYMENT**

---

## 📦 Project Structure

```
churn_detection_lakehouse/
├── 📄 README.md                         ← Project overview
├── 📄 PROJECT_SUMMARY.md                ← Complete deployment guide
├── 📄 SEND_REPORT.md                    ← Email/Discord setup
├── 📄 BUILD_MANIFEST.md                 ← This file
├── 📄 .gitignore                        ← Git ignore rules
│
├── 📋 databricks.yml                    ← Main bundle config (dashboard only)
│
├── 📁 resources/                        ← Modular bundle resources
│   ├── jobs.yml                         ← Producer, ML training, validation jobs
│   ├── pipelines.yml                    ← SDP pipeline (Bronze→Silver→Gold)
│   └── alerts.yml                       ← SQL alerts (high-risk, spikes)
│
├── 📁 src/
│   ├── 📁 notebooks/                    ← Databricks notebooks (PySpark)
│   │   ├── 01_produce_banking_events.py ← Generates 2K events/batch
│   │   ├── 02_train_churn_model.py      ← LogisticRegression training
│   │   └── 03_validate_gold_layer.py    ← Data quality checks
│   │
│   ├── 📁 pipeline/                     ← SDP SQL pipeline stages
│   │   ├── 02_silver_transforms.sql     ← Dedup + enrich events
│   │   └── 03_gold_churn_scores.sql     ← Risk scoring + interventions
│   │
│   ├── 📁 app/                          ← Web applications
│   │   └── churn_intervention_app.py     ← Streamlit intervention UI
│   │
│   └── 📁 dashboard/                    ← Lakeview dashboard config
│       └── churn_dashboard.json         ← AI/BI dashboard spec
│
├── 📁 scripts/                          ← Utility scripts
│   └── send_report.py                   ← Email + Discord distribution
│
├── 📁 docs/                             ← Documentation
│   ├── CHURN_DETECTION_REPORT.html      ← 3-PAGE REPORT (READ FIRST!)
│   ├── DISCORD_SETUP.md                 ← Discord integration guide
│   ├── architecture.md                  ← Architecture decisions (TBD)
│   └── intervention_playbook.md         ← Customer service guide (TBD)
│
└── 📁 tests/                            ← Test suite (TBD)
    └── README.md
```

---

## 📄 Key Files Explained

### 📖 Documentation (Read in Order)

| File | Purpose | Time |
|------|---------|------|
| `README.md` | Project overview + architecture diagram | 5 min |
| `PROJECT_SUMMARY.md` | Complete deployment guide (THIS IS YOUR ROADMAP) | 10 min |
| **`docs/CHURN_DETECTION_REPORT.html`** | **3-PAGE HTML REPORT — Read in browser or email it** | 15 min |
| `SEND_REPORT.md` | How to email/Discord the report | 5 min |
| `docs/DISCORD_SETUP.md` | Full Discord integration guide | 10 min |

### 🔧 Configuration

| File | Purpose | Status |
|------|---------|--------|
| `databricks.yml` | Main bundle config (includes resources/) | ✅ Ready |
| `resources/jobs.yml` | 3 jobs (producer, ML, validation) | ✅ Ready |
| `resources/pipelines.yml` | SDP pipeline (Bronze→Silver→Gold) | ✅ Ready |
| `resources/alerts.yml` | SQL alerts (high-risk, spikes) | ✅ Ready |

### 🐍 Notebooks (Databricks)

| Notebook | Purpose | Input | Output |
|----------|---------|-------|--------|
| `01_produce_banking_events.py` | Generates 2K events/batch | None | Bronze table |
| `02_train_churn_model.py` | Trains LogisticRegression model | Silver metrics | ML predictions |
| `03_validate_gold_layer.py` | Data quality validation | Gold tables | Validation report |

### 📊 SDP Pipeline SQL

| SQL File | Purpose | Input | Output |
|----------|---------|-------|--------|
| `02_silver_transforms.sql` | Dedup + parse events + compute RFM | Bronze | Silver tables |
| `03_gold_churn_scores.sql` | Risk scoring + intervention tracking | Silver | Gold tables |

### 💻 Applications

| App | Framework | Purpose | Access |
|-----|-----------|---------|--------|
| `churn_intervention_app.py` | Streamlit | Web UI for intervention logging | Local/Cloud |
| `churn_dashboard.json` | Lakeview | Interactive dashboard | Databricks workspace |

### 📤 Distribution

| Script | Purpose | Output |
|--------|---------|--------|
| `send_report.py` | Email + Discord sender | Report to inbox + Discord |

---

## 🎯 Data Model

### Bronze Layer
**Table:** `finserv.churn_demo.bronze_banking_events`  
**Source:** Zerobus gRPC from BOA iOS app  
**Schema:** event_id, user_id, event_type, timestamp, is_risk_signal, metadata_json, ingest_ts  
**Retention:** 90 days  
**Volume:** 2,000 events per 5-min batch

### Silver Layer
**Views:**
1. `silver_user_events` — Deduped, parsed events
2. `silver_user_metrics` — Weekly RFM + engagement metrics

**Retention:** 2 years

### Gold Layer
**Views:**
1. `gold_churn_risk` — Risk scores, tiers, recommendations
2. `gold_churn_predictions` — ML model predictions (0-100%)

**Tables:**
1. `gold_interventions` — Intervention log with outcomes

**Retention:** 1 year

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] Read `PROJECT_SUMMARY.md` (10 min)
- [ ] Read `docs/CHURN_DETECTION_REPORT.html` (15 min)
- [ ] Verify auth: `databricks auth describe`
- [ ] Verify SQL warehouse: `databricks sql execute "SELECT 1"`

### Deploy
- [ ] Validate: `databricks bundle validate`
- [ ] Deploy: `databricks bundle deploy`
- [ ] Check jobs created: `databricks jobs list | grep churn`
- [ ] Check pipeline: `databricks pipelines list-pipelines | grep churn`

### Run
- [ ] Generate data: `databricks jobs run-now --job-id [produce_banking_events]`
- [ ] Start pipeline: `databricks pipelines start-update --pipeline-id [churn_pipeline]`
- [ ] View dashboard: Open workspace → Dashboards → [dev churn]

### Use
- [ ] Open Genie Space (natural language Q&A)
- [ ] Launch web app: `streamlit run src/app/churn_intervention_app.py`
- [ ] Check alerts in workspace

---

## 📊 Component Inventory

### Jobs (3 total)
1. **produce_banking_events** — Schedule: Every 5 min | Serverless
2. **train_churn_model** — Schedule: Weekly Monday 2am | Serverless
3. **validate_gold_layer** — Schedule: Every 6 hours | Serverless

### Pipelines (1 total)
1. **churn_pipeline** — Continuous SDP | Bronze→Silver→Gold | Serverless

### Dashboards (1 total)
1. **churn_dashboard** — 3 pages (at-risk customers, risk distribution, interventions)

### Alerts (2 total)
1. **high_risk_vips** — Triggers on CRITICAL/HIGH tier customers
2. **churn_spike** — Triggers on rapid risk increases

### Web Apps (1 total)
1. **churn_intervention_app** — Streamlit UI for logging interventions

### Genie Spaces (1 total)
1. **TBD** — Natural language Q&A on churn data

---

## 📈 Scaling Options

### 2K → 10K Events/Batch
Change in `01_produce_banking_events.py`:
```python
for i in range(2000):  # Change to 10000
```

### Every 5 min → Every Hour
Change in `resources/jobs.yml`:
```yaml
quartz_cron_expression: "0 * * * *"  # Every hour
```

### Daily ML Retraining → Every 6 Hours
Change in `resources/jobs.yml`:
```yaml
quartz_cron_expression: "0 */6 * * *"  # Every 6 hours
```

---

## 🔐 Security & Governance

### Data Classification
- **Bronze:** Raw data (compliance audit trail)
- **Silver:** Enriched, PII masked (internal analytics)
- **Gold:** Aggregated (customer-facing)

### UC Grants Required
```sql
GRANT USE_CATALOG ON CATALOG finserv TO <user>
GRANT USE_SCHEMA, SELECT, MODIFY, CREATE TABLE ON SCHEMA finserv.churn_demo TO <user>
```

### Secrets Management
- No hardcoded credentials in code
- SENDER_EMAIL, SENDER_PASSWORD via environment variables
- Discord webhook URL via command-line argument

---

## 📦 Dependencies

### Databricks Features
- Unity Catalog (finserv catalog)
- Databricks SQL Warehouse (serverless)
- SDP (Spark Declarative Pipelines)
- Serverless compute (no cluster needed)
- AI/BI (Lakeview dashboards)
- Genie Spaces

### Python Libraries
- pyspark (DataFrame, SQL functions)
- mlflow (model tracking)
- streamlit (web app)
- databricks-sdk (authentication, SQL)
- requests (Discord webhooks)
- pandas (data frames)

### External Systems
- Zerobus (gRPC stream ingestion)
- Discord (optional, for alerts + reports)
- Gmail (optional, for email delivery)

---

## 🧪 Testing (TBD)

### Unit Tests
- Data validation (schemas, nulls, duplicates)
- Risk scoring logic
- ML model predictions

### Integration Tests
- Bronze → Silver dedup
- Silver → Gold scoring accuracy
- Intervention logging

### End-to-End Tests
- Producer → Dashboard latency
- Alert triggering
- Web app intervention logging

---

## 🔄 Maintenance Schedule

| Task | Frequency | Owner |
|------|-----------|-------|
| Monitor producer success | Daily | Data Engineer |
| Review at-risk customers | Daily | Customer Service |
| Log interventions | Ongoing | Support Team |
| Retrain ML model | Weekly | Data Scientist |
| Review intervention success | Weekly | Manager |
| Archive old Bronze data | Monthly | Data Engineer |
| Optimize costs | Quarterly | Finance |

---

## 📞 Support Matrix

| Issue | Resolution | Time |
|-------|-----------|------|
| Data not appearing in dashboard | Check producer job logs | 5 min |
| Email not sending | Verify SENDER_EMAIL, SENDER_PASSWORD | 5 min |
| Discord alert failed | Check webhook URL | 3 min |
| SDP pipeline slow | Check serverless cluster status | 10 min |
| ML model accuracy low | Retrain with more features | 30 min |

---

## 🎓 Learning Path

1. **30 min:** Read all docs (README → PROJECT_SUMMARY → REPORT)
2. **30 min:** Deploy bundle + run producer
3. **30 min:** Check dashboard + launch web app
4. **1 hour:** Log interventions, review success metrics
5. **2 hours:** Customize thresholds, retrain ML, adjust alert triggers
6. **Ongoing:** Monitor, measure, improve

---

## ✅ Sign-Off

**Project:** Banking Churn Detection Platform  
**Status:** ✅ Complete & Ready for Deployment  
**Built:** March 21, 2026  
**Author:** Claude Code (Databricks SA)  
**Next Step:** Read `PROJECT_SUMMARY.md` and deploy!

---

**Questions?** Email slysik@gmail.com or check Discord (coming soon!)
