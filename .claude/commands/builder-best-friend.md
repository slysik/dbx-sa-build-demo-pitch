---
description: Explain exactly what code is doing under the hood — for interview narration
argument-hint: [code snippet, table name, or SQL statement]
---

# Builder's Best Friend

Explain what code is doing under the hood so you can narrate it confidently during the interview. Translates PySpark/SQL into plain-English execution explanations.

## Variables

CODE: $ARGUMENTS

## Instructions

- If no `CODE` provided, look at the most recently written/executed code in the conversation.
- Explain at the level of a Senior SA talking to a technical customer.
- Cover WHAT it does, HOW Spark executes it, and WHY this approach was chosen.
- Include distributed computing details: partitioning, shuffles, stages, tasks.
- Keep explanations concise — this is for live narration, not a textbook.

## Workflow

1. **Identify the code** to explain (from `CODE` or recent context)

2. **Explain in 3 layers:**

   **Layer 1 — What it does (business logic):**
   > "This takes our raw orders, deduplicates on order_id keeping the latest timestamp, and writes to Silver."

   **Layer 2 — How Spark executes it (distributed mechanics):**
   > "Under the hood, Spark will: (1) scan the Bronze Delta table using partition pruning if available, (2) shuffle data by order_id for the window function, (3) filter to keep rank=1 rows, (4) write output as new Parquet files in the Delta table."

   **Layer 3 — Why this approach (architecture rationale):**
   > "I'm using a Window function for dedup instead of groupBy because it preserves all columns without explicit aggregation. The row_number approach is deterministic when we include event_ts in the orderBy."

3. **Flag any performance considerations:**
   - Shuffle points (joins, groupBy, window with partitionBy)
   - Broadcast opportunities (small dimension tables)
   - Partition count impact
   - Skew risks

4. **Provide a ready-to-speak narration block** (1-2 paragraphs, conversational tone)

## Output Format

```
## Under the Hood

**Business Logic:** [1-2 sentences]

**Spark Execution:**
1. [Stage 1: what happens]
2. [Stage 2: what happens]
3. [Stage 3: what happens]

**Architecture Rationale:** [why this approach]

**Performance Notes:**
- [shuffle/broadcast/partition consideration]

## Ready to Narrate
> "[Conversational explanation you can read aloud or paraphrase]"
```
