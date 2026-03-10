# "Think Out Loud" Narration Scripts

> This is their #1 evaluation criterion. Practice saying these OUT LOUD.
> The pattern: WHAT I'm doing → WHY → AUDIT the result → EXPLAIN to customer

---

## Script 1: Opening — Receiving the Prompt

**Interviewer says**: "Build a pipeline that analyzes [X] data"

**You say**:
> "Great, let me start with a few clarifying questions before I dive in:
> - What's the end goal — a dashboard, an ML feature table, or a report?
> - How many records are we thinking? Thousands for demo or millions for scale?
> - Any specific data quality issues you want me to handle?
> - Are there particular columns or metrics the business cares about?
>
> OK, based on that, here's my plan: I'll generate a synthetic dataset with 
> Faker in Python, land it as a Bronze Delta table, clean and validate in Silver, 
> then build the business-level aggregations in Gold. I'll use Python for the 
> data generation and SQL for all the transformations since that's what most 
> customers and analysts work with. Let me start..."

---

## Script 2: Generating Synthetic Data

**You say while prompting AI**:
> "I'm going to prompt Claude to generate a Faker-based dataset. I need 
> [customers/transactions/whatever] with realistic distributions — real data 
> isn't uniformly random. For example, transaction amounts follow a log-normal 
> distribution, most are small with a long tail of large purchases.
>
> *[paste prompt, get result]*
>
> Let me review what it generated... OK, the schema looks right. I see it's using 
> `random.choice` for merchant category — I want to change that to `random.choices` 
> with weights because grocery stores see more transactions than travel. 
> Also, I need to seed the random generators so this is reproducible.
>
> Good — now let me convert this to a Spark DataFrame and save it as a Delta table."

---

## Script 3: Bronze Layer

**You say**:
> "This is our Bronze layer — the philosophy here is land the data as-is, no 
> transforms. It's our system of record, our safety net. If anything goes wrong 
> downstream, we can always reprocess from Bronze.
>
> I'm saving with `mode('overwrite')` for this demo, but in production this 
> would be an append with Auto Loader picking up new files incrementally.
>
> Let me verify it landed correctly... *[runs SELECT COUNT and DISPLAY]* 
> Good, 10,000 records with the expected columns."

---

## Script 4: Silver Layer (SQL Transforms)

**You say**:
> "Now Silver — this is where data quality lives. I'm going to:
> 1. Deduplicate on the primary key using ROW_NUMBER window function
> 2. Cast data types — especially DECIMAL for monetary amounts, never float
> 3. Standardize strings — UPPER and TRIM for consistency
> 4. Handle nulls with COALESCE for required fields
> 5. Filter out records with null primary keys
>
> *[writes/generates SQL]*
>
> Let me walk through this SQL: The ROW_NUMBER partitions by transaction_id and 
> orders by timestamp descending, so if we have duplicate records, we keep the 
> most recent one. The WHERE row_num = 1 filters to just those winners.
>
> For the CAST to DECIMAL(12,2) — this gives us 12 total digits with 2 decimal 
> places. Using DECIMAL instead of DOUBLE avoids floating-point precision issues 
> with money — a $19.99 charge should stay exactly $19.99, not $19.989999..."

---

## Script 5: Gold Layer (Business Aggregations)

**You say**:
> "Gold is the business-facing layer — this is what analysts and dashboards 
> query directly. I'm building a [customer 360 / daily summary / feature table].
>
> *[writes/generates SQL]*
>
> This GROUP BY customer_id creates one row per customer with all their metrics. 
> Under the hood, Spark will shuffle the data — redistributing all transactions 
> for each customer to the same executor for aggregation. That's the most expensive 
> part of this query.
>
> I'm using a LEFT JOIN from customers to transactions so we keep customers even 
> if they have zero transactions — the counts will be zero, not missing.
>
> The CASE WHEN for fraud_count is a conditional aggregation — it counts only 
> the rows where is_fraud is true, without needing a separate filtered query."

---

## Script 6: When AI Generates Bad Code

**You say**:
> "Hmm, let me review this... I see a couple issues:
> 1. It's using `float` for the amount column — for financial data I need DECIMAL 
>    to avoid precision loss
> 2. The fraud distribution is 50/50 — that's way too high, real fraud rates 
>    are around 1-2%
> 3. It didn't seed the random generator, so we can't reproduce this
>
> Let me fix these... *[makes corrections]* 
>
> This is actually a common AI hallucination pattern — it generates syntactically 
> correct code but misses domain-specific requirements like realistic distributions."

---

## Script 7: When You Hit a Bug

**You say**:
> "OK, I got an error — let me read it... `AnalysisException: cannot resolve 
> 'customer_id'` — that usually means either a typo in the column name or 
> I'm referencing a column that doesn't exist in this table. Let me check 
> the schema... *[runs DESCRIBE TABLE]*
>
> Ah, it's called `cust_id` not `customer_id`. The AI used a different naming 
> convention than what Faker generated. Easy fix...
>
> In the real world as an SA, this is exactly the kind of thing I help customers 
> debug — schema mismatches between pipeline stages are one of the most common 
> issues I see."

---

## Script 8: Discussing Scale

**Interviewer asks**: "How would this work with 100 million rows?"

**You say**:
> "A few things would change at scale:
> 
> First, the data generation — I wouldn't use a single Python loop. I'd use 
> `spark.range(100000000)` to create a distributed DataFrame and then use 
> PySpark UDFs or pandas_udf to generate the fake data in parallel across 
> the cluster.
>
> For the pipeline, I'd add Liquid Clustering on the columns I filter by most — 
> probably customer_id and transaction_date. This co-locates related data 
> physically so queries can skip entire file groups.
>
> For the Gold aggregations, I'd move to incremental processing — instead of 
> recomputing the full GROUP BY every time, I'd use Delta's Change Data Feed 
> to only process new or changed records.
>
> And I'd definitely check the Spark UI to verify join strategies — for the 
> customer-transaction join, if customers is still small, Spark should broadcast 
> it. But I'd verify with EXPLAIN to make sure."

---

## Script 9: Wrapping Up — Walking Through Databricks UI

**You say**:
> "Let me walk you through what we built in the Databricks UI:
>
> Here's the notebook with our pipeline — you can see the logical flow from 
> data generation through Bronze, Silver, and Gold.
>
> In the Data Explorer, here are our three Delta tables. You can see the 
> schema, sample data, and the history of operations.
>
> If I click on the table history, you can see each version — this is Delta's 
> transaction log in action. If we needed to roll back, we could query any 
> previous version.
>
> From here, the next steps would be: connect a BI tool like Power BI to the 
> Gold tables, set up a scheduled job to run this pipeline daily, or build 
> an ML model on the feature table we created."

---

## Emergency Phrases (When Stuck)

| Situation | What to Say |
|-----------|-------------|
| Syntax error you can't fix | "I know the logic I need but I'm fighting the API — mind if I look this up?" |
| Blank on approach | "Let me think about this from first principles — the business needs [X], so I need to [Y]..." |
| AI gives nonsense | "The AI's output doesn't look right — let me describe what I actually need and regenerate" |
| Running out of time | "I want to be respectful of time — let me describe the remaining steps and show you what I'd build" |
| Don't know answer | "I'm not sure about the exact behavior there — in the field, I'd test it and check the docs" |
