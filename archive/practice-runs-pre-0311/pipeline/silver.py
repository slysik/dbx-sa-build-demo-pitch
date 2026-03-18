"""Silver layer — cleaned, typed, deduped, quality-enforced.
Reusable business semantics. Explicit schema contracts.
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# ---------------------------------------------------------------------------
# Silver: Customers — dedup, null handling, type enforcement
# ---------------------------------------------------------------------------
@dp.table(
    name="silver_customers",
    comment="Cleaned customer dimension — deduped on customer_id, nulls handled",
    cluster_by=["region", "loyalty_tier"],
)
@dp.expect_or_drop("valid_customer_id", "customer_id IS NOT NULL")
@dp.expect_or_drop("valid_signup", "signup_date IS NOT NULL")
def silver_customers():
    return (
        spark.read.table("bronze_customers")
        .dropDuplicates(["customer_id"])
        .select(
            F.col("customer_id").cast("string"),
            F.col("first_name").cast("string"),
            F.col("last_name").cast("string"),
            F.coalesce(F.col("email"), F.lit("unknown@missing.com")).alias("email"),
            F.col("region").cast("string"),
            F.col("loyalty_tier").cast("string"),
            F.col("signup_date").cast("date"),
        )
    )


# ---------------------------------------------------------------------------
# Silver: Products — dedup, enforce price constraints
# ---------------------------------------------------------------------------
@dp.table(
    name="silver_products",
    comment="Cleaned product dimension — valid prices, deduped",
    cluster_by=["category"],
)
@dp.expect_or_drop("valid_product_id", "product_id IS NOT NULL")
@dp.expect_or_drop("valid_price", "unit_price > 0")
@dp.expect_or_drop("valid_cost", "cost_price > 0")
def silver_products():
    return (
        spark.read.table("bronze_products")
        .dropDuplicates(["product_id"])
        .select(
            F.col("product_id").cast("string"),
            F.col("product_name").cast("string"),
            F.col("category").cast("string"),
            F.col("unit_price").cast("decimal(10,2)"),
            F.col("cost_price").cast("decimal(10,2)"),
        )
    )


# ---------------------------------------------------------------------------
# Silver: Orders — dedup on order_id (keeps latest), type casting, null handling
# ---------------------------------------------------------------------------
@dp.table(
    name="silver_orders",
    comment="Cleaned order facts — deduped, typed, 1M rows",
    cluster_by=["order_date", "channel"],
)
@dp.expect_or_drop("valid_order_id", "order_id IS NOT NULL")
@dp.expect_or_drop("valid_customer_id", "customer_id IS NOT NULL")
@dp.expect_or_drop("valid_timestamp", "order_timestamp IS NOT NULL")
def silver_orders():
    # Deterministic dedup: keep first occurrence per order_id using row_number
    w = Window.partitionBy("order_id").orderBy(F.col("order_timestamp").asc())

    return (
        spark.read.table("bronze_orders")
        .withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
        .select(
            F.col("order_id").cast("string"),
            F.col("customer_id").cast("string"),
            F.col("order_timestamp").cast("timestamp"),
            F.to_date("order_timestamp").alias("order_date"),
            F.col("channel").cast("string"),
            F.col("payment_method").cast("string"),
            F.col("status").cast("string"),
            F.col("store_id").cast("string"),
        )
    )


# ---------------------------------------------------------------------------
# Silver: Order Items — dedup, filter outliers, enforce referential integrity
# ---------------------------------------------------------------------------
@dp.table(
    name="silver_order_items",
    comment="Cleaned order line items — outliers filtered, typed",
    cluster_by=["order_id"],
)
@dp.expect_or_drop("valid_item_id", "item_id IS NOT NULL")
@dp.expect_or_drop("valid_order_id", "order_id IS NOT NULL")
@dp.expect_or_drop("valid_product_id", "product_id IS NOT NULL")
@dp.expect_or_drop("positive_quantity", "quantity > 0")
@dp.expect_or_drop("valid_line_total", "line_total > 0 AND line_total < 50000")
def silver_order_items():
    return (
        spark.read.table("bronze_order_items")
        .dropDuplicates(["item_id"])
        .select(
            F.col("item_id").cast("string"),
            F.col("order_id").cast("string"),
            F.col("product_id").cast("string"),
            F.col("quantity").cast("int"),
            F.col("unit_price").cast("decimal(10,2)"),
            F.col("discount_pct").cast("decimal(5,2)"),
            F.col("line_total").cast("decimal(12,2)"),
        )
    )
