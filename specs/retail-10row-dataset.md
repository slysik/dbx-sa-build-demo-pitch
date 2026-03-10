# Plan: 10-Row Retail Dataset

## Task Description
Generate a small (10-row) retail orders dataset using PySpark on the Databricks workspace. The dataset serves as a quick demo fixture for an interactive interview session — small enough to inspect every row, but realistic enough to demonstrate DataFrame fluency, data quality awareness, and scaling readiness.

## Objective
Create and display a 10-row retail orders DataFrame on Databricks using `spark.range()` + deterministic column derivation. Include intentional imperfections (1 null, 1 duplicate) to set up downstream Silver discussion.

## Relevant Files

- `specs/discovery-brief.md` — Discovery brief with assumptions and schema
- `CLAUDE.md` — Interview defaults, data agent protocol, narration guidance

### New Files
- None required — this is a single `execute_databricks_command` session on the cluster

## Step by Step Tasks

### 1. Build the PySpark DataFrame Generator
- Use `spark.range(0, 10)` as the seed
- Derive columns using `F.expr()`, `hash()`, and modular arithmetic (no `rand(column)` — lesson #1)
- Schema columns:
  | Column | Type | Generation |
  |--------|------|------------|
  | order_id | STRING | `concat("ORD-", lpad(id+1, 5, "0"))` |
  | order_ts | TIMESTAMP | `current_timestamp() - make_interval(0,0, hash(id,'ts') % 30, hash(id,'hr') % 12, 0, 0)` |
  | customer_id | INT | `abs(hash(id, 'cust')) % 500 + 1`, null for row 7 |
  | product | STRING | array pick from `["Laptop","Headphones","Keyboard","Mouse","Monitor","Charger","Cable","Stand","Webcam","Speaker"]` via `element_at(arr, (abs(hash(id,'prod')) % 10) + 1)` |
  | category | STRING | mapped from product (electronics/accessories/peripherals) |
  | quantity | INT | `abs(hash(id, 'qty')) % 5 + 1` |
  | amount | DOUBLE | `round(abs(hash(id, 'amt')) % 50000) / 100.0 + 9.99, 2)` |
  | region | STRING | array pick from `["East","South","Midwest","West"]` |
  | status | STRING | array pick from `["complete","pending","returned","cancelled"]` weighted toward complete |
- Row 9 = duplicate of row 0 (same order_id) to show dedup awareness
- Row 7 = null customer_id to show null handling awareness

### 2. Execute on Databricks Cluster
- Use `execute_databricks_command` to run the PySpark code
- Display with `df.show(truncate=False)` and `df.printSchema()`

### 3. Narrate Key Points
- Print TALK comments in Databricks orange explaining:
  - Why `spark.range()` over `createDataFrame()` with Python lists
  - Why `hash()` over `rand()` for determinism
  - Why imperfections are intentional
  - How this scales to 100k/1M with the same pattern

### 4. Validate Output
- Confirm 10 rows returned
- Confirm schema matches expected types
- Confirm 1 null in customer_id
- Confirm 1 duplicate order_id
- `df.printSchema()` matches expected contract

## Acceptance Criteria
- [ ] DataFrame has exactly 10 rows
- [ ] All 9 columns present with correct types
- [ ] 1 null customer_id (row 7)
- [ ] 1 duplicate order_id (row 9 = row 0)
- [ ] Generated via `spark.range()` — no Python-side list of dicts
- [ ] Deterministic — re-running produces same data
- [ ] Narration comments printed in Databricks orange

## Validation Commands
- `df.count()` — expect 10
- `df.filter(F.col("customer_id").isNull()).count()` — expect 1
- `df.groupBy("order_id").count().filter("count > 1").count()` — expect 1
- `df.printSchema()` — verify types

## Notes
- This is a **DataFrame-only** exercise. No Delta writes, no medallion, no dashboard unless interviewer directs.
- If asked to scale: `crossJoin(spark.range(10000))` with new `uuid()` order_ids → 100k rows instantly.
- If asked to write to Delta: `df.write.format("delta").mode("overwrite").saveAsTable("catalog.schema.retail_orders")`
- Keep the code in a single cell — interview pacing matters.
