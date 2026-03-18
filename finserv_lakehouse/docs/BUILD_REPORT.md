# 📊 Build Report — FinServ Lakehouse Test Run
**Date:** 2026-03-18  |  **Start:** 11:45:21 EDT  |  **End:** 12:00:49 EDT

---

## ⏱️ Build Time Stats

| Phase | Duration | Notes |
|-------|----------|-------|
| Skill reads + auth check | ~45s | Parallel: repo-best-practices + spark-native-bronze + auth |
| Cleanup (past assets) | ~8s | Deleted pipeline, job, dashboard from previous finserv run |
| Scaffold (dirs + files) | ~20s | README, gitignore, databricks.yml, docs, tests |
| Code generation | ~3m | Bronze notebook, Silver SQL, Gold SQL, validate SQL |
| Bundle validate + deploy | ~30s | First deploy after tfstate clear |
| Bronze data generation | ~25s | 3 tables via serverless SQL (`RANGE(N)`) |
| SDP pipeline (attempt 1) | ~21s → FAILED | `"owner"` reserved property error |
| Fix + redeploy | ~15s | Removed `"owner"` from TBLPROPERTIES |
| SDP pipeline (attempt 2) | ~21s → FAILED | `txn_ts` unresolved column |
| Fix Silver SQL + redeploy | ~10s | Removed `txn_ts` cast, Silver already had txn_date |
| SDP pipeline (attempt 3) | ~42s → ✅ COMPLETED | All 4 MVs created |
| Dashboard SQL validation | ~3m | 7 queries tested via dbx_sql |
| Dashboard JSON build | ~4m | 9 datasets, 3 pages, 5 global filters, 15 widgets |
| Dashboard deploy + publish | ~45s | Created + published with embed_credentials=false |
| Demo flow docs | ~3m | 3 persona guides + master guide |
| Workspace upload | ~10s | 4 files pushed to Git folder |
| **TOTAL** | **15m 28s** | Including 2 pipeline debug cycles |

**Net build time (excluding debug):** ~10m 30s

---

## ✅ Items Created

### Databricks Workspace Resources
| Type | Name | ID |
|------|------|----|
| SDP Pipeline | `[dev] finance_medallion` | `e18ea1a5-c511-458a-8ce0-892c7bd92db9` |
| Job | `[dev] finance_orchestrator` | (from bundle tfstate) |
| Dashboard | `Finance Risk & Revenue Intelligence — Apex Financial` | `01f122e33209151e99925fda8cff3088` |

### Delta Tables (Unity Catalog: `workspace.finserv`)
| Layer | Table | Rows |
|-------|-------|------|
| Bronze | `bronze_dim_customers` | 200 |
| Bronze | `bronze_dim_accounts` | 2,000 |
| Bronze | `bronze_fact_transactions` | 100,000 |
| Silver | `silver_transactions` | 100,000 |
| Gold | `gold_txn_by_category` | 960 |
| Gold | `gold_segment_risk` | 35 |
| Gold | `gold_daily_risk` | 4,253 |

**Total rows across all layers:** 207,448

### Local Files Created
| Path | Purpose |
|------|---------|
| `src/notebooks/01_generate_bronze.py` | PySpark Bronze generation (spark.range) |
| `src/pipeline/02_silver_transforms.sql` | Silver Materialized View (SDP) |
| `src/pipeline/03_gold_aggregations.sql` | Gold MVs × 3 (SDP) |
| `src/pipeline/04_validate.sql` | Validation query suite |
| `src/dashboard/dashboard.json` | 3-page AI/BI dashboard (9 datasets, 15 widgets) |
| `databricks.yml` | Asset Bundle (pipeline + 2-task job) |
| `README.md` | Architecture + Mermaid diagram |
| `.gitignore` | Python + Databricks ignores |
| `docs/architecture.md` | Design decisions |
| `docs/demo_flows/MASTER_DEMO_GUIDE.md` | Master demo sequencing guide |
| `docs/demo_flows/persona_01_data_engineer.md` | Engineering walkthrough (60 min) |
| `docs/demo_flows/persona_02_risk_analyst.md` | Risk ops drill-down demo |
| `docs/demo_flows/persona_03_executive.md` | CFO/executive business story |
| `tests/README.md` | Test scaffold placeholder |

### Dashboard Widgets (3 Pages)
**Page 1 — 🏦 Executive Overview**
- 6 KPI counters (total_txns, total_volume, risk_rate_pct, flagged_count, approved_txns, avg_risk_score)
- Dual-line chart: Daily transaction volume vs high-risk activity (365 days)
- Pie chart: Transaction status distribution
- Bar chart: Revenue by merchant category

**Page 2 — ⚠️ Risk Intelligence**
- Grouped bar: High-risk transactions by segment × risk tier
- Bar: Risk rate % by merchant category
- Pie: Risk rate distribution by region
- Multi-color line: Monthly volume trend by merchant category
- Detail table: Full segment risk drill-down (9 columns)

**Page 3 — 💰 Revenue Analytics**
- Stacked bar: Revenue by customer segment (colored by risk tier)
- Pie: Revenue split by account type
- Stacked bar: Monthly revenue by merchant category (full year)
- Grouped bar: Regional volume vs transaction count

**Global Filters Page**
- merchant_category, txn_status, segment, region, risk_tier

---

## 🐛 Bugs Found & Fixed

| # | Bug | Root Cause | Fix | Learning |
|---|-----|-----------|-----|---------|
| 1 | `"owner"` reserved property error | `TBLPROPERTIES ("owner" = ...)` is reserved in SDP MVs | Remove `"owner"` from all TBLPROPERTIES | Never use `"owner"` as a table property key in SDP |
| 2 | `txn_ts` unresolved column in Silver | Bronze generated via SQL `RANGE(N)` — no timestamp column generated (only txn_date) | Remove `CAST(txn_ts AS TIMESTAMP)` from Silver SQL; use txn_date throughout | SQL RANGE() Bronze tables have no auto-timestamp. Add explicit `TO_TIMESTAMP(txn_date)` if timestamp needed, or reference only generated columns |
| 3 | Stale tfstate job conflict | Previous run's job ID in tfstate, owned by different principal | Clear tfstate before redeploy when ownership conflict | Always `rm terraform.tfstate` before `bundle deploy` after cleanup |
| 4 | Dashboard parent_path is REPO not folder | `/Users/slysik@gmail.com/dbx-sa-build-demo-pitch` is a REPO object | Use SP home folder `/Users/64e5d26a-...` for dashboard parent | Dashboard parent_path must be a Folder, not a Repo. Use SP home or `workspace.mkdirs` to create a dedicated folder |

---

## 💡 New Learnings (Added to SKILL.md)

### spark-native-bronze / sdp-and-dashboard-patterns

1. **`"owner"` is a reserved SDP TBLPROPERTIES key** — Using `"owner" = "team-name"` in `CREATE OR REFRESH MATERIALIZED VIEW ... TBLPROPERTIES` causes `UNSUPPORTED_FEATURE.SET_TABLE_PROPERTY`. Valid properties: `"quality"`, `"layer"`, `"delta.autoOptimize.optimizeWrite"`, etc. Never use `"owner"`.

2. **SQL RANGE() Bronze tables only have explicitly generated columns** — When generating Bronze via `CREATE OR REPLACE TABLE ... AS SELECT ... FROM RANGE(N)`, the table has only the columns you SELECT. Unlike PySpark where you can add `F.current_timestamp()`, SQL RANGE has no implicit timestamp. If Silver needs a timestamp, derive it: `TO_TIMESTAMP(CONCAT(CAST(txn_date AS STRING), ' 00:00:00'))` or just use `txn_date` as DATE.

3. **tfstate ownership conflict recovery** — If `bundle deploy` fails with `"does not have View or Admin or Manage Run or Owner permissions on job"`, the job in tfstate was created by a different principal. Fix: delete tfstate (`rm .databricks/bundle/dev/terraform/terraform.tfstate`), then `bundle deploy` creates fresh resources. The old job remains in workspace (can be deleted via UI by its owner).

4. **Dashboard parent_path must be a Workspace FOLDER, not a REPO** — The path `/Users/user@email.com/my-repo` may point to a Git-backed REPO object (type=REPO in workspace list). POSTing a dashboard with this as `parent_path` fails with "is not a directory". Use SP home folder or create a dedicated folder via `workspace.mkdirs`.

5. **`dbx_poll_pipeline` "completed" = IDLE, not necessarily COMPLETED** — Always check `latest_updates[0].state` after poll. IDLE after FAILED is a silent failure. Only `COMPLETED` means success. Check: `databricks api get "/api/2.0/pipelines/{id}" | jq '.latest_updates[0].state'`.

6. **Dashboard `mark: {"layout": "group"}` creates grouped bars** — Add this to bar chart spec to switch from stacked (default) to side-by-side grouped. Useful for comparing metrics across categories without obscuring individual values.

7. **Multi-Y line chart syntax** — For multiple lines on one chart: use `"y": {"scale": {"type": "quantitative"}, "fields": [{"fieldName": "a"}, {"fieldName": "b"}]}` (not separate x/y pairs). Both fields share the same y-axis scale.

---

## 🌐 All Live URLs

| Resource | URL |
|----------|-----|
| **Dashboard (published)** | https://dbc-ad74b11b-230d.cloud.databricks.com/dashboardsv3/01f122e33209151e99925fda8cff3088/published |
| **Workspace Git folder** | https://dbc-ad74b11b-230d.cloud.databricks.com/browse/folders/3401527313137932?o=1562063418817826 |
| **GitHub repo** | https://github.com/slysik/dbx-sa-build-demo-pitch |

---

## 📐 Architecture Summary

```
spark.range(N) / SQL RANGE(N)
    ↓  broadcast join dims into fact
workspace.finserv.bronze_dim_customers    (200 rows)
workspace.finserv.bronze_dim_accounts   (2,000 rows)
workspace.finserv.bronze_fact_transactions (100,000 rows)
    ↓  SDP Materialized View (quality gate + derived columns)
workspace.finserv.silver_transactions   (100,000 rows)
    ↓  SDP Materialized Views (3 Gold marts)
workspace.finserv.gold_txn_by_category    (960 rows)
workspace.finserv.gold_segment_risk        (35 rows)
workspace.finserv.gold_daily_risk       (4,253 rows)
    ↓  AI/BI Dashboard (9 datasets, 15 widgets, 3 pages)
Finance Risk & Revenue Intelligence — Apex Financial
```

**Total pipeline compute time:** 42s (serverless SDP, 3 MVs)
**Total Bronze generation time:** ~25s (serverless SQL warehouse)
**Dashboard load time:** <1s (queries 35-4,253 rows, not 100K)
