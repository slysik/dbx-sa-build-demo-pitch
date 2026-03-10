# Practice Problem 4: Debugging & Resilience

## Day 4 Goal
Practice hitting errors and recovering gracefully while narrating.

## Exercise: Fix These Broken Code Blocks

Each block has 1-3 intentional bugs. Find them, explain them, fix them.
Practice narrating: "I see the error... that usually means... let me check..."

---

### Bug 1: Schema Mismatch
```python
from faker import Faker
fake = Faker()

data = []
for i in range(100):
    data.append({
        "customer_id": i,
        "name": fake.name(),
        "balance": fake.random_number(digits=5)  # generates an integer
    })

df = spark.createDataFrame(data)
df.write.format("delta").mode("overwrite").saveAsTable("test_customers")

# Then this SQL fails:
# SELECT customer_id, name, balance * 1.05 AS projected_balance FROM test_customers
# WHERE balance > 1000.50
```

**What's wrong?** `balance` is an integer (random_number returns int), but we're comparing 
to a float and multiplying by a float. While Spark handles implicit casting, the real issue 
is we should use DECIMAL for money. Also `customer_id` is an integer but should be a string 
for consistency.

**How to narrate**: "The data types aren't ideal here — balance should be DECIMAL for 
financial precision, and customer_id should be a string. Let me fix the generation..."

---

### Bug 2: Column Name Mismatch
```sql
-- This query fails with AnalysisException
SELECT 
    t.customer_id,
    t.amount,
    c.first_name,
    c.last_name,
    c.credit_score
FROM silver.transactions t
JOIN silver.customers c ON t.customer_id = c.cust_id
WHERE t.amount > 100
```

**What's wrong?** Column is `customer_id` in one table but `cust_id` in the join condition. 
Classic schema mismatch between tables.

**How to narrate**: "AnalysisException on column name — let me check both schemas with 
DESCRIBE TABLE to see the actual column names... Ah, it's `customer_id` in both tables, 
the AI used `cust_id` by mistake."

---

### Bug 3: Null Handling
```sql
-- This returns unexpected results
SELECT 
    merchant_category,
    COUNT(*) as total_txns,
    SUM(CASE WHEN is_fraud = true THEN 1 ELSE 0 END) as fraud_count,
    fraud_count * 100.0 / total_txns as fraud_rate  -- ERROR: can't reference alias
FROM silver.transactions
GROUP BY merchant_category
```

**What's wrong?** 
1. Can't reference column aliases (`fraud_count`, `total_txns`) in the same SELECT level
2. Need to use the full expressions or wrap in a CTE/subquery

**Fix**:
```sql
SELECT 
    merchant_category,
    COUNT(*) as total_txns,
    SUM(CASE WHEN is_fraud = true THEN 1 ELSE 0 END) as fraud_count,
    ROUND(SUM(CASE WHEN is_fraud = true THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as fraud_rate
FROM silver.transactions
GROUP BY merchant_category
```

---

### Bug 4: Window Function Error
```sql
SELECT 
    customer_id,
    transaction_date,
    amount,
    AVG(amount) OVER (
        PARTITION BY customer_id 
        ORDER BY transaction_date 
        ROWS BETWEEN 5 PRECEDING AND CURRENT ROW  -- off by one?
    ) AS rolling_avg_5
FROM silver.transactions
```

**What's tricky?** `ROWS BETWEEN 5 PRECEDING AND CURRENT ROW` includes 6 rows (5 before + current), 
not 5. Should be `ROWS BETWEEN 4 PRECEDING AND CURRENT ROW` for a rolling average of the last 5.

**How to narrate**: "Let me double-check the window frame — 5 PRECEDING plus CURRENT ROW 
is actually 6 rows, not 5. Classic off-by-one. I need 4 PRECEDING for a 5-row window."

---

### Bug 5: Delta Write Failure
```python
# This works the first time but fails on re-run
df = spark.createDataFrame(new_data)
df.write.format("delta").saveAsTable("my_table")
```

**What's wrong?** Default mode is "error" — fails if table already exists. 
Need `.mode("overwrite")` or `.mode("append")`.

---

### Bug 6: The AI Hallucination
```python
# AI generated this code to find top 10 customers by spend
from pyspark.sql.functions import *

df = spark.table("silver.transactions")
result = df.groupBy("customer_id") \
    .agg(sum("amount").alias("total_spend")) \
    .sort("total_spend") \
    .limit(10)
result.show()
```

**What's wrong?** `.sort("total_spend")` sorts ASCENDING by default — this gives the 
BOTTOM 10, not the top 10. Need `.sort(desc("total_spend"))` or `.orderBy(col("total_spend").desc())`.

**How to narrate**: "Wait — the AI sorted ascending, which gives me the lowest spenders. 
I need descending for the top 10. This is exactly why you have to audit AI output — 
syntactically correct but logically wrong."

---

## Practice Exercise: Timed Debugging

1. Copy each broken code block into a Databricks notebook
2. Set a timer for 3 minutes per bug
3. Find the bug, explain it out loud, fix it
4. If you can't fix in 3 minutes, practice saying: "I see the issue is related to [X], 
   let me look up the correct syntax" — this is the "bail out" they mention

## Success Criteria
- [ ] Fixed all 6 bugs
- [ ] Narrated the debugging process for each
- [ ] Stayed under 3 minutes per bug
- [ ] Practiced the "bail out" phrase at least once
