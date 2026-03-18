# finserv_lakehouse — Build Report

**Build date:** 2026-03-18  
**Schema:** `workspace.finserv`  
**Workspace:** `dbc-ad74b11b-230d.cloud.databricks.com`

---

## Row Counts (validated)

| Layer | Table | Rows |
|---|---|---|
| Bronze | `bronze_dim_customers` | 200 |
| Bronze | `bronze_dim_accounts` | 2,000 |
| Bronze | `bronze_fact_transactions` | 100,000 |
| Silver | `silver_transactions` | 100,000 |
| Gold | `gold_txn_by_category` | 1,303 |
| Gold | `gold_segment_risk` | 44 |
| Gold | `gold_daily_risk` | 4,380 |

## Revenue Reconciliation

| Layer | Total Revenue |
|---|---|
| Bronze | $166,991,362.86 |
| Silver | $166,991,362.86 |
| Gold (category rollup) | $166,991,362.86 |

✅ **All three layers match exactly.**

---

## Pipeline IDs

| Resource | ID |
|---|---|
| SDP Pipeline | `05ba7758-cf42-4a2f-9033-7a301b09c3f8` |
| Dashboard | `01f123059a321a288cbedf386dba1076` |
| Bronze Run ID | `566534070175236` |

## URLs

- **Git Folder:** https://dbc-ad74b11b-230d.cloud.databricks.com/browse/folders/3401527313137932?o=1562063418817826
- **SDP Pipeline:** https://dbc-ad74b11b-230d.cloud.databricks.com/pipelines/05ba7758-cf42-4a2f-9033-7a301b09c3f8?o=1562063418817826
- **Bronze Run:** https://dbc-ad74b11b-230d.cloud.databricks.com/jobs/runs/566534070175236?o=1562063418817826
- **Dashboard:** https://dbc-ad74b11b-230d.cloud.databricks.com/dashboards/01f123059a321a288cbedf386dba1076?o=1562063418817826

---

## Timing

| Phase | Duration |
|---|---|
| Bronze generation (100K rows) | ~75s |
| SDP pipeline (Silver + Gold) | ~47s |
| Total | ~2 min |
