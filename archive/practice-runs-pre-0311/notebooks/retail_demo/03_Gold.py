# Databricks notebook source
# MAGIC %md
# MAGIC # 03 - Gold Aggregates (Idempotent Window Rebuild)
# MAGIC **Delete-window + insert-window** — same correctness, 100x less I/O than full rewrite.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TALK: Gold idempotent rebuild — delete 14-day window, then re-insert
# MAGIC -- SCALING: At 1B rows, delete-window touches <1% of data vs full rewrite
# MAGIC -- DW-BRIDGE: In Netezza we'd TRUNCATE + reload. This is scoped to changed data only.
# MAGIC
# MAGIC DELETE FROM retail_demo.gold.daily_revenue
# MAGIC WHERE order_date >= date_sub(current_date(), 14);
# MAGIC
# MAGIC INSERT INTO retail_demo.gold.daily_revenue
# MAGIC SELECT
# MAGIC   CAST(order_ts AS DATE) AS order_date,
# MAGIC   store_id,
# MAGIC   loyalty_tier,
# MAGIC   COUNT(*) AS order_count,
# MAGIC   CAST(SUM(total_amount) AS DECIMAL(38,2)) AS total_revenue,
# MAGIC   CAST(AVG(total_amount) AS DECIMAL(18,2)) AS avg_basket,
# MAGIC   CAST(SUM(quantity) AS BIGINT) AS total_units
# MAGIC FROM retail_demo.silver.orders_current
# MAGIC WHERE CAST(order_ts AS DATE) >= date_sub(current_date(), 14)
# MAGIC GROUP BY CAST(order_ts AS DATE), store_id, loyalty_tier;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Post-DDL: clustering + stats
# MAGIC ALTER TABLE retail_demo.gold.daily_revenue CLUSTER BY (store_id, order_date);
# MAGIC OPTIMIZE retail_demo.gold.daily_revenue;
# MAGIC ANALYZE TABLE retail_demo.gold.daily_revenue COMPUTE STATISTICS FOR ALL COLUMNS;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TALK: Idempotency proof — run the rebuild again, count should be identical
# MAGIC SELECT count(*) AS gold_rows FROM retail_demo.gold.daily_revenue
