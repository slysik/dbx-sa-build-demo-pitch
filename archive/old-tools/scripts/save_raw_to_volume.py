"""Save DataFrames to Volume. Run this in the SAME notebook after generate_retail_data.py."""
CATALOG = "interview"
SCHEMA = "retail"

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.raw_data")

VOLUME = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data"

customers_df.write.mode("overwrite").parquet(f"{VOLUME}/customers")
print(f"✓ customers → {VOLUME}/customers")

products_df.write.mode("overwrite").parquet(f"{VOLUME}/products")
print(f"✓ products → {VOLUME}/products")

orders_1m_df.write.mode("overwrite").parquet(f"{VOLUME}/orders")
print(f"✓ orders (1M) → {VOLUME}/orders")

order_items_df.write.mode("overwrite").parquet(f"{VOLUME}/order_items")
print(f"✓ order_items → {VOLUME}/order_items")

for t in ["customers", "products", "orders", "order_items"]:
    cnt = spark.read.parquet(f"{VOLUME}/{t}").count()
    print(f"  {t}: {cnt:,} rows")

print(f"\n✅ Raw data landed in {VOLUME}")
