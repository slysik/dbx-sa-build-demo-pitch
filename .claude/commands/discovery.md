---
description: Scope an interview prompt — ask clarifying questions before planning
argument-hint: [interviewer prompt]
---

# Discovery

Scope a Databricks coding interview prompt by asking targeted clarifying questions. Output a structured brief that feeds into `/plan`.

## Variables

PROMPT: $ARGUMENTS

## Instructions

- If no `PROMPT` is provided, ask the user to paste the interviewer's prompt.
- You are acting as a Senior Databricks SA receiving a customer/interviewer prompt.
- Do NOT start building. Discovery is about understanding scope before code.
- Ask only what is genuinely missing — state assumptions for everything else.
- Keep it fast — this should take 2-3 minutes max during a live interview.

## Workflow

1. **Read the prompt** and identify:
   - Business domain (retail, media, generic)
   - Data shape (events, transactions, logs, etc.)
   - Scale expectation (rows, velocity)
   - Batch vs streaming
   - Target layers (Bronze only? Full medallion?)
   - Key features to demo (Delta MERGE, Lakeflow, Auto Loader, DBSQL, etc.)
   - Definition of done (table? dashboard? pipeline?)

2. **State assumptions explicitly** for anything you can infer:
   > "I'm assuming 100k rows, batch processing, full medallion, Delta tables. Let me know if any of that's off."

3. **Ask only missing questions** (max 3-5):
   - What's the dedup key?
   - Any specific aggregation the interviewer wants to see?
   - Dashboard required or just tables?
   - Any feature they specifically want demonstrated?

4. **Output a structured discovery brief:**

```
## Discovery Brief

**Domain:** [retail/media/generic]
**Entity:** [orders/events/streams/etc.]
**Scale:** [100k rows]
**Processing:** [batch/streaming]
**Layers:** [Bronze → Silver → Gold]

### Assumptions
- [assumption 1]
- [assumption 2]

### Key Deliverables
- [ ] Synthetic dataset (PySpark, ~100k rows)
- [ ] Bronze table with ingestion metadata
- [ ] Silver table (deduped, typed, quality gates)
- [ ] Gold aggregation table
- [ ] Dashboard (if requested)

### Features to Demonstrate
- [Delta MERGE / Liquid Clustering / etc.]

### Dedup Key: [field]
### Partition Strategy: [liquid clustering / none]
### Narration Points: [what to talk about while building]
```

5. **Save** the brief to `specs/discovery-brief.md`

## Report

```
Discovery complete. Brief saved to specs/discovery-brief.md.
Ready for /plan.
```
