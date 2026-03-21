# Test Prompts: synthetic-data-generation

Fixed validation data. Do not modify.

---

## Prompt 1: Scalable Bronze fact table

Generate 100,000 retail transaction rows using the most scalable Databricks-native approach. Include a broadcast join to a 200-row products dimension. Show how to scale to 1M by changing ONE parameter.

**EXPECT:** spark.range, N_TRANSACTIONS, broadcast, withColumn, saveAsTable, delta, not Faker

---

## Prompt 2: Bronze metadata columns

I'm generating synthetic Bronze data for a banking demo. What three metadata columns should every Bronze table have, and why?

**EXPECT:** ingest_ts, source_system, batch_id, current_timestamp, audit, lineage

---

## Prompt 3: Dimension table design constraints

How many columns should a dimension table have for interview demos, and why? Show an example dim_customers with the right column count.

**EXPECT:** 6 or fewer, broadcastable, spark.range, segment, region, customer_id, lean

---

## Prompt 4: Non-uniform category distribution

Generate a fact table where 60% of rows have `category = "grocery"`, 25% are `"dining"`, and 15% are `"travel"`. Use Spark-native column expressions — no Python loops, no Faker.

**EXPECT:** F.when, F.rand, seed, withColumn, spark.range, not Faker, not for loop

---

## Prompt 5: Direct Delta write pattern

Write Bronze data for 10,000 transactions directly to Delta in Unity Catalog `finserv.banking.bronze_fact_transactions`. Show the complete write statement with all required options.

**EXPECT:** write.format("delta"), mode("overwrite"), saveAsTable, finserv.banking.bronze_fact_transactions, not parquet, not CSV
