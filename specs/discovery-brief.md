## Discovery Brief

**Domain:** Retail
**Entity:** Orders/Transactions
**Scale:** 10 rows (small fixture/demo)
**Processing:** Batch
**Layers:** DataFrame only (unless directed otherwise)

### Assumptions
- 10 rows = small demo/fixture dataset, not a full pipeline exercise
- PySpark `spark.range()` + derived columns for data gen
- Standard retail schema: order_id, order_ts, customer_id, product, category, quantity, amount, region, status
- Realistic but small — include at least 1 null and 1 duplicate to show awareness
- No medallion layers, dashboards, or Delta writes unless you ask for them
- Output as a DataFrame displayed in the session

### Key Deliverables
- [ ] Synthetic retail DataFrame (PySpark, 10 rows)
- [ ] Displayed in session for inspection

### Features to Demonstrate
- `spark.range()` + hash-based column generation
- Explicit schema
- DataFrame API fluency

### Dedup Key: `order_id`
### Partition Strategy: N/A (10 rows)
### Narration Points
- "Starting with an explicit schema and small fixture so we can inspect every row"
- "Using spark.range() to keep generation distributed-ready even at small scale"
- "I've included a null and a duplicate intentionally — we'll handle those in Silver if we go further"

### Open Questions
1. Full medallion or DataFrame only?
2. Dashboard required?
3. Any specific feature to demonstrate?
