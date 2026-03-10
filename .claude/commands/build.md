---
description: Implement the plan
argument-hint: [path-to-plan]
---

# Build

Interview-optimized builder. Processes one step at a time, narrates as it goes, and waits for direction between steps.

## Variables

PATH_TO_PLAN: $ARGUMENTS

## Mode Detection

Check for interview context in this order:
1. Does `specs/discovery-brief.md` exist? → **Interview mode**
2. Is `PATH_TO_PLAN` provided? → **Plan mode** (standard)
3. Neither? → Ask the user what to build.

---

## Interview Mode (when `specs/discovery-brief.md` exists)

This is a live coding interview. Build interactively — one cell at a time.

### Rules
- **DataFrame-first** — PySpark with `spark.range()` + Faker UDFs for data gen
- **One step at a time** — do NOT auto-build end-to-end
- **Wait for interviewer direction** between steps
- **Narrate everything** — TALK/SCALING/DW-BRIDGE comments in Databricks orange
- **SQL is fine** for transforms, dashboards, tables — but only when asked
- **No MLflow** unless explicitly requested
- **Test SQL via `execute_sql`** before putting it in notebooks

### Interview Build Sequence

**Step 1: Synthetic Dataset (~100k rows)**
- Read `specs/discovery-brief.md` for domain, entity, schema
- Generate using PySpark (`spark.range()` + hash/Faker UDFs)
- Add realistic imperfections (2-5% nulls, 1-3% dupes, 1% outliers, skewed keys)
- Show the DataFrame: `.printSchema()`, `.show(10)`, `.count()`
- **PAUSE** — ask: "Dataset looks good. Want me to inspect anything before we move on?"

**Step 2: DataFrame Exploration (be ready)**
- Interviewer may ask: repartition, coalesce, getNumPartitions, explain, add columns, filter, groupBy, cache/persist, schema inspection
- Answer each question with code + narration
- **PAUSE** after each — wait for next question or "move on"

**Step 3: Bronze Table**
- Add ingestion metadata (`_ingest_timestamp`, `_source_file`, `_batch_id`)
- Write to Delta: `catalog.schema.table` (fully qualified)
- Verify: row count, `DESCRIBE DETAIL`
- **PAUSE** — "Bronze is loaded. Ready for Silver, or want to explore the table?"

**Step 4: Silver Transform**
- Dedup on natural key (from discovery brief)
- Type casting, null handling, business rules
- Write to Delta with explicit schema
- Verify: no dupes, no null keys, row count delta from Bronze
- **PAUSE** — "Silver is clean. Ready for Gold?"

**Step 5: Gold Aggregation**
- Build consumption-ready aggregation (from discovery brief)
- Use DECIMAL(38,2) for monetary SUMs
- Write to Delta
- Verify: business logic correctness
- **PAUSE** — "Gold is ready. Want a dashboard, or should we discuss scaling?"

**Step 6: Dashboard / Scaling (if directed)**
- Dashboard: test all SQL via `execute_sql` first, then deploy
- Scaling: run `/distributed-computing-review` on the pipeline

### Narration Format
Every code block should include orange narration:
```python
# TALK: [what you're doing and why]
# SCALING: [how this behaves at 10x/100x]
# DW-BRIDGE: [data warehouse parallel for Steve's background]
```

### Error Handling
If any step fails, automatically run `/bail` logic:
1. Check `tasks/lessons.md` for known gotchas
2. Fix immediately
3. Narrate the fix as a teaching moment
4. Capture new lessons

### Stage Reporting
After each completed step, output:
```
STAGE [name] — GATE [PASS/FAIL] — [summary]
```

---

## Plan Mode (standard — when PATH_TO_PLAN is provided)

- Read and execute the plan at `PATH_TO_PLAN`
- Think hard about the plan and implement it into the codebase
- Follow the plan's step-by-step tasks in order

---

## Report

**Interview mode:** After each step, report the stage gate. After all steps:
```
Databricks Objects Built:
| Object | Type | Gate | Link |
|--------|------|------|------|
```
(Use Databricks orange ANSI for the header)

**Plan mode:** Present the `## Report` section of the plan.
