# CLAUDE.md — Databricks Sr. SA Interview

**Interview: Sr. Databricks SA | Wednesday March 11, 2026**
**Profile: `slysik` | User: `slysik@gmail.com` | Catalog: `dbx_weg`**
**MCP: adb-7405619449104571.11.azuredatabricks.net (configured in `.mcp.json`, profile `slysik`)**

---

## MEMORY RULES — CLAUDE CODE

**Single source of truth:** `.pi/skills/*/SKILL.md` files for patterns, `CLAUDE.md` for config/routing.
- **DO NOT** read or write `tasks/lessons.md` — that file is owned by pi sessions only
- **DO NOT** create or write `MEMORY.md` in this project — pi owns memory persistence
- **DO** save new patterns/learnings to the relevant `.pi/skills/*/SKILL.md`
- **DO** update `CLAUDE.md` routing table or coding rules if a project-level default changes
- **DO** update `elle-core.md` rules only if the user explicitly asks

---

## OPERATING PRINCIPLE

Act as a **Senior Databricks Solutions Architect**. Don't ask unnecessary questions — state assumptions and build. Narrate decisions while coding (why this feature, where quality is enforced, how it scales). Correctness first, then optimize.

---

## INTERVIEW WORKFLOW

Prompt arrives → Scaffold project → State assumptions → Generate data → Build Bronze → Silver → Gold → (SDP / Dashboard if asked) → Validate → Git commit

**Do not** over-plan. Build incrementally, narrate as you go.

### Step 0: Project Scaffold (ALWAYS first)
1. **Read `.pi/skills/repo-best-practices/SKILL.md` FIRST** — creates clean project directory
2. Determine domain from prompt → `{domain}_lakehouse/` subdirectory
3. Scaffold: README.md, databricks.yml, .gitignore, docs/, tests/, src/ structure
4. ~30 seconds — then move to code generation

### Step 1: Data Generation (ALWAYS follow)
1. **Read `.pi/skills/spark-native-bronze/SKILL.md`** before writing any data gen code
2. `spark.range(N)` for all row generation — NO Faker, NO Pandas, NO Python loops
3. Dims ≤ 6 columns, direct to Bronze Delta, broadcast join into fact
4. Same code scales 100 → 1M by changing one param
5. PySpark for Bronze, SQL for Silver/Gold (SDP)
6. All code written INTO the scaffold paths: `src/notebooks/`, `src/pipeline/`

---

## INTERVIEW-DAY CHECKLIST (before the call)
- [ ] Start `interview-cluster` 10 min early (takes ~3 min to boot)
- [ ] Verify PAT token not expired: `databricks -p slysik auth describe`
- [ ] If auth fails, generate new PAT from workspace UI → Settings → Developer → Access tokens
- [ ] When scaling DataFrames, scale ALL related tables (fact + detail) to keep join keys aligned
- [ ] Paste code into notebooks with **Cmd+Shift+V** (no formatting)
- [ ] If notebook cell stuck "Waiting", detach/reattach cluster
- [ ] Dashboard publish: ALWAYS use `embed_credentials: false` (personal MS account flakes with embedded)
- [ ] Jobs: trigger from **UI "Run now"** if CLI fails with "principal inactive" — browser session works
- [ ] **Root cause of all auth flakes:** personal MS account (@gmail.com via live.com) SCIM `active: false`. Fix: service principal or org account

## PI EXTENSION: dbx-tools (PREFER OVER RAW CLI)

**Location:** `.pi/extensions/dbx-tools.ts` — custom Databricks tools that eliminate CLI brittleness.

| Tool | Replaces | Why Better |
|------|----------|------------|
| `dbx_auth_check` | `databricks auth describe` | Returns structured ok/fail |
| `dbx_cluster_status` | `clusters get` + JSON parse | One call, clean output |
| `dbx_run_notebook` | `runs/submit` + polling loop | Handles submit + poll + timeout in one call |
| `dbx_poll_pipeline` | Manual pipeline poll loop | Find-by-name + start + poll in one call |
| `dbx_validate_tables` | Multiple SQL count queries | One call validates entire schema |
| `dbx_sql` | Raw SQL Statements API | Clean output with column headers |
| `dbx_deploy_dashboard` | POST/PATCH + publish dance | Create-or-update + publish in one call |
| `dbx_cleanup` | Manual delete loops | Pipelines → tables → jobs → dashboards in correct order |

**Always prefer these tools over raw `databricks` CLI commands when running in pi.**

---

## CLI GOTCHAS — CRITICAL (learned 2026-03-11 test run)

- **`databricks api get --query` is BROKEN** on macOS system Python 3.9. Use URL params: `api get "/api/2.1/jobs/runs/get?run_id=$ID"`
- **`databricks pipelines list` doesn't exist** — use `pipelines list-pipelines`
- **Pipeline list = flat JSON array**, Jobs list = `{"jobs": [...]}`
- **`DROP METRIC VIEW` is invalid SQL** — use `DROP VIEW IF EXISTS`
- **Multi-statement SQL via Statements API fails** — one statement per call
- **SDP pipeline poll every 20 sec** — completes in 1-2 cycles typically (~50 sec total)
- **Cleanup order: pipelines → tables → jobs → dashboards → workspace folders**

---

## WORKSPACE — QUICK COMMANDS

**Active workspace:** `dbx-interview` (West US 3) | Auth: PAT token
**Cluster:** `interview-cluster` (0310-193517-r0u8giyo) — 4-core single node, 16.4 LTS
**Catalog:** `interview` | **Schema:** `retail` | **Volume:** `/Volumes/interview/retail/raw_data`
**SDP Pipeline:** `retail_medallion` (ac4d06ae-c2f5-4d12-8f86-a886f6d248d5) — serverless
**SQL Warehouse:** `b89b264d78f9d52e` (Serverless Starter Warehouse)

```bash
just dbx-auth                          # Check auth
just dbx-sql "SELECT 1"               # Run SQL via serverless
just dbx-catalogs                      # List catalogs
just dbx-schemas dbx_weg               # List schemas
just dbx-tables dbx_weg bronze         # List tables
just nb-upload <local> <workspace>     # Upload notebook
just nb-upload-all                     # Upload all notebooks
```

---

## SKILL ROUTING — READ BEFORE BUILDING

Skills load on-demand with full patterns, gotchas, and code templates. **Always read the relevant SKILL.md before building that component.**

| Interview Task | Skill to Read |
|---|---|
| **Project scaffold (ALWAYS FIRST)** | `.pi/skills/repo-best-practices/SKILL.md` |
| **Synthetic data + Bronze + SDP + Dashboard + Bundle** | `.pi/skills/spark-native-bronze/SKILL.md` + `sdp-and-dashboard-patterns.md` |
| **SDP / Lakeflow pipelines** | `.agents/skills/spark-declarative-pipelines/SKILL.md` |
| **AI/BI Dashboard** | `.agents/skills/databricks-aibi-dashboards/SKILL.md` |
| **DBSQL / SQL features** | `.agents/skills/databricks-dbsql/SKILL.md` |
| **Unity Catalog / Volumes** | `.agents/skills/databricks-unity-catalog/SKILL.md` |
| **Structured Streaming** | `.agents/skills/databricks-spark-structured-streaming/SKILL.md` |
| **Jobs / Workflows** | `.agents/skills/databricks-jobs/SKILL.md` |
| **Asset Bundles (CI/CD)** | `.agents/skills/asset-bundles/SKILL.md` |
| **Genie Spaces** | `.agents/skills/databricks-genie/SKILL.md` |
| **Model Serving** | `.agents/skills/model-serving/SKILL.md` |
| **Vector Search** | `.agents/skills/databricks-vector-search/SKILL.md` |
| **SA knowledge base** | `.pi/skills/databricks-sa/SKILL.md` |
| **Databricks docs lookup** | `.agents/skills/databricks-docs/SKILL.md` |

---

## CODING RULES — NON-NEGOTIABLE

### Always
- Explicit schema (`StructType`) — never infer in Silver or Gold
- Full 3-level UC namespace: `catalog.schema.table`
- Type-annotate functions: `def fn(df: DataFrame) -> DataFrame:`
- Chain transforms — don't reassign `df` in loops
- Delta for all persisted medallion layers
- `dbutils.secrets.get()` — never hardcode credentials
- Unique `checkpointLocation` per streaming query
- Deterministic sort + `row_number()` before any dataset split (never `limit()`)
- Bronze metadata: `ingest_ts`, `source_system`, `batch_id`
- Silver: dedup on natural key, UTC timestamps, null handling
- Gold: pre-aggregated, stable column contract

### Never
- Python UDF where `F.*` built-in exists
- `collect()` / `toPandas()` on non-trivial data
- `SELECT *` in Silver or Gold
- Partition on high-cardinality columns (UUID, user_id)
- `repartition()` to reduce — use `coalesce()`
- Schema inference in Silver/Gold
- Actions (`collect`, `count`, `save`) inside Lakeflow dataset-definition functions
- Faker / Pandas / Python loops for large fact generation — use `spark.range()` + native cols
- Intermediate parquet-to-Volume-to-Delta hop for synthetic data — write direct to Bronze Delta
- Dimension tables with > 6 columns — keep lean, broadcastable, easy to walk through
- Repeated `count()` after every step — one validation pass at end

### Standard Imports
```python
import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.window import Window
```

---

## ARCHITECTURE DEFAULTS

| Decision | Default |
|---|---|
| Data generation | `spark.range()` native, dims ≤ 6 cols, direct to Bronze Delta, scale by param only |
| Cloud file ingestion | Auto Loader |
| Managed pipeline | Lakeflow Spark Declarative Pipelines (`from pyspark import pipelines as dp`) |
| Custom upsert | Delta MERGE (seed first batch, merge subsequent) |
| New table layout | Liquid clustering (not legacy partitioning) |
| CDC | `create_auto_cdc_flow()` (only for true CDC) |
| Governance | Unity Catalog — 3-level namespace everywhere |
| BI serving | Databricks SQL / AI/BI Dashboards |
| Streaming trigger | `availableNow=True` for serverless; `processingTime` for sustained |
| Perf tuning | AQE enabled, broadcast small dims, discuss partition count |

---

## MEDALLION LAYERS

```
Bronze → Raw. Append-only. NO business logic. Metadata columns. Full source fidelity.
Silver → Typed. Deduped. Null-handled. Explicit schema. Reusable business semantics.
Gold   → Consumption-shaped. Pre-aggregated. Stable contract for BI/ML/serving.
```

---

## NARRATION CHECKLIST (say these while coding)

1. What you're building and why
2. Why you chose that Databricks feature over alternatives
3. Where data quality is enforced
4. How the design scales (AQE, broadcast, partition awareness)
5. What you'd productionize next (monitoring, CI/CD, cost)

---

## VALIDATION — RUN AFTER EVERY LAYER

```sql
-- Row counts across layers
SELECT 'bronze' AS layer, COUNT(*) AS rows FROM dbx_weg.bronze.{table}
UNION ALL SELECT 'silver', COUNT(*) FROM dbx_weg.silver.{table}
UNION ALL SELECT 'gold', COUNT(*) FROM dbx_weg.gold.{table};

-- Duplicate check (Silver)
SELECT {key}, COUNT(*) cnt FROM dbx_weg.silver.{table} GROUP BY {key} HAVING cnt > 1;

-- Null audit
SELECT COUNT(*) total, SUM(CASE WHEN {key} IS NULL THEN 1 ELSE 0 END) null_keys FROM dbx_weg.silver.{table};

-- Delta health
DESCRIBE DETAIL dbx_weg.silver.{table};
DESCRIBE HISTORY dbx_weg.silver.{table} LIMIT 5;
```

---

## REPO STRUCTURE

```
/
├── CLAUDE.md                    # This file
├── .mcp.json                   # MCP server config
├── justfile                    # Workspace commands
├── databricks.yml              # Asset Bundle config (root-level)
│
├── {domain}_lakehouse/          # ← Interview project (created per prompt)
│   ├── databricks.yml           # Project bundle config
│   ├── README.md                # Architecture + Mermaid diagram
│   ├── .gitignore
│   ├── src/
│   │   ├── notebooks/           # PySpark notebooks (full inline code)
│   │   │   └── 01_generate_bronze.py
│   │   └── pipeline/            # Raw SQL for SDP (no notebook headers)
│   │       ├── 02_silver_transforms.sql
│   │       ├── 03_gold_aggregations.sql
│   │       └── 04_validate.sql
│   ├── docs/
│   │   └── architecture.md      # Mermaid + design decisions
│   └── tests/
│       └── README.md
│
├── notebooks/                   # Legacy / scratch notebooks
├── src/                         # Legacy pipeline code
└── tests/                       # pytest + chispa
```
