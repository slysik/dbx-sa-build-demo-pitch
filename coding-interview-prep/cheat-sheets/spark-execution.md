# Spark Execution — How to Explain What's Happening Under the Hood

> They WILL ask: "How does this scale?" and "What happens when this runs?"
> You don't need to be a Spark internist — just know these key patterns.

## The 30-Second Spark Mental Model

```
Your SQL/PySpark Code
        ↓
   Catalyst Optimizer    ← Rewrites your query for efficiency
        ↓
   Physical Plan         ← Decides HOW to execute (join strategy, etc.)
        ↓
   DAG of Stages         ← Breaks work into stages separated by shuffles
        ↓
   Tasks per Partition   ← Each partition = 1 task = 1 CPU core
        ↓
   Executors             ← Distributed across the cluster
```

## Narrow vs Wide Transformations

### Narrow (no shuffle — fast, stays on same partition)
- `SELECT`, `WHERE`, `CAST`, `COALESCE` — column-level operations
- Each partition processes independently, no data movement
- **Say**: "This is a narrow transformation — each partition handles its own data, no shuffle needed"

### Wide (shuffle required — expensive, data moves across network)
- `GROUP BY`, `JOIN`, `DISTINCT`, `ORDER BY`, window functions with `PARTITION BY`
- Data must be redistributed across partitions by key
- **Say**: "This GROUP BY triggers a shuffle — Spark needs to collect all rows with the same key onto the same partition to aggregate them"

## How to Explain Common Operations

### GROUP BY / Aggregation
```
"When Spark executes this GROUP BY customer_id, it first does a local 
partial aggregation on each partition — like a local SUM — then shuffles 
the partial results across the network so all data for each customer_id 
lands on the same executor for the final aggregation. This is a two-stage 
process: partial aggregate → shuffle → final aggregate."
```

### JOIN
```
"For this JOIN between transactions and customers, Spark will pick a 
join strategy. If the customers table is small enough (< ~10MB), it'll 
use a broadcast join — send the entire small table to every executor. 
That avoids a shuffle entirely. If both tables are large, it'll do a 
sort-merge join, which requires shuffling both tables by the join key."
```

**Broadcast hint** (if you know one table is small):
```sql
-- NARRATE: "I'm hinting Spark to broadcast the customers table since it's 
--           only 1000 rows — this avoids an expensive shuffle on the large 
--           transactions table"
SELECT /*+ BROADCAST(c) */ *
FROM transactions t
JOIN customers c ON t.customer_id = c.customer_id
```

### Window Functions
```
"Window functions with PARTITION BY customer_id work similarly to GROUP BY — 
Spark shuffles so all rows for each customer land on the same partition. 
But unlike GROUP BY, it doesn't collapse rows — it computes the window 
value and attaches it to each original row."
```

### ORDER BY
```
"A global ORDER BY is expensive — it requires collecting all data and 
sorting across the entire dataset. For large datasets, if I just need 
the top N, I'd use LIMIT which Spark can optimize by only taking the 
top N from each partition first."
```

## Delta Lake — What to Say

### ACID Transactions
```
"Delta Lake uses a transaction log (_delta_log) to provide ACID guarantees. 
When I write to this table, it creates a new set of Parquet files and a 
JSON commit entry. If the write fails, those files are simply ignored — 
no partial data corruption. Readers always see a consistent snapshot."
```

### Time Travel
```sql
-- NARRATE: "Delta keeps a history of all changes. I can query previous 
--           versions — useful for debugging or auditing."
SELECT * FROM my_table VERSION AS OF 3;
SELECT * FROM my_table TIMESTAMP AS OF '2026-03-01';
DESCRIBE HISTORY my_table;
```

### OPTIMIZE and Z-ORDER
```sql
-- NARRATE: "OPTIMIZE compacts small files into larger ones — small files 
--           cause too many tasks and overhead. Z-ORDER on customer_id 
--           co-locates related data within files, so queries filtering 
--           by customer_id skip entire files (data skipping)."
OPTIMIZE silver.transactions ZORDER BY (customer_id);
```

### Liquid Clustering (newer, preferred over Z-ORDER)
```sql
-- NARRATE: "Liquid Clustering is the modern replacement for partitioning 
--           and Z-ORDER. It automatically reorganizes data for optimal 
--           query performance without manual maintenance."
CREATE TABLE silver.transactions
CLUSTER BY (customer_id, transaction_date)
AS SELECT * FROM bronze.transactions_raw;
```

## Scaling Talking Points

### "How would this handle 1 billion rows?"
```
"A few things I'd consider at scale:
1. The dataset generation would need to be parallelized — not a single 
   Python loop but maybe using spark.range() with UDFs
2. For the pipeline, I'd use Liquid Clustering on frequently filtered 
   columns like customer_id and date
3. The JOINs — I'd verify join strategies in the Spark UI and add 
   broadcast hints where appropriate  
4. For the Gold aggregations, I'd consider incremental processing — 
   only process new/changed records rather than full recompute
5. Delta's OPTIMIZE would compact small files from streaming writes"
```

### "What if this was streaming instead of batch?"
```
"I'd switch from batch reads to Structured Streaming:
- Bronze: Auto Loader (cloudFiles) to incrementally pick up new files
- Silver/Gold: Use streaming reads from the Delta table with 
  readStream, which processes only new rows via Delta's change data feed
- Trigger: availableNow=True for micro-batch, or processingTime 
  for continuous"
```

## Spark UI — What to Point Out (if they ask)
- **Jobs tab**: Each action (write, count, show) creates a job
- **Stages tab**: Stages are separated by shuffles — more stages = more shuffles
- **SQL tab**: Shows the physical plan — look for BroadcastHashJoin vs SortMergeJoin
- **Storage tab**: Shows cached/persisted DataFrames
