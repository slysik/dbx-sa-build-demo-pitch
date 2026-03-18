# Databricks notebook source

# MAGIC %md
# MAGIC # 🛍️ Retail Bronze Data Generation
# MAGIC
# MAGIC | Table | Type | Rows | Key |
# MAGIC |-------|------|------|-----|
# MAGIC | `bronze_customers` | Dimension | 5,000 | customer_id |
# MAGIC | `bronze_products` | Dimension | 500 | product_id |
# MAGIC | `bronze_orders` | Fact | 100K → 1M | order_id |
# MAGIC | `bronze_order_items` | Detail | ~300K → 3M | item_id |
# MAGIC
# MAGIC **Pattern:** `spark.range(N)` → native PySpark cols → broadcast join dims → Bronze Delta
# MAGIC
# MAGIC **Scale:** Change `N_ORDERS` only. Zero code changes at any volume.

# COMMAND ----------

# SA: All row generation uses spark.range() — distributed across executors from the start.
#     No Faker, no Pandas, no Python loops. This scales from 100 to 10M by changing one param.
#     Compare to Netezza: like nzload parallelizing inserts across SPUs — same concept, Spark execution.

from pyspark.sql import functions as F

CATALOG    = "interview"
SCHEMA     = "retail"
BATCH_ID   = "batch_001"

N_CUSTOMERS = 5_000       # Dim — small, broadcastable
N_PRODUCTS  = 500         # Dim — small, broadcastable
N_ORDERS    = 100_000     # Fact — change to 1_000_000 to scale. Zero code changes.

START_DATE = "2025-09-12"
DAYS_SPAN  = 180          # 6 months of order history

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"Target: {CATALOG}.{SCHEMA} | Orders: {N_ORDERS:,} | Batch: {BATCH_ID}")

# COMMAND ----------

# SA: Customers dimension — 6 columns max. Lean dims are fast to broadcast, easy to walk through.
#     Weighted distributions via rand() give realistic skew — not uniform, not random noise.
#     2% null emails injected intentionally — Silver will COALESCE these. Shows quality enforcement.
#     Modulo + hash for deterministic output — same seed = same data every run.

customers = (
    spark.range(N_CUSTOMERS)
    .withColumn("customer_id",
        F.format_string("CUST-%06d", F.col("id") + 1))

    .withColumn("first_name",
        F.concat(F.lit("First"), (F.abs(F.hash(F.col("id"), F.lit("fn"))) % 9999).cast("string")))

    # SA: Region — weighted: West 30%, South 28%, Midwest 22%, NE 20%. Realistic US distribution.
    .withColumn("_r", F.abs(F.hash(F.col("id"), F.lit("region"))) % 100)
    .withColumn("region",
        F.when(F.col("_r") < 30, "West")
         .when(F.col("_r") < 58, "South")
         .when(F.col("_r") < 80, "Midwest")
         .otherwise("Northeast"))

    # SA: Loyalty tier — Standard 70%, Premium 22%, VIP 8%. Power-law distribution.
    .withColumn("_t", F.abs(F.hash(F.col("id"), F.lit("tier"))) % 100)
    .withColumn("loyalty_tier",
        F.when(F.col("_t") < 70, "Standard")
         .when(F.col("_t") < 92, "Premium")
         .otherwise("VIP"))

    .withColumn("signup_date",
        F.date_sub(F.current_date(), (F.abs(F.hash(F.col("id"), F.lit("signup"))) % 1000 + 180).cast("int")))

    # SA: Intentional imperfection — 2% null emails. Bronze captures source as-is.
    #     Silver applies COALESCE('unknown@missing.com'). This demonstrates quality gates.
    .withColumn("email",
        F.when(F.abs(F.hash(F.col("id"), F.lit("null_email"))) % 100 >= 2,
               F.concat(F.lower(F.col("first_name")), F.lit("@example.com"))))

    .drop("id", "_r", "_t")
)

display(customers.limit(5))

# COMMAND ----------

# SA: Products dimension — 5 columns. Category-aware pricing via WHEN/OTHERWISE.
#     Electronics: $50-$2500, Grocery: $2-$30. Mirrors real retail price bands.
#     cost_price derived from unit_price with variable margin — enables Gold margin analysis.
#     500 products × 6 categories = realistic cardinality for chart readability.

products = (
    spark.range(N_PRODUCTS)
    .withColumn("product_id",
        F.format_string("PROD-%05d", F.col("id") + 1))

    # SA: 6 categories — low cardinality for dashboard pie/bar charts (3-8 ideal).
    .withColumn("_c", F.abs(F.hash(F.col("id"), F.lit("cat"))) % 100)
    .withColumn("category",
        F.when(F.col("_c") < 25, "Electronics")
         .when(F.col("_c") < 45, "Apparel")
         .when(F.col("_c") < 63, "Home & Garden")
         .when(F.col("_c") < 75, "Sports")
         .when(F.col("_c") < 85, "Beauty")
         .otherwise("Grocery"))

    .withColumn("product_name",
        F.concat(F.col("category"), F.lit(" Item "), F.col("product_id")))

    # SA: Category-aware pricing — Electronics premium, Grocery low. Not uniform random.
    .withColumn("_p", (F.abs(F.hash(F.col("id"), F.lit("price"))) % 10000) / 10000.0)
    .withColumn("unit_price", F.round(
        F.when(F.col("category") == "Electronics", F.lit(49.99) + F.col("_p") * 2450.0)
         .when(F.col("category") == "Grocery",     F.lit(1.99) + F.col("_p") * 28.0)
         .when(F.col("category") == "Beauty",      F.lit(9.99) + F.col("_p") * 140.0)
         .otherwise(F.lit(14.99) + F.col("_p") * 285.0), 2))

    # SA: Cost price = 30-65% of unit price. Variable margin enables Gold profitability analysis.
    .withColumn("cost_price",
        F.round(F.col("unit_price") * (F.lit(0.30) + F.col("_p") * 0.35), 2))

    .drop("id", "_c", "_p")
)

display(products.limit(5))

# COMMAND ----------

# SA: Orders fact — the core transaction table. FK to customers via modulo on N_CUSTOMERS.
#     Modulo guarantees referential integrity without maintaining lookup maps or post-hoc validation.
#     date_sub + rand spreads orders across 180 days. make_interval adds realistic hour/minute.
#     Channel weighted: web 45%, mobile 35%, in-store 20%. Matches typical omnichannel retailer.
#     1% duplicates injected via .sample().unionByName() — Silver dedup via ROW_NUMBER proves quality.

orders = (
    spark.range(N_ORDERS)
    .withColumn("order_id",
        F.format_string("ORD-%07d", F.col("id") + 1))

    # SA: FK to customers — modulo guarantees valid references at any scale.
    .withColumn("customer_id",
        F.format_string("CUST-%06d",
            (F.abs(F.hash(F.col("id"), F.lit("cust"))) % N_CUSTOMERS).cast("int") + 1))

    # SA: Realistic timestamps — date spread + hour/minute. Not just dates.
    .withColumn("order_timestamp",
        F.date_sub(F.current_date(), (F.abs(F.hash(F.col("id"), F.lit("day"))) % DAYS_SPAN).cast("int"))
         .cast("timestamp")
         + F.make_interval(
             F.lit(0), F.lit(0), F.lit(0), F.lit(0),
             (F.abs(F.hash(F.col("id"), F.lit("hr"))) % 18 + 6).cast("int"),   # 6am-midnight
             (F.abs(F.hash(F.col("id"), F.lit("mn"))) % 60).cast("int"),
             F.lit(0)))

    # SA: Channel — weighted distribution. In-store gets store_id, others get NULL.
    .withColumn("_ch", F.abs(F.hash(F.col("id"), F.lit("ch"))) % 100)
    .withColumn("channel",
        F.when(F.col("_ch") < 45, "web")
         .when(F.col("_ch") < 80, "mobile")
         .otherwise("in-store"))

    # SA: Payment method — credit dominates, cash only for in-store (realistic constraint).
    .withColumn("_pay", F.abs(F.hash(F.col("id"), F.lit("pay"))) % 100)
    .withColumn("payment_method",
        F.when(F.col("_pay") < 40, "credit_card")
         .when(F.col("_pay") < 65, "debit_card")
         .when(F.col("_pay") < 90, "digital_wallet")
         .otherwise(F.when(F.col("channel") == "in-store", "cash").otherwise("digital_wallet")))

    # SA: Order status — 65% completed. 3% cancelled + 7% returned = 10% loss rate.
    .withColumn("_st", F.abs(F.hash(F.col("id"), F.lit("st"))) % 100)
    .withColumn("status",
        F.when(F.col("_st") < 65, "completed")
         .when(F.col("_st") < 80, "shipped")
         .when(F.col("_st") < 90, "processing")
         .when(F.col("_st") < 97, "returned")
         .otherwise("cancelled"))

    .drop("id", "_ch", "_pay", "_st")
)

# SA: Intentional 1% duplicates — simulates upstream system double-sends.
#     Silver dedup via ROW_NUMBER() OVER (PARTITION BY order_id) removes these.
dupes = orders.sample(fraction=0.01, seed=42)
orders = orders.unionByName(dupes)

display(orders.limit(5))

# COMMAND ----------

# SA: Order items — detail table generated FROM orders. FK integrity by construction.
#     explode(sequence(1, n_items)) creates 1-5 line items per order — no Python loop.
#     Broadcast join to products pulls unit_price for line_total calculation.
#     1% outlier line_totals (50x multiplier) injected — Silver expectation drops these.
#     This pattern scales linearly: 100K orders → ~300K items, 1M → ~3M items.

order_items = (
    orders.select("order_id")
    # SA: 1-5 items per order. explode + sequence = distributed row multiplication.
    .withColumn("n_items",
        (F.abs(F.hash(F.col("order_id"))) % 5 + 1).cast("int"))
    .select("order_id",
        F.explode(F.sequence(F.lit(1), F.col("n_items"))).alias("line_num"))
    .withColumn("item_id",
        F.concat(F.col("order_id"), F.lit("-"), F.col("line_num")))

    # SA: FK to products via modulo — guaranteed valid product_id at any scale.
    .withColumn("product_id",
        F.format_string("PROD-%05d",
            (F.abs(F.hash(F.col("item_id"), F.lit("prod"))) % N_PRODUCTS).cast("int") + 1))

    .withColumn("quantity",
        (F.abs(F.hash(F.col("item_id"), F.lit("qty"))) % 4 + 1).cast("int"))

    # SA: Discount distribution — 60% none, tiered up to 20%. Realistic promo pattern.
    .withColumn("_d", F.abs(F.hash(F.col("item_id"), F.lit("disc"))) % 100)
    .withColumn("discount_pct",
        F.when(F.col("_d") < 60, 0.0)
         .when(F.col("_d") < 75, 0.05)
         .when(F.col("_d") < 87, 0.10)
         .when(F.col("_d") < 95, 0.15)
         .otherwise(0.20))
    .drop("line_num", "n_items", "_d")
)

# SA: Broadcast join — products dim is 500 rows (~10KB). Sent to every executor, zero shuffle.
#     This is the canonical pattern: small dim broadcast into large fact. No skew, no spill.
order_items = (
    order_items
    .join(F.broadcast(products.select("product_id", "unit_price")), "product_id", "left")
    .withColumn("line_total",
        F.round(F.col("unit_price") * F.col("quantity") * (1 - F.col("discount_pct")), 2))
    # SA: 1% outlier line_totals — simulates data quality issues from upstream.
    #     Silver expectation (line_total > 0 AND line_total < 50000) drops these rows.
    .withColumn("line_total",
        F.when(F.abs(F.hash(F.col("item_id"), F.lit("outlier"))) % 100 == 0,
               F.col("line_total") * 50)
         .when(F.abs(F.hash(F.col("item_id"), F.lit("outlier"))) % 100 == 1,
               F.lit(-99.99))
         .otherwise(F.col("line_total")))
)

display(order_items.limit(5))

# COMMAND ----------

# SA: Write all 4 tables to managed Delta in Unity Catalog — direct, no intermediate parquet/Volume.
#     Every table gets 3 governance columns: ingest_ts, source_system, batch_id.
#     batch_id groups all tables from the same run — enables full-load traceability and rollback.
#     Liquid Clustering applied post-write — keys match downstream Silver/Gold access patterns.
#     repartition(8) on fact tables sizes files for optimal downstream read performance.
#     This is Bronze: source-shaped, append-only, NO business logic. Silver handles everything.

TABLES = {
    "bronze_customers":   (customers,   "customer_id",    None),
    "bronze_products":    (products,    "product_id",     None),
    "bronze_orders":      (orders,      "order_timestamp", 8),
    "bronze_order_items": (order_items, "order_id",        8),
}

for name, (df, cluster_col, repart) in TABLES.items():
    fqn = f"{CATALOG}.{SCHEMA}.{name}"

    # SA: Bronze metadata — consistent across all tables. ingest_ts = when this batch landed.
    bronze = (
        df
        .withColumn("ingest_ts", F.current_timestamp())
        .withColumn("source_system", F.lit("synthetic_generator"))
        .withColumn("batch_id", F.lit(BATCH_ID))
    )

    writer = bronze
    if repart:
        # SA: repartition(8) on fact tables — targets ~128MB files for downstream reads.
        #     Dims are small enough that default partitioning is fine.
        writer = bronze.repartition(repart)

    (writer.write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(fqn))

    # SA: Liquid Clustering post-write — keys match query patterns in Silver/Gold.
    #     Unlike PARTITION BY, LC handles multi-column skipping via Hilbert curves,
    #     auto-compacts small files, and keys are MUTABLE with ALTER TABLE.
    spark.sql(f"ALTER TABLE {fqn} CLUSTER BY ({cluster_col})")

    cnt = spark.table(fqn).count()
    print(f"  ✓ {fqn}: {cnt:,} rows | LC({cluster_col})")

print(f"\n  Batch: {BATCH_ID}")

# COMMAND ----------

# SA: Single validation pass — one loop for counts, one distribution check.
#     No repeated count() after each step. Validate once at the end.
#     Distribution checks prove weighted distributions are working as designed.

print("=" * 60)
print("BRONZE VALIDATION")
print("=" * 60)

# Row counts
print("\n--- Row Counts ---")
for tbl in TABLES:
    cnt = spark.table(f"{CATALOG}.{SCHEMA}.{tbl}").count()
    print(f"  {tbl}: {cnt:,}")

# Distribution checks — prove weighted distributions work
print("\n--- Channel Distribution (expect: web ~45%, mobile ~35%, in-store ~20%) ---")
spark.table(f"{CATALOG}.{SCHEMA}.bronze_orders").groupBy("channel").count().orderBy(F.desc("count")).show()

print("--- Region Distribution (expect: West ~30%, South ~28%, Midwest ~22%, NE ~20%) ---")
spark.table(f"{CATALOG}.{SCHEMA}.bronze_customers").groupBy("region").count().orderBy(F.desc("count")).show()

print("--- Loyalty Tier (expect: Standard ~70%, Premium ~22%, VIP ~8%) ---")
spark.table(f"{CATALOG}.{SCHEMA}.bronze_customers").groupBy("loyalty_tier").count().orderBy(F.desc("count")).show()

# Imperfections audit — these are INTENTIONAL for Silver to clean
print("--- Intentional Imperfections (Bronze captures as-is, Silver cleans) ---")
null_emails = spark.table(f"{CATALOG}.{SCHEMA}.bronze_customers").filter(F.col("email").isNull()).count()
dupe_orders = spark.table(f"{CATALOG}.{SCHEMA}.bronze_orders").groupBy("order_id").count().filter("count > 1").count()
bad_totals  = spark.table(f"{CATALOG}.{SCHEMA}.bronze_order_items").filter(
    (F.col("line_total") < 0) | (F.col("line_total") > 50000)).count()
print(f"  Null emails:          {null_emails} (~2% of {N_CUSTOMERS:,})")
print(f"  Duplicate order_ids:  {dupe_orders} (~1% of {N_ORDERS:,})")
print(f"  Outlier line_totals:  {bad_totals} (~2% of items)")

print(f"\n✅ Bronze complete. SDP pipeline starts at Silver.")
