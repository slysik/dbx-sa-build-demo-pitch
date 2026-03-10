---
name: dbx-interview-playbook
description: "Databricks SA coding interview playbook — vertical-agnostic (retail/media/generic), PySpark data gen + SQL transforms. Use when generating interview code, building Bronze/Silver/Gold pipelines, or preparing for Databricks SA coding interviews. Covers: PySpark spark.range() data gen, deterministic MERGE, CHECK constraints, Liquid Clustering, idempotent Gold rebuilds, validation harness, quarantine patterns, SCD2, CDC, scaling discussion, and narration comments."
---

# Databricks SA Interview Playbook

This skill wraps the full `dbx-best-practices.md` playbook. Read it for complete templates.
See `vertical-quick-swap.md` for retail/media/generic entity maps.

## Step 0: Session Setup (MANDATORY -- Do This First)

Before generating any code, ask these questions to steer the session:

### Q1: Workspace & Catalog
Ask: "What catalog should I use?"
- **Create new** (recommended): `CREATE CATALOG <name>` + bronze/silver/gold schemas
- **Use existing**: User provides catalog name
- **Auto-detect**: `SHOW CATALOGS` and pick the right one
- NOTE: Catalog names cannot contain hyphens -- use underscores (e.g., `retail_demo`)
- NOTE: On this workspace, catalog creation requires `storage_root` parameter

### Q2: Interview Scenario
Ask: "What's the interview prompt?"
Map to vertical using `vertical-quick-swap.md`:
- **Retail**: orders, customers, products, returns, stores
- **Media**: streams, users, content, subscriptions
- **Generic** (fallback): entities, events, attributes
- **Custom prompt** (user describes)

### Q3: Time Budget
Ask: "How much time do we have?"
- 30 min -> Bronze + Silver + Gold + harness only (skip dashboard)
- 45 min -> Add dashboard + validation proof points
- 60 min -> Full pipeline including DQ page + scaling discussion

### Q4: Workspace Constraints
Ask: "Any constraints I should know about?"
- Free Edition (no serverless, no MV, limited clusters)
- Shared workspace (can't create catalogs, use existing)
- No internet access (skip pip install, use pre-loaded libs)
- None / full access

After setup, use the catalog name throughout as `{catalog}.bronze.*`, `{catalog}.silver.*`, `{catalog}.gold.*`.

## Catalog Naming Convention

All templates use `{catalog}` as placeholder. Replace with the actual catalog name from Step 0.

```
{catalog}.bronze.<table>   -- Raw ingest
{catalog}.silver.<table>   -- Cleaned, deduplicated
{catalog}.gold.<table>     -- Aggregated, feature-engineered
```

### Environment Bootstrap (first cells of every pipeline)
```sql
-- Step 0: Environment Setup
CREATE CATALOG IF NOT EXISTS {catalog};
CREATE SCHEMA IF NOT EXISTS {catalog}.bronze;
CREATE SCHEMA IF NOT EXISTS {catalog}.silver;
CREATE SCHEMA IF NOT EXISTS {catalog}.gold;
USE CATALOG {catalog};
```

## Interview Flow (CRITICAL -- Read This First)

The interview is **interactive, NOT auto-build**. Follow this phased approach:

### Phase 1: DataFrame First (0:00-0:15)
```
 0:00-0:03  Discovery (2-3 crisp questions -- see Discovery Cheat Sheet)
 0:03-0:15  PySpark data gen (spark.range + Faker UDFs, ~100k rows as DataFrame)
```
**STOP HERE.** Do NOT auto-advance to Bronze/Silver/Gold. The interviewer will:
- Ask questions about the DataFrame (schema, partitions, explain plan)
- Request adding/modifying columns
- Ask about `.repartition()`, `.coalesce()`, `df.rdd.getNumPartitions()`
- Ask about `.cache()`, `.persist()`, `.explain()`
- Ask you to optimize or filter the DataFrame

**Have `dbx_toolkit` ready:** `%run /Users/slysik@gmail.com/dbx-tools/dbx_toolkit`
- `profile(df)` -- schema, counts, partitions, nulls, execution plan
- `skew(df, keys=["store_id"])` -- partition + key skew analysis
- `nulls(df)` -- null counts per column
- `keys(df, keys=["order_id"])` -- key distribution
- `plan(df)` -- formatted execution plan

### Phase 2: Medallion Layers (only when directed)
```
 Bronze DDL + INSERT + CHECK constraints + CLUSTER BY
 Silver MERGE (ROW_NUMBER staging + OPTIMIZE + ANALYZE)
 Gold aggregates (delete-window + insert-window)
```
Only build these when the interviewer says to proceed. SQL is fine for transforms.

### Phase 3: Dashboard / Validation (only when directed)
```
 AI/BI Dashboard (KPIs + charts + DQ page)
 Validation harness + proof points
 Scaling discussion ("What if 1M rows?") + Q&A
```

### Time Budget (60 min, adaptive)
```
 0:00-0:03  Discovery
 0:03-0:15  PySpark data gen -> DataFrame ready ← CHECKPOINT
 0:15-0:30  Interactive Q&A on DataFrame (interviewer-driven)
 0:30-0:45  Medallion layers (if/when directed)
 0:45-0:55  Dashboard + validation (if/when directed)
 0:55-0:60  Scaling discussion + Q&A
```

## Pipeline Execution Protocol

### Plan-Before-Build
Before writing code, state in 1 sentence what you're building. If >3 SQL statements, write the plan as comments first. Identify which template applies.

### Stage Gates (verify each before advancing)
| Stage | Gate Criteria | Pass = |
|-------|--------------|--------|
| Data Gen | `df.count()` returns ~100k | Correct row count |
| Bronze | `SELECT count(*) FROM {catalog}.bronze.<table>` | > 0 rows |
| Silver | `SELECT pk, count(*) FROM {catalog}.silver.<table> GROUP BY pk HAVING count(*)>1` | 0 rows returned |
| Gold | Run idempotent rebuild twice, compare counts | Same count both runs |
| Dashboard | All widget queries return data via execute_sql | No empty results |
| Validation | Full 4-part harness passes | All checks green |

### Stage Report Format
After each stage gate, report: `STAGE [name] -- GATE [PASS/FAIL] -- [1-line summary]`

### When Things Go Sideways
1. **STOP** -- don't retry blindly
2. **Read** the full error message
3. **Check** Quick Fixes table below + `tasks/lessons.md`
4. **Fix** the root cause
5. **Re-run** the gate query
6. **Capture** new pattern in `tasks/lessons.md`

## Narration Comment Standards

All generated code MUST include narration comments for the two-screen interview format:

### Comment Types
- `# TALK:` -- what Steve says aloud (the "what and why")
- `# SCALING:` -- distributed systems reasoning ("what if 1M rows?")
- `# DW-BRIDGE:` -- Netezza/traditional DW comparison (shows depth)

### Terminal Output
When outputting code to the Claude Code terminal, narration comments render in Databricks orange:
```
\033[38;2;255;106;0m# TALK: This MERGE uses ROW_NUMBER to pick the latest record per key\033[0m
\033[38;2;255;106;0m# SCALING: At 1M rows, CLUSTER BY on the join key pre-sorts -> merge-join instead of shuffle\033[0m
\033[38;2;255;106;0m# DW-BRIDGE: In Netezza, this is a distribution key on the join column -- same locality principle\033[0m
```

### Rules
- 2-3 narration lines per code block (not more -- keep it tight)
- Notebook code does NOT have ANSI codes -- only terminal output
- Every stage must have at least one TALK + one SCALING comment

## Scaling Discussion Talk Track

Condensed per-stage reference for "What if 1M rows?":

| Stage | Key Point | 20-Second Talk Track |
|-------|-----------|---------------------|
| Data Gen | spark.range() distributes | "spark.range() is embarrassingly parallel -- same code at 1M, just change N. Like nzload across SPUs." |
| Bronze | Append-only, parallel writes | "Delta append writes parallelize naturally. Liquid Clustering replaces distribution keys without schema lock-in." |
| Silver MERGE | ROW_NUMBER shuffle is the bottleneck | "The expensive op is the shuffle for ROW_NUMBER. CLUSTER BY pre-sorts on the join key -- merge-join instead of hash-join." |
| Gold | Window-delete touches <1% | "Delete-window scopes to 14 days. At 1B rows, that's <1% I/O vs full rewrite. Same correctness, 100x less work." |
| Dashboard | Pre-aggregated Gold | "Dashboard queries hit Gold, which is KB not TB. Summary tables -- same principle as EDW." |

## Elegance Checkpoint (Gold only)
After Gold works, pause 15 seconds and ask:
- Is the window scope tight enough? (14 days default -- appropriate for the data volume?)
- Is CLUSTER BY aligned with the dashboard's WHERE filters?
- Would a Staff Engineer approve this, or is there a cleaner approach?

## Subagent Strategy
- **Offload to subagents:** dashboard query testing (5-10 queries), proof point execution, debug investigation
- **One task per subagent**, results feed back as 1-line summary
- **Main context stays clean:** Data Gen -> Bronze -> Silver -> Gold -> Dashboard -> Validation
- Never let subagent work block the main pipeline flow

## When to Use This Skill

Invoke when:
- Building **Bronze -> Silver -> Gold** pipelines
- Generating **synthetic data** with PySpark (spark.range + Faker UDFs)
- Writing **MERGE** operations (must be deterministic with ROW_NUMBER)
- Creating **Gold aggregates** (use delete-window + insert-window, not overwrite)
- Adding **data quality** patterns (CHECK constraints, quarantine tables)
- Preparing **interview narration** (TALK/SCALING/DW-BRIDGE comments, validation harness)

## Critical Rules (Always Apply)

### 1. PySpark Data Gen + SQL Transforms
PySpark (`spark.range()` + Faker UDFs) for data gen. ALL transforms in SQL. **Never SQL-only or pandas-only for data gen.**

### 2. DECIMAL for Money
```sql
CAST(amount AS DECIMAL(18,2))  -- NEVER use FLOAT/DOUBLE for monetary values
```

### 3. Deterministic MERGE (ROW_NUMBER Staging)
```sql
-- Inline subquery (works everywhere, including serverless/MCP)
MERGE INTO {catalog}.silver.{entity}_current t
USING (
  SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY {pk} ORDER BY ingest_ts DESC) AS rn
    FROM {catalog}.bronze.{entity}_events
  ) WHERE rn = 1
) s ON t.{pk} = s.{pk}
WHEN MATCHED THEN UPDATE SET
  col1 = s.col1, col2 = s.col2  -- explicit columns, never SET *
WHEN NOT MATCHED THEN INSERT (col1, col2) VALUES (s.col1, s.col2);
```

### 4. Post-DDL Standards (Every Table)
```sql
-- CHECK constraints
ALTER TABLE {catalog}.silver.{entity} ADD CONSTRAINT chk_amt CHECK (amount IS NULL OR amount >= 0);

-- Liquid Clustering
ALTER TABLE {catalog}.silver.{entity} CLUSTER BY ({fk}, event_date);
OPTIMIZE {catalog}.silver.{entity};
ANALYZE TABLE {catalog}.silver.{entity} COMPUTE STATISTICS FOR ALL COLUMNS;
```

### 5. Gold: Idempotent Window Rebuild
```sql
DELETE FROM {catalog}.gold.{entity}_agg WHERE event_date >= date_sub(current_date(), 14);
INSERT INTO {catalog}.gold.{entity}_agg SELECT ... WHERE event_date >= date_sub(current_date(), 14);
```

### 6. Validation Harness (Last Cells, Always)
- Row counts across layers (Bronze >= Silver)
- Uniqueness check on business key (`GROUP BY HAVING count > 1`)
- Rule violation counts (negative amounts, bad enums)
- Pruning-friendly sample query (filters match CLUSTER BY keys)

### 7. AI Audit Self-Check
Before outputting code: Compiles? Deterministic? Idempotent? Scalable? Why-comments? Harness?
8. **Narration?** -- TALK/SCALING/DW-BRIDGE comments in every code block
9. **PySpark data gen?** -- spark.range(), not pandas-only or SQL-only
10. **Vertical-agnostic?** -- No hardcoded FinServ terms, uses entity placeholders
11. **Dashboard?** -- All queries tested, DQ page included, proper versions
12. **Proof points?** -- At least 2 of: constraint test, EXPLAIN pruning, idempotency, time travel

## Pipeline Sequence

```
PySpark Data Gen -> Bronze DDL + INSERT -> Silver MERGE ->
Gold Agg -> Dashboard (+ DQ page) -> Validation Harness -> Proof Points
```

No MV or metric views in default flow (add only if time permits and workspace supports).

## Discovery Cheat Sheet

Pre-computed discovery questions for each vertical:

### Retail
| Question 1 | Question 2 | Question 3 |
|-----------|-----------|-----------|
| "What's the business key -- order_id, or composite with line_id?" | "Do returns arrive as separate events or status updates?" | "Loyalty tiers -- do they affect pricing or just segmentation?" |

### Media
| Question 1 | Question 2 | Question 3 |
|-----------|-----------|-----------|
| "Business key -- stream_id, or user_id + content_id + start_ts?" | "Tracking engagement (watch_pct) or just view counts?" | "Churn definition -- no activity in 30 days, or subscription lapsed?" |

### Generic
| Question 1 | Question 2 | Question 3 |
|-----------|-----------|-----------|
| "What's the natural business key for dedup?" | "Latest-wins, or do we need history (SCD2)?" | "Main query patterns -- date range? entity lookup? category drill-down?" |

## DW Bridge -- Say These to Show Depth

**PySpark Data Gen:**
"spark.range() distributes row generation across executors --
same principle as nzload parallelizing inserts across SPUs in Netezza.
The hash-based column generation avoids Python UDF overhead."

**CLUSTER BY:**
"In Netezza, we'd pick distribution keys upfront and be locked in.
Liquid Clustering gives the same data locality benefit but adapts
automatically as query patterns shift -- it's distribution keys without
the schema rigidity."

**MERGE determinism:**
"In a traditional DW, the RDBMS enforces PK/FK at the storage layer.
Delta doesn't enforce PKs, so I build integrity INTO the pipeline --
ROW_NUMBER staging guarantees one source row per key. That's actually
more robust because we handle it explicitly rather than relying on
a constraint violation to catch our bug."

**Validation harness:**
"This is the equivalent of the ETL reconciliation counts we'd run
after every load in an EDW. But here I also prove data skipping
works -- the EXPLAIN shows files pruned, which means my clustering
keys are aligned with my query filters."

**Gold idempotent rebuild:**
"In Netezza, we'd TRUNCATE and reload a summary table. The problem
at scale is you're rewriting 100% of data for a 1% change. Delete-
window + insert-window scopes the rebuild to the changed date range --
same correctness, 100x less I/O."

## Proof Points -- Do These Proactively

### 1. Constraint Enforcement (30 sec)
```sql
INSERT INTO {catalog}.silver.{entity}_current VALUES ('bad', ..., -100.00, ...);
-- Shows: CHECK constraint rejects the row. "Delta enforces this at write time."
```

### 2. Pruning Proof (30 sec)
```sql
EXPLAIN SELECT ... WHERE {fk} = 'E000123' AND event_date >= '2026-02-01';
-- Point out: "files pruned" in output. "My CLUSTER BY keys match my WHERE clause."
```

### 3. Idempotency Proof (20 sec)
```sql
-- Run Gold rebuild twice, compare counts. "Same numbers -- rerun-safe."
```

### 4. Time Travel (20 sec)
```sql
DESCRIBE HISTORY {catalog}.silver.{entity}_current;
SELECT * FROM {catalog}.silver.{entity}_current VERSION AS OF 0 LIMIT 5;
-- "Full audit trail built into Delta -- no extra infrastructure."
```

## Quick Fixes (When Things Break)

| Symptom | Cause | Fix (< 30 sec) |
|---------|-------|-----------------|
| MERGE "multiple source rows match" | Missing ROW_NUMBER | Add staging view with dedup |
| INSERT violates CHECK | Bad source data | Add WHERE filter, explain to interviewer |
| CREATE MATERIALIZED VIEW fails | Free Edition / no serverless | `CREATE OR REPLACE VIEW` instead |
| Cluster won't start | Free Edition limits | Switch to serverless warehouse |
| Query takes >30s | No clustering/stats | OPTIMIZE + ANALYZE, explain trade-off |
| Dashboard "Invalid widget" | Wrong version number | Counter/table/filter: v2. Chart: v3. Text: no spec. |
| TEMP VIEW not found in MERGE | Serverless: each SQL is separate session | Use inline subquery/CTE |
| ProtocolChangedException on ALTER | Two ALTERs on same table ran concurrently | Run constraints sequentially |
| MERGE inserts extra `rn` column | `SET *` pulls all columns from ROW_NUMBER | Use explicit column list |
| TABLE_OR_VIEW_NOT_FOUND | Missing catalog/schema qualifier | Always use `catalog.schema.table` |
| CHECK constraint violation on INSERT | Source data violates constraint | Add WHERE filter, explain |
| DECIMAL overflow in Gold SUM | DECIMAL(18,2) overflows on large agg | Use DECIMAL(38,2) for Gold |
| Column name is reserved word | `timestamp`, `date`, `type` etc. | Backtick reserved words |
| CREATE CATALOG fails "storage root" | Workspace requires explicit storage | Add `MANAGED LOCATION '<path>'` |
| Catalog name with hyphen fails | UC doesn't allow hyphens | Use underscores |
| Faker UDF fails on serverless | No library install on serverless | Use hash-based generation only, skip Faker |

## Full Reference
See `dbx-best-practices.md` in project root for:
- SS6: PySpark data gen (spark.range + Faker UDFs)
- SS7: Silver templates (current-state, CDC, SCD2)
- SS8: Gold templates (idempotent rebuild)
- SS9: Quarantine pattern
- SS10: Reconciliation template
- SS11: Validation harness queries
- SS12: AI audit checklist
- SS13: Scaling Discussion Framework
- SS15: 30-second "think out loud" script
