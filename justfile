# Databricks SA Interview — Justfile v4
# Workspace: dbc-ad74b11b-230d.cloud.databricks.com (AWS)
# Profile: slysik-aws  |  User: slysik@gmail.com  |  SP: dbx-ssa-coding-agent
set dotenv-load := true

# ── WORKSPACE CONFIG ────────────────────────────────────────────
PROFILE        := "slysik-aws-sp"   # SP — always authenticated. Switch to slysik-aws after `just login`
WS_HOST        := "https://dbc-ad74b11b-230d.cloud.databricks.com"
WAREHOUSE_ID   := "214e9f2a308e800d"   # SQL WH (PRO serverless, RUNNING)
WS_USER        := "slysik@gmail.com"
CATALOG        := "workspace"
GIT_FOLDER     := "/Workspace/Users/slysik@gmail.com/dbx-sa-build-demo-pitch"
GIT_FOLDER_ID  := "3401527313137932"   # for direct browser URL
GITHUB_REPO    := "https://github.com/slysik/dbx-sa-build-demo-pitch"
# ────────────────────────────────────────────────────────────────

default:
  @just --list

# ═══════════════════════════════════════════════════════════════════
# INTERVIEW DAY — Primary Commands
# ═══════════════════════════════════════════════════════════════════

# Launch Pi with dbx-tools extension (custom Databricks tools + cockpit)
interview *file:
  cd {{justfile_directory()}} && pi -e .pi/extensions/dbx-tools.ts -e .pi/extensions/interview-cockpit.ts {{file}}

# Launch Pi with dbx-tools only (no cockpit)
interview-lite *file:
  cd {{justfile_directory()}} && pi -e .pi/extensions/dbx-tools.ts {{file}}

# Pre-flight check before the interview starts
preflight:
  #!/usr/bin/env bash
  echo "╔══════════════════════════════════════════════╗"
  echo "║   ◆ Databricks SA Interview — Pre-Flight    ║"
  echo "╚══════════════════════════════════════════════╝"
  echo ""
  echo "── Auth ──"
  databricks -p {{PROFILE}} auth describe 2>&1 | head -3 || echo "  ✗ Auth failed — run: databricks auth login -p {{PROFILE}}"
  echo ""
  echo "── SQL Warehouse ──"
  databricks -p {{PROFILE}} api get "/api/2.0/sql/warehouses/{{WAREHOUSE_ID}}" 2>&1 | python3 -c "
  import json,sys
  try:
    d=json.load(sys.stdin)
    print(f'  {d[\"name\"]}: {d[\"state\"]}')
    if d['state'] not in ('RUNNING','STARTING'): print('  → Start: just wh-start')
  except: print('  ✗ Could not check warehouse')
  " 2>&1
  echo ""
  echo "── Extensions ──"
  for f in .pi/extensions/dbx-tools.ts .pi/extensions/interview-cockpit.ts; do
    test -f "$f" && echo "  ✓ $(basename $f)" || echo "  ✗ MISSING: $f"
  done
  echo ""
  echo "── Theme ──"
  test -f .pi/themes/databricks.json && echo "  ✓ databricks theme" || echo "  ✗ MISSING"
  echo ""
  echo "── Skills ──"
  for f in \
    ".pi/skills/repo-best-practices/SKILL.md:Repo Scaffold" \
    ".pi/skills/spark-native-bronze/SKILL.md:Bronze Gen + Workflow" \
    ".pi/skills/databricks-sa/SKILL.md:SA Knowledge Base"; do
    FILE="${f%%:*}"
    LABEL="${f##*:}"
    test -f "$FILE" && echo "  ✓ $LABEL" || echo "  ✗ MISSING: $LABEL"
  done
  echo ""
  echo "── Workspace ──"
  databricks -p {{PROFILE}} pipelines list-pipelines --output json 2>&1 | python3 -c "
  import json,sys
  try:
    data=json.load(sys.stdin)
    if not data: print('  No pipelines (clean slate ✓)')
    else:
      for p in data: print(f'  Pipeline: {p.get(\"name\",\"?\")} | {p.get(\"state\",\"?\")}')
  except: print('  ✗ Could not list pipelines')
  " 2>&1
  echo ""
  echo "── Ready ──"
  echo "  Launch: just interview"

# ═══════════════════════════════════════════════════════════════════
# WORKSPACE CLEANUP — Run before each interview
# ═══════════════════════════════════════════════════════════════════

clean-workspace schema="media":
  #!/usr/bin/env bash
  echo "=== Cleaning {{CATALOG}}.{{schema}} + workspace ==="
  echo ""
  echo "── Deleting Pipelines ──"
  databricks -p {{PROFILE}} pipelines list-pipelines --output json 2>&1 | python3 -c "
  import json,sys,subprocess
  data=json.load(sys.stdin)
  for p in data:
    pid=p['pipeline_id']
    subprocess.run(['databricks','-p','{{PROFILE}}','pipelines','delete',pid])
    print(f'  Deleted: {p.get(\"name\",\"?\")}')
  if not data: print('  None')
  " 2>&1
  echo ""
  echo "── Dropping Tables ──"
  just sql "SELECT table_name, table_type FROM {{CATALOG}}.information_schema.tables WHERE table_schema='{{schema}}'" 2>&1 | tail -n+2 | while IFS=$'\t' read -r tbl ttype; do
    [ -z "$tbl" ] && continue
    CMD="DROP TABLE"
    [ "$ttype" = "VIEW" ] && CMD="DROP VIEW"
    just sql "$CMD IF EXISTS {{CATALOG}}.{{schema}}.\`$tbl\`" >/dev/null 2>&1
    echo "  Dropped: $tbl"
  done
  echo ""
  echo "── Deleting Jobs ──"
  databricks -p {{PROFILE}} jobs list --output json 2>&1 | python3 -c "
  import json,sys,subprocess
  data=json.load(sys.stdin)
  jobs=data.get('jobs',data) if isinstance(data,dict) else data
  for j in jobs:
    jid=str(j['job_id'])
    subprocess.run(['databricks','-p','{{PROFILE}}','jobs','delete',jid])
    print(f'  Deleted: {j.get(\"settings\",{}).get(\"name\",\"?\")}')
  if not jobs: print('  None')
  " 2>&1
  echo ""
  echo "── Deleting Dashboards ──"
  databricks -p {{PROFILE}} api get /api/2.0/lakeview/dashboards 2>&1 | python3 -c "
  import json,sys,subprocess
  data=json.load(sys.stdin)
  for d in data.get('dashboards',[]):
    did=d['dashboard_id']
    subprocess.run(['databricks','-p','{{PROFILE}}','api','delete',f'/api/2.0/lakeview/dashboards/{did}'])
    print(f'  Deleted: {d.get(\"display_name\",\"?\")}')
  if not data.get('dashboards'): print('  None')
  " 2>&1
  echo ""
  echo "── Cleaning Workspace Folders ──"
  databricks -p {{PROFILE}} workspace list /Users/{{WS_USER}} --output json 2>&1 | python3 -c "
  import json,sys,subprocess
  skip={'.assistant','.bundle','Sample Dashboards'}
  items=json.load(sys.stdin)
  for i in items:
    name=i['path'].split('/')[-1]
    if name in skip or i.get('object_type')=='REPO': continue
    subprocess.run(['databricks','-p','{{PROFILE}}','workspace','delete','--recursive',i['path']])
    print(f'  Deleted: {i[\"path\"]}')
  " 2>&1
  echo ""
  echo "=== Clean slate ✓ ==="

# ═══════════════════════════════════════════════════════════════════
# DATABRICKS CLI
# ═══════════════════════════════════════════════════════════════════

# Check auth status
dbx-auth:
  databricks -p {{PROFILE}} auth describe

# Login (OAuth browser flow — run once to set up token)
login:
  databricks auth login -p {{PROFILE}}

# Check SQL warehouse status (no cluster — all compute is serverless)
wh-status:
  databricks -p {{PROFILE}} api get "/api/2.0/sql/warehouses/{{WAREHOUSE_ID}}" 2>&1 | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'{d[\"name\"]}: {d[\"state\"]}')"

# Start SQL warehouse if stopped
wh-start:
  databricks -p {{PROFILE}} api post "/api/2.0/sql/warehouses/{{WAREHOUSE_ID}}/start" --json '{}' 2>&1
  @echo "Warehouse starting..."

# Run SQL on serverless warehouse
sql query:
  #!/usr/bin/env bash
  databricks -p {{PROFILE}} api post /api/2.0/sql/statements --json "{
    \"warehouse_id\": \"{{WAREHOUSE_ID}}\",
    \"statement\": \"{{query}}\",
    \"wait_timeout\": \"50s\"
  }" 2>&1 | python3 -c "
  import json,sys
  d=json.load(sys.stdin)
  cols = [c['name'] for c in d.get('manifest',{}).get('schema',{}).get('columns',[])]
  if cols: print('\t'.join(cols))
  for r in d.get('result',{}).get('data_array',[]):
    print('\t'.join(str(v) for v in r))
  "

# List tables in a schema (default: media)
tables schema="media":
  just sql "SELECT table_name, table_type FROM {{CATALOG}}.information_schema.tables WHERE table_schema='{{schema}}' AND table_name NOT LIKE '__materialization%' ORDER BY table_name"

# Row counts for all non-materialization tables in a schema
counts schema="media":
  #!/usr/bin/env bash
  just sql "SELECT table_name FROM {{CATALOG}}.information_schema.tables WHERE table_schema='{{schema}}' AND table_name NOT LIKE '__materialization%' ORDER BY table_name" 2>&1 | tail -n+2 | while read tbl; do
    [ -z "$tbl" ] && continue
    cnt=$(just sql "SELECT COUNT(*) FROM {{CATALOG}}.{{schema}}.\`$tbl\`" 2>&1 | tail -1)
    printf "  %-40s %s\n" "$tbl" "$cnt"
  done

# ═══════════════════════════════════════════════════════════════════
# GIT FOLDER — Demo asset upload + navigation
# ═══════════════════════════════════════════════════════════════════

# Open the Git folder in the Databricks workspace browser
open:
  @echo "Workspace: {{WS_HOST}}/browse/folders/{{GIT_FOLDER_ID}}?o=1562063418817826"
  @echo "GitHub:    {{GITHUB_REPO}}"
  @open "{{WS_HOST}}/browse/folders/{{GIT_FOLDER_ID}}?o=1562063418817826" 2>/dev/null || true

# Open the GitHub repo directly
open-github:
  @open "{{GITHUB_REPO}}" 2>/dev/null || echo "{{GITHUB_REPO}}"

# Upload all project notebooks + SQL into the Git folder (flat, easy to browse)
# Structure: dbx-sa-build-demo-pitch/{project}/notebooks/ and /pipeline/
upload-project project:
  #!/usr/bin/env bash
  set -e
  PROJ="{{project}}"
  BASE="{{GIT_FOLDER}}/$PROJ"
  NB_DIR="$BASE/notebooks"
  SQL_DIR="$BASE/pipeline"

  echo "── Creating folders in Git repo ──"
  databricks -p {{PROFILE}} workspace mkdirs "$NB_DIR"
  databricks -p {{PROFILE}} workspace mkdirs "$SQL_DIR"

  echo "── Uploading notebooks ──"
  for f in {{justfile_directory()}}/$PROJ/src/notebooks/*.py; do
    [ -f "$f" ] || continue
    NAME=$(basename "$f" .py)
    databricks -p {{PROFILE}} workspace import "$NB_DIR/$NAME" \
      --file "$f" --format SOURCE --language PYTHON --overwrite
    echo "  ✓ notebooks/$NAME"
  done

  echo "── Uploading pipeline SQL ──"
  for f in {{justfile_directory()}}/$PROJ/src/pipeline/*.sql; do
    [ -f "$f" ] || continue
    NAME=$(basename "$f" .sql)
    databricks -p {{PROFILE}} workspace import "$SQL_DIR/$NAME" \
      --file "$f" --format SOURCE --language SQL --overwrite
    echo "  ✓ pipeline/$NAME"
  done

  echo ""
  echo "✅ Uploaded to: $BASE"
  echo "   Open: {{WS_HOST}}/browse/folders/{{GIT_FOLDER_ID}}?o=1562063418817826"

# List what's currently in the Git folder
ls-git project="":
  #!/usr/bin/env bash
  if [ -z "{{project}}" ]; then
    databricks -p {{PROFILE}} workspace list "{{GIT_FOLDER}}" 2>&1
  else
    databricks -p {{PROFILE}} workspace list "{{GIT_FOLDER}}/{{project}}" 2>&1
  fi

# ═══════════════════════════════════════════════════════════════════
# BUNDLE DEPLOYMENT (per-project)
# ═══════════════════════════════════════════════════════════════════

bundle project:
  cd {{justfile_directory()}}/{{project}} && databricks -p {{PROFILE}} bundle validate && databricks -p {{PROFILE}} bundle deploy

# ═══════════════════════════════════════════════════════════════════
# WORKSPACE NAVIGATION
# ═══════════════════════════════════════════════════════════════════

ls path="{{GIT_FOLDER}}":
  databricks -p {{PROFILE}} workspace list {{path}}

upload local_path workspace_path:
  databricks -p {{PROFILE}} workspace import {{workspace_path}} --file {{local_path}} --format SOURCE --language PYTHON --overwrite

upload-sql local_path workspace_path:
  databricks -p {{PROFILE}} workspace import {{workspace_path}} --file {{local_path}} --format SOURCE --language SQL --overwrite

# ═══════════════════════════════════════════════════════════════════
# DELTA PROOF POINTS
# ═══════════════════════════════════════════════════════════════════

detail table:
  just sql "DESCRIBE DETAIL {{CATALOG}}.{{table}}"

history table:
  just sql "DESCRIBE HISTORY {{CATALOG}}.{{table}} LIMIT 5"

tblproperties table:
  just sql "SHOW TBLPROPERTIES {{CATALOG}}.{{table}}"

# ═══════════════════════════════════════════════════════════════════
# CLAUDE CODE
# ═══════════════════════════════════════════════════════════════════

# Generate build metrics report (run at end of every demo build)
# Usage: just metrics finserv_lakehouse <pipeline-id> <run-id> <dashboard-id> <genie-id> [phase-times-json]
metrics project pipeline_id run_id dashboard_id genie_id phase_times='{"cleanup":8,"bundle":22,"bronze":75,"sdp":47,"validate":12,"dashboard":6,"genie":18}':
  python3 {{justfile_directory()}}/{{project}}/scripts/generate_build_metrics.py \
    --phase-times '{{phase_times}}' \
    --run-id      "{{run_id}}" \
    --pipeline-id "{{pipeline_id}}" \
    --dashboard-id "{{dashboard_id}}" \
    --genie-id    "{{genie_id}}" \
    --claude-model "claude-opus-4-5" \
    2>&1

claude:
  claude --model opus

auto prompt:
  claude --model opus --dangerously-skip-permissions -p "{{prompt}}"
