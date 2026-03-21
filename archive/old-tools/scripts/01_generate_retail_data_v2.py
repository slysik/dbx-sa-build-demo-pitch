# Databricks notebook source
# MAGIC %md
# MAGIC # Step 1: Generate 1000 Retail Streaming Records (v2)
# MAGIC **3 Vs Demo**: Volume (1000 records) | Variety (multi-type retail events) | Velocity (trickle every 10s)
# MAGIC
# MAGIC Uses PySpark + Faker to generate realistic retail events with log-normal pricing,
# MAGIC Poisson quantities, and weighted categorical distributions.

# COMMAND ----------

# MAGIC %pip install faker
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import json
import numpy as np  # noqa: F821
from datetime import datetime, timedelta
from faker import Faker  # noqa: F821

# =============================================================================
# CONFIGURATION (v2)
# =============================================================================
CATALOG = "dbx_weg"
SCHEMA = "bronze"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/streaming_data_v2"
N_RECORDS = 1000
SEED = 99

# =============================================================================
# SETUP
# =============================================================================
np.random.seed(SEED)
Faker.seed(SEED)
fake = Faker()
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.streaming_data_v2")

# =============================================================================
# PRODUCT CATALOG
# =============================================================================
PRODUCTS = {
    "Electronics": [
        ("Wireless Earbuds", 29.99, 149.99),
        ("USB-C Charger", 9.99, 39.99),
        ("Bluetooth Speaker", 19.99, 89.99),
        ("Smart Watch", 99.99, 399.99),
        ("Phone Case", 9.99, 29.99),
    ],
    "Groceries": [
        ("Organic Milk", 3.99, 7.99),
        ("Sourdough Bread", 4.49, 8.99),
        ("Avocados (6pk)", 5.99, 9.99),
        ("Chicken Breast", 7.99, 14.99),
        ("Coffee Beans", 9.99, 18.99),
    ],
    "Apparel": [
        ("Running Shoes", 49.99, 129.99),
        ("Denim Jeans", 29.99, 79.99),
        ("Cotton T-Shirt", 12.99, 29.99),
        ("Winter Jacket", 59.99, 199.99),
        ("Baseball Cap", 14.99, 34.99),
    ],
    "Home & Garden": [
        ("LED Desk Lamp", 19.99, 59.99),
        ("Throw Pillow", 14.99, 39.99),
        ("Plant Pot Set", 12.99, 34.99),
        ("Scented Candle", 8.99, 24.99),
        ("Kitchen Towels", 7.99, 19.99),
    ],
    "Sports": [
        ("Yoga Mat", 19.99, 49.99),
        ("Water Bottle", 9.99, 29.99),
        ("Resistance Bands", 12.99, 34.99),
        ("Jump Rope", 7.99, 19.99),
        ("Foam Roller", 14.99, 39.99),
    ],
}

PAYMENT_METHODS = ["credit_card", "debit_card", "mobile_pay", "cash", "gift_card"]
PAYMENT_WEIGHTS = [0.40, 0.25, 0.20, 0.10, 0.05]
EVENT_TYPES = ["purchase", "return", "exchange"]
EVENT_WEIGHTS = [0.85, 0.10, 0.05]
STORE_IDS = [f"STORE-{i:03d}" for i in range(1, 21)]
CATEGORIES = list(PRODUCTS.keys())
CATEGORY_WEIGHTS = [0.30, 0.25, 0.20, 0.15, 0.10]

# =============================================================================
# GENERATE 1000 RETAIL RECORDS
# =============================================================================
records = []
base_time = datetime.now()

for i in range(N_RECORDS):
    category = np.random.choice(CATEGORIES, p=CATEGORY_WEIGHTS)
    products_in_cat = PRODUCTS[category]
    product_idx = abs(hash(f"{i}-prod-{SEED}")) % len(products_in_cat)
    product_name, min_price, max_price = products_in_cat[product_idx]

    raw_price = np.random.lognormal(mean=0, sigma=0.5)
    unit_price = round(min_price + (max_price - min_price) * min(raw_price / 3.0, 1.0), 2)
    quantity = max(1, int(np.random.poisson(lam=2)))
    total_amount = round(unit_price * quantity, 2)

    seconds_ago = np.random.exponential(scale=7.0)
    event_time = base_time - timedelta(seconds=float(i * 7.2 + seconds_ago))

    records.append({
        "order_id": f"ORD-V2-{fake.unique.random_int(min=100000, max=999999)}",
        "customer_id": f"CUST-{abs(hash(f'{i}-cust-{SEED}')) % 500 + 1:05d}",
        "product_name": product_name,
        "category": category,
        "quantity": quantity,
        "unit_price": float(unit_price),
        "total_amount": float(total_amount),
        "event_timestamp": event_time.strftime("%Y-%m-%dT%H:%M:%S.%f"),
        "store_id": np.random.choice(STORE_IDS),
        "payment_method": np.random.choice(PAYMENT_METHODS, p=PAYMENT_WEIGHTS),
        "event_type": np.random.choice(EVENT_TYPES, p=EVENT_WEIGHTS),
    })

print(f"Generated {len(records)} retail records")
print(f"Categories: {set(r['category'] for r in records)}")
print(f"Event types: {set(r['event_type'] for r in records)}")
print(f"Price range: ${min(r['unit_price'] for r in records):.2f} - ${max(r['unit_price'] for r in records):.2f}")

# =============================================================================
# SAVE AS JSON BATCHES TO VOLUME
# =============================================================================
BATCH_SIZE = 50
for batch_idx in range(0, N_RECORDS, BATCH_SIZE):
    batch = records[batch_idx:batch_idx + BATCH_SIZE]
    batch_num = batch_idx // BATCH_SIZE
    json_content = "\n".join(json.dumps(r) for r in batch)
    dbutils.fs.put(f"{VOLUME_PATH}/batch_{batch_num:03d}.json", json_content, overwrite=True)

full_json = "\n".join(json.dumps(r) for r in records)
dbutils.fs.put(f"{VOLUME_PATH}/all_records.json", full_json, overwrite=True)

print(f"\nSaved {N_RECORDS // BATCH_SIZE} batch files to {VOLUME_PATH}")
print(f"Each batch: {BATCH_SIZE} records")
print(f"Ready for Zerobus trickle ingestion!")
