"""Generate 1M-row synthetic retail dataset — pure PySpark, no scaling step.

Architecture (v2):
  1. Generate synthetic/source-shaped DataFrames in notebook
  2. Persist directly to managed Bronze Delta tables in catalog.schema.bronze_*
  3. SDP Silver reads from Bronze Delta tables
  4. SDP Gold reads from Silver

Benefits:
  - Removes unnecessary intermediate landing step (no Volumes/parquet staging)
  - Produces Delta-governed Bronze tables immediately (ACID, time travel, lineage)
  - Reduces pipeline complexity and improves developer velocity

Architectural tradeoff:
  - We are intentionally replacing file-based Bronze ingestion with table-based
    Bronze persistence. This is appropriate for synthetic/demo data generated
    inside Spark. If raw file arrival, replay-from-files, or Auto Loader
    semantics are required, file-based ingestion (v1) may still be justified.

Bronze governance columns:
  _ingest_ts, _batch_id, _source_system, _source_type, _generator_version, _run_id

Usage: Run on cluster via notebook or scripts/run_on_cluster.py
"""
import uuid
import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark.sql import DataFrame, SparkSession

spark = SparkSession.builder.getOrCreate()

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════
CATALOG = "interview"
SCHEMA = "retail"
N_ORDERS = 1_000_000
N_CUSTOMERS = 5_000
N_PRODUCTS = 500

# Bronze governance metadata — consistent across all tables in this run
GENERATOR_VERSION = "retail_synth_v2.0"
SOURCE_SYSTEM = "interview_data_generator"
SOURCE_TYPE = "synthetic"
RUN_ID = str(uuid.uuid4())        # unique per execution
BATCH_ID = str(uuid.uuid4())[:8]  # short batch identifier


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════
def add_bronze_metadata(df: DataFrame) -> DataFrame:
    """Append governance columns to every Bronze table.

    TALK: "Every Bronze table carries the same six metadata columns.
      _ingest_ts marks when this batch landed. _batch_id groups all
      tables written in the same run — so I can trace or roll back a
      full load. _source_system and _source_type make lineage explicit
      in Unity Catalog. _generator_version pins the code version so
      downstream consumers know exactly what produced this data.
      _run_id is the unique execution ID for audit."
    """
    return (
        df
        .withColumn("_ingest_ts",          F.current_timestamp())
        .withColumn("_batch_id",           F.lit(BATCH_ID))
        .withColumn("_source_system",      F.lit(SOURCE_SYSTEM))
        .withColumn("_source_type",        F.lit(SOURCE_TYPE))
        .withColumn("_generator_version",  F.lit(GENERATOR_VERSION))
        .withColumn("_run_id",             F.lit(RUN_ID))
    )


# ═══════════════════════════════════════════════════════════════════
# 0. CATALOG / SCHEMA SETUP
# ═══════════════════════════════════════════════════════════════════
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"Target: {CATALOG}.{SCHEMA}")
print(f"Run ID: {RUN_ID}")
print(f"Batch:  {BATCH_ID}")


# ═══════════════════════════════════════════════════════════════════
# 1. CUSTOMERS DIMENSION (5K rows)
# ═══════════════════════════════════════════════════════════════════
print("\n1/6 Generating customers...")

customers_df: DataFrame = (
    spark.range(N_CUSTOMERS)
    .withColumn("customer_id", F.format_string("CUST-%06d", F.col("id") + 1))
    .withColumn("first_name", F.concat(F.lit("First"), (F.abs(F.hash(F.col("id"), F.lit("fn"))) % 9999).cast("string")))
    .withColumn("last_name", F.concat(F.lit("Last"), (F.abs(F.hash(F.col("id"), F.lit("ln"))) % 9999).cast("string")))
    .withColumn("email", F.concat(F.lower(F.col("first_name")), F.lit("."), F.lower(F.col("last_name")), F.lit("@example.com")))
    # Region: West 30%, South 28%, Midwest 22%, Northeast 20%
    .withColumn("_r", F.abs(F.hash(F.col("id"), F.lit("region"))) % 100)
    .withColumn("region",
        F.when(F.col("_r") < 30, "West")
         .when(F.col("_r") < 58, "South")
         .when(F.col("_r") < 80, "Midwest")
         .otherwise("Northeast"))
    # Tier: Standard 70%, Premium 22%, VIP 8%
    .withColumn("_t", F.abs(F.hash(F.col("id"), F.lit("tier"))) % 100)
    .withColumn("loyalty_tier",
        F.when(F.col("_t") < 70, "Standard")
         .when(F.col("_t") < 92, "Premium")
         .otherwise("VIP"))
    .withColumn("signup_date", F.date_sub(F.current_date(), (F.abs(F.hash(F.col("id"), F.lit("signup"))) % 1000 + 180).cast("int")))
    # Imperfection: 2% null emails
    .withColumn("email", F.when(F.abs(F.hash(F.col("id"), F.lit("null_email"))) % 100 < 2, F.lit(None)).otherwise(F.col("email")))
    .drop("id", "_r", "_t")
)
customers_df.cache()
print(f"  ✓ customers: {customers_df.count():,}")


# ═══════════════════════════════════════════════════════════════════
# 2. PRODUCTS DIMENSION (500 rows)
# ═══════════════════════════════════════════════════════════════════
print("2/6 Generating products...")

products_df: DataFrame = (
    spark.range(N_PRODUCTS)
    .withColumn("product_id", F.format_string("PROD-%05d", F.col("id") + 1))
    .withColumn("_c", F.abs(F.hash(F.col("id"), F.lit("cat"))) % 100)
    .withColumn("category",
        F.when(F.col("_c") < 25, "Electronics")
         .when(F.col("_c") < 45, "Apparel")
         .when(F.col("_c") < 63, "Home & Garden")
         .when(F.col("_c") < 75, "Sports")
         .when(F.col("_c") < 85, "Beauty")
         .otherwise("Grocery"))
    .withColumn("product_name", F.concat(F.col("category"), F.lit(" Item "), F.col("product_id")))
    .withColumn("_p", (F.abs(F.hash(F.col("id"), F.lit("price"))) % 10000) / 10000.0)
    .withColumn("unit_price", F.round(
        F.when(F.col("category") == "Electronics", F.lit(49.99) + F.col("_p") * 2450.0)
         .when(F.col("category") == "Grocery", F.lit(1.99) + F.col("_p") * 28.0)
         .when(F.col("category") == "Beauty", F.lit(9.99) + F.col("_p") * 140.0)
         .otherwise(F.lit(14.99) + F.col("_p") * 285.0)
    , 2))
    .withColumn("cost_price", F.round(F.col("unit_price") * (F.lit(0.30) + F.col("_p") * 0.35), 2))
    .drop("id", "_c", "_p")
)
products_df.cache()
print(f"  ✓ products: {products_df.count():,}")


# ═══════════════════════════════════════════════════════════════════
# 3. ORDERS FACT (1M rows — generated directly, no scaling)
# ═══════════════════════════════════════════════════════════════════
print(f"3/6 Generating {N_ORDERS:,} orders...")

orders_df: DataFrame = (
    spark.range(N_ORDERS)
    .withColumn("order_id", F.format_string("ORD-%07d", F.col("id") + 1))
    .withColumn("_ci", (F.sqrt((F.abs(F.hash(F.col("id"), F.lit("cust"))) % 10000) / 10000.0) * N_CUSTOMERS).cast("int"))
    .withColumn("customer_id", F.format_string("CUST-%06d", F.least(F.col("_ci"), F.lit(N_CUSTOMERS - 1)) + 1))
    .withColumn("_day", (F.abs(F.hash(F.col("id"), F.lit("day"))) % 180).cast("int"))
    .withColumn("_hr", (F.abs(F.hash(F.col("id"), F.lit("hr"))) % 18 + 6).cast("int"))
    .withColumn("_mn", (F.abs(F.hash(F.col("id"), F.lit("mn"))) % 60).cast("int"))
    .withColumn("order_timestamp",
        (F.date_sub(F.current_date(), F.col("_day")).cast("timestamp")
         + F.make_interval(F.lit(0), F.lit(0), F.lit(0), F.lit(0), F.col("_hr"), F.col("_mn"), F.lit(0))))
    .withColumn("_ch", F.abs(F.hash(F.col("id"), F.lit("ch"))) % 100)
    .withColumn("channel",
        F.when(F.col("_ch") < 45, "web")
         .when(F.col("_ch") < 80, "mobile")
         .otherwise("in-store"))
    .withColumn("_pay", F.abs(F.hash(F.col("id"), F.lit("pay"))) % 100)
    .withColumn("payment_method",
        F.when(F.col("_pay") < 40, "credit_card")
         .when(F.col("_pay") < 65, "debit_card")
         .when(F.col("_pay") < 90, "digital_wallet")
         .otherwise(F.when(F.col("channel") == "in-store", "cash").otherwise("digital_wallet")))
    .withColumn("_st", F.abs(F.hash(F.col("id"), F.lit("st"))) % 100)
    .withColumn("status",
        F.when(F.col("_st") < 65, "completed")
         .when(F.col("_st") < 80, "shipped")
         .when(F.col("_st") < 90, "processing")
         .when(F.col("_st") < 97, "returned")
         .otherwise("cancelled"))
    .withColumn("store_id",
        F.when((F.col("channel") == "in-store") & (F.abs(F.hash(F.col("id"), F.lit("null_store"))) % 100 >= 3),
               F.format_string("STORE-%03d", F.abs(F.hash(F.col("id"), F.lit("store"))) % 50 + 1)))
    .drop("id", "_ci", "_day", "_hr", "_mn", "_ch", "_pay", "_st")
)

# Imperfection: 1% duplicate orders
dupes = orders_df.sample(fraction=0.01, seed=42)
orders_df = orders_df.unionByName(dupes)
orders_df.cache()
order_count = orders_df.count()
print(f"  ✓ orders: {order_count:,} (includes ~1% dupes)")


# ═══════════════════════════════════════════════════════════════════
# 4. ORDER ITEMS — generated FROM orders (FK integrity by construction)
# ═══════════════════════════════════════════════════════════════════
print("4/6 Generating order items...")

order_items_df: DataFrame = (
    orders_df.select("order_id")
    .withColumn("_n", F.greatest(F.lit(1), (F.abs(F.hash(F.col("order_id"), F.lit("nitems"))) % 5 + 1).cast("int")))
    .select("order_id", F.explode(F.sequence(F.lit(1), F.col("_n"))).alias("_line"))
    .withColumn("item_id", F.concat(F.col("order_id"), F.lit("-"), F.col("_line")))
    .withColumn("_pi", (F.sqrt((F.abs(F.hash(F.col("item_id"), F.lit("prod"))) % 10000) / 10000.0) * N_PRODUCTS).cast("int"))
    .withColumn("product_id", F.format_string("PROD-%05d", F.least(F.col("_pi"), F.lit(N_PRODUCTS - 1)) + 1))
    .withColumn("quantity", (F.abs(F.hash(F.col("item_id"), F.lit("qty"))) % 4 + 1).cast("int"))
    .withColumn("_d", F.abs(F.hash(F.col("item_id"), F.lit("disc"))) % 100)
    .withColumn("discount_pct",
        F.when(F.col("_d") < 60, 0.0)
         .when(F.col("_d") < 75, 0.05)
         .when(F.col("_d") < 87, 0.10)
         .when(F.col("_d") < 95, 0.15)
         .otherwise(0.20))
    .drop("_line", "_pi", "_d")
)

order_items_df = (
    order_items_df
    .join(F.broadcast(products_df.select("product_id", "unit_price")), "product_id", "left")
    .withColumn("line_total", F.round(F.col("unit_price") * F.col("quantity") * (1 - F.col("discount_pct")), 2))
    .withColumn("line_total",
        F.when(F.abs(F.hash(F.col("item_id"), F.lit("outlier"))) % 100 == 0, F.col("line_total") * 50)
         .when(F.abs(F.hash(F.col("item_id"), F.lit("outlier"))) % 100 == 1, F.lit(-99.99))
         .otherwise(F.col("line_total")))
)
order_items_df.cache()
items_count = order_items_df.count()
print(f"  ✓ order_items: {items_count:,} | avg items/order: {items_count / order_count:.1f}")


# ═══════════════════════════════════════════════════════════════════
# 5. FK VALIDATION — assert integrity before writing
# ═══════════════════════════════════════════════════════════════════
print("5/6 Validating FK integrity...")

orphan_items = order_items_df.join(orders_df.select("order_id").distinct(), "order_id", "left_anti").count()
orphan_orders = orders_df.join(customers_df.select("customer_id"), "customer_id", "left_anti").count()
orphan_products = order_items_df.join(products_df.select("product_id"), "product_id", "left_anti").count()
print(f"  orphan order_items→orders: {orphan_items} (expect 0)")
print(f"  orphan orders→customers:  {orphan_orders} (expect 0)")
print(f"  orphan items→products:    {orphan_products} (expect 0)")
assert orphan_items == 0, f"FK violation: {orphan_items} orphan order_items"
assert orphan_orders == 0, f"FK violation: {orphan_orders} orphan orders"
assert orphan_products == 0, f"FK violation: {orphan_products} orphan products"
print("  ✓ All FK checks passed")


# ═══════════════════════════════════════════════════════════════════
# 6. WRITE BRONZE DELTA TABLES
#
# TALK: "I'm persisting directly to managed Delta tables in Unity Catalog
#   rather than staging parquet to Volumes. This gives me ACID transactions,
#   time travel, and Unity Catalog lineage on the Bronze layer immediately.
#   Every table carries six governance columns: _ingest_ts, _batch_id,
#   _source_system, _source_type, _generator_version, and _run_id.
#   The _batch_id groups all tables written in the same execution so I can
#   trace or roll back an entire load. The SDP pipeline starts at Silver —
#   it reads from these Bronze tables and applies dedup, typing, and
#   quality expectations.
#
#   This pattern is appropriate for notebook-generated or application-
#   produced data. If we needed raw file replay, schema drift handling,
#   or Auto Loader semantics, I'd use file-based ingestion instead."
# ═══════════════════════════════════════════════════════════════════
print(f"\n6/6 Writing Bronze Delta tables to {CATALOG}.{SCHEMA}...")

BRONZE_TABLES: dict[str, tuple[DataFrame, str, str]] = {
    # table_name: (dataframe, comment, cluster_by_col)
    "bronze_customers": (
        customers_df,
        "Raw customer dimension — synthetic, deterministic, includes 2% null emails",
        "customer_id",
    ),
    "bronze_products": (
        products_df,
        "Raw product catalog — 6 categories, log-normal price distribution",
        "product_id",
    ),
    "bronze_orders": (
        orders_df,
        "Raw order facts — 1M+ rows, includes 1% duplicates, 3% null store_ids on in-store",
        "order_timestamp",
    ),
    "bronze_order_items": (
        order_items_df,
        "Raw order line items — FK-safe to orders, includes 1% outlier line_totals",
        "order_id",
    ),
}

for table_name, (df, comment, cluster_col) in BRONZE_TABLES.items():
    fqn = f"{CATALOG}.{SCHEMA}.{table_name}"

    # Add governance metadata before writing
    bronze_df = add_bronze_metadata(df)

    # Write as managed Delta table
    (
        bronze_df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(fqn)
    )

    # Set table properties: comment, Liquid Clustering, governance tags
    spark.sql(f"COMMENT ON TABLE {fqn} IS '{comment}'")
    spark.sql(f"ALTER TABLE {fqn} CLUSTER BY ({cluster_col})")
    spark.sql(f"""
        ALTER TABLE {fqn} SET TBLPROPERTIES (
            'bronze.source_system'      = '{SOURCE_SYSTEM}',
            'bronze.source_type'        = '{SOURCE_TYPE}',
            'bronze.generator_version'  = '{GENERATOR_VERSION}',
            'bronze.initial_batch_id'   = '{BATCH_ID}',
            'bronze.initial_run_id'     = '{RUN_ID}',
            'quality.tier'              = 'bronze'
        )
    """)

    cnt = spark.table(fqn).count()
    print(f"  ✓ {fqn}: {cnt:,} rows | LC({cluster_col})")

print(f"\n  Batch ID: {BATCH_ID}")
print(f"  Run ID:   {RUN_ID}")
print(f"  Version:  {GENERATOR_VERSION}")


# ═══════════════════════════════════════════════════════════════════
# 7. VALIDATION + DELTA PROOF POINTS
# ═══════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("BRONZE LAYER COMPLETE — GOVERNANCE AUDIT")
print("=" * 60)

# Row counts
print("\n--- Row Counts ---")
for table_name in BRONZE_TABLES:
    fqn = f"{CATALOG}.{SCHEMA}.{table_name}"
    cnt = spark.table(fqn).count()
    print(f"  {fqn}: {cnt:,}")

# Governance metadata sample
print("\n--- Governance Columns (sample from bronze_orders) ---")
(spark.table(f"{CATALOG}.{SCHEMA}.bronze_orders")
 .select("order_id", "_ingest_ts", "_batch_id", "_source_system", "_source_type", "_generator_version", "_run_id")
 .limit(3)
 .show(truncate=False))

# Table properties
print("--- Table Properties (bronze_orders) ---")
spark.sql(f"SHOW TBLPROPERTIES {CATALOG}.{SCHEMA}.bronze_orders").show(20, truncate=False)

# Delta proof points
print("--- DESCRIBE DETAIL (Liquid Clustering + format) ---")
(spark.sql(f"DESCRIBE DETAIL {CATALOG}.{SCHEMA}.bronze_orders")
 .select("name", "format", "clusteringColumns", "numFiles")
 .show(truncate=False))

print("--- DESCRIBE HISTORY (audit trail) ---")
(spark.sql(f"DESCRIBE HISTORY {CATALOG}.{SCHEMA}.bronze_orders LIMIT 3")
 .select("version", "timestamp", "operation", "operationMetrics")
 .show(truncate=False))

# Distributions
print("\n--- Distributions ---")
spark.table(f"{CATALOG}.{SCHEMA}.bronze_orders").groupBy("channel").count().orderBy(F.desc("count")).show(truncate=False)
spark.table(f"{CATALOG}.{SCHEMA}.bronze_customers").groupBy("region").count().orderBy(F.desc("count")).show(truncate=False)
spark.table(f"{CATALOG}.{SCHEMA}.bronze_customers").groupBy("loyalty_tier").count().orderBy(F.desc("count")).show(truncate=False)

# Imperfections
print("--- Imperfections ---")
bc = f"{CATALOG}.{SCHEMA}.bronze_customers"
bo = f"{CATALOG}.{SCHEMA}.bronze_orders"
bi = f"{CATALOG}.{SCHEMA}.bronze_order_items"
print(f"  null emails:         {spark.table(bc).filter(F.col('email').isNull()).count()}")
print(f"  null store_id:       {spark.table(bo).filter((F.col('channel') == 'in-store') & F.col('store_id').isNull()).count()}")
print(f"  duplicate order_ids: {spark.table(bo).groupBy('order_id').count().filter('count > 1').count()}")
print(f"  outlier line_totals: {spark.table(bi).filter((F.col('line_total') < 0) | (F.col('line_total') > 10000)).count()}")

# Batch consistency check
print("\n--- Batch Consistency ---")
for table_name in BRONZE_TABLES:
    fqn = f"{CATALOG}.{SCHEMA}.{table_name}"
    batch_count = spark.table(fqn).select("_batch_id").distinct().count()
    print(f"  {table_name}: {batch_count} distinct batch_id(s) (expect 1)")

print(f"\n✅ Bronze Delta tables ready with full governance metadata.")
print(f"   SDP pipeline starts at Silver: python3 scripts/deploy_pipeline.py --full-refresh")
