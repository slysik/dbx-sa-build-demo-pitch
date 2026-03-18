# 🔧 Persona 1: Data Engineer / Platform Team
## Demo Flow — "How We Built This in Under 10 Minutes"

**Customer Role:** Data Engineer, Platform Architect, MLOps Lead
**Their Problem:** "Our pipelines are brittle, hard to maintain, and take weeks to deliver new data products."
**Your Goal:** Show that Databricks reduces pipeline complexity to declarative SQL, eliminates infra management, and delivers production-quality data in minutes.

---

## Opening Statement (30 seconds)

> *"Let me show you how we built a full medallion lakehouse for a finance use case — 100,000 transactions, three Gold analytical marts, and a live dashboard — entirely with serverless compute. No cluster management. No infra tickets. You'll see exactly how your team would work day-to-day."*

---

## Step-by-Step Walkthrough

### 🟫 BRONZE — Data Ingestion (2 minutes)

**Navigate to:** Workspace → `finserv_lakehouse` folder → `01_generate_bronze`

**Narrate:**
> *"Bronze is our raw layer — source-faithful, append-only, and enriched with just three metadata columns: `ingest_ts`, `source_system`, and `batch_id`. That's our data lineage contract."*

**Point out:**
- `spark.range(N)` at top — "This generates 100K rows distributed across the cluster. Same code at 1M rows, zero changes."
- FK modulo pattern — "Modulo guarantees referential integrity without maintaining lookup tables."
- Broadcast join — "Dims are 200 and 2000 rows — they fit in memory on every executor. Zero shuffle, zero skew."
- `overwriteSchema: true` — "Safe re-runs during development. In production we'd append."

**Run:** Cell 7 (write statement) — watch the 3 tables write in ~5 seconds.

**Show validation (Cell 8):**
```
bronze_dim_customers:    200 rows
bronze_dim_accounts:   2,000 rows
bronze_fact_transactions: 100,000 rows
```

**Key Quote:** *"We went from idea to 100K rows in Delta in under 30 seconds. No Spark cluster to configure, no YAML overhead."*

---

### 🥈 SILVER — SDP Declarative Pipeline (3 minutes)

**Navigate to:** Lakeflow Pipelines → `[dev] finance_medallion`

**Narrate while showing the pipeline graph:**
> *"Silver is where business logic lives. We use Lakeflow Spark Declarative Pipelines — you write SQL, Databricks handles incremental processing, checkpointing, and retry logic automatically."*

**Open** `02_silver_transforms.sql` in the workspace. Walk through:
```sql
-- Quality gate — at Silver boundary, not Gold
WHERE txn_id IS NOT NULL AND amount > 0 AND txn_date BETWEEN '...' AND '...'

-- Derived column — high-risk flag computed once, reused everywhere
CASE WHEN risk_score > 60 OR txn_status = 'Flagged' THEN TRUE ELSE FALSE END AS is_high_risk

-- CLUSTER BY — replaces legacy partitioning, handles skew automatically
CLUSTER BY (txn_date, merchant_category)
```

**Key Talking Points:**
- "Quality gates are in Silver, not Gold — fail early, fail loud."
- "Liquid Clustering instead of `PARTITION BY`. Databricks auto-optimizes file layout as data grows."
- "`CREATE OR REFRESH MATERIALIZED VIEW` — Databricks tracks what's changed and only reprocesses deltas."
- "Pipeline ran in 42 seconds for 100K rows — provisioning is fixed overhead, execution scales linearly."

**Show Pipeline UI:**
- Green checkmarks on Silver + 3 Gold MVs
- Lineage graph: Bronze → Silver → Gold 1, 2, 3
- "This lineage is tracked in Unity Catalog automatically — every table knows its upstream source."

---

### 🥇 GOLD — Analytical Marts (2 minutes)

**Open** `03_gold_aggregations.sql`. Show 3 MVs:

| MV | Purpose | Rows |
|----|---------|------|
| `gold_txn_by_category` | Merchant category × month | ~960 |
| `gold_segment_risk` | Customer segment × risk tier | ~35 |
| `gold_daily_risk` | Day-level risk intelligence | ~4,253 |

**Narrate:**
> *"Gold is consumption-shaped — pre-aggregated for BI and ML. The dashboard never touches Silver or Bronze. Gold is the contract."*

**Key Quote:** *"Dashboard queries run against 35-4,253 rows, not 100,000. That's why everything loads in under a second."*

---

### 📦 ASSET BUNDLE — Production Deploy (1 minute)

**Open** `databricks.yml`. Show:
```yaml
resources:
  pipelines:
    finance_medallion: ...
  jobs:
    finance_orchestrator:
      tasks:
        - generate_bronze → run_pipeline (DAG wiring)
```

**Narrate:**
> *"This one file defines the entire data product — pipeline, job, DAG dependencies. One command: `databricks bundle deploy`. That's our CI/CD story. In production, GitHub Actions runs `bundle validate` on every PR and `bundle deploy` on merge to main."*

**Discussion Points to Raise:**
- "In production we'd add `dev/staging/prod` targets — same config, different catalogs."
- "We'd add SDP `EXPECT` constraints on Silver for data quality monitoring with alerting."
- "Service principal as `run_as` identity — eliminates personal credential dependency."

---

## Close (30 seconds)

> *"What you just saw: 100K transactions, Bronze → Silver → Gold → Dashboard, deployed from a single YAML file, running on serverless compute with zero cluster management. Your engineers focus on SQL and business logic — Databricks handles everything else."*

**Hand off to:** Risk Analyst persona or open Dashboard directly.

---

## Objection Handling

| Objection | Response |
|-----------|----------|
| "We already have Spark pipelines in Airflow" | "SDP is the managed layer on top of Spark. You keep your orchestration pattern, remove the pipeline plumbing." |
| "How does this handle schema evolution?" | "Auto Loader + `overwriteSchema` + MV auto-refresh — Silver picks up new columns on the next pipeline run." |
| "What about testing?" | "Same `spark.range()` data gen runs in CI — chispa for unit tests, SDP `EXPECT` for integration." |
| "Is serverless more expensive?" | "No cluster idle cost. You pay only when executing. For batch workloads, typically 30-50% cheaper." |
