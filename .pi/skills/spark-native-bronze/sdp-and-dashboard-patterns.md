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
