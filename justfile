# Databricks SA Workspace
set dotenv-load := true

# List all recipes
default:
  @just --list

# --- Claude Code Modes ---

# Interactive Claude session (default)
claude:
  claude --model opus

# Plan a feature with 7-review team workflow
plan prompt:
  claude --model opus --dangerously-skip-permissions "/plan_w_team_v3 {{prompt}}"

# Headless Claude with full permissions
auto prompt:
  claude --model opus --dangerously-skip-permissions -p "{{prompt}}"

# --- Databricks CLI ---

# Check Databricks auth status
dbx-auth:
  databricks -p slysik auth describe

# Run SQL query against workspace (serverless)
dbx-sql query:
  databricks -p slysik api post /api/2.0/sql/statements --json '{"warehouse_id": "auto", "statement": "{{query}}", "wait_timeout": "30s"}'

# List catalogs in Unity Catalog
dbx-catalogs:
  databricks -p slysik catalogs list

# List schemas in a catalog
dbx-schemas catalog:
  databricks -p slysik schemas list {{catalog}}

# List tables in a schema
dbx-tables catalog schema:
  databricks -p slysik tables list {{catalog}} {{schema}}

# List running clusters
dbx-clusters:
  databricks -p slysik clusters list -o json | python3 -m json.tool

# List SQL warehouses
dbx-warehouses:
  databricks -p slysik warehouses list

# List workspace contents
dbx-ls path="/":
  databricks -p slysik workspace list {{path}}

# --- Notebooks ---

# Upload a local notebook to workspace
nb-upload local_path workspace_path:
  databricks -p slysik workspace import {{local_path}} {{workspace_path}} --format SOURCE --language PYTHON --overwrite

# Upload all demo notebooks to workspace
nb-upload-all:
  #!/usr/bin/env bash
  for nb in notebooks/*.py; do
    name=$(basename "$nb" .py)
    echo "Uploading $name..."
    databricks -p slysik workspace import "$nb" "/Users/slysik@gmail.com/finserv-demo/$name" --format SOURCE --language PYTHON --overwrite
  done
  echo "Done. All notebooks uploaded."

# Download a notebook from workspace
nb-download workspace_path local_path:
  databricks -p slysik workspace export {{workspace_path}} {{local_path}} --format SOURCE

# --- Jobs & Pipelines ---

# List all jobs
dbx-jobs:
  databricks -p slysik jobs list

# Run a job by ID
dbx-run job_id:
  databricks -p slysik jobs run-now --job-id {{job_id}}

# --- Quick Explore ---

# Show full medallion architecture (all tables across bronze/silver/gold)
medallion:
  #!/usr/bin/env bash
  for schema in bronze silver gold; do
    echo "=== $schema ==="
    databricks -p slysik tables list dbx_weg $schema 2>/dev/null || echo "  (empty)"
    echo
  done

# ─── Databricks Coding Interview (Pi) ────────────────────────────────────────

# Launch Pi for the coding interview — full copilot with task tracker + phase gate
# Uses updated extensions: coding-interview-tasks.ts + coding-interview-gate.ts
coding-interview:
  pi -e .pi/extensions/coding-interview-tasks.ts -e .pi/extensions/coding-interview-gate.ts -e .pi/extensions/interview-focus.ts

# Launch coding interview with a specific vertical pre-set
# Usage: just coding-interview-vertical retail
coding-interview-vertical vertical:
  pi -e .pi/extensions/coding-interview-tasks.ts -e .pi/extensions/coding-interview-gate.ts -e .pi/extensions/interview-focus.ts \
     "Vertical is {{vertical}}. Catalog is dbx_weg. I have a full Azure workspace with serverless, Unity Catalog, and MCP. Waiting for interviewer prompt."

# Practice run with Pi — simulates the full interview
# Usage: just coding-practice retail  or  just coding-practice media
coding-practice vertical:
  #!/usr/bin/env bash
  if [ "{{vertical}}" = "retail" ]; then
    PROMPT="Build a data pipeline for a retail company: ingest online orders, clean and deduplicate, then build daily revenue aggregations by store and product category with loyalty tier breakdowns."
  elif [ "{{vertical}}" = "media" ]; then
    PROMPT="Build a data pipeline for a streaming media platform: ingest viewing events, deduplicate and clean, then build daily engagement metrics by content type and subscription tier."
  else
    echo "Usage: just coding-practice retail  or  just coding-practice media"
    exit 0
  fi
  pi -e .pi/extensions/coding-interview-tasks.ts -e .pi/extensions/coding-interview-gate.ts -e .pi/extensions/interview-focus.ts \
     "The interviewer prompt is: $PROMPT. Catalog: dbx_weg. Full Azure workspace. Go straight to building — skip discovery. Start with /next."

# Open live-arch.md in browser for real-time architecture diagram
live-arch:
  bash .pi/skills/databricks-sa/scripts/open-live.sh ./live-arch.md

# ─── Claude Code Interview Copilot ──────────────────────────────────────────

# Generate a structured interview prompt from a plain-English use case description
# Usage: just interview-prompt "streaming payment authorizations with fraud detection"
# Output: saves to interview-prompt.md, ready for `just interview interview-prompt.md`
interview-prompt usecase:
  claude --model opus --dangerously-skip-permissions -p "You are a Databricks SA interview prompt writer. Given this use case description, generate a detailed structured interview prompt in the style of a coding challenge. Include: use case summary, constraints (SQL-first, idempotent, validation harness), data model with field definitions, and numbered deliverable sections (discovery, data gen, bronze, silver, gold, dashboard queries, validation harness, distributed reasoning notes). Output format: markdown. Use case: {{usecase}}" > interview-prompt.md && echo "Saved to interview-prompt.md. Run: just interview interview-prompt.md"

# Execute interview pipeline (headless, defaults baked in)
# Usage: just interview "create a dataset with 10k rows, then end to end medallion layer sdp"
interview prompt:
  @claude --model opus --dangerously-skip-permissions -p "/dbx-interview-playbook Step 0 answers: (1) Catalog: dbx_weg (2) Real Azure workspace with serverless, no Free Edition constraints (3) Time budget: 60 min. Skip questions — go straight to building. Generate the full pipeline for: {{prompt}}. PySpark for data gen (~100k rows via spark.range + Faker UDFs), SQL for all transforms. Include TALK/SCALING/DW-BRIDGE narration comments in ALL code — output narration lines in Databricks orange ANSI (\033[38;2;255;106;0m). Execute SQL via MCP. Create dashboard. Include proof points. Be ready for scaling discussion at every stage. EXECUTION RULES: (A) Follow Pipeline Execution Protocol — verify each stage gate before advancing. (B) Use subagents for dashboard query testing and proof points. (C) If any SQL fails, fix autonomously using Quick Fixes table, then capture lesson in tasks/lessons.md. (D) After each stage report: STAGE [name] -- GATE [PASS/FAIL] -- [summary]."

# Execute a single pipeline stage (for targeted re-runs)
# Usage: just interview-stage gold "retail orders pipeline with loyalty tiers"
interview-stage stage prompt:
  @claude --model opus --dangerously-skip-permissions -p "/dbx-interview-playbook Re-run ONLY the {{stage}} stage for: {{prompt}}. Catalog: dbx_weg. Execute SQL via MCP. Verify stage gate. Report: STAGE [{{stage}}] -- GATE [PASS/FAIL] -- [summary]. If SQL fails, fix autonomously and capture lesson in tasks/lessons.md."

# Execute interview pipeline — interactive mode (inline prompt)
# Usage: just interview-interactive "create a dataset with 10k rows, then medallion sdp"
interview-interactive prompt:
  @claude --model opus "/dbx-interview-playbook Before generating code, run Step 0: Session Setup. Ask me: (1) What catalog to use? (2) Any workspace constraints? (3) Time budget? Then generate the full pipeline for: {{prompt}}. Execute SQL via MCP. Create dashboard. Include proof points. Narrate everything for interview read-aloud. EXECUTION RULES: (A) Follow Pipeline Execution Protocol — verify each stage gate before advancing. (B) Use subagents for dashboard query testing and proof points. (C) If any SQL fails, fix autonomously using Quick Fixes table, then capture lesson in tasks/lessons.md. (D) After each stage report: STAGE [name] -- GATE [PASS/FAIL] -- [summary]."

# Execute interview pipeline — interactive mode (read prompt from file)
# Usage: just dbx-coding-agent-interactive-file prompt1.md
dbx-coding-agent-interactive-file prompt_file:
  #!/usr/bin/env bash
  PROMPT="$(cat {{prompt_file}})"
  claude --model opus "/dbx-interview-playbook Before generating code, run Step 0: Session Setup. Ask me: (1) What catalog to use? (2) Any workspace constraints? (3) Time budget? Then generate the full pipeline for: $PROMPT. Execute SQL via MCP. Create dashboard. Include proof points. Narrate everything for interview read-aloud. EXECUTION RULES: (A) Follow Pipeline Execution Protocol — verify each stage gate before advancing. (B) Use subagents for dashboard query testing and proof points. (C) If any SQL fails, fix autonomously using Quick Fixes table, then capture lesson in tasks/lessons.md. (D) After each stage report: STAGE [name] -- GATE [PASS/FAIL] -- [summary]."

# Practice run: full pipeline with a retail or media prompt (Claude Code)
# Usage: just practice-run retail  or  just practice-run media
practice-run vertical:
  #!/usr/bin/env bash
  if [ "{{vertical}}" = "retail" ]; then
    PROMPT="Build a streaming retail orders pipeline: ingest 100k orders, deduplicate, aggregate daily revenue by store and loyalty tier, build a dashboard."
  elif [ "{{vertical}}" = "media" ]; then
    PROMPT="Build a streaming media engagement pipeline: ingest 100k stream events, deduplicate, aggregate daily watch time by content type and subscription tier, build a dashboard."
  else
    echo "Usage: just practice-run retail  or  just practice-run media"
    exit 0
  fi
  claude --model opus --dangerously-skip-permissions -p "/dbx-interview-playbook Step 0 answers: (1) Catalog: dbx_weg (2) Real Azure workspace with serverless (3) Time budget: 60 min. Skip questions. Generate the full pipeline for: $PROMPT. PySpark for data gen (~100k rows via spark.range + Faker UDFs), SQL for all transforms. Include TALK/SCALING/DW-BRIDGE narration comments. Execute SQL via MCP. Create dashboard. Include proof points."

# ─── Pre-Flight & Verification ──────────────────────────────────────────────

# Verify all interview tooling before the session (Pi + Claude Code)
interview-check:
  #!/usr/bin/env bash
  echo "╔══════════════════════════════════════════╗"
  echo "║   Coding Interview Pre-Flight Check      ║"
  echo "╚══════════════════════════════════════════╝"
  echo ""
  # Databricks auth
  echo "── Databricks ──"
  databricks -p slysik auth describe 2>&1 | head -3
  echo ""
  # Claude Code files
  echo "── Claude Code ──"
  for f in \
    ".claude/skills/dbx-interview-playbook/SKILL.md:Interview Playbook (Skill)" \
    "vertical-quick-swap.md:Vertical Quick-Swap" \
    "tasks/lessons.md:Lessons Learned" \
    ".claude/hooks/validators/dbx_best_practices_validator.py:Best Practices Validator"; do
    FILE="${f%%:*}"
    LABEL="${f##*:}"
    test -f "$FILE" && echo "  ✓ $LABEL" || echo "  ✗ MISSING: $LABEL ($FILE)"
  done
  echo ""
  # Pi files
  echo "── Pi ──"
  for f in \
    ".pi/agents/databricks-code-gen.md:Code Gen Agent" \
    ".pi/agents/spark-explainer.md:Spark Explainer Agent" \
    ".pi/agents/coding-interview-chain.yaml:Interview Chain" \
    ".pi/extensions/coding-interview-tasks.ts:Task Tracker" \
    ".pi/extensions/coding-interview-gate.ts:Interview Gate" \
    ".pi/extensions/interview-focus.ts:Focus Mode UI"; do
    FILE="${f%%:*}"
    LABEL="${f##*:}"
    test -f "$FILE" && echo "  ✓ $LABEL" || echo "  ✗ MISSING: $LABEL ($FILE)"
  done
  echo ""
  # Skills count
  echo "── Skills ──"
  CLAUDE_SKILLS=$(find .claude/skills -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
  PI_SKILLS=$(find .pi/skills -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
  echo "  $CLAUDE_SKILLS Claude Code skills | $PI_SKILLS Pi skills"
  echo ""
  # MCP
  echo "── MCP ──"
  test -f .mcp.json && echo "  ✓ MCP config present" || echo "  ✗ MISSING: .mcp.json"
  echo ""
  echo "── Ready! ──"
  echo "  Pi:          just coding-interview"
  echo "  Pi practice: just coding-practice retail"
  echo "  Claude:      just interview 'prompt here'"
  echo "  Claude file: just dbx-coding-agent-interactive-file prompt.md"
