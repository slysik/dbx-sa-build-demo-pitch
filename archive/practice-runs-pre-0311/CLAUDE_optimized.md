# CLAUDE.md — Databricks Sr. SA Interview

**Interview: Sr. Databricks SA | Wednesday March 11, 2026**
**Profile: `slysik` | User: `slysik@gmail.com` | Catalog: `dbx_weg`**
**MCP: adb-7405613453749188.8.azuredatabricks.net (configured in `.mcp.json`)**

---

## OPERATING PRINCIPLE

Act as a **Senior Databricks Solutions Architect**. Don't ask unnecessary questions — state assumptions and build. Narrate decisions while coding (why this feature, where quality is enforced, how it scales). Correctness first, then optimize.

---

## INTERVIEW WORKFLOW

Prompt arrives → State assumptions → Generate data → Build Bronze → Silver → Gold → (SDP / Dashboard if asked) → Validate

**Do not** over-plan. Build incrementally, narrate as you go.

---

## WORKSPACE — QUICK COMMANDS

```bash
just dbx-auth                          # Check auth
just dbx-sql "SELECT 1"               # Run SQL via serverless
just dbx-catalogs                      # List catalogs
just dbx-schemas dbx_weg               # List schemas
just dbx-tables dbx_weg bronze         # List tables
just nb-upload <local> <workspace>     # Upload notebook
just nb-upload-all                     # Upload all notebooks
```

---

## SKILL ROUTING — READ BEFORE BUILDING

Skills load on-demand with full patterns, gotchas, and code templates. **Always read the relevant SKILL.md before building that component.**

| Interview Task | Skill to Read |
|---|---|
| **Synthetic data generation** | `.agents/skills/synthetic-data-generation/SKILL.md` |
| **SDP / Lakeflow pipelines** | `.agents/skills/spark-declarative-pipelines/SKILL.md` |
| **AI/BI Dashboard** | `.agents/skills/databricks-aibi-dashboards/SKILL.md` |
| **DBSQL / SQL features** | `.agents/skills/databricks-dbsql/SKILL.md` |
| **Unity Catalog / Volumes** | `.agents/skills/databricks-unity-catalog/SKILL.md` |
| **Structured Streaming** | `.agents/skills/databricks-spark-structured-streaming/SKILL.md` |
| **Jobs / Workflows** | `.agents/skills/databricks-jobs/SKILL.md` |
| **Asset Bundles (CI/CD)** | `.agents/skills/asset-bundles/SKILL.md` |
| **Genie Spaces** | `.agents/skills/databricks-genie/SKILL.md` |
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
- Bronze metadata: `_ingest_timestamp`, `_source_file`, `_batch_id`
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
| Data generation | 100k rows, explicit schema, seed=42, realistic imperfections |
| Cloud file ingestion | Auto Loader |
| Managed pipeline | Lakeflow Spark Declarative Pipelines (`from pyspark import pipelines as dp`) |
| Custom upsert | Delta MERGE (seed first batch, merge subsequent) |
| New table layout | Liquid clustering (not legacy partitioning) |
| CDC | `create_auto_cdc_flow()` (only for true CDC) |
| Governance | Unity Catalog — 3-level namespace everywhere |
| BI serving | Databricks SQL / AI/BI Dashboards |
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
├── databricks.yml              # Asset Bundle config
├── notebooks/                  # Databricks notebooks
├── src/                        # Pipeline code
│   ├── bronze/                 # Ingestion
│   ├── silver/                 # Transforms
│   ├── gold/                   # Aggregations
│   └── pipelines/              # Lakeflow definitions
└── tests/                      # pytest + chispa
```
