# Practice Problem 3: Explain Spark Execution

## Day 3 Goal
Be able to look at ANY SQL/PySpark code and explain how Spark executes it.

## Exercise: Explain Each Query

For each query below, practice saying OUT LOUD:
1. What transformations happen (narrow vs wide)
2. Where shuffles occur
3. How many stages Spark creates
4. What join strategy Spark would pick
5. How it would scale to 1 billion rows

---

### Query 1: Simple Filter + Projection
```sql
SELECT customer_id, amount, merchant_category
FROM silver.transactions
WHERE amount > 100 AND channel = 'online'
```

**Practice answer**: "This is all narrow transformations — a filter and projection. 
Spark processes each partition independently, no shuffle needed. It's a single stage. 
At 1 billion rows, it still scales linearly — just more partitions, more tasks."

---

### Query 2: GROUP BY Aggregation
```sql
SELECT merchant_category, COUNT(*) as cnt, SUM(amount) as total
FROM silver.transactions
GROUP BY merchant_category
```

**Practice answer**: "The GROUP BY triggers a shuffle — Spark needs all rows for 
each category on the same partition. It's actually a 2-stage process: first a 
partial aggregation locally on each partition, then shuffle the partial results, 
then final aggregation. This is efficient because it reduces data before shuffling."

---

### Query 3: JOIN
```sql
SELECT t.*, c.customer_segment, c.credit_score
FROM silver.transactions t
JOIN silver.customers c ON t.customer_id = c.customer_id
```

**Practice answer**: "Spark will pick a join strategy based on table sizes. 
Customers is 1,000 rows — well under the broadcast threshold (~10MB). So Spark 
will broadcast the entire customers table to every executor, avoiding a shuffle 
on the large transactions table. This is a BroadcastHashJoin — one stage for 
the broadcast, then a single pass through transactions matching against the 
in-memory hash table. Very efficient. If both tables were huge, Spark would 
use SortMergeJoin — shuffle both tables by customer_id, sort each partition, 
then merge. That's two shuffles and much more expensive."

---

### Query 4: Window Function
```sql
SELECT *,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY transaction_date DESC) as row_num,
    AVG(amount) OVER (PARTITION BY customer_id) as customer_avg
FROM silver.transactions
```

**Practice answer**: "PARTITION BY customer_id means Spark shuffles data so all 
transactions for each customer are co-located. Then within each partition, it 
computes the window functions. Unlike GROUP BY, it doesn't collapse rows — 
it adds the computed values to each original row. So we still have the same 
number of output rows as input rows, just with extra columns."

---

### Query 5: Complex Multi-Join Gold Table
```sql
SELECT 
    c.customer_id,
    c.customer_segment,
    COUNT(t.transaction_id) as txn_count,
    SUM(t.amount) as total_spend,
    COUNT(DISTINCT a.account_id) as num_accounts,
    SUM(a.balance) as total_balance
FROM silver.customers c
LEFT JOIN silver.transactions t ON c.customer_id = t.customer_id
LEFT JOIN silver.accounts a ON c.customer_id = a.customer_id
GROUP BY c.customer_id, c.customer_segment
```

**Practice answer**: "This has two JOINs and a GROUP BY — multiple shuffles. 
Customers (1K rows) will likely be broadcast for both joins. But there's a 
subtlety: joining transactions (50K) and accounts (1.5K) through the customer 
key could create a many-to-many fan-out if a customer has 50 transactions and 
3 accounts — that's 150 intermediate rows per customer. I'd consider doing the 
aggregations in separate CTEs first, then joining the pre-aggregated results. 
That reduces the row explosion."

---

## Bonus: Run EXPLAIN on your queries
```sql
EXPLAIN FORMATTED
SELECT ... your query ...
```

Look for:
- `BroadcastHashJoin` vs `SortMergeJoin`
- `HashAggregate` (partial + final)
- `Exchange` = shuffle
- `FileScan` with `PushedFilters` = predicate pushdown into Delta

## Success Criteria
- [ ] Can explain all 5 queries out loud in < 2 minutes each
- [ ] Know narrow vs wide transformation for any operation
- [ ] Can discuss broadcast vs sort-merge join trade-offs
- [ ] Can suggest optimizations for scale
- [ ] Ran EXPLAIN on at least 2 queries and interpreted the output
