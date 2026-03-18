# Lessons Learned
> Auto-loaded at session start. Each lesson prevents a past mistake.

## Pipeline Execution Rules
| # | Date | Trigger | Rule |
|---|------|---------|------|
| 1 | 2026-03-04 | rand(column) fails | Use hash(id,'salt') with modular arithmetic |
| 2 | 2026-03-04 | INTERVAL expr parse error | Use timestampadd(DAY, -expr, ts) |
| 3 | 2026-03-04 | TEMP VIEW not found in serverless | Use inline subquery/CTE |
| 4 | 2026-03-04 | Concurrent ALTER fails | Run constraints on same table sequentially |
| 5 | 2026-03-04 | CLUSTER BY in execute_sql_multi | Run separately via execute_sql |
| 6 | 2026-03-04 | Column DEFAULT not enabled | Handle defaults at INSERT time, not DDL |
| 7 | 2026-03-04 | Dashboard missing pageType | Always include "pageType": "PAGE_TYPE_CANVAS" |

## Process Rules
| # | Date | Trigger | Rule |
|---|------|---------|------|
| 8 | 2026-03-05 | Interview format change | PySpark (spark.range + Faker UDFs) for data gen, SQL for transforms |
| 9 | 2026-03-05 | Candidates dinged for SQL-only | Never SQL-only for data gen — PySpark required |
| 10 | 2026-03-05 | Two-screen interview format | Narrate code (TALK/SCALING/DW-BRIDGE comments), scaling discussion, no MLflow |
| 24 | 2026-03-05 | CHECK constraint rejects insert | Expected behavior — proof point for interview |
| 25 | 2026-03-05 | F.timestampadd not in PySpark | Use F.expr("make_interval(...)") or column arithmetic for timestamp offsets in PySpark |
| 26 | 2026-03-05 | Dashboard text widget format | multilineTextboxSpec works with lines as markdown strings; fails with nested item objects. frame goes INSIDE spec. |
| 27 | 2026-03-05 | Stage report request | Always output "Databricks Objects Built" in orange with clickable workspace links for every object |
| 28 | 2026-03-05 | Notebooks not visible after MCP run | Always upload notebooks to workspace so artifacts are browseable during interview |
| 29 | 2026-03-05 | Zerobus DECIMAL(p,s) fails | Zerobus does NOT support DECIMAL — use DOUBLE for monetary columns |
| 30 | 2026-03-08 | Dashboard datasets not found | Datasets must be at dashboard root level (not inside pages) with `displayName` field |
| 31 | 2026-03-08 | Dashboard dataset displayName empty | Every dataset needs `"displayName": "Human Name"` — validation rejects empty |
| 32 | 2026-03-08 | Interview flow update | DataFrame-first, interactive session. Don't auto-build end-to-end. Wait for interviewer direction. |
| 33 | 2026-03-08 | DataFrame questions expected | Be ready: repartition, coalesce, getNumPartitions, explain, add columns, cache/persist, schema |
| 34 | 2026-03-09 | .rdd fails on serverless | Never use df.rdd on serverless — use F.spark_partition_id() for partition count. SQL warehouses only run SQL cells. |
| 35 | 2026-03-09 | Code without skill check | ALWAYS invoke relevant Databricks skill before writing code — ensures best practices and correct patterns |
| 48 | 2026-03-10 | Error calling tool 'execute_sql': Failed to list SQL warehouses: unable to parse response. This is likely a bug in the D... | TODO: add rule |

## Practice Run Lessons (2026-03-10)
| # | Date | Trigger | Rule |
|---|------|---------|------|
| 49 | 2026-03-10 | SessionStart hook error on startup | Hooks referencing missing files crash silently. Audit all hook paths before interview. Removed `check_update.sh` reference. |
| 50 | 2026-03-10 | 43-second response for simple MCP call | PreToolUse/PostToolUse hooks doing JSON read-parse-append-rewrite on every tool call. **Disable all logging hooks for interview.** Log files grow to MBs and kill performance. |
| 51 | 2026-03-10 | 7-second delay on every prompt | UserPromptSubmit hook injecting scratchpad + lessons on every prompt via `uv run`. **Disabled for interview.** Context injection isn't worth 7s/prompt. |
| 52 | 2026-03-10 | CLAUDE.md 41KB burns ~10K tokens/prompt | Keep CLAUDE.md under 200 lines. All reference content belongs in skills (loaded on-demand), not top-level context. Optimized version is 166 lines. |
| 53 | 2026-03-10 | CREATE CATALOG fails on new workspace | New Azure Databricks workspace has no default storage root. Must create: storage account → access connector → role assignment (wait 30s for propagation) → storage credential → external location → catalog with `storage_root`. |
| 54 | 2026-03-10 | User Active: False in SCIM on new workspace | Personal Microsoft accounts (@gmail.com via live.com) often get `active: false` in new Azure Databricks workspaces. Causes 403 on CLI, session expiry in UI. **Fix: generate PAT token from UI before session expires, switch to `token =` in databrickscfg.** |
| 55 | 2026-03-10 | DataFrames not available in API execution context | Each `run_on_cluster.py` call creates a new execution context. Cached DataFrames from notebook cells aren't available. **Run Volume-save code in the same notebook where DataFrames are cached.** |
| 56 | 2026-03-10 | SDP notebook path mismatch | Files uploaded as `bronze.sql` but pipeline referenced `/pipeline/bronze` (no extension). **Always check `workspace list` to confirm actual paths match pipeline library config.** |
| 57 | 2026-03-10 | Gold tables empty after scaling orders to 1M | `crossJoin(spark.range(10))` appended `-0` through `-9` to order_id. Order_items still had original IDs → join produced 0 rows. **When scaling a fact table, also scale all child/detail tables with matching keys, OR adjust join logic.** |
| 58 | 2026-03-10 | Serverless SQL wait_timeout error | `wait_timeout` must be between 5s and 50s (not 60s). Use `"wait_timeout": "50s"`. |
| 59 | 2026-03-10 | databricks workspace import syntax | `databricks workspace import <TARGET_PATH> --file <LOCAL_PATH>` — target path is positional arg, source is `--file` flag. |
| 60 | 2026-03-10 | Notebook cell "Waiting" indefinitely | Previous cell or API execution context blocking the cluster. **Fix: click red stop button, or detach/reattach notebook to cluster (switch to serverless and back works too).** |
| 61 | 2026-03-10 | Indented code when pasting into Databricks notebook | Use **Cmd+Shift+V** (paste without formatting) instead of Cmd+V to avoid extra indentation. |
| 62 | 2026-03-10 | F.broadcast() on crossJoin multiplier | Always `F.broadcast()` the small multiplier DataFrame in crossJoin to avoid shuffle. Also prefer cast-to-long arithmetic over `make_interval()` for timestamp offsets — faster. |
| 63 | 2026-03-10 | .rdd.getNumPartitions() on classic vs serverless | `.rdd` works fine on all-purpose clusters. Only blocked on serverless. Use `F.spark_partition_id()` as the universal safe pattern for interview narration. |
| 64 | 2026-03-10 | SDP pipeline completes in ~30s on serverless | Serverless SDP is fast. Don't over-estimate pipeline run times. Bronze+Silver+Gold with 1M orders completes in under a minute. |
| 65 | 2026-03-10 | MCP not available in pi sessions | `run_python_file_on_databricks` MCP tool only available in Claude Code, not pi. Use `scripts/run_on_cluster.py` helper (Command API) as fallback, or run code directly in notebook cells. |
| 66 | 2026-03-10 | Parquet→Volume→read_files→Bronze MV is unnecessary | Write DataFrames directly to managed Bronze Delta tables via `.saveAsTable()`. SDP starts at Silver. Eliminates Volume creation, parquet staging, and `read_files()` layer. Bronze gets full Delta: time travel, DESCRIBE HISTORY, Liquid Clustering, table properties. Every Bronze table must carry governance columns: `_ingest_ts`, `_batch_id`, `_source_system`, `_source_type`, `_generator_version`, `_run_id`. Also set TBLPROPERTIES for lineage. This pattern is for notebook/app-generated data — if raw file arrival or Auto Loader replay is needed, file-based ingestion is still justified. |
| 67 | 2026-03-10 | Extensions add friction in interviews | 5 interview extensions were tried and disabled. Interactive mode + pre-built templates beats extension-heavy automation. ONE passive extension (timer + prompt widget + context %) is the sweet spot. |

## Community / Free Edition Workspace Differences (2026-03-13)
| # | Date | Trigger | Rule |
|---|------|---------|------|
| 68 | 2026-03-13 | cannot create job: Only serverless compute is supported | Databricks Free Edition / Community workspaces only support serverless compute for jobs. Do not use `new_cluster` blocks with node types (e.g., `m5d.large`) in `databricks.yml`. |
| 69 | 2026-03-13 | Metastore storage root URL does not exist | Free Edition workspaces often lack a default storage root for Unity Catalog. Do not try to `CREATE CATALOG`. Use the pre-existing `workspace` catalog instead. |
| 70 | 2026-03-13 | Invalid JSON in field 'serialized_space' | Programmatically creating Genie spaces via the Databricks Python SDK (`w.genie.create_space`) is brittle due to undocumented, strict JSON schemas. Generate instructions in Markdown and paste them into the UI. |
| 71 | 2026-03-13 | Privilege MODIFY is not applicable | You cannot `GRANT MODIFY` on Silver or Gold tables created by Spark Declarative Pipelines (SDP) because they are Materialized Views. Only `GRANT SELECT` is permitted. |
| 72 | 2026-03-13 | unknown command "sql" for "databricks" | To list SQL warehouses via CLI, the correct command is `databricks warehouses list`, NOT `databricks sql warehouses list`. |
