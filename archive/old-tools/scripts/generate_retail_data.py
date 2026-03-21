"""Generate 100k-row synthetic retail dataset using pure PySpark DataFrames.
No Delta writes — DataFrame only. Designed to scale to 1M via crossJoin.
"""
import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.window import Window

spark = SparkSession.builder.getOrCreate()

# =============================================================================
# CONFIGURATION
# =============================================================================
N_ORDERS = 100_000
N_CUSTOMERS = 5_000
N_PRODUCTS = 500

# =============================================================================
# 1. CUSTOMERS DIMENSION (5k rows)
# =============================================================================
print("Generating customers...")

regions = ["West", "South", "Midwest", "Northeast"]
tiers = ["Standard", "Premium", "VIP"]

customers_df: DataFrame = (
    spark.range(0, N_CUSTOMERS)
    .withColumnRenamed("id", "customer_id")
    .withColumn("customer_id", F.format_string("CUST-%06d", F.col("customer_id")))
    .withColumn("first_name", F.concat(F.lit("First"), F.expr("cast(hash(customer_id, 'fn') % 9999 as string)")))
    .withColumn("last_name", F.concat(F.lit("Last"), F.expr("cast(hash(customer_id, 'ln') % 9999 as string)")))
    .withColumn("email", F.concat(F.lower(F.col("first_name")), F.lit("."), F.lower(F.col("last_name")), F.lit("@example.com")))
    .withColumn("region", F.element_at(
        F.array([F.lit(r) for r in regions]),
        (F.abs(F.hash(F.col("customer_id"), F.lit("region"))) % 100)
        .cast("int")
        # West 30%, South 28%, Midwest 22%, Northeast 20%
        + F.lit(1)  # 1-indexed
    ))
    # Simpler weighted region using ranges
    .drop("region")
    .withColumn("_rand_region", F.abs(F.hash(F.col("customer_id"), F.lit("region"))) % 100)
    .withColumn("region", F.when(F.col("_rand_region") < 30, F.lit("West"))
                           .when(F.col("_rand_region") < 58, F.lit("South"))
                           .when(F.col("_rand_region") < 80, F.lit("Midwest"))
                           .otherwise(F.lit("Northeast")))
    .withColumn("_rand_tier", F.abs(F.hash(F.col("customer_id"), F.lit("tier"))) % 100)
    .withColumn("loyalty_tier", F.when(F.col("_rand_tier") < 70, F.lit("Standard"))
                                 .when(F.col("_rand_tier") < 92, F.lit("Premium"))
                                 .otherwise(F.lit("VIP")))
    .withColumn("signup_date", F.date_sub(F.current_date(), (F.abs(F.hash(F.col("customer_id"), F.lit("signup"))) % 1000 + 180).cast("int")))
    # 2% null emails
    .withColumn("email", F.when(F.abs(F.hash(F.col("customer_id"), F.lit("null_email"))) % 100 < 2, F.lit(None)).otherwise(F.col("email")))
    .drop("_rand_region", "_rand_tier")
)

customers_df.cache()
print(f"  ✓ customers: {customers_df.count():,} rows")
customers_df.show(5, truncate=False)

# =============================================================================
# 2. PRODUCTS DIMENSION (500 rows)
# =============================================================================
print("Generating products...")

category_list = ["Electronics", "Apparel", "Home & Garden", "Sports", "Beauty", "Grocery"]

products_df: DataFrame = (
    spark.range(0, N_PRODUCTS)
    .withColumnRenamed("id", "product_id")
    .withColumn("product_id", F.format_string("PROD-%05d", F.col("product_id")))
    .withColumn("_rand_cat", F.abs(F.hash(F.col("product_id"), F.lit("cat"))) % 100)
    .withColumn("category", F.when(F.col("_rand_cat") < 25, F.lit("Electronics"))
                              .when(F.col("_rand_cat") < 45, F.lit("Apparel"))
                              .when(F.col("_rand_cat") < 63, F.lit("Home & Garden"))
                              .when(F.col("_rand_cat") < 75, F.lit("Sports"))
                              .when(F.col("_rand_cat") < 85, F.lit("Beauty"))
                              .otherwise(F.lit("Grocery")))
    .withColumn("product_name", F.concat(F.col("category"), F.lit(" Item "), F.col("product_id")))
    # Log-normal price: exp(mu + sigma*randn). Use hash-based deterministic approach.
    .withColumn("_price_seed", (F.abs(F.hash(F.col("product_id"), F.lit("price"))) % 10000) / 10000.0)
    .withColumn("unit_price", F.round(
        F.when(F.col("category") == "Electronics", F.exp(F.lit(5.5) + F.lit(0.9) * (F.col("_price_seed") * 2 - 1)))
         .when(F.col("category") == "Grocery", F.exp(F.lit(2.5) + F.lit(0.4) * (F.col("_price_seed") * 2 - 1)))
         .otherwise(F.exp(F.lit(3.8) + F.lit(0.7) * (F.col("_price_seed") * 2 - 1)))
    , 2))
    .withColumn("unit_price", F.least(F.col("unit_price"), F.lit(2999.99)))
    .withColumn("unit_price", F.greatest(F.col("unit_price"), F.lit(1.99)))
    .withColumn("cost_price", F.round(F.col("unit_price") * (F.lit(0.3) + F.col("_price_seed") * 0.4), 2))
    .drop("_rand_cat", "_price_seed")
)

products_df.cache()
print(f"  ✓ products: {products_df.count():,} rows")
products_df.show(5, truncate=False)

# =============================================================================
# 3. ORDERS FACT (100k rows)
# =============================================================================
print(f"Generating {N_ORDERS:,} orders...")

channels = ["web", "mobile", "in-store"]
statuses = ["completed", "shipped", "processing", "returned", "cancelled"]
payment_methods = ["credit_card", "debit_card", "digital_wallet", "cash"]

orders_df: DataFrame = (
    spark.range(0, N_ORDERS)
    .withColumnRenamed("id", "order_seq")
    .withColumn("order_id", F.format_string("ORD-%07d", F.col("order_seq")))

    # Customer assignment — VIP/Premium customers order more (skewed via hash weighting)
    # Create skewed customer_id: lower customer_ids (VIP/Premium) appear more often
    .withColumn("_cust_seed", F.abs(F.hash(F.col("order_seq"), F.lit("cust"))) % 10000)
    # Power-law: square root pulls distribution toward lower IDs (more active customers)
    .withColumn("_cust_idx", (F.sqrt(F.col("_cust_seed") / 10000.0) * N_CUSTOMERS).cast("int"))
    .withColumn("_cust_idx", F.least(F.col("_cust_idx"), F.lit(N_CUSTOMERS - 1)))
    .withColumn("customer_id", F.format_string("CUST-%06d", F.col("_cust_idx")))

    # Order timestamp: last 180 days, business-hours weighted
    .withColumn("_day_offset", (F.abs(F.hash(F.col("order_seq"), F.lit("day"))) % 180).cast("int"))
    .withColumn("_hour", F.abs(F.hash(F.col("order_seq"), F.lit("hour"))) % 18 + 6)  # 6am-11pm
    .withColumn("_minute", F.abs(F.hash(F.col("order_seq"), F.lit("min"))) % 60)
    .withColumn("order_timestamp",
        F.to_timestamp(
            F.date_sub(F.current_date(), F.col("_day_offset")).cast("string")
        ) + F.expr("make_interval(0,0,0,0,_hour,_minute,0)")
    )

    # Channel
    .withColumn("_rand_ch", F.abs(F.hash(F.col("order_seq"), F.lit("ch"))) % 100)
    .withColumn("channel", F.when(F.col("_rand_ch") < 45, F.lit("web"))
                             .when(F.col("_rand_ch") < 80, F.lit("mobile"))
                             .otherwise(F.lit("in-store")))

    # Payment method — cash only for in-store
    .withColumn("_rand_pay", F.abs(F.hash(F.col("order_seq"), F.lit("pay"))) % 100)
    .withColumn("payment_method",
        F.when(F.col("_rand_pay") < 40, F.lit("credit_card"))
         .when(F.col("_rand_pay") < 65, F.lit("debit_card"))
         .when(F.col("_rand_pay") < 90, F.lit("digital_wallet"))
         .otherwise(F.when(F.col("channel") == "in-store", F.lit("cash")).otherwise(F.lit("digital_wallet")))
    )

    # Status
    .withColumn("_rand_st", F.abs(F.hash(F.col("order_seq"), F.lit("st"))) % 100)
    .withColumn("status", F.when(F.col("_rand_st") < 65, F.lit("completed"))
                            .when(F.col("_rand_st") < 80, F.lit("shipped"))
                            .when(F.col("_rand_st") < 90, F.lit("processing"))
                            .when(F.col("_rand_st") < 97, F.lit("returned"))
                            .otherwise(F.lit("cancelled")))

    # Store ID only for in-store
    .withColumn("store_id",
        F.when(F.col("channel") == "in-store",
               F.format_string("STORE-%03d", F.abs(F.hash(F.col("order_seq"), F.lit("store"))) % 50 + 1))
    )
    # 3% null store_id on in-store orders (data quality issue)
    .withColumn("store_id",
        F.when((F.col("channel") == "in-store") & (F.abs(F.hash(F.col("order_seq"), F.lit("null_store"))) % 100 < 3), F.lit(None))
         .otherwise(F.col("store_id"))
    )

    .drop("order_seq", "_cust_seed", "_cust_idx", "_day_offset", "_hour", "_minute",
          "_rand_ch", "_rand_pay", "_rand_st")
)

# Inject 1% duplicate orders
dupes_df = orders_df.sample(fraction=0.01, seed=42)
orders_df = orders_df.unionByName(dupes_df)

orders_df.cache()
order_count = orders_df.count()
print(f"  ✓ orders: {order_count:,} rows (includes ~1% dupes)")
orders_df.show(5, truncate=False)

# =============================================================================
# 4. ORDER_ITEMS (Detail fact — ~2.5 items per order)
# =============================================================================
print("Generating order items...")

# Explode each order into 1-5 line items
order_items_df: DataFrame = (
    orders_df.select("order_id")
    .withColumn("_n_items", (F.abs(F.hash(F.col("order_id"), F.lit("nitems"))) % 5 + 1).cast("int"))
    .withColumn("_item_idx", F.explode(F.sequence(F.lit(1), F.col("_n_items"))))
    .withColumn("item_id", F.concat(F.col("order_id"), F.lit("-"), F.col("_item_idx")))

    # Assign product — skewed toward popular products (lower IDs)
    .withColumn("_prod_seed", F.abs(F.hash(F.col("item_id"), F.lit("prod"))) % 10000)
    .withColumn("_prod_idx", (F.sqrt(F.col("_prod_seed") / 10000.0) * N_PRODUCTS).cast("int"))
    .withColumn("_prod_idx", F.least(F.col("_prod_idx"), F.lit(N_PRODUCTS - 1)))
    .withColumn("product_id", F.format_string("PROD-%05d", F.col("_prod_idx")))

    # Quantity: mostly 1-3
    .withColumn("quantity", (F.abs(F.hash(F.col("item_id"), F.lit("qty"))) % 4 + 1).cast("int"))

    # Discount: 60% none, rest 5-20%
    .withColumn("_rand_disc", F.abs(F.hash(F.col("item_id"), F.lit("disc"))) % 100)
    .withColumn("discount_pct",
        F.when(F.col("_rand_disc") < 60, F.lit(0.0))
         .when(F.col("_rand_disc") < 75, F.lit(0.05))
         .when(F.col("_rand_disc") < 87, F.lit(0.10))
         .when(F.col("_rand_disc") < 95, F.lit(0.15))
         .otherwise(F.lit(0.20))
    )
    .drop("_n_items", "_item_idx", "_prod_seed", "_prod_idx", "_rand_disc")
)

# Join product price and compute line_total
order_items_df = (
    order_items_df
    .join(products_df.select("product_id", "unit_price"), "product_id", "left")
    .withColumn("line_total", F.round(F.col("unit_price") * F.col("quantity") * (1 - F.col("discount_pct")), 2))
    # 1% outlier line_totals
    .withColumn("line_total",
        F.when(F.abs(F.hash(F.col("item_id"), F.lit("outlier"))) % 100 == 0, F.col("line_total") * 50)
         .when(F.abs(F.hash(F.col("item_id"), F.lit("outlier"))) % 100 == 1, F.lit(-99.99))
         .otherwise(F.col("line_total"))
    )
)

order_items_df.cache()
items_count = order_items_df.count()
print(f"  ✓ order_items: {items_count:,} rows | avg items/order: {items_count/order_count:.1f}")
order_items_df.show(5, truncate=False)

# =============================================================================
# 5. VALIDATION SUMMARY
# =============================================================================
print("\n" + "=" * 60)
print("DATASET SUMMARY")
print("=" * 60)

for name, df in [("customers", customers_df), ("products", products_df),
                  ("orders", orders_df), ("order_items", order_items_df)]:
    cnt = df.count()
    parts = df.withColumn("_pid", F.spark_partition_id()).agg(F.max("_pid")).collect()[0][0] + 1
    print(f"\n{name}: {cnt:,} rows | {len(df.columns)} cols | {parts} partitions")

print("\n--- Distributions ---")
orders_df.groupBy("channel").count().orderBy(F.desc("count")).show()
orders_df.groupBy("status").count().orderBy(F.desc("count")).show()
orders_df.groupBy("payment_method").count().orderBy(F.desc("count")).show()
customers_df.groupBy("loyalty_tier").count().orderBy(F.desc("count")).show()
customers_df.groupBy("region").count().orderBy(F.desc("count")).show()
products_df.groupBy("category").count().orderBy(F.desc("count")).show()

# Null audit
print("--- Null Audit ---")
orders_null_store = orders_df.filter((F.col("channel") == "in-store") & F.col("store_id").isNull()).count()
cust_null_email = customers_df.filter(F.col("email").isNull()).count()
print(f"  null emails: {cust_null_email}")
print(f"  null store_id (in-store): {orders_null_store}")

# Duplicate check
dupes = orders_df.groupBy("order_id").count().filter("count > 1").count()
print(f"  duplicate order_ids: {dupes}")

# Outlier line_totals
outliers = order_items_df.filter((F.col("line_total") < 0) | (F.col("line_total") > 10000)).count()
print(f"  outlier line_totals: {outliers}")

print("\n✅ DataFrames ready for review. Scale to 1M with crossJoin(spark.range(10)).")
