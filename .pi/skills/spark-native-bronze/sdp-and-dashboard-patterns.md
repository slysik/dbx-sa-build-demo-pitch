# SDP + Dashboard + Bundle Deployment Patterns (Supplemental Reference)

Loaded on-demand from the spark-native-bronze skill when building Silver/Gold/Dashboard.

## SDP Pipeline Gotchas

1. **Bronze tables from `spark.range()` are regular Delta — not streaming tables.** Silver/Gold must use `CREATE OR REFRESH MATERIALIZED VIEW`, NOT `CREATE OR REFRESH STREAMING TABLE`.
2. **Column availability**: Silver should only SELECT columns that exist in the Bronze table it reads. If Bronze fact was broadcast-joined with dims, those dim columns ARE in Bronze. But if Silver reads only the fact table, dim columns must come from joins in Gold.
3. **Pipeline CREATED state can last 3-5 min** — serverless compute provisioning. Don't panic or re-trigger.
4. **`RETRY_ON_FAILURE` auto-retries** — if a pipeline fails, Databricks retries automatically. Stop the pipeline before redeploying updated SQL to avoid running stale code.
5. **Pipeline creation via REST API**: Use `PUT` for updates (not `POST`). `POST` to `/api/2.0/pipelines` creates; `PUT` to `/api/2.0/pipelines/{id}` updates.
6. **`LIBRARY_FILE_FETCH_PERMISSION_DENIED`** — means the PAT expired while serverless was booting. The fix is a stable PAT, not a code change.
7. **Pipeline deploy script pattern**: Upload SQL → find-or-create pipeline → trigger → poll → validate row counts. Keep the poll loop resilient to transient auth failures.

## Metric View Patterns

1. **YAML must be in a proper SQL file** — inline JSON-escaped YAML in API calls breaks parsing. Write to `.sql` file, read and send as statement.
2. **Quoted expressions in YAML** — wrap SQL expressions in double quotes: `expr: "DATE_TRUNC('MONTH', event_date)"`. Bare expressions with single quotes break YAML parsing.
3. **Star-schema joins** — use `on: source.fk = dim_name.pk`. Reference joined columns as `dim_name.column` in dimension exprs.
4. **Query metric views** — `SELECT dim, MEASURE(measure) FROM mv GROUP BY ALL`. `SELECT *` is NOT supported.
5. **Metric views work in dashboard datasets** — just put the MEASURE() query in `queryLines`. No special handling needed.
6. **Requires serverless SQL warehouse** — classic SQL warehouses may not support metric views.

## Dashboard Deployment via REST API

### Create
```python
api_post("/api/2.0/lakeview/dashboards", {
    "display_name": "Name",
    "parent_path": f"/Users/{USER}",
    "serialized_dashboard": json.dumps(dashboard_dict),
    "warehouse_id": WH_ID,
})
```

### Update
```python
api_patch(f"/api/2.0/lakeview/dashboards/{dash_id}", {
    "display_name": "Name",
    "serialized_dashboard": json.dumps(dashboard_dict),
    "warehouse_id": WH_ID,
})
```

### Publish (ALWAYS embed_credentials=false on this workspace)
```python
api_post(f"/api/2.0/lakeview/dashboards/{dash_id}/published", {
    "embed_credentials": False,  # CRITICAL — personal MS account issue
    "warehouse_id": WH_ID,
})
```

## Asset Bundle Patterns

### Bundle Structure (Canonical)
```
my_bundle/
├── databricks.yml              # bundle name, variables, targets
├── resources/
│   ├── pipeline.yml            # SDP pipeline resource
│   └── job.yml                 # Orchestrator job resource
└── src/
    ├── notebooks/              # PySpark notebooks (Bronze gen)
    └── pipeline/               # SQL files (Silver, Gold, metric view, validate)
```

### Key Gotchas
1. **`file:` not `notebook:`** for pipeline libraries pointing to raw `.sql` files. `notebook:` expects Databricks notebook format with `-- Databricks notebook source` header.
2. **Serverless tasks** — omit all cluster config from the task YAML. No `new_cluster`, no `existing_cluster_id`.
3. **Pipeline task references** — use `${resources.pipelines.my_pipeline.id}` to reference the pipeline created by the same bundle.
4. **SQL tasks need `warehouse_id`** — always pass `${var.warehouse_id}`.
5. **`destroy` deletes SDP-managed tables** — MVs and streaming tables owned by the pipeline get dropped. Bronze tables (written by notebook) survive.
6. **Development mode** — `development: true` on pipelines enables dev mode (faster, no production triggers).
7. **Job `run_as`** — if personal identity is inactive, job can't run via CLI. Trigger from UI as workaround. Proper fix: service principal.
8. **Table ownership conflict** — SDP tables (MVs/streaming tables) are owned by one pipeline. If you create a new pipeline (e.g., via bundle) targeting the same schema, you must first delete the old pipeline AND drop its tables. Error: `TABLE_ALREADY_MANAGED_BY_OTHER_PIPELINE`. Fix: `DELETE /api/2.0/pipelines/{old_id}` then `DROP TABLE IF EXISTS` for each Silver/Gold table. Bronze tables are unaffected (they're not SDP-managed).

### Orchestrator Job Pattern (4-Task DAG)
```yaml
tasks:
  - task_key: generate_bronze        # notebook (serverless)
  - task_key: run_pipeline           # pipeline_task (SDP serverless)
    depends_on: [generate_bronze]
  - task_key: create_metric_view     # sql_task (warehouse)
    depends_on: [run_pipeline]
  - task_key: validate               # sql_task (warehouse)
    depends_on: [create_metric_view]
```

### Deploy + Run Commands
```bash
cd my_bundle
databricks bundle validate           # Check config
databricks bundle deploy             # Deploy to workspace
databricks bundle run my_job         # Run orchestrator
databricks bundle destroy --auto-approve  # Tear down
```

## Practice Run Fixes (2026-03-10) — DO NOT REPEAT THESE MISTAKES

| Mistake | Fix | Rule |
|---------|-----|------|
| `# ruff: noqa` inside `%md` cell | Put lint directives in Python cell or omit | Notebook `%md` renders ALL text as markdown |
| SDP SQL files with `-- Databricks notebook source` header | Raw SQL only for `file:` pipeline libs | `notebook:` for notebook format, `file:` for raw |
| Tried running `CREATE OR REFRESH MATERIALIZED VIEW` on serverless compute | SDP syntax = pipeline only | Upload as notebooks for **viewing**, run via pipeline |
| `sql_task.query.query_text` in job YAML | Use `notebook_task` instead | `sql_task` requires saved `query_id`, not inline SQL |
| Dashboard POST when name already exists | PATCH existing dashboard by ID | Always list dashboards first, update if exists |
| Pipeline + Job only in local YAML, not deployed | `bundle deploy` after `bundle validate` | Local YAML ≠ workspace resources |
| Orphaned `__materialization_*` tables from deleted pipeline | Query info_schema, DROP all matching | Clean schema before creating new pipeline |
| Dropped ACTIVE pipeline's materialization tables | Pipeline state corrupted → "initialization failed" | Only drop tables from DELETED pipelines (check pipeline_id in table name) |
| Notebook URL used `/browse/` path | Use `?o={ws_id}#notebook/{object_id}` | `/browse/` is for folders only |
| Stale notebooks/pipelines/dashboards from previous runs | Clean workspace before each run | Delete old artifacts → one clean folder |
| Code pushed to git before validation | Broken code in repo | Validate ALL steps THEN push to git as final step |

## Auth / Workspace Gotchas (This Workspace) — CRITICAL

**Root cause:** Personal Microsoft account (`slysik@gmail.com` via `live.com`) on Azure Databricks. The SCIM endpoint intermittently reports `active: false` for this identity. This is the #1 blocker — once fixed, the entire workflow (deploy + run) completes in ~5 minutes.

### Symptoms (all caused by the same identity issue)
| Error Message | Where It Hits |
|---|---|
| `User slysik@gmail.com does not belong to workspace` | CLI auth, API calls, pipeline file fetch |
| `Principal is not an active member of account` | Dashboard embedded credentials |
| `Job cannot run because the principal bound to the job is inactive` | Job execution (CLI and API) |
| `LIBRARY_FILE_FETCH_PERMISSION_DENIED` | SDP pipeline reading SQL files during serverless boot |

### Workarounds (current)
1. **PAT tokens** — regenerate frequently; use max TTL. Token itself is valid but identity behind it flakes.
2. **Dashboard** — publish with `embed_credentials: false`. Viewer's browser session auth works.
3. **Jobs** — trigger from **UI "Run now" button** (browser session works). CLI `bundle run` and `jobs run-now` both fail.
4. **SDP pipelines** — work once serverless compute boots (if auth holds during the 3-5 min boot window).
5. **Long-running scripts** — auth can die mid-execution. Make scripts resilient to transient failures.

### Proper Fix (do one of these)
1. **Create a service principal** — use it for `run_as` on jobs, dashboard publishing, and pipeline ownership. Eliminates personal identity dependency entirely.
2. **Switch to AAD/Entra ID org account** — if the workspace is backed by an Azure AD tenant, use a proper org identity instead of personal MS account.
3. **Contact workspace admin** — ask them to verify SCIM sync status and ensure the user is marked `active: true` persistently.

### Impact on Workflow
| Step | Without Fix | With Fix |
|---|---|---|
| `bundle deploy` | Works (usually) | Works |
| `bundle run` | ❌ Fails ~80% of time | ✅ Works |
| SDP pipeline | ⚠️ Fails if auth dies during boot | ✅ Works |
| Dashboard publish | ❌ embed_credentials broken | ✅ Both modes work |
| **Total time** | 15-30 min (retries + re-auth) | **~5 min** |

## Other Workspace Notes
1. **SQL Statements API `wait_timeout`** must be between 5s and 50s (not 60s).
2. **Serverless SDP completes in 1-3 min** — most time is compute provisioning, not execution.
3. **Serverless notebook tasks** — omit cluster config in job YAML to use serverless.
4. **DABs pipeline libraries** — use `file:` (not `notebook:`) for raw `.sql` files. `notebook:` expects Databricks notebook format.

## Test Run Learnings (2026-03-11 media_lakehouse run)

### CLI API Call Patterns
5. **`databricks api get --query` is BROKEN on macOS system Python 3.9** — returns empty response, causes JSON parse errors. **Always use URL query params instead**: `databricks api get "/api/2.1/jobs/runs/get?run_id=$RUN_ID"`.
6. **`databricks pipelines list` does NOT exist** — use `databricks pipelines list-pipelines`. The CLI subcommand name is different from what you'd expect.
7. **Pipeline list returns a flat JSON array**, not `{"statuses": [...]}`. Parse accordingly: `data=json.load(sys.stdin); for p in data: ...`.
8. **Jobs list returns `{"jobs": [...]}` dict**, not a flat array. Parse with `data.get('jobs', data)`.
9. **`DROP METRIC VIEW` syntax does not exist** — use `DROP VIEW IF EXISTS` to drop metric views.
10. **Multi-statement SQL via Statements API fails** — submit one statement per API call. Don't chain with semicolons.

### SDP Pipeline Performance
11. **SDP serverless provisioning + execution for 3 MVs (Silver) + 3 MVs (Gold) against 10M Bronze rows: ~50 seconds total.** Much faster than expected. Provisioning is the bottleneck, not execution.
12. **Pipeline goes RUNNING → IDLE quickly** — poll every 20 sec, not every 60 sec. Most runs complete in 1-2 poll cycles.

### Dashboard Deployment
13. **Dashboard creation via POST works on first try when workspace is clean.** No collision issues when old dashboards are deleted first.
14. **Dashboard publish with `embed_credentials: false` works reliably** — confirmed again on this workspace.
15. **Upload SDP SQL files as notebooks for interviewer viewing** — use `workspace import --language SQL`. They can't run standalone (SDP-only syntax) but interviewer can read the logic.

### Project Structure (repo-best-practices integration)
16. **Scaffold + code gen takes ~2 min regardless of data size** — it's all local file writes. This is "free" time.
17. **Bundle validate + deploy: ~25 sec** — fast. No reason to skip validation.
18. **The `media_lakehouse/` subdirectory pattern works cleanly** — `databricks.yml` at project root, `bundle validate` and `bundle deploy` run from inside the subdir.
19. **Workspace folder `/Users/slysik@gmail.com/media_lakehouse/` holds uploaded notebooks for UI viewing** — separate from the `.bundle/` deploy path. Both are needed: `.bundle/` for pipeline/job execution, visible folder for interviewer walkthrough.

### Cleanup Workflow
20. **Full workspace cleanup order matters**: delete pipelines FIRST (releases table ownership), then drop tables (materialization + bronze), then delete jobs, then delete dashboards, then delete workspace folders. Wrong order causes `TABLE_ALREADY_MANAGED` errors.
21. **Drop tables one at a time via SQL Statements API** — multi-statement fails. Loop through table names individually.
22. **Metric views show as `METRIC_VIEW` table_type in information_schema** but are dropped with `DROP VIEW`, not `DROP METRIC VIEW`.

## Test Run Learnings (2026-03-11 retail_lakehouse run)

### Bronze via Serverless SQL (Auth Workaround)
23. **When cluster auth fails ("principal inactive"), generate Bronze via serverless SQL warehouse instead.** `CREATE OR REPLACE TABLE ... AS SELECT ... FROM RANGE(N)` works identically to `spark.range(N)`. Same distributed generation, same data quality — just runs on serverless compute instead of the interview cluster. The notebook still exists for walkthrough but data was created via `dbx_sql`.
24. **SQL RANGE(N) is the serverless equivalent of spark.range(N).** Supports all the same patterns: modulo for FK integrity, rand(seed) for reproducibility, CASE/WHEN for weighted distributions, DATE_ADD for date spread.

### Dashboard — What Made It Work This Time
25. **Dashboard datasets query ONLY Gold MVs — never Silver or Bronze.** Gold tables are pre-aggregated (72-600 rows), which means dashboard queries are instant. Previous attempts that queried Silver (100K+ rows) were slower and more error-prone.
26. **Dashboard dataset SQL re-aggregates Gold by dropping time dimensions.** Gold has `category × year × month` (72 rows). Dashboard `ds_category` does `GROUP BY category` to collapse months → 6 rows. This two-stage aggregation (Silver→Gold in SDP, Gold→dashboard in SQL) keeps both layers clean.
27. **Every dashboard SQL query was tested via `dbx_sql` BEFORE building the dashboard JSON.** All 5 queries returned valid data. Zero broken widgets on first deploy.
28. **Counter widgets use `disaggregated: true` with a 1-row KPI summary dataset.** The `ds_kpi` dataset pre-aggregates everything into a single row (`COUNT(*), SUM(), AVG()`). Counter widgets just reference the column name directly — no widget-level aggregation needed.
29. **Dashboard field name matching is exact and case-sensitive.** `name` in `query.fields` MUST equal `fieldName` in `encodings`. For pre-aggregated data with `disaggregated: true`, both use the bare column alias (e.g., `"revenue"`, not `"sum(revenue)"`).
30. **Widget versions confirmed working: counter=2, table=2, bar=3, line=3, pie=3, filter-multi-select=2.** Text widgets have NO spec block — use `multilineTextboxSpec` directly.
31. **Separate text widgets for title and subtitle.** Multiple items in `lines` array concatenate on one line. Use separate widgets at different y positions.
32. **Global filters on `PAGE_TYPE_GLOBAL_FILTERS` page affect all datasets containing the filter column.** Category filter affects `ds_category` (has `category`), region filter affects `ds_region` (has `region`). Datasets without the column are unaffected.

### Dashboard Dataset Design Pattern (Canonical)
```
Gold MV (pre-aggregated by SDP):
  gold_sales_by_category: category × year × month → 72 rows
  gold_sales_by_store: region × format × city × year × month → 600 rows
  gold_daily_revenue: date → 365 rows

Dashboard datasets (re-aggregate Gold):
  ds_kpi: SUM/AVG across all gold_sales_by_category → 1 row
  ds_category: GROUP BY category → 6 rows
  ds_region: GROUP BY region, store_format → ~15 rows
  ds_daily: direct SELECT from gold_daily_revenue → 365 rows
```
**Rule: Dashboard SQL should never touch more than ~1000 rows. If it does, add another Gold MV.**

### CDC Pipeline Deployment (media_lakehouse 2026-03-11)
33. **Pipeline created by PAT user inherits `run_as_user_name: slysik@gmail.com`.** If SCIM-inactive, pipeline fails with zero error details — just `FAILED` in `latest_updates`. No `flow_progress` or `dataset_progress` events are emitted.
34. **Solution: delete old pipeline, create new one via SP profile.** SP-created pipeline gets `run_as_user_name: {sp_client_id}`. SCIM-immune. Completes in ~42 sec for CDC + 3 Gold MVs.
35. **Dashboard JSON `queryLines` is FLAT on the dataset object, not nested under `query`.** Wrong: `{"query": {"queryLines": [...]}}`. Right: `{"queryLines": [...]}`. Causes "failed to parse serialized dashboard" error.
36. **Dashboard pages need `"pageType": "PAGE_TYPE_CANVAS"`.** Missing this field can cause parse failures.
37. **CDC Bronze validation: check `_change_type` distribution.** `GROUP BY _change_type` should show expected INSERT/UPDATE/DELETE counts. Silver count = INSERT count - DELETE count.
38. **Gold aggregation reconciliation: all Gold MVs must agree on totals.** `SUM(total_watch_minutes)` from gold_daily, gold_content, and gold_engagement must all match Silver's `SUM(watch_minutes)`. This confirms join integrity and no data loss.
39. **SP needs `GRANT ALL PRIVILEGES ON SCHEMA` to manage tables.** Without this, SP gets `PERMISSION_DENIED: User does not have MANAGE on Table` when trying to DROP old tables.

### Pi Footer Extension
40. **`ctx.ui.setStatus()` is invisible when `ctx.ui.setFooter()` is used.** Custom footers replace the default footer entirely, including all status entries. Pipeline checkmarks must be rendered INSIDE the custom footer's `render()` function, not via `setStatus()`.
41. **`tool_result` event has `event.content` (array) and `event.toolName` directly on the event.** Match on tool output text (`text.includes("completed")`) for reliable detection regardless of result structure changes.

## Test Run Learnings (2026-03-12 Genie Space build)

### Genie Space API — Two Completely Different APIs
42. **`/api/2.0/genie/spaces` (SDK) requires opaque `serialized_space` protobuf JSON.** The `GenieSpaceExport` proto has undocumented field names, mandatory sorting, and NO sample question support. Do NOT use this API directly.
43. **`/api/2.0/data-rooms/{id}` is the higher-level Genie API.** Accepts simple `table_identifiers: string[]`, `display_name`, `description`. Used by the Databricks MCP server's `create_or_update_genie` tool. **Always prefer data-rooms over genie/spaces.**
44. **`serialized_space` proto field names: `identifier` (not `full_name`, `table_identifier`, or `catalog_name`).** Tables go in `{"version": 2, "data_sources": {"tables": [{"identifier": "catalog.schema.table"}]}}`. Tables MUST be sorted alphabetically by identifier or creation fails with `data_sources.tables must be sorted by identifier`.
45. **`sample_questions` is NOT in the `GenieSpaceExport` proto.** Cannot add sample questions via `/api/2.0/genie/spaces` create/update. Must use `/api/2.0/data-rooms/{id}/curated-questions/batch-actions` API separately.

### Genie Space — Sample Questions & Instructions
46. **Add sample questions via batch API:** `POST /api/2.0/data-rooms/{id}/curated-questions/batch-actions` with `{"actions": [{"action_type": "CREATE", "curated_question": {"data_room_id": space_id, "question_text": "...", "question_type": "SAMPLE_QUESTION"}}]}`. Also supports `DELETE` action with `{"id": question_id}`.
47. **SQL Instructions teach Genie certified query patterns:** `POST /api/2.0/data-rooms/{id}/instructions` with `{"title": "...", "content": "SELECT ...", "instruction_type": "SQL_INSTRUCTION"}`. Genie uses these as templates when generating SQL.
48. **Text Instructions guide Genie behavior:** Same endpoint with `"instruction_type": "TEXT_INSTRUCTION"`. Use for chart preferences ("prefer line charts for trends"), terminology mapping ("revenue = total_revenue"), and table relationship hints.
49. **Chart-oriented sample questions drive visualization:** Questions like "Show monthly revenue trends by region as a line chart" or "Revenue breakdown by category as a pie chart" prime Genie to render visual results, not just tables.

### Genie Space — Permissions
50. **SP-created tables need ownership transfer for Genie.** When `dbx_sql` (which auto-failovers to SP) creates Gold tables, the SP owns them. Genie runs queries as the user's identity. Fix: `ALTER TABLE ... SET OWNER TO 'user@email.com'` from SP profile.
51. **Schema/catalog ownership ≠ table SELECT access in UC.** Even if `slysik@gmail.com` owns the schema and catalog, SP-created tables within that schema require explicit SELECT grants or ownership transfer. UC doesn't grant implicit SELECT to schema owners on tables they don't own.
52. **`GRANT USE SCHEMA` requires MANAGE on schema.** If SP doesn't have MANAGE (only inherited USE_SCHEMA from catalog grants), it can't grant USE SCHEMA to others. Workaround: the schema owner runs the grant, or transfer table ownership instead.

### Genie Space — SCIM Impact
53. **SCIM `active: false` breaks Genie even when browser SSO works.** Error: `Principal {id} is not an active member of account`. The user can log into the workspace UI via Azure AD, but Genie's UC schema retrieval fails because SCIM marks the identity inactive.
54. **Fix: `databricks auth login -p slysik-oauth` re-activates SCIM user.** This requires an interactive browser popup — cannot be automated through pi/Claude Code. Must be run manually in a terminal.

### MCP vs dbx-tools — Quantified Comparison
55. **MCP `create_or_update_genie` = 1 call. Manual REST = 17 calls (12 failures).** The MCP tool abstracts the proto format, handles sorting, and includes sample questions. The 22:1 call reduction on Genie creation alone justifies having MCP loaded.
56. **MCP `get_table_details` = 1 call for all schemas + stats + cardinality.** Replaces 8 separate `dbx_sql` calls (3 DESCRIBE + 4 SELECT DISTINCT + 1 aggregate). 8:1 reduction.
57. **dbx-tools wins for auth failover, pipeline polling, cleanup, and validation.** `dbx_auth_check` (SP auto-failover), `dbx_poll_pipeline`, `dbx_cleanup`, and `dbx_validate_tables` have no MCP equivalent.
58. **Optimal config: both loaded.** dbx-tools (always) for auth/pipelines/cleanup/SQL. MCP (on-demand via `defer_loading: true`) for Genie/Dashboard/VectorSearch/AgentBricks CRUD. Use dbx-tools for SQL execution (auth failover) even when MCP is available.
59. **MCP `.mcp.json` should use `slysik-sp` profile, not `slysik` PAT.** SP is SCIM-immune. PAT profile causes MCP tool failures when SCIM deactivates the user mid-session.

## Test Run Learnings (2026-03-18 finserv_lakehouse run)

### SDP TBLPROPERTIES Gotchas
60. **`"owner"` is a reserved SDP TBLPROPERTIES key.** Using `"owner" = "team-name"` in `CREATE OR REFRESH MATERIALIZED VIEW ... TBLPROPERTIES` causes `UNSUPPORTED_FEATURE.SET_TABLE_PROPERTY`. Remove `"owner"` from all TBLPROPERTIES blocks. Valid properties: `"quality"`, `"layer"`, `"delta.autoOptimize.optimizeWrite"`, etc.

### SQL RANGE() vs spark.range() — Column Availability
61. **SQL RANGE() Bronze tables only have explicitly generated columns.** When generating Bronze via `CREATE OR REPLACE TABLE ... AS SELECT ... FROM RANGE(N)`, the table contains only the columns you SELECT. Unlike PySpark where `F.current_timestamp()` is easy to add inline, SQL RANGE has no implicit timestamp. If Silver needs a timestamp, derive it: `TO_TIMESTAMP(CONCAT(CAST(txn_date AS STRING), ' 00:00:00'))` or just use `txn_date` as DATE. Do NOT reference a PySpark-derived column (like `txn_ts`) in Silver SQL when Bronze was generated via SQL RANGE.

### Bundle Deployment — tfstate Conflicts
62. **tfstate ownership conflict recovery.** If `bundle deploy` fails with `"does not have View or Admin or Manage Run or Owner permissions on job"`, the job ID in tfstate was created by a different principal. Fix: delete stale tfstate (`rm .databricks/bundle/dev/terraform/terraform.tfstate`), then `bundle deploy` creates fresh resources. The old job remains in workspace (delete via UI by the original owner if needed).

### Dashboard Deployment — parent_path Must Be a Folder
63. **Dashboard `parent_path` must be a Workspace FOLDER, not a REPO.** The path `/Users/user@email.com/my-repo` may be a Git-backed REPO object (type=REPO in workspace list). POSTing a dashboard with a REPO as `parent_path` fails: "is not a directory". Use SP home folder `/Users/{sp_client_id}` or create a dedicated folder via `workspace.mkdirs`. Check with `databricks workspace list "/Users/..."` — look for `Type: REPO` vs `Type: DIRECTORY`.

### Dashboard Widget Patterns
64. **Grouped bar chart: add `"mark": {"layout": "group"}` to bar spec.** Default is stacked. Group mode shows bars side-by-side — better for comparing absolute values across categories when you don't want stacking to hide individual bars.
65. **Multi-Y line chart syntax: `"y": {"scale": ..., "fields": [...]}`.** For multiple lines sharing one y-axis, use the `fields` array under a single `y` encoding (not multiple x/y pairs). Both fields must exist in the dataset. Each object in `fields` needs `fieldName` and `displayName`.
66. **`dbx_poll_pipeline` "completed" = IDLE, not necessarily COMPLETED.** After poll returns, ALWAYS verify with `databricks api get "/api/2.0/pipelines/{id}"` and check `latest_updates[0].state`. IDLE after FAILED is a silent failure. Only `state: "COMPLETED"` means success.

## Test Run Learnings (2026-03-18 retail_lakehouse test run)

### Notebook Execution — Serverless Multi-Task Format
67. **`dbx_run_notebook` tool does NOT support serverless compute.** It submits a single-task run which requires `job_cluster_key`, `new_cluster`, or `existing_cluster_id`. Error: "For serverless compute, please use multi-task with tasks array instead." **Always use direct API call instead:**
```bash
databricks -p slysik-aws api post "/api/2.1/jobs/runs/submit" --json '{
  "run_name": "bronze_gen",
  "tasks": [{"task_key": "generate_bronze", "notebook_task": {"notebook_path": "/Workspace/..."}}],
  "queue": {"enabled": true}
}'
```
Then poll with the working URL-param pattern (not `--query`).

### Auth — PAT on AWS is Clean
68. **AWS workspace with PAT has no SCIM issues.** `current_user()` returns `slysik@gmail.com` (not SP UUID), pipeline `run_as_user_name` is the human user, table ownership is clean. SCIM flakiness was Azure-specific. PAT is the right primary credential on AWS — no SP workarounds needed.

### Dashboard Deployment — Canonical Folder
69. **Always deploy dashboards to `/Users/slysik@gmail.com/dashboards/`.** Create once with `workspace mkdirs`, reuse every run. Never use the REPO path (`dbx-sa-build-demo-pitch`) as `parent_path` — it's type REPO not DIRECTORY and will fail. Never use `.bundle/` path.

### Jobs List — Not JSON
70. **`databricks jobs list` returns tabular text, not JSON.** Cannot pipe to `python3 -c json.load()`. Parse as plain text or use `api get "/api/2.1/jobs?limit=25"` for JSON response.

### Workspace Cleanup — DROP SCHEMA CASCADE
71. **`DROP SCHEMA IF EXISTS catalog.schema CASCADE` drops all tables + the schema in one call.** Faster than dropping tables individually. Use AFTER `dbx_cleanup` (which handles pipeline + job + dashboard deletion first). Order: `dbx_cleanup` → `DROP SCHEMA CASCADE`.

### Build Timing (100K rows, serverless, PAT, AWS)
72. **Confirmed timings for finserv-scale builds:**
- Bronze notebook (serverless, multi-task submit): ~75 sec
- SDP pipeline (3 Silver + 3 Gold MVs): ~47–51 sec
- Dashboard deploy + publish: ~20 sec
- Bundle validate + deploy: ~25 sec
- Total end-to-end: ~6 min (well within interview window)

## Test Run Learnings (2026-03-18 finserv clean rebuild)

### Dashboard Deployment — dbx_deploy_dashboard Always Fails on This Workspace
73. **`dbx_deploy_dashboard` tool hardcodes the REPO path as `parent_path`.** The tool resolves to `/Users/slysik@gmail.com/dbx-sa-build-demo-pitch` which is a REPO object (type=REPO), not a DIRECTORY. Always bypass this tool and use direct API calls:
```bash
# Step 1: create (first time)
databricks -p slysik-aws api post "/api/2.0/lakeview/dashboards" --json "$PAYLOAD"
# Step 2: publish
databricks -p slysik-aws api post "/api/2.0/lakeview/dashboards/{id}/published" \
  --json '{"embed_credentials": false, "warehouse_id": "214e9f2a308e800d"}'
```
Use `parent_path: "/Users/slysik@gmail.com/dashboards"` (pre-created DIRECTORY). Never use the REPO path.

### dbx_cleanup — Deletes ALL Dashboards Workspace-Wide
74. **`dbx_cleanup` deletes every dashboard in the workspace, not just ones related to the target schema.** Collateral deletions happen (e.g., "Workspace Usage Dashboard" was deleted during retail cleanup). This is acceptable for interview prep but worth knowing. If a specific dashboard must be preserved, delete it manually before running cleanup.

### Bronze Notebook — Column Naming Rules
75. **Always name fact status/type columns with a domain prefix BEFORE the broadcast join.** Pattern: `txn_status` not `status`, `order_status` not `status`. Dim tables commonly have a `status` column (account_status, product_status). If the fact also has `status`, Spark's `withColumnRenamed("status", ...)` after the join renames ALL matching columns — silently dropping the fact status. Fix at source: name it distinctly in the fact build step.
76. **Never write a dim table twice.** Write each dim exactly once — in the cell where it's built. Do NOT re-write it inside the broadcast join cell. Double writes cause unnecessary overwrites and confuse the notebook narrative.

### Domain Discipline
77. **`finserv_lakehouse` / `workspace.finserv` is the permanent demo domain.** Never reuse `retail`, `finance`, or any other schema for the real demo build. Test runs use a throwaway domain (e.g., `retail_lakehouse`) and are cleaned up immediately after. The interview workspace should show only `workspace.finserv` + `workspace.default`.
78. **Bundle/pipeline names must match the domain.** Use `finserv_medallion` and `finserv_orchestrator` — not `finance_medallion` or generic names. Interviewers see these names in the Pipelines and Jobs UI.

### Architecture Slide Narration — 4-Layer Coverage
79. **Our build covers 3 of 4 slide layers directly; 1 layer is narrated.** Mapping:
- **Spark Compute** → serverless notebooks + SDP serverless pipeline ✅ demo
- **Data Lakehouse** → Bronze → Silver → Gold → Trusted Delta tables ✅ demo
- **Unity Catalog** → `workspace.finserv.*` 3-level namespace, TBLPROPERTIES quality tags ✅ demo
- **Analytics & AI** → SQL Warehouse + AI/BI Dashboard + SQL queries ✅ demo
- **Mosaic AI** → narrate only: *"Gold tables are feature-ready — next step is `ai_query()` risk scoring or a served MLflow model on the transaction stream"*
- **Streaming** → narrate only: *"In production this lands via Auto Loader or Zerobus — I'm using `spark.range()` here so the full pipeline runs in under 2 min on serverless"*
- **UC Govern/Discover/Share/Audit** → narrate only: *"UC system tables give us full query lineage and audit trail — Delta Sharing publishes Gold to external consumers without data copies"*

## Test Run Learnings (2026-03-18 finserv_lakehouse full clean build — post-interview)

### Genie Space `serialized_space` — CORRECTED Proto Format
80. **Entry #44 was WRONG — `config.sample_questions` IS valid in `GenieSpaceConfig` proto.** Correct full format:
```json
{
  "version": 2,
  "data_sources": {
    "tables": [{"identifier": "catalog.schema.table"}]
  },
  "config": {
    "sample_questions": [
      {"id": "<32-char-hex-uuid-no-hyphens>", "question": ["Question string?"]}
    ]
  }
}
```
Key rules:
- `tables` array MUST be sorted alphabetically by `identifier` — fails with `data_sources.tables must be sorted by identifier` otherwise
- `SampleQuestion.id` is REQUIRED — lowercase 32-hex UUID without hyphens (use `uuid.uuid4().hex`)
- `SampleQuestion.question` is an ARRAY of strings, not a plain string
- `version: 1` works but API upgrades to `version: 2` when `table_identifiers` top-level field is used

81. **`table_identifiers` is a top-level API request field, not inside `serialized_space`.** Pass it alongside `serialized_space` in the outer JSON payload. The API converts it to `data_sources.tables` internally:
```python
payload = {
    "warehouse_id": "...",
    "serialized_space": json.dumps(inner),  # version + config only
    "title": "...",
    "description": "...",
    "parent_path": "/Users/user@email.com/dashboards",
    "table_identifiers": [                  # ← top-level, NOT in serialized_space
        "workspace.finserv.gold_daily_risk",
        "workspace.finserv.silver_transactions"
    ]
}
```

82. **Genie Space PATCH (update) accepts `serialized_space` with both `data_sources` and `config`.** Use `PATCH /api/2.0/genie/spaces/{id}` to add/update tables + sample questions on an existing space. Combine `data_sources.tables` (sorted) + `config.sample_questions` (with ids) in one call.

83. **`create_or_update_genie` MCP tool still preferred over raw REST for Genie.** The raw REST approach required ~15 probe calls to discover the proto format. MCP abstracts all of this. Only use raw REST when MCP is unavailable.

### Build Metrics — Standard Post-Build Step
84. **Always run `generate_build_metrics.py` after every demo build.** It:
- Queries live Databricks for row counts + revenue reconciliation
- Fires a live Genie test question and captures SQL + answer
- Outputs `docs/BUILD_METRICS.md` (human-readable) + `docs/metrics/YYYY-MM-DD.json` (machine-readable)
- Captures: phase runtimes, row counts, revenue recon, Delta health, AI asset details, LLM/token stats, all URLs
```bash
just metrics finserv_lakehouse <pipeline_id> <run_id> <dashboard_id> <genie_id>
# or
python3 finserv_lakehouse/scripts/generate_build_metrics.py \
  --phase-times '{"cleanup":8,"bundle":22,"bronze":75,"sdp":47,"validate":12,"dashboard":6,"genie":18}' \
  --pipeline-id "..." --run-id "..." --dashboard-id "..." --genie-id "..."
```

85. **SQL Statements API `wait_timeout` hard cap is 50s, not 60s.** Use `"wait_timeout": "50s"` — anything higher returns "must be between 5 and 50 seconds". Update all SQL helper scripts.

### Git Security — Critical Lessons
86. **NEVER hardcode API keys, OAuth tokens, or client_secret values in any `.py`, `.json`, or `.yml` file.** Even as `os.environ.get("KEY", "fallback_value")` — the fallback is committed and leaked. Pattern:
```python
# ❌ WRONG — fallback leaks to git
client_secret = os.environ.get("DATABRICKS_CLIENT_SECRET", "dose8aa3af746...")
# ✅ RIGHT — fail fast if not set
client_secret = os.environ.get("DATABRICKS_CLIENT_SECRET")
if not client_secret:
    raise ValueError("DATABRICKS_CLIENT_SECRET not set")
```

87. **Store all API keys in `~/.zshrc` or `~/.zshenv` as env vars — never in repo files.** Confirmed working pattern:
```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
echo 'export DATABRICKS_CLIENT_SECRET="dose..."' >> ~/.zshrc
source ~/.zshrc
```
Both files are outside any repo and never committed.

88. **Use `git-filter-repo` to purge secrets from ALL git history.** If a secret lands in any commit (even a deleted file), it persists in history and is visible to GitHub secret scanning:
```bash
pip3 install git-filter-repo
# Create replacements file
echo "actual_secret_value==>REDACTED" > /tmp/replacements.txt
# Rewrite all history
git filter-repo --replace-text /tmp/replacements.txt --force
# Re-add remote (filter-repo removes it) and force push
git remote add origin https://github.com/...
git push origin main --force
```
Then revoke the leaked token immediately — treat all public-duration exposure as compromised.

89. **GitHub secret scanning fires within ~3 minutes of push.** GitHub's push protection detects Databricks OAuth tokens (`dose*`) and Anthropic API keys (`sk-ant-api03-*`) automatically. Check Security tab after every push to a public repo.

### Git Remote — Always Verify
90. **Always verify `git remote -v` before pushing.** The remote may silently point to a different repo. We pushed 4 commits to `databricks-claude-coding` thinking they went to `dbx-sa-build-demo-pitch`. Fix: `git remote set-url origin https://github.com/slysik/dbx-sa-build-demo-pitch.git`. Correct remote is now set and saved.

### Repo Hygiene — node_modules
91. **Add `node_modules/` to `.gitignore` immediately after any `npm install`.** Pi extension `node_modules` were tracked and committed — 700+ files. Fix: `git rm -r --cached .pi/extensions/node_modules/ && echo "node_modules/" >> .gitignore`. Force push removes them from GitHub. Add to `.gitignore` before first commit in any new repo.

### Genie Space — Confirmed Working Pattern (End-to-End)
92. **Confirmed working Genie Space creation sequence (2026-03-18, AWS workspace):**
```python
import json, subprocess, uuid

tables = sorted([  # MUST be sorted
    "workspace.finserv.gold_daily_risk",
    "workspace.finserv.gold_segment_risk",
    "workspace.finserv.gold_txn_by_category",
    "workspace.finserv.silver_transactions"
])

inner = {
    "version": 2,
    "data_sources": {"tables": [{"identifier": t} for t in tables]},
    "config": {
        "sample_questions": [
            {"id": uuid.uuid4().hex, "question": ["What is total revenue?"]}
        ]
    }
}

payload = {
    "warehouse_id": "214e9f2a308e800d",
    "serialized_space": json.dumps(inner),
    "title": "My Genie Space",
    "description": "...",
    "parent_path": "/Users/slysik@gmail.com/dashboards"
}
# POST to /api/2.0/genie/spaces — returns {space_id, title, warehouse_id}
# URL: https://{host}/genie/rooms/{space_id}?o={org_id}
```
PATCH to same endpoint to update existing space. GET does NOT return `serialized_space`.
