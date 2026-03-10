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
