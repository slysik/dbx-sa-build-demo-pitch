# Databricks notebook source
# MAGIC %md
# MAGIC # 02 - Bronze DDL + Silver MERGE
# MAGIC **CHECK constraints, Liquid Clustering, deterministic MERGE with ROW_NUMBER**

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TALK: Bronze table with CHECK constraints — Delta enforces at write time
# MAGIC -- SCALING: Liquid Clustering replaces distribution keys — adaptive, no schema lock-in
# MAGIC -- DW-BRIDGE: In Netezza, we'd pick distribution keys upfront and be locked in
# MAGIC
# MAGIC ALTER TABLE retail_demo.bronze.order_events
# MAGIC   ADD CONSTRAINT chk_amount_nonneg CHECK (total_amount IS NULL OR total_amount >= 0);
# MAGIC
# MAGIC ALTER TABLE retail_demo.bronze.order_events
# MAGIC   ADD CONSTRAINT chk_unit_price_nonneg CHECK (unit_price IS NULL OR unit_price >= 0);
# MAGIC
# MAGIC ALTER TABLE retail_demo.bronze.order_events CLUSTER BY (customer_id, event_date);
# MAGIC
# MAGIC OPTIMIZE retail_demo.bronze.order_events;
# MAGIC ANALYZE TABLE retail_demo.bronze.order_events COMPUTE STATISTICS FOR ALL COLUMNS;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- TALK: Silver MERGE — dedup on order_id, keep latest record per business key
# MAGIC -- SCALING: ROW_NUMBER triggers a shuffle (PARTITION BY). CLUSTER BY pre-sorts for merge-join.
# MAGIC -- DW-BRIDGE: In Netezza, distribution key on the join column gives same locality.
# MAGIC
# MAGIC MERGE INTO retail_demo.silver.orders_current t
# MAGIC USING (
# MAGIC   SELECT * FROM (
# MAGIC     SELECT
# MAGIC       order_id, customer_id, store_id, product_id,
# MAGIC       order_ts, event_date, quantity, unit_price, total_amount,
# MAGIC       currency, status, loyalty_tier, ingest_ts, source_system,
# MAGIC       ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY ingest_ts DESC) AS rn
# MAGIC     FROM retail_demo.bronze.order_events
# MAGIC   ) WHERE rn = 1
# MAGIC ) s ON t.order_id = s.order_id
# MAGIC WHEN MATCHED THEN UPDATE SET
# MAGIC   customer_id = s.customer_id, store_id = s.store_id, product_id = s.product_id,
# MAGIC   order_ts = s.order_ts, event_date = s.event_date, quantity = s.quantity,
# MAGIC   unit_price = s.unit_price, total_amount = s.total_amount, currency = s.currency,
# MAGIC   status = s.status, loyalty_tier = s.loyalty_tier,
# MAGIC   last_updated = s.ingest_ts, source_system = s.source_system
# MAGIC WHEN NOT MATCHED THEN INSERT (
# MAGIC   order_id, customer_id, store_id, product_id,
# MAGIC   order_ts, event_date, quantity, unit_price, total_amount,
# MAGIC   currency, status, loyalty_tier, last_updated, source_system
# MAGIC ) VALUES (
# MAGIC   s.order_id, s.customer_id, s.store_id, s.product_id,
# MAGIC   s.order_ts, s.event_date, s.quantity, s.unit_price, s.total_amount,
# MAGIC   s.currency, s.status, s.loyalty_tier, s.ingest_ts, s.source_system
# MAGIC );

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Silver post-DDL: constraints + clustering + stats
# MAGIC ALTER TABLE retail_demo.silver.orders_current
# MAGIC   ADD CONSTRAINT chk_silver_amount CHECK (total_amount IS NULL OR total_amount >= 0);
# MAGIC ALTER TABLE retail_demo.silver.orders_current
# MAGIC   ADD CONSTRAINT chk_silver_status CHECK (status IN ('COMPLETED', 'PENDING', 'RETURNED'));
# MAGIC ALTER TABLE retail_demo.silver.orders_current CLUSTER BY (customer_id, event_date);
# MAGIC OPTIMIZE retail_demo.silver.orders_current;
# MAGIC ANALYZE TABLE retail_demo.silver.orders_current COMPUTE STATISTICS FOR ALL COLUMNS;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Gate check: 0 duplicates expected
# MAGIC SELECT order_id, count(*) AS cnt
# MAGIC FROM retail_demo.silver.orders_current
# MAGIC GROUP BY order_id HAVING count(*) > 1
