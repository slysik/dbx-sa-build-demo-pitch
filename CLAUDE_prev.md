# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Databricks Solutions Architect workspace primarily focused on preparing for the **Design & Architecture Interview** (see `Design & Architecture Interview_Candidate Prep.pdf`). Contains technical demos, reference architectures, and platform exploration materials. Vertical-agnostic: retail, media, or generic (see `vertical-quick-swap.md`). Not a git repository.

## Key Commands

```bash
# Databricks CLI (all use profile "slysik")
just dbx-auth                          # Check auth status
just dbx-sql "SELECT 1"               # Run SQL via serverless warehouse
just dbx-catalogs                      # List Unity Catalog catalogs
just dbx-schemas <catalog>             # List schemas
just dbx-tables <catalog> <schema>     # List tables
just medallion                         # Show all bronze/silver/gold tables in dbx_weg

# Notebook management
just nb-upload-all                     # Upload all notebooks to workspace
just nb-upload <local> <workspace>     # Upload single notebook
just nb-download <workspace> <local>   # Download notebook

# Jobs
just dbx-jobs                          # List all jobs
just dbx-run <job_id>                  # Trigger a job run

# Claude Code modes
just claude                            # Interactive session (opus)
just plan "prompt"                     # Plan with 7-review team workflow
just auto "prompt"                     # Headless with full permissions
```

## Architecture: FinServ Medallion Demo

The `notebooks/` directory contains a 4-stage pipeline running on the `dbx_weg` catalog:

```
01_Bronze  -->  02_Silver  -->  03_Gold  -->  04_MLflow
Raw ingest      PII masking     Aggregates     Fraud detection
(streaming)     + validation    + features     + model registry
```

- **Catalog**: `dbx_weg` with `bronze`, `silver`, `gold` schemas
- **Checkpoints**: stored in Unity Catalog Volumes (`/Volumes/dbx_weg/...`)
- **MLflow experiment**: `/Users/slysik@gmail.com/finserv-fraud-detection`
- **Streaming pattern**: uses `availableNow=True` (serverless-compatible) instead of `processingTime`
- All notebooks are Databricks notebook format (not `.ipynb`) with `# COMMAND ----------` cell separators

## MCP Integration

The Databricks MCP server is configured in `.mcp.json` using the `slysik` config profile. This provides direct tool access to Databricks APIs (execute SQL, manage clusters/warehouses, Unity Catalog operations, etc.).

## Databricks Skills

Over 30 Databricks-specific skills are installed in `.claude/skills/` covering: Unity Catalog, DBSQL, Spark Declarative Pipelines, Model Serving, Agent Bricks, Genie, Jobs, Asset Bundles, Lakebase, Zerobus Ingest, MLflow tracing/evaluation, and more.

### Skill Routing (MUST follow)

Before executing any Databricks task, **READ the relevant SKILL.md** file for domain-specific patterns, gotchas, and best practices. This is especially critical for subagents/builders that don't auto-trigger skills.

| Task | Skill to Read |
|------|--------------|
| Dashboard creation | `.claude/skills/databricks-aibi-dashboards/SKILL.md` |
| Data generation (PySpark + Faker) | `.claude/skills/databricks-synthetic-data-generation/SKILL.md` |
| Zerobus / streaming ingest | `.claude/skills/databricks-zerobus-ingest/SKILL.md` |
| SQL scripting / stored procs / AI functions | `.claude/skills/databricks-dbsql/SKILL.md` |
| Unity Catalog (grants, volumes, system tables) | `.claude/skills/databricks-unity-catalog/SKILL.md` |
| Spark Declarative Pipelines (DLT/SDP) | `.claude/skills/databricks-spark-declarative-pipelines/SKILL.md` |
| Jobs (create, schedule, run) | `.claude/skills/databricks-jobs/SKILL.md` |
| Genie Spaces (NL-to-SQL) | `.claude/skills/databricks-genie/SKILL.md` |
| Model Serving endpoints | `.claude/skills/databricks-model-serving/SKILL.md` |
| Interview prep / coding demo | `.claude/skills/dbx-interview-playbook/SKILL.md` |
| Architecture diagrams | `.claude/skills/excalidraw-architect/SKILL.md` |
| Vector Search | `.claude/skills/databricks-vector-search/SKILL.md` |
| Asset Bundles (DABs) | `.claude/skills/databricks-asset-bundles/SKILL.md` |
| Metric Views | `.claude/skills/databricks-metric-views/SKILL.md` |

When spawning builder/subagents, always include `Read these skill files:` with the relevant paths in the agent prompt.

## Hooks

Extensive hook system configured in `.claude/settings.json`:
- **PreToolUse/PostToolUse**: Logging and validation (ruff linter runs on Write/Edit)
- **Notification**: Desktop alerts for permission prompts, idle, auth
- **Stop**: Auto-saves scratchpad and session state
- **SessionStart**: Loads context on startup/resume/clear
- **PreCompact**: Backs up context before compaction

## Code Style: Two Modes

- **Existing notebooks** (`notebooks/*.py`): PySpark-heavy, streaming-first demos with `foreachBatch`, rate source, and PySpark DataFrame API. Good for showing streaming patterns.
- **Interview pipeline** (`.pi/agents/`): PySpark for data gen (`spark.range()` + Faker UDFs, ~100k rows), SQL for all transforms per `dbx-best-practices.md` playbook. Enforces: DECIMAL for money, ROW_NUMBER before MERGE, CHECK constraints, Liquid Clustering + OPTIMIZE + ANALYZE, idempotent Gold window-rebuild, TALK/SCALING/DW-BRIDGE narration comments, and mandatory validation harness.

When generating new interview code, always use **PySpark for data gen** and **SQL for transforms**. Include narration comments (TALK/SCALING/DW-BRIDGE) in all code.

## Conventions

- Databricks profile name: `slysik`
- Workspace user: `slysik@gmail.com`
- Python scripts use `uv run` for execution (single-file script pattern)
- Excalidraw files (`.excalidraw`) are architecture diagrams - treat as binary artifacts
- **Interview focus**: Databricks SA Design & Architecture Interview — vertical-agnostic (retail/media/generic), two-screen format, PySpark data gen + SQL transforms
