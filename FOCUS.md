# 🎯 Interview Focus — Where to Find Everything

**Interview: Sr. Databricks SA | Final Round**
**Workspace:** dbc-ad74b11b-230d.cloud.databricks.com

---

## 📂 Active Project — Demo for Tomorrow

```
finserv_lakehouse/
├── src/
│   ├── notebooks/01_generate_bronze.py       ← spark.range() Bronze generation
│   ├── pipeline/02_silver_transforms.sql     ← Silver MV (SDP)
│   ├── pipeline/03_gold_aggregations.sql     ← Gold MVs × 3 (SDP)
│   └── dashboard/dashboard.json             ← 3-page AI/BI dashboard
├── docs/
│   ├── demo_flows/
│   │   ├── MASTER_DEMO_GUIDE.md             ← START HERE before the call
│   │   ├── persona_01_data_engineer.md      ← Engineering walkthrough
│   │   ├── persona_02_risk_analyst.md       ← Risk ops drill-down
│   │   └── persona_03_executive.md          ← CFO / exec business story
│   └── BUILD_REPORT.md                      ← Build stats, bugs fixed, learnings
├── databricks.yml                           ← Asset Bundle (pipeline + job)
└── README.md                               ← Architecture + Mermaid diagram
```

---

## 🔗 Live Assets (Databricks)

| Asset | Link |
|-------|------|
| **Dashboard** (published) | https://dbc-ad74b11b-230d.cloud.databricks.com/dashboardsv3/01f122e33209151e99925fda8cff3088/published |
| **Pipeline** | Lakeflow Pipelines → `[dev] finance_medallion` |
| **Job** | Workflows → `[dev] finance_orchestrator` |
| **Workspace folder** | https://dbc-ad74b11b-230d.cloud.databricks.com/browse/folders/3401527313137932 |

---

## 📚 Interview Prep

```
coding-interview-prep/
├── PLAN.md                 ← Interview strategy
├── cheat-sheets/           ← Quick reference cards
├── practice/               ← Practice scenarios
└── sample-prompts/         ← Example interview prompts
```

---

## ⚙️ Config Files (root)

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Main agent config + workspace details |
| `justfile` | All CLI shortcuts (`just sql`, `just preflight`, etc.) |
| `.mcp.json` | MCP server config (SP profile) |

---

## 🗄️ Archive (not needed tomorrow)

```
archive/
├── practice-runs/          ← retail, media, payments, finance, wegmans (wealth_mgmt), etc.
├── misc-files/             ← old scripts, JSON artifacts, loose root files
└── old-tools/              ← scripts/, dbx-tools/, ai-dev-kit/, logs/, docs/
```

---

## ✅ Pre-Interview Checklist

```bash
just preflight              # auth + warehouse check
just counts finserv         # verify all 7 tables have rows
just sql "SELECT current_user()"  # confirm SQL warehouse works
```

Then open 4 browser tabs:
1. Dashboard (link above)
2. Lakeflow Pipelines → finance_medallion
3. Workspace folder (Bronze notebook)
4. `finserv_lakehouse/docs/demo_flows/MASTER_DEMO_GUIDE.md`
