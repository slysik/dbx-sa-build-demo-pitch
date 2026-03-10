---
description: Distributed reasoning review — analyze how code scales and suggest optimizations
argument-hint: [table name, SQL statement, or "last" for most recent code]
---

# Distributed Computing Review

Analyze code or tables for distributed computing behavior. Provides scaling discussion points, optimization suggestions, and ready-to-use syntax for the interview's "distributed reasoning" phase.

## Variables

TARGET: $ARGUMENTS

## Instructions

- If `TARGET` is a table name, inspect it via MCP (`DESCRIBE DETAIL`, `DESCRIBE HISTORY`, row counts).
- If `TARGET` is SQL/PySpark code, analyze the execution plan.
- If `TARGET` is "last" or empty, review the most recently executed code.
- Output must include concrete syntax the interviewer can ask you to run (`.explain()`, `getNumPartitions()`, etc.).
- Frame everything as what a Senior SA would discuss with a customer about production readiness.

## Workflow

1. **Identify the target** (table, SQL, or recent code)

2. **Analyze distributed behavior:**

   **Partitioning:**
   - How many partitions? (`df.rdd.getNumPartitions()`)
   - Is the data skewed? (check key distribution)
   - Would repartition or coalesce help?

   **Shuffles:**
   - Where do shuffles occur? (joins, groupBy, window, distinct)
   - Can any be eliminated? (broadcast join, pre-partitioned data)
   - What's the shuffle partition count? (`spark.sql.shuffle.partitions`)

   **Execution Plan:**
   - Run `.explain(True)` or `.explain("formatted")` analysis
   - Identify: scans, exchanges (shuffles), sorts, projections
   - Is AQE enabled and helping?

   **Scaling Characteristics:**
   - How does this behave at 10x, 100x, 1000x?
   - What's the bottleneck? (CPU, memory, I/O, shuffle)
   - Is there a skew risk on any key?

3. **Provide optimization suggestions** (ranked by impact):
   ```
   OPTIMIZATION 1: [description] — IMPACT: [high/medium/low]
   SYNTAX: [exact code to run]
   TALK TRACK: [what to say]
   ```

4. **Ready-to-run commands** for the interviewer:
   ```python
   # Partition inspection
   print(f"Partitions: {df.rdd.getNumPartitions()}")

   # Partition distribution
   part_counts = df.rdd.mapPartitions(lambda rows: [sum(1 for _ in rows)]).collect()
   print(f"Rows per partition: min={min(part_counts)}, max={max(part_counts)}, avg={sum(part_counts)//len(part_counts)}")

   # Execution plan
   df.explain("formatted")

   # Key distribution (skew check)
   df.groupBy("key_column").count().orderBy(F.desc("count")).show(10)

   # Cache for iterative analysis
   df.cache()
   df.count()  # materialize
   ```

5. **Scaling discussion template:**

## Output Format

```
## Distributed Computing Review

### Current State
- **Partitions:** [N]
- **Row count:** [N]
- **Avg rows/partition:** [N]
- **Shuffle points:** [list]
- **Skew risk:** [low/medium/high on which key]

### Execution Plan Summary
[Key stages and operations]

### Optimizations
1. **[Name]** — Impact: [high/medium/low]
   - Syntax: `[code]`
   - Talk track: "[what to say]"

2. **[Name]** — Impact: [high/medium/low]
   - Syntax: `[code]`
   - Talk track: "[what to say]"

### Scaling Discussion
> "At 100k rows this runs fine on a single node. At 10M, I'd want to [specific optimization].
> At 100M+, the key considerations are [shuffle cost / skew / partition count].
> In production, I'd configure [AQE / liquid clustering / auto-optimize] to handle this automatically."

### Commands Ready to Demo
[Pre-built code blocks the interviewer might ask you to run]
```
