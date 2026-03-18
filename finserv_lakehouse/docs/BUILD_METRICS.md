# finserv_lakehouse — Build Metrics

**Build date:** 2026-03-18 20:52 UTC  
**Schema:** `workspace.finserv`  
**Claude model:** `claude-opus-4-5`  
**Total build time:** 3m 8s

---

## ⏱ Phase Runtimes

| Phase | Duration | Notes |
|---|---|---|
| Phase 1 — Clean Slate | 8s | dbx_cleanup + DROP SCHEMA + verify |
| Phase 2 — Bundle Deploy | 22s | validate + deploy + upload |
| Phase 3 — Bronze Gen | 1m 15s | 100K rows via spark.range() serverless |
| Phase 4 — SDP Pipeline | 47s | Silver MV + 3 Gold MVs serverless |
| Phase 5 — Validate | 12s | row counts + revenue recon |
| Phase 6 — Dashboard | 6s | POST + publish lakeview |
| Phase 7 — Genie Space | 18s | create + tables + sample questions |
| **Total** | **3m 8s** | |

---

## 📊 Data Assets — Row Counts

| Layer | Table | Rows |
|---|---|---|
| Bronze | `bronze_dim_accounts` | 2,000 |
| Bronze | `bronze_dim_customers` | 200 |
| Bronze | `bronze_fact_transactions` | 100,000 |
| Silver | `silver_transactions` | 100,000 |
| Gold | `gold_daily_risk` | 4,380 |
| Gold | `gold_segment_risk` | 44 |
| Gold | `gold_txn_by_category` | 1,303 |
| | **Bronze total** | **102,200** |
| | **Silver total** | **100,000** |
| | **Gold total** | **5,727** |

---

## 💰 Revenue Reconciliation

| Layer | Total Revenue | Match |
|---|---|---|
| bronze | $166,991,362.86 | ✅ |
| silver | $166,991,362.86 | ✅ |
| gold_category | $166,991,362.86 | ✅ |
| **Reconciliation** | | **✅ MATCH** |

---

## 🏗 Databricks Assets Created

| Asset | Type | ID | URL |
|---|---|---|---|
| SDP Pipeline | Lakeflow Serverless | `05ba7758-cf42-4a2f-9033-7a301b09c3f8` | [Open](https://dbc-ad74b11b-230d.cloud.databricks.com/pipelines/05ba7758-cf42-4a2f-9033-7a301b09c3f8?o=1562063418817826) |
| Bronze Run | Serverless Notebook | `566534070175236` | [Open](https://dbc-ad74b11b-230d.cloud.databricks.com/jobs/runs/566534070175236?o=1562063418817826) |
| AI/BI Dashboard | Lakeview | `01f123059a321a288cbedf386dba1076` | [Open](https://dbc-ad74b11b-230d.cloud.databricks.com/dashboards/01f123059a321a288cbedf386dba1076?o=1562063418817826) |
| Genie Space | AI/BI Genie | `01f123083e551b77b5eaa2959201f257` | [Open](https://dbc-ad74b11b-230d.cloud.databricks.com/genie/rooms/01f123083e551b77b5eaa2959201f257?o=1562063418817826) |

---

## 🔺 Delta Health

| Table | Format | Files | Size | Liquid Clustering |
|---|---|---|---|---|
| `bronze_fact_transactions` | delta | 8 | 1.1 MB | [, ] |

---

## 🤖 AI Assets

### Genie Space

| Field | Value |
|---|---|
| Space ID | `01f123083e551b77b5eaa2959201f257` |
| Tables connected | 4 (silver_transactions, gold_txn_by_category, gold_segment_risk, gold_daily_risk) |
| Sample questions | 8 |
| Warehouse | `214e9f2a308e800d` (PRO Serverless) |
| Foundation model | Databricks Foundation Model API (auto-selected) |

**Test query result:**

> **Q:** What is the total revenue and how many transactions were high risk?
>
> **Status:** COMPLETED | **Latency:** ~6s
>
> **SQL:** `SELECT SUM(`total_revenue`) AS total_revenue, SUM(`high_risk_count`) AS high_risk_txns FROM `workspace`.`finserv`.`gold_txn_by_category` WHERE `total_revenue` IS NOT NULL AND `high_risk_count` IS NOT NULL;`
>
> **Answer:** The **total revenue** is $166,991,362.86 and there were **3,853 high risk transactions**. All values are based on the available data where both total revenue and high risk transaction counts are present.

### AI/BI Dashboard

| Field | Value |
|---|---|
| Dashboard ID | `01f123059a321a288cbedf386dba1076` |
| Warehouse | `214e9f2a308e800d` |
| Published | ✅ embed_credentials=false |
| Datasets | KPI summary, category breakdown, segment risk, daily trends |

---

## 🧠 LLM & Token Usage

| Metric | Value |
|---|---|
| Claude model (build agent) | `claude-opus-4-5` |
| Genie FM (query engine) | Databricks Foundation Model API (auto) |
| Genie test queries | 2 (1 during build, 1 in metrics) |
| API calls to Databricks | ~52 |
| SQL statements executed | ~12 |
| Notebook runs | 1 (Bronze gen, serverless) |
| Pipeline runs | 1 (SDP full refresh) |
| Est. DBU consumed | ~0.15 DBU (serverless notebook + SDP) |

---

## 🔗 All URLs

```
Git Folder:   https://dbc-ad74b11b-230d.cloud.databricks.com/browse/folders/3401527313137932?o=1562063418817826
GitHub:       https://github.com/slysik/dbx-sa-build-demo-pitch
SDP Pipeline: https://dbc-ad74b11b-230d.cloud.databricks.com/pipelines/05ba7758-cf42-4a2f-9033-7a301b09c3f8?o=1562063418817826
Bronze Run:   https://dbc-ad74b11b-230d.cloud.databricks.com/jobs/runs/566534070175236?o=1562063418817826
Dashboard:    https://dbc-ad74b11b-230d.cloud.databricks.com/dashboards/01f123059a321a288cbedf386dba1076?o=1562063418817826
Genie Space:  https://dbc-ad74b11b-230d.cloud.databricks.com/genie/rooms/01f123083e551b77b5eaa2959201f257?o=1562063418817826
```
