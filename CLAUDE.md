# CLAUDE.md — Databricks Sr. SA Interview

**Interview: Sr. Databricks SA | Final Round**
**Profile: `slysik-aws` | Workspace: `dbc-ad74b11b-230d.cloud.databricks.com` (AWS)**
**MCP: dbc-ad74b11b-230d.cloud.databricks.com (configured in `.mcp.json`, profile `slysik-aws-sp`)**
**User: `slysik@gmail.com` | SP: `dbx-ssa-coding-agent`**

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
- [ ] Verify auth: `just dbx-auth` — should show `slysik@gmail.com` via PAT
- [ ] Verify SQL warehouse is running: `just wh-status` (if STOPPED: `just wh-start`)
- [ ] Verify SQL works: `just sql "SELECT current_user()"` — must return `slysik@gmail.com`
- [ ] Verify workspace is clean: `SHOW SCHEMAS IN workspace` → only `default` + `information_schema`
- [ ] No cluster needed — all compute is serverless (notebooks + SDP pipelines)
- [ ] When scaling DataFrames, scale ALL related tables (fact + detail) to keep join keys aligned
- [ ] Paste code into notebooks with **Cmd+Shift+V** (no formatting)
- [ ] Dashboard publish: ALWAYS use `embed_credentials: false`
- [ ] Dashboard parent folder: `/Users/slysik@gmail.com/dashboards` — verify it exists (`workspace list`)
- [ ] Demo domain: `workspace.finserv` ONLY — never `finance`, `retail`, or other schemas

### Auth Failover (profiles configured)
| Profile | Auth Type | When to Use |
|---------|-----------|-------------|
| `slysik-aws` | **PAT** ✅ (configured 2026-03-18) | Primary — all CLI, bundle, notebook runs |
| `slysik-aws-sp` | OAuth M2M (SP: `dbx-ssa-coding-agent`) | SCIM-immune auto-failover in dbx-tools extension |

**PAT configured:** `slysik-aws` profile has a valid PAT in `~/.databrickscfg`. Auth is clean — no OAuth U2M needed.
**If PAT expires:** Workspace UI → Settings → Developer → Access tokens → Generate new token → replace `token = dapi...` in `~/.databrickscfg` under `[slysik-aws]`. Remove `auth_type = databricks-cli` if present — it conflicts with PAT.
**AWS = no SCIM issues:** `current_user()` returns `slysik@gmail.com` (human email, not SP UUID). Pipeline `run_as_user_name` is clean. No Azure-style SCIM flakiness.
**dbx-tools auto-failover:** If primary fails with auth error, tools retry with `slysik-aws-sp` automatically.
**MCP profile:** `.mcp.json` uses `slysik-aws-sp`. MCP tools for Genie/Dashboard/VectorSearch CRUD.

## PI EXTENSION: dbx-tools (PREFER OVER RAW CLI)

**Location:** `.pi/extensions/dbx-tools.ts` — custom Databricks tools that eliminate CLI brittleness.

| Tool | Replaces | Why Better |
|------|----------|------------|
| `dbx_auth_check` | `databricks auth describe` | Returns structured ok/fail |
| `dbx_cluster_status` | `clusters get` + JSON parse | One call, clean output |
| `dbx_run_notebook` | `runs/submit` + polling loop | ⚠️ BROKEN for serverless — use direct `api post /api/2.1/jobs/runs/submit` with tasks array |
| `dbx_poll_pipeline` | Manual pipeline poll loop | Find-by-name + start + poll in one call |
| `dbx_validate_tables` | Multiple SQL count queries | One call validates entire schema |
| `dbx_sql` | Raw SQL Statements API | Clean output with column headers |
| `dbx_deploy_dashboard` | POST/PATCH + publish dance | ⚠️ BROKEN — uses REPO path as parent. Always use direct `api post` with `/Users/slysik@gmail.com/dashboards` |
| `dbx_cleanup` | Manual delete loops | Pipelines → tables → jobs → dashboards in correct order |

**Always prefer these tools over raw `databricks` CLI commands when running in pi.**

### Tool Selection: dbx-tools vs MCP

| Task | Use | Why |
|------|-----|-----|
| SQL execution | **dbx-tools** (`dbx_sql`) | Auth failover to SP |
| Genie Space CRUD | **MCP** (`create_or_update_genie`) | Abstracts proto format, 22:1 call reduction |
| Dashboard deploy | **dbx-tools** (`dbx_deploy_dashboard`) | Auth failover + publish in one call |
| Table exploration | **MCP** (`get_table_details`) | Schemas + stats + cardinality in 1 call |
| Vector Search / Agent Bricks | **MCP** | Complex multi-step CRUD abstracted |
| Pipeline polling | **dbx-tools** (`dbx_poll_pipeline`) | No MCP equivalent |
| Notebook execution | **dbx-tools** (`dbx_run_notebook`) | No MCP equivalent |
| Cleanup | **dbx-tools** (`dbx_cleanup`) | Correct deletion order in one call |
| Auth check | **dbx-tools** (`dbx_auth_check`) | SP auto-failover |
| Genie questions | **MCP** (`ask_genie`) | Structured response with columns/data |

**Heuristic:** MCP for complex resource CRUD (proto/serialization). dbx-tools for operations (polling, cleanup, auth, SQL).

---

## CLI GOTCHAS — CRITICAL

### AWS workspace-specific
- **GRANT to SP must use `client_id`, not display name** — `GRANT ... TO \`64e5d26a-41fd-4089-b71b-c6b83154bd91\`` not `\`dbx-ssa-coding-agent\``
- **Workspace admin implicit UC access** — `SHOW GRANTS` won't show admin-derived privileges; workspace admins have full UC access without explicit grants
- **Serverless-only** — no cluster available; notebooks run on serverless compute (omit `existing_cluster_id` in runs/submit API)
- **Notebook serverless submit** — `dbx_run_notebook` tool DOES NOT support serverless. Use direct API: `api post "/api/2.1/jobs/runs/submit"` with `tasks` array + `"queue": {"enabled": true}`, no cluster spec
- **Dashboard parent_path** — ALWAYS use `/Users/slysik@gmail.com/dashboards` (DIRECTORY). The git repo path is type REPO and fails. `dbx_deploy_dashboard` tool uses REPO path — always bypass with direct `api post`

### General (learned 2026-03-11 + 2026-03-18 test runs)

- **`databricks api get --query` is BROKEN** on macOS system Python 3.9. Use URL params: `api get "/api/2.1/jobs/runs/get?run_id=$ID"`
- **`databricks pipelines list` doesn't exist** — use `pipelines list-pipelines`
- **Pipeline list = flat JSON array**, Jobs list = tabular text (not JSON — read as plain text or use `api get "/api/2.1/jobs"`)
- **`DROP METRIC VIEW` is invalid SQL** — use `DROP VIEW IF EXISTS`
- **Multi-statement SQL via Statements API fails** — one statement per call
- **SDP pipeline poll every 15–20 sec** — completes in ~47–51 sec on serverless for 3 MVs
- **Cleanup order: pipelines → tables → jobs → dashboards → workspace folders**
- **`dbx_cleanup` deletes ALL dashboards workspace-wide** — not just schema-specific ones
- **`DROP SCHEMA IF EXISTS catalog.schema CASCADE`** — drops all tables + schema in one call; run after `dbx_cleanup`
- **Stale tfstate** — if `bundle deploy` fails with permission error, delete `.databricks/bundle/dev/terraform/terraform.tfstate` and redeploy
- **Bronze column naming** — name fact status/type columns with domain prefix (`txn_status`, not `status`) BEFORE broadcast join. Dim tables also have `status` → collision causes `withColumnRenamed` to rename both silently

---

## WORKSPACE — QUICK COMMANDS

**Active workspace:** `dbc-ad74b11b-230d` (AWS) | Auth: PAT ✅ (`slysik-aws` profile configured)
**Cluster:** none — workspace is serverless-only. Notebooks use serverless compute, pipelines use serverless SDP.
**Catalog:** `workspace` ✅
**Schema:** `finserv` — THE demo domain. Never use `finance`, `retail`, or other schemas for the real demo.
**SQL Warehouse:** `214e9f2a308e800d` (SQL WH — PRO serverless) ✅
**User email:** `slysik@gmail.com` ✅
**Git folder:** `/Workspace/Users/slysik@gmail.com/dbx-sa-build-demo-pitch` (ID: `3401527313137932`) — type REPO
**Dashboard folder:** `/Users/slysik@gmail.com/dashboards` — type DIRECTORY, use as `parent_path` for all dashboard deploys
**GitHub repo:** `https://github.com/slysik/dbx-sa-build-demo-pitch`

```bash
just upload-project {domain}_lakehouse   # push notebooks + SQL into Git folder
just open                                 # open Git folder in browser (+ print GitHub URL)
just open-github                         # open GitHub repo
just ls-git                              # list projects in Git folder
just ls-git {domain}_lakehouse           # list files within a project
```

```bash
just login                             # First-time OAuth login (browser popup)
just dbx-auth                          # Check auth status
just preflight                         # Full pre-flight check
just sql "SELECT current_user()"       # Verify SQL warehouse works
just cluster-start                     # Start interview cluster
just tables media                      # List tables in schema
just counts media                      # Row counts across schema
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
| **Asset Bundles (CI/CD)** | `.agents/skills/databricks-bundles/SKILL.md` (preferred, Jan 2026) or `.agents/skills/asset-bundles/SKILL.md` |
| **AI Functions (ai_classify, ai_extract, ai_forecast, ai_query, ai_gen, ai_mask etc.)** | `.agents/skills/databricks-ai-functions/SKILL.md` |
| **Genie Spaces** | `.agents/skills/databricks-genie/SKILL.md` + `sdp-and-dashboard-patterns.md` #42-59 |
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
| Notebook compute | Serverless (no cluster) — omit `existing_cluster_id` in runs/submit |
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
