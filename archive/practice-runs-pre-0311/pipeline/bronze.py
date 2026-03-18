"""Bronze layer — raw ingestion from Volume parquet files.
Append-only. No business logic. Full source fidelity + ingestion metadata.
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F

VOLUME_PATH = "/Volumes/interview/retail/raw_data"

# ---------------------------------------------------------------------------
# Bronze: Customers
# ---------------------------------------------------------------------------
@dp.table(
    name="bronze_customers",
    comment="Raw customer dimension from landing zone",
    cluster_by=["customer_id"],
)
def bronze_customers():
    return (
        spark.read.parquet(f"{VOLUME_PATH}/customers")
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source", F.lit("raw_data/customers"))
    )


# ---------------------------------------------------------------------------
# Bronze: Products
# ---------------------------------------------------------------------------
@dp.table(
    name="bronze_products",
    comment="Raw product dimension from landing zone",
    cluster_by=["product_id"],
)
def bronze_products():
    return (
        spark.read.parquet(f"{VOLUME_PATH}/products")
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source", F.lit("raw_data/products"))
    )


# ---------------------------------------------------------------------------
# Bronze: Orders (1M rows)
# ---------------------------------------------------------------------------
@dp.table(
    name="bronze_orders",
    comment="Raw order facts from landing zone — 1M rows",
    cluster_by=["order_timestamp"],
)
def bronze_orders():
    return (
        spark.read.parquet(f"{VOLUME_PATH}/orders")
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source", F.lit("raw_data/orders"))
    )


# ---------------------------------------------------------------------------
# Bronze: Order Items
# ---------------------------------------------------------------------------
@dp.table(
    name="bronze_order_items",
    comment="Raw order line items from landing zone",
    cluster_by=["order_id"],
)
def bronze_order_items():
    return (
        spark.read.parquet(f"{VOLUME_PATH}/order_items")
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source", F.lit("raw_data/order_items"))
    )
