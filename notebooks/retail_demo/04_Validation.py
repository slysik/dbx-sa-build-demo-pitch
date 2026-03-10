# Databricks notebook source
# MAGIC %md
# MAGIC # 04 - Validation Harness + Proof Points
# MAGIC **4 validation checks + 4 proof points** — the "ETL reconciliation" equivalent.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TALK: Row count comparison across layers — Bronze >= Silver is expected
# MAGIC SELECT 'Bronze' AS layer, count(*) AS row_count FROM retail_demo.bronze.order_events
# MAGIC UNION ALL
# MAGIC SELECT 'Silver', count(*) FROM retail_demo.silver.orders_current
# MAGIC UNION ALL
# MAGIC SELECT 'Gold', count(*) FROM retail_demo.gold.daily_revenue

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Uniqueness check on business key (should return 0 rows)
# MAGIC SELECT order_id, count(*) AS cnt
# MAGIC FROM retail_demo.silver.orders_current
# MAGIC GROUP BY order_id HAVING count(*) > 1

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Rule violation counts (all should be 0)
# MAGIC SELECT 'Negative Amount' AS check_name, COUNT(CASE WHEN total_amount < 0 THEN 1 END) AS violations
# MAGIC FROM retail_demo.silver.orders_current
# MAGIC UNION ALL
# MAGIC SELECT 'Negative Unit Price', COUNT(CASE WHEN unit_price < 0 THEN 1 END)
# MAGIC FROM retail_demo.silver.orders_current
# MAGIC UNION ALL
# MAGIC SELECT 'Invalid Status', COUNT(CASE WHEN status NOT IN ('COMPLETED','PENDING','RETURNED') THEN 1 END)
# MAGIC FROM retail_demo.silver.orders_current

# COMMAND ----------

# MAGIC %md
# MAGIC ## Proof Points

# COMMAND ----------

# MAGIC %sql
# MAGIC -- PROOF 1: CHECK constraint enforcement — this INSERT should FAIL
# MAGIC -- TALK: "Delta enforces constraints at write time — no bad data gets through."
# MAGIC INSERT INTO retail_demo.silver.orders_current VALUES
# MAGIC   ('BAD-001', 'C000001', 'S0001', 'P00001', current_timestamp(), current_date(), 1, 10.00, -100.00, 'USD', 'COMPLETED', 'Gold', current_timestamp(), 'test')

# COMMAND ----------

# MAGIC %sql
# MAGIC -- PROOF 2: Pruning proof — EXPLAIN should show files pruned
# MAGIC -- TALK: "My CLUSTER BY keys match my WHERE clause — data skipping in action."
# MAGIC EXPLAIN SELECT * FROM retail_demo.silver.orders_current
# MAGIC WHERE customer_id = 'C000123' AND event_date >= '2026-02-20'

# COMMAND ----------

# MAGIC %sql
# MAGIC -- PROOF 3: Time travel — full audit trail built into Delta
# MAGIC -- TALK: "No extra infrastructure needed. Every operation is versioned."
# MAGIC DESCRIBE HISTORY retail_demo.silver.orders_current

# COMMAND ----------

# MAGIC %sql
# MAGIC -- PROOF 4: Version 0 vs current — show the table evolution
# MAGIC SELECT * FROM retail_demo.silver.orders_current VERSION AS OF 0 LIMIT 5
