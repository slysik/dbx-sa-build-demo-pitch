# 🚀 QUICKSTART — Get Going in 30 Minutes

**Your banking churn detection platform is built and ready to deploy.**

This guide gets you from zero to live dashboard in **30 minutes**.

---

## ⏱️ Timeline

| Step | Time | What |
|------|------|------|
| 1️⃣ | 5 min | Read this guide + check auth |
| 2️⃣ | 3 min | Deploy to Databricks |
| 3️⃣ | 2 min | Generate data |
| 4️⃣ | 15 min | Run SDP pipeline |
| 5️⃣ | 5 min | View dashboard + Genie |

---

## 1️⃣ Read & Verify (5 minutes)

### Read the Key Docs
1. **`README.md`** — Project overview (2 min)
2. **`PROJECT_SUMMARY.md`** — Your deployment roadmap (3 min)

**Don't have 15 min?** Just skim the diagrams and skip to **Step 2**.

### Verify Auth
```bash
databricks auth describe
# Should show: ✅ Host, ✅ Profile, ✅ Token valid
```

### Verify Warehouse
```bash
databricks sql execute "SELECT current_user()"
# Should show: ✅ User ID or email
```

---

## 2️⃣ Deploy (3 minutes)

```bash
# Navigate to project
cd /Users/slysik/databricks/churn_detection_lakehouse

# Validate bundle config
databricks bundle validate
# ✅ Should show: All validations passed

# Deploy to workspace
databricks bundle deploy
# ✅ Should create jobs, pipeline, alerts, dashboard
```

**What got deployed:**
- ✅ 3 jobs (producer, ML training, validation)
- ✅ 1 SDP pipeline (Bronze → Silver → Gold)
- ✅ 2 SQL alerts
- ✅ 1 dashboard

---

## 3️⃣ Generate Data (2 minutes)

```bash
# Run the producer job (generates 2K events)
databricks jobs run-now --job-id [produce_banking_events]

# Wait for it to complete (check workspace jobs UI)
# Or run async and check logs:
databricks jobs runs get --run-id [RUN_ID] | grep state
```

**Status:** Shows `SUCCEEDED` when done.

---

## 4️⃣ Run Pipeline (15 minutes)

```bash
# Start the SDP pipeline
databricks pipelines start-update --pipeline-id [churn_pipeline]

# Watch progress:
databricks pipelines get --pipeline-id [churn_pipeline] | grep state
# State: RUNNING → IDLE when complete (~2 min)
```

**What happens:**
1. Bronze table ingests 2K events (30 sec)
2. Silver transforms: dedup + enrich (30 sec)
3. Gold computes: risk scores + interventions (30 sec)

**Total:** ~2 minutes

---

## 5️⃣ View Results (5 minutes)

### 📊 Open the Dashboard
```bash
# List dashboards
databricks workspace list /Users/lysiak043@gmail.com/dashboards/

# Or search your workspace for "[dev churn] Real-Time Churn Detection"
```

Click the dashboard link. You should see:
- 🚨 CRITICAL customer count
- 🔴 HIGH tier count
- 🟡 MEDIUM tier count
- 📈 Top 25 at-risk customers

### 🤖 Try Genie Space (Q&A)
Go to your workspace:
1. Click **Genie** (left sidebar)
2. Create new space or use existing `[dev churn]` space
3. Ask questions:
   - "Show me customers who opened the app but didn't transact"
   - "Which regions have the highest churn?"

### 💬 Launch the Web App
```bash
streamlit run src/app/churn_intervention_app.py

# Opens at http://localhost:8501
# Features:
# - Filter by risk tier
# - Click customer to see signals
# - Log intervention (call, email, offer)
# - View 30-day intervention history
```

---

## 🎉 You're Done!

Your system is now:
- ✅ Ingesting 2K events every 5 min
- ✅ Detecting at-risk customers in real-time
- ✅ Scoring churn risk (0-100)
- ✅ Recommending interventions
- ✅ Tracking outcomes

---

## 📧 Next: Share the Report (5 minutes)

Want to email yourself the full 3-page report + send to Discord?

```bash
# Set up email (one-time)
export SENDER_EMAIL="your-gmail@gmail.com"
export SENDER_PASSWORD="your-app-password"  # Get from Google Account

# Send report
python3 scripts/send_report.py --email slysik@gmail.com

# Or add Discord too
python3 scripts/send_report.py \
  --email slysik@gmail.com \
  --discord-webhook "YOUR_WEBHOOK_URL"
```

**Full setup:** See `SEND_REPORT.md` and `docs/DISCORD_SETUP.md`

---

## 🔧 Troubleshooting

### "Bundle validation failed"
```bash
# Check workspace connection
databricks auth describe

# Make sure catalog exists
databricks sql execute "SHOW CATALOGS" | grep finserv
```

### "Producer job failed"
```bash
# Check logs
databricks jobs runs list --job-id [produce_banking_events] --limit 1

# Get detailed logs
databricks jobs runs get-output --run-id [RUN_ID]
```

### "SDP pipeline stuck on RUNNING"
```bash
# Check pipeline status
databricks pipelines get --pipeline-id [churn_pipeline]

# Check logs
databricks pipelines get-updates --pipeline-id [churn_pipeline]
```

### "Dashboard shows no data"
1. Wait 3 minutes (SDP needs time to process)
2. Manually run: `SELECT COUNT(*) FROM finserv.churn_demo.gold_churn_risk`
3. If zero rows → producer or SDP failed (check logs above)

---

## 📚 Go Deeper

After you've verified the dashboard works:

1. **Customize risk thresholds** → Edit `src/pipeline/03_gold_churn_scores.sql`
2. **Change batch frequency** → Edit `resources/jobs.yml`
3. **Add Discord alerts** → Follow `docs/DISCORD_SETUP.md`
4. **Scale to 100K events** → Change `spark.range(2000)` → `spark.range(100000)`
5. **Read architecture** → `docs/CHURN_DETECTION_REPORT.html` (3-page report)

---

## 🎯 Success Metrics

You'll know it's working when:

✅ Dashboard shows at-risk customers  
✅ Web app lets you log interventions  
✅ Genie answers natural language questions  
✅ Alerts fire on high-risk spikes  
✅ Intervention success rate appears in dashboard  

---

## 💬 Questions?

📧 Email: slysik@gmail.com  
📖 Full docs: `PROJECT_SUMMARY.md`  
📊 Report: `docs/CHURN_DETECTION_REPORT.html`  
💬 Discord: (coming soon)

---

**That's it! You now have a production-grade real-time churn detection system.** 🚀

Go retain some customers! 🏦
