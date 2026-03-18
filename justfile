# Databricks SA Interview — Justfile v3
# Workspace: adb-7405619449104571.11.azuredatabricks.net (West US 3)
# Catalog: interview | Schema: varies per prompt (retail, media, etc.)
set dotenv-load := true

default:
  @just --list

# ═══════════════════════════════════════════════════════════════════
# INTERVIEW DAY — Primary Commands
# ═══════════════════════════════════════════════════════════════════

# Launch Pi with dbx-tools extension (custom Databricks tools + cockpit)
# Optionally pass a plan file: just interview plan.md
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
  databricks -p slysik auth describe 2>&1 | head -3 || echo "  ✗ Auth failed — generate new PAT"
  echo ""
  echo "── Cluster ──"
  databricks -p slysik clusters get 0310-193517-r0u8giyo 2>&1 | python3 -c "
  import json,sys
  try:
    d=json.load(sys.stdin)
    print(f'  {d[\"cluster_name\"]}: {d[\"state\"]}')
    if d['state'] != 'RUNNING': print('  → Start: just cluster-start')
  except: print('  ✗ Could not check cluster')
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
  databricks -p slysik pipelines list-pipelines --output json 2>&1 | python3 -c "
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

# Full cleanup: pipelines → tables → jobs → dashboards (correct order)
clean-workspace schema="media":
  #!/usr/bin/env bash
  echo "=== Cleaning interview.{{schema}} + workspace ==="
  echo ""
  echo "── Deleting Pipelines ──"
  databricks -p slysik pipelines list-pipelines --output json 2>&1 | python3 -c "
  import json,sys,subprocess
  data=json.load(sys.stdin)
  for p in data:
    pid=p['pipeline_id']
    subprocess.run(['databricks','-p','slysik','pipelines','delete',pid])
    print(f'  Deleted: {p.get(\"name\",\"?\")}')
  if not data: print('  None')
  " 2>&1
  echo ""
  echo "── Dropping Tables ──"
  just sql "SELECT table_name, table_type FROM interview.information_schema.tables WHERE table_schema='{{schema}}'" 2>&1 | tail -n+2 | while IFS=$'\t' read -r tbl ttype; do
    [ -z "$tbl" ] && continue
    CMD="DROP TABLE"
    [ "$ttype" = "VIEW" ] && CMD="DROP VIEW"
    just sql "$CMD IF EXISTS interview.{{schema}}.\`$tbl\`" >/dev/null 2>&1
    echo "  Dropped: $tbl"
  done
  echo ""
  echo "── Deleting Jobs ──"
  databricks -p slysik jobs list --output json 2>&1 | python3 -c "
  import json,sys,subprocess
  data=json.load(sys.stdin)
  jobs=data.get('jobs',data) if isinstance(data,dict) else data
  for j in jobs:
    jid=str(j['job_id'])
    subprocess.run(['databricks','-p','slysik','jobs','delete',jid])
    print(f'  Deleted: {j.get(\"settings\",{}).get(\"name\",\"?\")}')
  if not jobs: print('  None')
  " 2>&1
  echo ""
  echo "── Deleting Dashboards ──"
  databricks -p slysik api get /api/2.0/lakeview/dashboards 2>&1 | python3 -c "
  import json,sys,subprocess
  data=json.load(sys.stdin)
  for d in data.get('dashboards',[]):
    did=d['dashboard_id']
    subprocess.run(['databricks','-p','slysik','api','delete',f'/api/2.0/lakeview/dashboards/{did}'])
    print(f'  Deleted: {d.get(\"display_name\",\"?\")}')
  if not data.get('dashboards'): print('  None')
  " 2>&1
  echo ""
  echo "── Cleaning Workspace Folders ──"
  databricks -p slysik workspace list /Users/slysik@gmail.com --output json 2>&1 | python3 -c "
  import json,sys,subprocess
  skip={'.assistant','.bundle','Sample Dashboards','sa-workflows','databricks-claude-coding'}
  items=json.load(sys.stdin)
  for i in items:
    name=i['path'].split('/')[-1]
    if name in skip or i.get('object_type')=='REPO': continue
    subprocess.run(['databricks','-p','slysik','workspace','delete','--recursive',i['path']])
    print(f'  Deleted: {i[\"path\"]}')
  " 2>&1
  echo ""
  echo "=== Clean slate ✓ ==="

# ═══════════════════════════════════════════════════════════════════
# DATABRICKS CLI
# ═══════════════════════════════════════════════════════════════════

# Check auth status
dbx-auth:
  databricks -p slysik auth describe

# Start the interview cluster
cluster-start:
  databricks -p slysik clusters start 0310-193517-r0u8giyo
  @echo "Cluster starting — takes ~3 min"

# Check cluster status
cluster-status:
  databricks -p slysik clusters get 0310-193517-r0u8giyo 2>&1 | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'{d[\"cluster_name\"]}: {d[\"state\"]}')"

# Run SQL on serverless warehouse
sql query:
  #!/usr/bin/env bash
  databricks -p slysik api post /api/2.0/sql/statements --json "{
    \"warehouse_id\": \"b89b264d78f9d52e\",
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
  just sql "SELECT table_name, table_type FROM interview.information_schema.tables WHERE table_schema='{{schema}}' AND table_name NOT LIKE '__materialization%' ORDER BY table_name"

# Row counts for all non-materialization tables in a schema
counts schema="media":
  #!/usr/bin/env bash
  just sql "SELECT table_name FROM interview.information_schema.tables WHERE table_schema='{{schema}}' AND table_name NOT LIKE '__materialization%' ORDER BY table_name" 2>&1 | tail -n+2 | while read tbl; do
    [ -z "$tbl" ] && continue
    cnt=$(just sql "SELECT COUNT(*) FROM interview.{{schema}}.\`$tbl\`" 2>&1 | tail -1)
    printf "  %-40s %s\n" "$tbl" "$cnt"
  done

# ═══════════════════════════════════════════════════════════════════
# BUNDLE DEPLOYMENT (per-project)
# ═══════════════════════════════════════════════════════════════════

# Validate + deploy a project bundle (e.g., just bundle media_lakehouse)
bundle project:
  cd {{justfile_directory()}}/{{project}} && databricks -p slysik bundle validate && databricks -p slysik bundle deploy

# Upload project notebooks to workspace for interviewer viewing
upload-project project:
  #!/usr/bin/env bash
  PROJ="{{project}}"
  WS_DIR="/Users/slysik@gmail.com/$PROJ"
  databricks -p slysik workspace mkdirs "$WS_DIR" 2>/dev/null
  for f in {{justfile_directory()}}/$PROJ/src/notebooks/*.py; do
    NAME=$(basename "$f" .py)
    databricks -p slysik workspace import "$WS_DIR/$NAME" --file "$f" --language PYTHON --overwrite
    echo "  Uploaded: $NAME"
  done
  for f in {{justfile_directory()}}/$PROJ/src/pipeline/*.sql; do
    NAME=$(basename "$f" .sql)
    databricks -p slysik workspace import "$WS_DIR/$NAME" --file "$f" --language SQL --overwrite
    echo "  Uploaded: $NAME"
  done

# ═══════════════════════════════════════════════════════════════════
# WORKSPACE NAVIGATION
# ═══════════════════════════════════════════════════════════════════

# List workspace contents
ls path="/Users/slysik@gmail.com":
  databricks -p slysik workspace list {{path}}

# Upload a notebook
upload local_path workspace_path:
  databricks -p slysik workspace import {{workspace_path}} --file {{local_path}} --format SOURCE --language PYTHON --overwrite

# Upload SQL file
upload-sql local_path workspace_path:
  databricks -p slysik workspace import {{workspace_path}} --file {{local_path}} --format SOURCE --language SQL --overwrite

# ═══════════════════════════════════════════════════════════════════
# DELTA PROOF POINTS (for interview narration)
# ═══════════════════════════════════════════════════════════════════

# Show Liquid Clustering on a table (e.g., just detail media.bronze_stream_events)
detail table:
  just sql "DESCRIBE DETAIL interview.{{table}}"

# Show Delta history (audit trail)
history table:
  just sql "DESCRIBE HISTORY interview.{{table}} LIMIT 5"

# Show table properties (governance metadata)
tblproperties table:
  just sql "SHOW TBLPROPERTIES interview.{{table}}"

# ═══════════════════════════════════════════════════════════════════
# CLAUDE CODE (alternate interface)
# ═══════════════════════════════════════════════════════════════════

# Interactive Claude session
claude:
  claude --model opus

# Headless Claude with full permissions
auto prompt:
  claude --model opus --dangerously-skip-permissions -p "{{prompt}}"
