# CLAUDE.md — Databricks Sr. SA Interview

**Interview: Sr. Databricks SA | Final Round**
**Profile: `slysik-aws` | Workspace: `dbc-61514402-8451.cloud.databricks.com` (AWS)**
**MCP: dbc-61514402-8451.cloud.databricks.com (configured in `.mcp.json`, profile `slysik-aws-sp`)**
**User: `lysiak043@gmail.com` | SP: `dbx-agent` (client_id: `5d54409d-304c-42aa-8a21-8070a8879443`)**

---

## MEMORY RULES — CLAUDE CODE

**Single source of truth:** `.pi/skills/*/SKILL.md` files for patterns, `CLAUDE.md` for config/routing.
- **DO NOT** read or write `tasks/lessons.md` — that file is owned by pi sessions only
- **DO NOT** create or write `MEMORY.md` in this project — pi owns memory persistence
- **DO** save new patterns/learnings to the relevant `.pi/skills/*/SKILL.md`
- **DO** update `CLAUDE.md` routing table or coding rules if a project-level default changes
- **DO** update `elle-core.md` rules only if the user explicitly asks

### ⚠️ Skill Conflicts Resolved (2026-03-24)

**3 major skill conflicts identified and resolved.** See `SKILLS_CONFLICT_RESOLUTION.md` for full analysis.

**TL;DR:**
- **Data generation:** Use `spark-native-bronze` for interviews (default), `databricks-synthetic-data-gen` for production realistic data
- **Bundles:** Use `databricks-bundles` ONLY (2026+); `asset-bundles` is DEPRECATED
- **Interview mode is the default** for ambiguous prompts — optimize for speed over realism

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

### Primary Workspace
- [ ] Verify auth: `just dbx-auth` — should show SP `5d54409d-304c-42aa-8a21-8070a8879443` via OAuth M2M
- [ ] Verify SQL works: `just sql "SELECT current_user()"` — returns SP UUID (no PAT yet; SP runs SQL)
- [ ] Verify SQL warehouse is running: `just wh-status` (ID: `4bbaafe9538467a0` — auto_resume enabled)
- [ ] Verify catalog is clean: `SHOW SCHEMAS IN finserv` → only `default` + `information_schema`
- [ ] No cluster needed — all compute is serverless (notebooks + SDP pipelines)
- [ ] When scaling DataFrames, scale ALL related tables (fact + detail) to keep join keys aligned
- [ ] Paste code into notebooks with **Cmd+Shift+V** (no formatting)
- [ ] Dashboard publish: ALWAYS use `embed_credentials: false`
- [ ] Dashboard parent folder: SP home `/Users/5d54409d-304c-42aa-8a21-8070a8879443/dashboards` OR `lysiak043@gmail.com/dashboards` if SP granted folder access via UI
- [ ] ⚠️ SP not yet in workspace admins — SP CANNOT write to `/Users/lysiak043@gmail.com/`. Fix: Workspace UI → Admin Console → Groups → admins → Add `5d54409d-304c-42aa-8a21-8070a8879443`
- [ ] Demo catalog: `finserv` | Demo schema: project-specific (e.g., `finserv.demo`) — never raw `default`

### Backup Workspace (failover check — run if primary has issues)
- [ ] Verify backup SP auth: `databricks auth describe -p slysik-aws-backup-sp` — should show `oauth-m2m`
- [ ] Start backup warehouse: `databricks -p slysik-aws-backup-sp api post "/api/2.0/sql/warehouses/228419b788367ab7/start" --json '{}'`
- [ ] Verify backup tables exist: count `workspace.finserv.bronze_fact_transactions` — should be 100,000
- [ ] Verify backup pipeline state: `databricks -p slysik-aws-backup-sp api get "/api/2.0/pipelines/203da4c9-d48e-46df-8e9f-fa64b91a546e"` → state=IDLE
- [ ] If redeploying: `cd finserv_lakehouse && databricks bundle deploy -t backup`
- [ ] Get fresh OAuth token via curl (NOT `databricks auth token`) for direct REST calls on backup

### Auth Failover (profiles configured)
| Profile | Auth Type | When to Use |
|---------|-----------|-------------|
| `slysik-aws` | OAuth M2M ✅ (SP: `dbx-agent`, configured 2026-03-19) | Primary — all CLI, bundle, notebook runs |
| `slysik-aws-sp` | OAuth M2M ✅ (SP: `dbx-agent`) | MCP auto-failover in dbx-tools extension |
| `slysik-aws-backup` | OAuth CLI (run `databricks auth login -p slysik-aws-backup`) | Old backup workspace — `slysik@yahoo.com` |
| `slysik-aws-backup-sp` | OAuth M2M (SP: `databricks-agent`) | Old backup workspace SP |

**PAT not yet configured:** New workspace uses OAuth M2M via SP `5d54409d-304c-42aa-8a21-8070a8879443` (dbx-agent).
**To add PAT later:** Workspace UI → Settings → Developer → Access tokens → Generate → add `token = dapi...` to `[slysik-aws]` in `~/.databrickscfg`, remove `client_id`/`client_secret` from that profile.
**AWS = no SCIM issues:** `current_user()` via SQL returns SP UUID (not email) until a PAT is added.
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
- **GRANT to SP must use `client_id`, not display name** — `GRANT ... TO \`5d54409d-304c-42aa-8a21-8070a8879443\`` not `\`dbx-agent\``
- **Workspace admin implicit UC access** — `SHOW GRANTS` won't show admin-derived privileges; workspace admins have full UC access without explicit grants
- **Serverless-only** — no cluster available; notebooks run on serverless compute (omit `existing_cluster_id` in runs/submit API)
- **Notebook serverless submit** — `dbx_run_notebook` tool DOES NOT support serverless. Use direct API: `api post "/api/2.1/jobs/runs/submit"` with `tasks` array + `"queue": {"enabled": true}`, no cluster spec
- **Dashboard parent_path** — ALWAYS use `/Users/lysiak043@gmail.com/dashboards` (DIRECTORY) once SP has admin access. Until then, use SP home: `/Users/5d54409d-304c-42aa-8a21-8070a8879443/dashboards`. Always bypass `dbx_deploy_dashboard` tool with direct `api post`.
- **SP not in admins group** — SP `5d54409d-304c-42aa-8a21-8070a8879443` cannot write to `/Users/lysiak043@gmail.com/`. Add to workspace admins: Workspace UI → Admin Console → Groups → admins → Add member (2026-03-19)

### Backup workspace-specific (learned 2026-03-19)
- **`databricks auth token -p slysik-aws-backup-sp` is BROKEN on macOS** — returns `Error: cache: d...`. Get OAuth token via direct curl client_credentials grant:
  ```bash
  TOKEN=$(curl -s -X POST "https://dbc-a092293f-ea93.cloud.databricks.com/oidc/v1/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials&client_id=bb2b9d09-a4b3-40e4-b848-6efc2e31480a&client_secret=$BACKUP_SP_SECRET&scope=all-apis" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
  # BACKUP_SP_SECRET stored in ~/.zshrc — NEVER hardcode
  ```
- **SQL RANGE() Bronze — always include `customer_id` from dim_accounts join** — PySpark notebook selects `a.customer_id` from the accounts dim. SQL RANGE() translation can silently drop it. Without it, Silver SDP fails immediately: `UNRESOLVED_COLUMN: customer_id`. Double-check all FK columns from dim joins are in the SELECT list.
- **Backup bundle target — independent tfstate** — adding a `backup` target to `databricks.yml` creates `.databricks/bundle/backup/terraform/terraform.tfstate` separate from `dev`. No tfstate conflict. Use `databricks bundle deploy -t backup` to deploy.
- **Backup workspace SQL warehouse starts STOPPED** — always start it first: `databricks -p slysik-aws-backup-sp api post "/api/2.0/sql/warehouses/228419b788367ab7/start" --json '{}'`
- **`workspace import` flag syntax on backup** — use `--file /path/to/local.py TARGET_PATH` (not positional second arg). Wrong: `workspace import TARGET src/file.py`. Right: `workspace import --file src/file.py TARGET`.
- **`slysik@yahoo.com` is already workspace admin on backup** — implicit UC access. Explicit UC grants still best practice for governance demonstration. Don't skip them.
- **Dashboard `parent_path` on backup = `/Users/slysik@yahoo.com/dashboards`** — pre-create with `workspace mkdirs` before first deploy. SP home folder also works (`/Users/bb2b9d09-a4b3-40e4-b848-6efc2e31480a`) but less clean for user visibility.
- **Pipeline permissions API uses `user_name` key, not `principal_name`** — `{"access_control_list": [{"user_name": "slysik@yahoo.com", "permission_level": "CAN_MANAGE"}]}`
- **Genie Space has NO explicit permissions API** — `PATCH /api/2.0/permissions/data-rooms/{id}` returns `400: 'data-rooms' is not a supported object type`. Genie Spaces are accessible to workspace admins automatically. For non-admins, share via UI or use the `/api/2.0/data-rooms/{id}/collaborators` endpoint if available.
- **`databricks jobs list` on backup returns tabular text** — not JSON. Parse plaintext or use `api get "/api/2.1/jobs?limit=25"` for JSON.

### New primary workspace gotchas (learned 2026-03-19 finserv_lakehouse build)
- **Workspace admin ≠ UC CREATE SCHEMA** — adding SP to workspace admins group grants `USE CATALOG` implicitly but NOT `CREATE SCHEMA`. SP needs `GRANT ALL PRIVILEGES ON CATALOG finserv TO <sp_id>` from the catalog owner (`lysiak043@gmail.com`) before bundle can deploy a pipeline.
- **`GRANT ALL PRIVILEGES ON CATALOG` must come from catalog owner** — SP cannot self-grant even as workspace admin. Human user must run this once in SQL editor or notebook.
- **`GRANT SELECT ON ALL TABLES IN SCHEMA` syntax is invalid** — `PARSE_SYNTAX_ERROR at 'TABLES'`. Grant per table in a loop.
- **Grants lost on table drop+recreate** — when SDP MV is dropped and notebook writes Delta table in its place, all prior SELECT grants are gone. Re-grant after every drop+recreate cycle.
- **`client: "1"` environment spec not supported on this workspace** — `INVALID_PARAMETER_VALUE: Workspace doesn't support Client-1 channel for REPL`. Remove `environments:` block from bundle job YAML entirely; serverless is the default for notebook tasks.
- **`databricks bundle run --task` flag doesn't exist** — use `--only <task_key>` instead.
- **MLflow `spark.mlflow.modelRegistryUri` not available on serverless** — `mlflow.set_experiment()` and `spark.conf.set("spark.mlflow.modelRegistryUri", ...)` both throw `[CONFIG_NOT_AVAILABLE]`. Remove all MLflow setup from notebooks on this workspace. Narrate MLflow as the production add-on (`"wrap pipe.fit() in mlflow.start_run() — one context manager"`).
- **Sklearn churn labels: check temporal alignment** — if Bronze data spans 2023-2025 and current date is 2026, `days_since_last_txn >= 90` labels ALL customers as at-risk (100% class 1). LogisticRegression fails: `ValueError: needs at least 2 classes`. Use complaint/escalation/sentiment signals for labels instead, or adjust the recency threshold to match actual date range.
- **OAuth token for direct REST calls** — `databricks auth token --output json` doesn't work reliably. Always use curl client_credentials grant: `curl -s -X POST "{host}/oidc/v1/token" -d "grant_type=client_credentials&client_id={id}&client_secret={secret}&scope=all-apis"`.
- **RAG in pure SQL — no Vector Search needed for small corpus** — `ai_similarity(question, chunk_text)` scores all chunks, `ORDER BY score DESC LIMIT 3` retrieves top-k, `ai_query(model, CONCAT(context, question))` generates the answer. Works for < 100 chunks in a Delta table. Scales to Vector Search for production.

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
- **Genie Space `serialized_space` format** — proto3 JSON: `{"version": 2, "data_sources": {"tables": [{"identifier": "cat.schema.tbl"}]}, "config": {"sample_questions": [{"id": "<32hex>", "question": ["Q?"]}]}}`. Tables MUST be sorted alphabetically by identifier. Pass `table_identifiers` as top-level API field (not inside serialized_space). `create_or_update_genie` MCP tool abstracts all of this — prefer it. See sdp-and-dashboard-patterns.md #80-92.
- **Build metrics** — always run `python3 {project}/scripts/generate_build_metrics.py` after every build. Outputs `docs/BUILD_METRICS.md` + `docs/metrics/{date}.json`. Add to git commit.
- **NEVER hardcode secrets** — no fallback values in `os.environ.get("KEY", "hardcoded")`. Store all keys in `~/.zshrc`. Use `git-filter-repo` to purge if leaked. GitHub detects `dose*` (Databricks OAuth) and `sk-ant-api03-*` (Anthropic) within 3 min of push.
- **Git remote** — always verify `git remote -v` before pushing. Canonical remote: `https://github.com/slysik/dbx-sa-build-demo-pitch.git`
- **SQL Statements API wait_timeout** — max 50s (not 60s). Use `"wait_timeout": "50s"` in all SQL API calls.
- **macOS bash 3.2 — no associative arrays** — `/bin/bash` is 3.2.57 on macOS (Apple won't ship GPLv3). `declare -A` fails silently or throws `unbound variable`. Always use Python or zsh for scripts needing maps/dicts. No `/opt/homebrew/bin/bash` installed either.

---

## SKILLS SYNC — UPSTREAM TRACKING (2026-03-25)

### Upstream Sources
Skills in `.agents/skills/` are sourced from **3 upstream repos** and synced manually:

| Repo | Branch | Skills Path | Skills Count |
|------|--------|-------------|-------------|
| `databricks-solutions/ai-dev-kit` | `main` | `databricks-skills/` | 25 Databricks skills |
| `mlflow/skills` | `main` | `.` (root) | 8 MLflow skills |
| `databricks-solutions/apx` | `main` | `skills/apx/` | 1 APX skill |

### Name Mapping (upstream → local)
Several skills are renamed locally (prefix stripped). Full mapping in `scripts/sync-skills.py::SKILL_MAP`.

| Upstream Name | Local Name | Why Renamed |
|--------------|------------|-------------|
| `databricks-model-serving` | `model-serving` | Prefix stripped |
| `databricks-lakebase-provisioned` | `lakebase-provisioned` | Prefix stripped |
| `databricks-spark-declarative-pipelines` | `spark-declarative-pipelines` | Prefix stripped |
| `databricks-synthetic-data-gen` | `synthetic-data-generation` | Renamed + suffix change |
| `databricks-unstructured-pdf-generation` | `unstructured-pdf-generation` | Prefix stripped |
| `databricks-zerobus-ingest` | `zerobus-ingest` | Prefix stripped |

### Local-Only Skills (no upstream)
| Skill | Notes |
|-------|-------|
| `asset-bundles` | ❌ DEPRECATED — use `databricks-bundles` |
| `databricks-parsing` | Legacy — upstream equivalent is in `databricks-ai-functions` |

### Automated Daily Check
**GitHub Actions:** `.github/workflows/check-skills-updates.yml`
- Runs daily at 8am ET (`cron: 0 12 * * *`) + manual dispatch
- Clones all 3 upstream repos, compares every skill by SHA256
- Extracts **feature-level diffs** (new/removed/modified sections in SKILL.md)
- Includes upstream commit messages per skill (last 30 days)
- Creates a GitHub Issue with full Markdown report when updates found
- Closes stale `skills-update` issues automatically
- Archives JSON report as build artifact (30-day retention)

### Local Commands
```bash
just skills-check              # Quick terminal check — no changes
just skills-report             # Markdown report → docs/SKILLS_UPDATE_REPORT.md
just skills-sync               # Interactive — prompts per skill
just skills-update             # Force-apply all updates
just skills-sync-one <names>   # Sync specific skills only
```

### After Syncing Skills
1. Review `git diff .agents/skills/` for unexpected changes
2. Check if upstream **removed sections you added** (e.g., `⚠️ Known Gotchas` added to `spark-declarative-pipelines`)
3. Re-apply local patches if needed (gotchas, interview-specific overrides)
4. Run `just skills-check` to confirm clean
5. Commit: `git add .agents/skills/ && git commit -m "skills: sync from upstream (YYYY-MM-DD)"`

### ⚠️ Sync Gotchas (learned 2026-03-25)
- **Upstream removes README.md** — many skills had `README.md` removed upstream (Mar 24 cleanup). Safe to apply.
- **Upstream may remove your local patches** — e.g., `⚠️ Known Gotchas (workspace-validated)` was added to `spark-declarative-pipelines/SKILL.md` locally but doesn't exist upstream. A sync will overwrite it. Keep interview-specific gotchas in `CLAUDE.md` (primary) and skill files (secondary).
- **`install_skills.sh` targets `.claude/skills/`** — the upstream installer writes to `.claude/skills/` (Claude Code convention). Our project uses `.agents/skills/`. The Python sync script handles this correctly.
- **Upstream is active** — ~10+ commits/week to `databricks-skills/`. Check before interview day.
- **`databricks-bundles` upstream reverted our serverless additions** — upstream `SKILL.md` is now +4/-35 vs local (removed serverless notebook task section and `--only` flag gotcha that we added). Keep local version or re-apply after sync.

---

## WORKSPACE — QUICK COMMANDS

### Primary Workspace (dbc-61514402-8451) — NEW ✅ (2026-03-19)
**Active workspace:** `dbc-61514402-8451` (AWS) | Org: `7474656067656578` | Auth: OAuth M2M (`slysik-aws-sp`)
**Cluster:** none — workspace is serverless-only. Notebooks use serverless compute, pipelines use serverless SDP.
**Catalog:** `finserv` ✅ (clean — only `default` + `information_schema` schemas)
**Schema:** project-specific under `finserv` catalog — e.g., `finserv.demo`
**SQL Warehouse:** `4bbaafe9538467a0` (Serverless Starter Warehouse — PRO, RUNNING, auto_resume) ✅
**User email:** `lysiak043@gmail.com`
**SP:** `dbx-agent` | client_id: `5d54409d-304c-42aa-8a21-8070a8879443` ⚠️ NOT yet in workspace admins
**Git folder:** `/Workspace/Users/lysiak043@gmail.com/dbx-sa-build-demo-pitch` (ID: TBD — no repo yet, clone from GitHub)
**Dashboard folder (SP):** `/Users/5d54409d-304c-42aa-8a21-8070a8879443/dashboards` — SP home (usable today)
**Dashboard folder (user):** `/Users/lysiak043@gmail.com/dashboards` — create via UI once SP has admin access
**GitHub repo:** `https://github.com/slysik/dbx-sa-build-demo-pitch`

#### ⚠️ SETUP TODO (new workspace — 2026-03-19)
- [x] Add SP to workspace admins: Admin Console → Groups → admins → Add `5d54409d-304c-42aa-8a21-8070a8879443` ✅
- [x] Grant SP ALL PRIVILEGES ON CATALOG finserv (run as lysiak043@gmail.com in SQL editor) ✅
- [x] Grant lysiak043@gmail.com SELECT on all 12 finserv.banking tables ✅
- [ ] Create dashboard folder in user home: `workspace mkdirs /Users/lysiak043@gmail.com/dashboards`
- [ ] Clone Git repo: Workspace → Repos → Add → `https://github.com/slysik/dbx-sa-build-demo-pitch` → note folder ID
- [ ] Generate PAT (optional but cleaner): Settings → Developer → Access tokens → update `~/.databrickscfg [slysik-aws]`
- [ ] Update `GIT_FOLDER_ID` in `justfile` once repo is cloned

#### Primary Workspace — Live Asset IDs (finserv_lakehouse, 2026-03-19)
| Asset | ID | URL |
|-------|----|----|
| SDP Pipeline | `25fe1040-0aa8-4d2f-8f90-ab8c0754c956` | `.../?o=7474656067656578#pipelines/25fe1040-...` |
| Job | `995548364992521` | `.../?o=7474656067656578#job/995548364992521` |
| Dashboard | `01f123be25df19bb8f33e18d0fd6b197` | `.../dashboardsv3/01f123be25df19bb8f33e18d0fd6b197` |
| Genie Space | `01f123af4575169f84599de01de4855c` | `.../genie/rooms/01f123af4575169f84599de01de4855c` |

#### Primary Workspace — Table Counts (finserv.banking, 2026-03-19)
| Table | Rows | Notes |
|-------|------|-------|
| `bronze_dim_customers` | 200 | Core Banking (Postgres) |
| `bronze_dim_accounts` | 500 | Core Banking (Postgres) |
| `bronze_fact_transactions` | 10,000 | Core Banking (Postgres) |
| `bronze_crm_interactions` | 500 | Salesforce CRM SaaS |
| `bronze_policy_docs` | 15 | Internal policy vault (3 docs × 5 chunks) |
| `silver_transactions` | 10,000 | SDP MV |
| `silver_interactions` | 500 | SDP MV + ai_classify + ai_analyze_sentiment |
| `gold_rfm_features` | 200 | SDP MV — ML feature store |
| `gold_churn_risk` | 200 | SDP MV — rule-based scoring |
| `gold_customer_ai_summary` | 200 | Delta table (notebook) — ai_summarize |
| `gold_segment_kpis` | 15 | SDP MV — BI aggregates |
| `gold_churn_predictions` | 200 | Delta table (notebook) — sklearn LogReg |

### Old Primary Workspace (dbc-ad74b11b-230d) — ARCHIVED (was active until 2026-03-19)
**Host:** `https://dbc-ad74b11b-230d.cloud.databricks.com`
**User:** `slysik@gmail.com` | **Catalog:** `workspace` | **Schema:** `workspace.finserv`
**SQL Warehouse:** `214e9f2a308e800d` | **SP:** `dbx-ssa-coding-agent` (client_id: `64e5d26a-41fd-4089-b71b-c6b83154bd91`)
**Profiles:** archived as `slysik-aws-old` / `slysik-aws-sp-old` in `~/.databrickscfg`

### Backup Workspace (dbc-a092293f-ea93) — DEPLOYED ✅ (2026-03-19)
**Host:** `https://dbc-a092293f-ea93.cloud.databricks.com`
**Org ID:** `7474660773634193`
**User:** `slysik@yahoo.com` (workspace admin, SCIM active ✅)
**SP:** `databricks-agent` | client_id: `bb2b9d09-a4b3-40e4-b848-6efc2e31480a` (admins group ✅)
**Catalog:** `workspace` | **Schema:** `workspace.finserv` ✅
**SQL Warehouse:** `228419b788367ab7` (Serverless Starter Warehouse — starts on demand)
**Notebook folder:** `/Users/slysik@yahoo.com/finserv_lakehouse/`
**Dashboard folder:** `/Users/slysik@yahoo.com/dashboards/` — pre-created DIRECTORY ✅
**Bundle target:** `backup` in `finserv_lakehouse/databricks.yml` — deploy with `databricks bundle deploy -t backup`

#### Backup Workspace — Live Asset IDs
| Asset | ID | URL |
|-------|----|----|
| SDP Pipeline | `203da4c9-d48e-46df-8e9f-fa64b91a546e` | `.../?o=7474660773634193#pipelines/203da4c9-...` |
| Job | `662188896016780` | `.../?o=7474660773634193#job/662188896016780` |
| Dashboard | `01f12331054a1f618a8e6a36bebcd2fb` | `.../dashboardsv3/01f12331054a1f618a8e6a36bebcd2fb` |
| Genie Space | `01f12331f45515778ae0d2ab78a0e7aa` | `.../genie/rooms/01f12331f45515778ae0d2ab78a0e7aa?o=7474660773634193` |
| Notebook | `4400390734878752` | `.../?o=7474660773634193#notebook/4400390734878752` |

#### Backup Workspace — Table Counts (baseline, 2026-03-19)
| Table | Rows |
|-------|------|
| `bronze_dim_customers` | 200 |
| `bronze_dim_accounts` | 2,000 |
| `bronze_fact_transactions` | 100,000 |
| `silver_transactions` | 100,000 |
| `gold_txn_by_category` | 144 |
| `gold_segment_risk` | 24 |
| `gold_daily_risk` | 4,380 |

#### Backup Workspace — Permissions Granted (slysik@yahoo.com)
| Asset | Permission | Method |
|-------|-----------|--------|
| UC Catalog `workspace` | `USE_CATALOG` | SQL GRANT |
| UC Schema `workspace.finserv` | `USE_SCHEMA`, `SELECT`, `MODIFY`, `CREATE TABLE` | SQL GRANT |
| SDP Pipeline | `CAN_MANAGE` | REST PATCH `/permissions/pipelines/{id}` |
| Job | `CAN_MANAGE` | REST PATCH `/permissions/jobs/{id}` |
| Dashboard | `CAN_MANAGE` | REST PATCH `/permissions/dashboards/{id}` |
| SQL Warehouse | `CAN_USE` | REST PATCH `/permissions/warehouses/{id}` |
| Genie Space | implicit ✅ | workspace admin — `data-rooms` is NOT a valid ACL object type |

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
just metrics finserv_lakehouse <pipeline> <run_id> <dashboard> <genie>   # Build metrics report
```

---

## MULTI-WORKSPACE PATTERNS (2026-03-19)

### Bundle Multi-Target Deployment
Add a `backup` target to any `databricks.yml` — independent tfstate, zero conflict with `dev`:
```yaml
targets:
  dev:                                           # primary workspace
    mode: development
    default: true
    workspace:
      host: https://dbc-ad74b11b-230d.cloud.databricks.com

  backup:                                        # backup workspace
    mode: development
    workspace:
      host: https://dbc-a092293f-ea93.cloud.databricks.com
      profile: slysik-aws-backup-sp
    variables:
      warehouse_id: 228419b788367ab7             # override workspace-specific vars
```
```bash
databricks bundle validate -t backup   # validate against backup workspace
databricks bundle deploy   -t backup   # deploy pipeline + job to backup workspace
```

### Backup SP OAuth Token (curl — not CLI)
`databricks auth token -p slysik-aws-backup-sp` fails on macOS. Always use curl:
```bash
TOKEN=$(curl -s -X POST "https://dbc-a092293f-ea93.cloud.databricks.com/oidc/v1/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=bb2b9d09-a4b3-40e4-b848-6efc2e31480a&client_secret=$BACKUP_SP_SECRET&scope=all-apis" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
# BACKUP_SP_SECRET stored in ~/.zshrc — NEVER hardcode
# Then use: -H "Authorization: Bearer $TOKEN" in all curl calls
```

### Backup Workspace — SQL Bronze Generation
No PySpark cluster → use SQL RANGE() via Statements API. Identical pattern to `spark.range()`.
**Critical:** Always include `a.customer_id` from the accounts dim join — easy to drop, breaks Silver immediately.
```sql
-- Canonical fact join for backup workspace
SELECT
  CONCAT('TXN-', LPAD(CAST(f.id AS STRING), 8, '0'))         AS txn_id,
  CONCAT('ACCT-', LPAD(CAST(f.id % 2000 AS STRING), 6, '0')) AS account_id,
  a.customer_id,           -- ← MUST INCLUDE — Silver references this column
  a.account_type, a.branch, a.account_status,
  c.segment, c.risk_tier, c.region,
  ...
FROM RANGE(100000) f
JOIN workspace.finserv.bronze_dim_accounts  a ON a.account_id  = CONCAT('ACCT-', ...)
JOIN workspace.finserv.bronze_dim_customers c ON c.customer_id = CONCAT('CUST-', ...)
```

### Backup Workspace — Dashboard Deploy
```bash
# 1. Create (first deploy)
curl -s -X POST "https://dbc-a092293f-ea93.cloud.databricks.com/api/2.0/lakeview/dashboards" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"display_name":"...", "parent_path":"/Users/slysik@yahoo.com/dashboards",
       "serialized_dashboard":"...", "warehouse_id":"228419b788367ab7"}'

# 2. Publish
curl -s -X POST "https://dbc-a092293f-ea93.cloud.databricks.com/api/2.0/lakeview/dashboards/{id}/published" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"embed_credentials": false, "warehouse_id": "228419b788367ab7"}'
```

### Backup Workspace — Permission Grants
```bash
# UC grants (run as SP via SQL Statements API)
GRANT USE_CATALOG ON CATALOG workspace TO `slysik@yahoo.com`
GRANT USE_SCHEMA, SELECT, MODIFY, CREATE TABLE ON SCHEMA workspace.finserv TO `slysik@yahoo.com`

# Object permissions (REST API — PATCH, not POST)
PATCH /api/2.0/permissions/pipelines/{id}  → {"access_control_list": [{"user_name":"slysik@yahoo.com","permission_level":"CAN_MANAGE"}]}
PATCH /api/2.0/permissions/jobs/{id}       → same pattern
PATCH /api/2.0/permissions/dashboards/{id} → same pattern
PATCH /api/2.0/permissions/warehouses/{id} → permission_level: "CAN_USE"
```

### Backup Workspace — Genie Space Creation
```python
import json, uuid, urllib.request, urllib.parse

BKUP_HOST = "https://dbc-a092293f-ea93.cloud.databricks.com"
BKUP_WH   = "228419b788367ab7"

# Tables MUST be sorted alphabetically
tables = sorted([
    "workspace.finserv.gold_daily_risk",
    "workspace.finserv.gold_segment_risk",
    "workspace.finserv.gold_txn_by_category",
    "workspace.finserv.silver_transactions",
])

serialized_space = {
    "version": 2,
    "data_sources": {"tables": [{"identifier": t} for t in tables]},
    "config": {
        "sample_questions": [
            {"id": uuid.uuid4().hex, "question": [q]}      # id = 32hex, question = list
            for q in ["What is total revenue by category?", ...]
        ]
    }
}

payload = {
    "warehouse_id":      BKUP_WH,
    "serialized_space":  json.dumps(serialized_space),     # inner dict as JSON string
    "title":             "Apex Financial — Risk & Revenue Intelligence",
    "description":       "...",
    "parent_path":       "/Users/slysik@yahoo.com/dashboards",
    "table_identifiers": tables,                           # ALSO top-level, not inside serialized_space
}
# POST /api/2.0/genie/spaces → returns {space_id, title, warehouse_id}
# URL: {BKUP_HOST}/genie/rooms/{space_id}?o=7474660773634193
```
**Permissions:** `data-rooms` is NOT a valid ACL object type — `PATCH /permissions/data-rooms/{id}` returns 400.
Workspace admins (`slysik@yahoo.com`) have implicit access. No explicit grant needed.

### Workspace Import — Correct Flag Syntax
```bash
# ✅ CORRECT
databricks -p slysik-aws-backup-sp workspace import \
  --format SOURCE --language PYTHON --overwrite \
  --file /local/path/notebook.py \
  "/Users/slysik@yahoo.com/finserv_lakehouse/notebook_name"

# ❌ WRONG — positional second arg not supported
databricks workspace import TARGET_PATH /local/file.py
```

---

## SKILL ROUTING — READ BEFORE BUILDING

Skills load on-demand with full patterns, gotchas, and code templates. **Always read the relevant SKILL.md before building that component.**

### ⚠️ CONFLICT RESOLUTION (2026-03-24) — CANONICAL ROUTING

**3 major skill conflicts have been resolved.** See `SKILLS_CONFLICT_RESOLUTION.md` for full details.

| Conflict | Resolution | Always Use | Never Use |
|----------|-----------|-----------|-----------|
| Data generation for interviews | `spark.range()` is canonical for speed | `.pi/skills/spark-native-bronze/SKILL.md` | `databricks-synthetic-data-gen` (production only) |
| Data generation for production | Faker + Pandas UDFs for realistic data | `.agents/skills/synthetic-data-generation/SKILL.md` | N/A |
| Bundle configuration naming | "Declarative Automation Bundles" (2026+) | `.agents/skills/databricks-bundles/SKILL.md` | ❌ `.agents/skills/asset-bundles/SKILL.md` (DEPRECATED) |

**Decision tree for routing:**
- **Interview mode** (default for ambiguous prompts) → Use `spark-native-bronze` + `repo-best-practices`
- **Production mode** (user asks for "realistic data" or "Faker") → Use `databricks-synthetic-data-gen`
- **Bundle/DAB task** (any) → Use `databricks-bundles` ONLY (not `asset-bundles`)

---

### Interview Mode (Speed Focus) — Invoke These

| Interview Task | Skill to Read |
|---|---|
| **Project scaffold (ALWAYS FIRST)** | `.pi/skills/repo-best-practices/SKILL.md` |
| **Synthetic data + Bronze + SDP + Dashboard + Bundle** | `.pi/skills/spark-native-bronze/SKILL.md` + `sdp-and-dashboard-patterns.md` |
| **SDP / Lakeflow pipelines** | `.agents/skills/spark-declarative-pipelines/SKILL.md` |
| **AI/BI Dashboard** | `.agents/skills/databricks-aibi-dashboards/SKILL.md` |
| **Bundles / Declarative Automation** | `.agents/skills/databricks-bundles/SKILL.md` ✅ (2026+) |
| **Genie Spaces (SQL exploration)** | `.agents/skills/databricks-genie/SKILL.md` + `sdp-and-dashboard-patterns.md` #42-59 |

### Production Mode (Realism Focus) — Invoke These

| Production Task | Skill to Read |
|---|---|
| **Realistic synthetic data (Faker + names/addresses)** | `.agents/skills/synthetic-data-generation/SKILL.md` |
| **DBSQL / SQL features (stored procedures, geospatial, ai_query)** | `.agents/skills/databricks-dbsql/SKILL.md` |
| **Structured Streaming (Kafka, CDC, stateful ops)** | `.agents/skills/databricks-spark-structured-streaming/SKILL.md` |
| **Vector Search / RAG** | `.agents/skills/databricks-vector-search/SKILL.md` |
| **Model Serving / LLM endpoints** | `.agents/skills/model-serving/SKILL.md` |
| **MLflow Tracing / Observability** | `.agents/skills/instrumenting-with-mlflow-tracing/SKILL.md` |
| **Agent Bricks (Knowledge Assistants, Supervisor Agents)** | `.agents/skills/databricks-agent-bricks/SKILL.md` |

### Shared Skills (Interview + Production)

| Task | Skill to Read |
|---|---|
| **Unity Catalog / Volumes / System Tables** | `.agents/skills/databricks-unity-catalog/SKILL.md` |
| **Jobs / Workflows / Scheduling** | `.agents/skills/databricks-jobs/SKILL.md` |
| **AI Functions (ai_classify, ai_extract, ai_summarize, ai_gen, etc.)** | `.agents/skills/databricks-ai-functions/SKILL.md` |
| **SA knowledge base (DW architecture, FinServ, design patterns)** | `.pi/skills/databricks-sa/SKILL.md` |
| **Databricks docs / API reference lookup** | `.agents/skills/databricks-docs/SKILL.md` |

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
├── scripts/
│   ├── sync-skills.py           # Skills sync engine (Python 3.9+)
│   └── sync-skills.sh           # Shell wrapper → delegates to .py
│
├── .github/
│   └── workflows/
│       └── check-skills-updates.yml  # Daily skills update check (→ GitHub Issue)
│
├── .agents/skills/              # Upstream skills (synced from ai-dev-kit + mlflow/skills + apx)
├── .pi/skills/                  # Local interview skills (repo-best-practices, spark-native-bronze, databricks-sa)
│
├── notebooks/                   # Legacy / scratch notebooks
├── src/                         # Legacy pipeline code
└── tests/                       # pytest + chispa
```
