# 🎬 Master Demo Guide — Apex Financial Services Lakehouse
## "From Raw Transactions to Business Intelligence in Under 10 Minutes"

---

## Quick Reference — All Assets

| Asset | URL / Location |
|-------|---------------|
| **Pipeline** | Databricks → Lakeflow Pipelines → `[dev] finance_medallion` |
| **Job** | Databricks → Workflows → `[dev] finance_orchestrator` |
| **Dashboard** | https://dbc-ad74b11b-230d.cloud.databricks.com/dashboardsv3/01f122e33209151e99925fda8cff3088/published |
| **Bronze Notebook** | Workspace → `.bundle/finserv_lakehouse/dev/files/src/notebooks/01_generate_bronze` |
| **Silver SQL** | Workspace → `.bundle/finserv_lakehouse/dev/files/src/pipeline/02_silver_transforms.sql` |
| **Gold SQL** | Workspace → `.bundle/finserv_lakehouse/dev/files/src/pipeline/03_gold_aggregations.sql` |

---

## Pre-Demo Checklist (5 minutes before call)

- [ ] Dashboard tab open in browser (not loading on first click)
- [ ] Pipeline UI open in second tab (shows green graph)
- [ ] Bronze notebook open in third tab (cells visible)
- [ ] `databricks.yml` open in fourth tab (shows bundle structure)
- [ ] Zoom screen share ready — share specific window, not desktop
- [ ] Water on desk

---

## Choosing Your Persona Flow

```
Is the audience...
│
├── Engineers / Platform Team?
│   └── → Start with Bronze notebook → Pipeline UI → databricks.yml → Dashboard
│       Flow: Persona 1 (45 min) → Persona 2 (15 min) → close
│
├── Analysts / Risk Team?
│   └── → Start with Dashboard → drill-down story → data quality Q&A
│       Flow: Persona 2 (30 min) → Persona 1 brief (15 min) → close
│
└── Executives / C-Suite?
    └── → Start with Revenue Analytics tab → Risk Intelligence → Pipeline as "how it works"
        Flow: Persona 3 (20 min) → Persona 2 (10 min) → technical depth only if asked
```

---

## Full End-to-End Demo Flow (60 minutes, mixed audience)

### Act 1 — The Problem (5 min)
**Don't show anything yet.** Ask:
1. "How does your risk team get their morning briefing today?"
2. "How long does it take new transaction data to become a business report?"
3. "What's your current pipeline failure rate?"

Use their answers to frame the demo.

---

### Act 2 — Bronze: Data at Scale (10 min)
**Persona 1 audience**

Open Bronze notebook. Narrate the `spark.range()` pattern.
> *"100K transactions in 5 seconds. Same code at 1 million rows — we change one number."*

Show validation output:
```
bronze_dim_customers:       200
bronze_dim_accounts:      2,000
bronze_fact_transactions: 100,000
```

**What the customer feels:** "They built that fast. My team could build that fast."

---

### Act 3 — Silver/Gold: Declarative Pipeline (10 min)
**Persona 1 audience**

Open Pipeline UI. Show the lineage graph (Bronze → Silver → 3 Gold tables).

Open `02_silver_transforms.sql` — point to:
- Quality WHERE clause: *"Fail early at Silver."*
- `is_high_risk` derived column: *"Computed once, used everywhere in Gold."*
- `CLUSTER BY`: *"Liquid Clustering — no manual partition tuning."*

Open `03_gold_aggregations.sql` — show 3 MVs:
- *"These 35 and 4,253 rows are what the dashboard queries. Not 100,000."*

> *"The entire Silver + Gold layer ran in 42 seconds. Serverless. Zero infrastructure."*

---

### Act 4 — Dashboard: The Business Layer (20 min)
**All personas**

**Page 1: Executive Overview** (5 min)
- 6 KPIs: Volume, Risk Rate, Flagged, Approved, Avg Risk Score
- Dual-line daily chart: "Volume vs High-Risk — your early warning system"
- Status pie + Category bar: "Operational health + spend distribution"

**Page 2: Risk Intelligence** (8 min)
- Grouped bar (Segment × Risk Tier): "Risk committee view"
- Category risk rate: "Where is fraud concentrated?"
- Region pie: "Geographic exposure"
- Monthly trend lines: "Seasonality patterns"
- Detail table: "Your daily triage queue, replacing Excel"

**Page 3: Revenue Analytics** (7 min)
- Stacked bar (Segment × Risk Tier): "Customer profitability matrix"
- Account type pie: "Product mix — which products drive per-transaction value?"
- Monthly stacked bar: "Full-year revenue story by category"
- Regional grouped bar: "Geographic P&L"

**Filters demo (2 min):**
- Apply: Merchant Category = Travel + Risk Tier = High
> *"Travel transactions for high-risk customers only. Built a risk report in 10 seconds."*

---

### Act 5 — Asset Bundle: The CI/CD Story (5 min)
**Engineering/Architect audience**

Show `databricks.yml`:
```yaml
resources:
  pipelines: [finance_medallion]
  jobs:
    finance_orchestrator:
      tasks: [generate_bronze → run_pipeline]  # DAG wiring
```

> *"One command: `databricks bundle deploy`. GitHub Actions runs this on every merge. Infrastructure as code. Reproducible, auditable, version-controlled."*

---

### Act 6 — The "What's Next" Close (10 min)
Frame the next steps based on audience:

**Engineering:** "Add streaming tables for real-time latency, EXPECT constraints for data quality, CI/CD integration."

**Risk/Analyst:** "Genie Space for NL queries, Model Serving for ML risk scores, scheduled alerts when risk rate exceeds threshold."

**Executive:** "Unity Catalog governance across all your data products. 4-week POV on your highest-priority use case. Migration path from existing stack."

---

## Power Moments — Quotes That Land

1. *"Same code at 100 rows or 1 million — you change one number."*
2. *"The pipeline ran in 42 seconds. Provisioning is fixed overhead, execution is instant."*
3. *"The dashboard never touches 100,000 rows. It queries 35 pre-aggregated rows. That's why it loads in under a second."*
4. *"Your risk team's morning briefing — automated, filterable, drillable. No Excel. No data requests. No 24-hour lag."*
5. *"One file deploys the entire data product — pipeline, job, dashboard. That's your CI/CD story."*
6. *"What business question takes your team days to answer today that you'd want answered every morning?"*

---

## Demo Fail Recovery Protocols

| What fails | Recovery |
|------------|----------|
| Dashboard doesn't load | Pivot to SQL query demo: `SELECT ... FROM workspace.finserv.gold_txn_by_category` |
| Pipeline in FAILED state | "Let me show you how we debug" — open Events tab, show error → fix → re-trigger (2 min) |
| Tables missing rows | Run validation SQL live: shows Bronze counts → powerful data quality demo |
| Slow warehouse | "Serverless auto-scales — this is cold start. Warm it takes under 1 sec." |
| Auth error | Pre-login before the call. PAT tokens are stable. Have a backup screenshot. |

---

## Files in This Demo Package

```
docs/demo_flows/
├── MASTER_DEMO_GUIDE.md          ← You are here
├── persona_01_data_engineer.md   ← Full engineering walkthrough
├── persona_02_risk_analyst.md    ← Risk ops + dashboard drill-down
└── persona_03_executive.md       ← CFO/executive business story

src/
├── notebooks/01_generate_bronze.py     ← Bronze generation (spark.range)
├── pipeline/02_silver_transforms.sql   ← Silver MV (SDP)
├── pipeline/03_gold_aggregations.sql   ← Gold MVs × 3 (SDP)
├── pipeline/04_validate.sql            ← Validation queries
└── dashboard/dashboard.json            ← 3-page AI/BI dashboard
```
