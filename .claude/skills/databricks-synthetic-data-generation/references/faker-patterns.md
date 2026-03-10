# Faker and Data Generation Patterns

## Table of Contents

- [PySpark-First with spark.range (Interview Mode)](#pyspark-first-with-sparkrange-interview-mode)
- [Pandas + Faker (Non-Interview)](#pandas--faker-non-interview)
- [Referential Integrity](#referential-integrity)
- [Faker Providers and Locale](#faker-providers-and-locale)
- [Custom Faker Providers](#custom-faker-providers)

## PySpark-First with spark.range (Interview Mode)

For interview scenarios, use `spark.range()` as the primary data gen pattern -- it is distributed and impressive:

```python
# TALK: spark.range() distributes generation across executors -- no driver bottleneck
# SCALING: At 1M rows, just change N. Same code, same pattern.
from pyspark.sql import functions as F

N = 100_000  # Default for interviews (mention "scales to 1M+")
N_ENTITIES = 10_000

df = (spark.range(N)
    .withColumn("entity_id", F.concat(F.lit("E"), F.lpad(
        (F.abs(F.hash(F.col("id"), F.lit("ent"))) % N_ENTITIES).cast("string"), 6, "0")))
    .withColumn("event_ts", F.timestampadd("SECOND",
        -(F.abs(F.hash(F.col("id"), F.lit("ts"))) % (14 * 86400)).cast("int"),
        F.current_timestamp()))
    .withColumn("amount", F.round(
        F.abs(F.hash(F.col("id"), F.lit("amt"))) % 500000 / 100.0 + 0.99, 2).cast("decimal(18,2)"))
    .withColumn("status", F.when(F.abs(F.hash(F.col("id"), F.lit("st"))) % 100 < 85, "ACTIVE")
                           .when(F.abs(F.hash(F.col("id"), F.lit("st"))) % 100 < 95, "PENDING")
                           .otherwise("CLOSED"))
    .drop("id")
)
```

Use Faker UDFs only for realistic names/addresses. Use `F.hash()` + modular arithmetic for everything else.

Include TALK/SCALING/DW-BRIDGE narration comments when generating interview data.

### Faker UDFs with spark.range

When you need realistic text fields (names, addresses, emails) in a spark.range pipeline:

```python
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
from faker import Faker

fake = Faker()
Faker.seed(42)

@udf(StringType())
def fake_name(id):
    Faker.seed(id)  # Deterministic per row
    return Faker().name()

@udf(StringType())
def fake_company(id):
    Faker.seed(id)
    return Faker().company()

@udf(StringType())
def fake_email(id):
    Faker.seed(id)
    return Faker().email()

df = (spark.range(N)
    .withColumn("customer_name", fake_name(F.col("id")))
    .withColumn("company", fake_company(F.col("id")))
    .withColumn("email", fake_email(F.col("id")))
    # ... hash-based columns for everything else
)
```

## Pandas + Faker (Non-Interview)

Generate data with pandas (faster, easier), convert to Spark for saving:

```python
import pandas as pd
from faker import Faker
import numpy as np

fake = Faker()
Faker.seed(42)
np.random.seed(42)

# Generate with pandas
customers_pdf = pd.DataFrame({
    "customer_id": [f"CUST-{i:05d}" for i in range(N_CUSTOMERS)],
    "name": [fake.company() for _ in range(N_CUSTOMERS)],
    "tier": np.random.choice(['Free', 'Pro', 'Enterprise'], N_CUSTOMERS, p=[0.6, 0.3, 0.1]),
    "region": np.random.choice(['North', 'South', 'East', 'West'], N_CUSTOMERS, p=[0.4, 0.25, 0.2, 0.15]),
    "created_at": [fake.date_between(start_date='-2y', end_date='-6m') for _ in range(N_CUSTOMERS)],
})

# Convert to Spark and save
customers_df = spark.createDataFrame(customers_pdf)
customers_df.write.mode("overwrite").parquet(f"{VOLUME_PATH}/customers")
```

### Common Faker Methods

| Method | Output | Use For |
|--------|--------|---------|
| `fake.company()` | "Johnson LLC" | Business names |
| `fake.name()` | "John Smith" | Person names |
| `fake.email()` | "john@example.com" | Email addresses |
| `fake.address()` | "123 Main St..." | Full addresses |
| `fake.city()` | "New York" | City names |
| `fake.state()` | "California" | US states |
| `fake.phone_number()` | "(555) 123-4567" | Phone numbers |
| `fake.date_between(start, end)` | datetime.date | Date in range |
| `fake.text(max_nb_chars=200)` | "Lorem ipsum..." | Descriptive text |
| `fake.uuid4()` | "a1b2c3d4-..." | Unique IDs |
| `fake.credit_card_number()` | "4111111111111111" | Card numbers (test) |
| `fake.iban()` | "GB82WEST..." | Bank accounts |

## Referential Integrity

Generate master tables first, then iterate on them to create related tables with matching IDs:

```python
# 1. Generate customers (master table)
customers_pdf = pd.DataFrame({
    "customer_id": [f"CUST-{i:05d}" for i in range(N_CUSTOMERS)],
    "tier": np.random.choice(['Free', 'Pro', 'Enterprise'], N_CUSTOMERS, p=[0.6, 0.3, 0.1]),
    # ...
})

# 2. Create lookup for foreign key generation
customer_ids = customers_pdf["customer_id"].tolist()
customer_tier_map = dict(zip(customers_pdf["customer_id"], customers_pdf["tier"]))

# Weight by tier - Enterprise customers generate more orders
tier_weights = customers_pdf["tier"].map({'Enterprise': 5.0, 'Pro': 2.0, 'Free': 1.0})
customer_weights = (tier_weights / tier_weights.sum()).tolist()

# 3. Generate orders with valid foreign keys and tier-based logic
orders_data = []
for i in range(N_ORDERS):
    cid = np.random.choice(customer_ids, p=customer_weights)
    tier = customer_tier_map[cid]

    # Amount depends on tier
    if tier == 'Enterprise':
        amount = np.random.lognormal(7, 0.8)
    elif tier == 'Pro':
        amount = np.random.lognormal(5, 0.7)
    else:
        amount = np.random.lognormal(3.5, 0.6)

    orders_data.append({
        "order_id": f"ORD-{i:06d}",
        "customer_id": cid,
        "amount": round(amount, 2),
        "order_date": fake.date_between(start_date=START_DATE, end_date=END_DATE),
    })

orders_pdf = pd.DataFrame(orders_data)

# 4. Generate tickets that reference both customers and orders
order_ids = orders_pdf["order_id"].tolist()
tickets_data = []
for i in range(N_TICKETS):
    cid = np.random.choice(customer_ids, p=customer_weights)
    oid = np.random.choice(order_ids)  # Or None for general inquiry

    tickets_data.append({
        "ticket_id": f"TKT-{i:06d}",
        "customer_id": cid,
        "order_id": oid if np.random.random() > 0.3 else None,
        # ...
    })

tickets_pdf = pd.DataFrame(tickets_data)
```

## Faker Providers and Locale

### Using Locales

```python
# US-specific data
fake_us = Faker('en_US')

# Multi-locale for international data
fake = Faker(['en_US', 'en_GB', 'de_DE', 'fr_FR', 'ja_JP'])
# Each call randomly picks a locale
names = [fake.name() for _ in range(100)]  # Mix of American, British, German, French, Japanese names

# Locale-specific financial data
fake_uk = Faker('en_GB')
fake_uk.iban()      # GB-format IBAN
fake_uk.postcode()  # UK postcode format
```

### Domain-Specific Providers

```python
# Automotive
from faker.providers import automotive
fake.add_provider(automotive)
fake.license_plate()  # "ABC 1234"

# Internet
fake.ipv4()           # "192.168.1.1"
fake.url()            # "https://www.example.com"
fake.user_agent()     # "Mozilla/5.0..."

# Financial
fake.cryptocurrency()      # ('BTC', 'Bitcoin')
fake.pricetag()           # "$1,234.56"
```

## Custom Faker Providers

For domain-specific values not covered by built-in providers:

```python
from faker.providers import BaseProvider

class RetailProvider(BaseProvider):
    """Custom provider for retail domain data."""

    PRODUCT_CATEGORIES = ['Electronics', 'Clothing', 'Home & Garden', 'Sports', 'Books']
    PAYMENT_METHODS = ['Credit Card', 'Debit Card', 'PayPal', 'Apple Pay', 'Cash']
    ORDER_STATUSES = ['pending', 'processing', 'shipped', 'delivered', 'returned']

    def product_category(self):
        return self.random_element(self.PRODUCT_CATEGORIES)

    def payment_method(self):
        return self.random_element(self.PAYMENT_METHODS)

    def order_status(self):
        return self.random_element(self.ORDER_STATUSES)

    def sku(self):
        return f"SKU-{self.random_int(min=10000, max=99999)}"

# Register and use
fake.add_provider(RetailProvider)
fake.product_category()  # "Electronics"
fake.sku()               # "SKU-34567"
```

### Media Domain Provider

```python
class MediaProvider(BaseProvider):
    CONTENT_TYPES = ['movie', 'series', 'documentary', 'short']
    GENRES = ['Drama', 'Comedy', 'Action', 'Thriller', 'Sci-Fi', 'Romance', 'Horror']
    PLATFORMS = ['web', 'mobile_ios', 'mobile_android', 'smart_tv', 'tablet']

    def content_type(self):
        return self.random_element(self.CONTENT_TYPES)

    def genre(self):
        return self.random_element(self.GENRES)

    def viewing_platform(self):
        return self.random_element(self.PLATFORMS)

    def content_id(self):
        return f"CNT-{self.random_int(min=100000, max=999999)}"
```
