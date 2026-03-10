# Complete Example: Customer, Order, and Ticket Data

## Table of Contents

- [Full Script](#full-script)
- [Execution](#execution)
- [Validation](#validation)

## Full Script

Save as `scripts/generate_data.py`:

```python
"""Generate synthetic customer, order, and ticket data."""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker
import holidays
from pyspark.sql import SparkSession

# =============================================================================
# CONFIGURATION
# =============================================================================
CATALOG = "my_catalog"
SCHEMA = "my_schema"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/raw_data"

N_CUSTOMERS = 2500
N_ORDERS = 25000
N_TICKETS = 8000

# Date range - last 6 months from today
END_DATE = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
START_DATE = END_DATE - timedelta(days=180)

# Special events (within the date range)
INCIDENT_END = END_DATE - timedelta(days=21)
INCIDENT_START = INCIDENT_END - timedelta(days=10)

# Holiday calendar
US_HOLIDAYS = holidays.US(years=[START_DATE.year, END_DATE.year])

SEED = 42

# =============================================================================
# SETUP
# =============================================================================
np.random.seed(SEED)
Faker.seed(SEED)
fake = Faker()
spark = SparkSession.builder.getOrCreate()

# =============================================================================
# CREATE INFRASTRUCTURE
# =============================================================================
print(f"Creating catalog/schema/volume if needed...")
spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.raw_data")

print(f"Generating: {N_CUSTOMERS:,} customers, {N_ORDERS:,} orders, {N_TICKETS:,} tickets")

# =============================================================================
# 1. CUSTOMERS (Master Table)
# =============================================================================
print("Generating customers...")

customers_pdf = pd.DataFrame({
    "customer_id": [f"CUST-{i:05d}" for i in range(N_CUSTOMERS)],
    "name": [fake.company() for _ in range(N_CUSTOMERS)],
    "tier": np.random.choice(['Free', 'Pro', 'Enterprise'], N_CUSTOMERS, p=[0.6, 0.3, 0.1]),
    "region": np.random.choice(['North', 'South', 'East', 'West'], N_CUSTOMERS, p=[0.4, 0.25, 0.2, 0.15]),
})

# ARR correlates with tier
customers_pdf["arr"] = customers_pdf["tier"].apply(
    lambda t: round(np.random.lognormal(11, 0.5), 2) if t == 'Enterprise'
              else round(np.random.lognormal(8, 0.6), 2) if t == 'Pro' else 0
)

# Lookups for foreign keys
customer_ids = customers_pdf["customer_id"].tolist()
customer_tier_map = dict(zip(customers_pdf["customer_id"], customers_pdf["tier"]))
tier_weights = customers_pdf["tier"].map({'Enterprise': 5.0, 'Pro': 2.0, 'Free': 1.0})
customer_weights = (tier_weights / tier_weights.sum()).tolist()

print(f"  Created {len(customers_pdf):,} customers")

# =============================================================================
# 2. ORDERS (References Customers)
# =============================================================================
print("Generating orders...")

orders_data = []
for i in range(N_ORDERS):
    cid = np.random.choice(customer_ids, p=customer_weights)
    tier = customer_tier_map[cid]
    amount = np.random.lognormal(7 if tier == 'Enterprise' else 5 if tier == 'Pro' else 3.5, 0.7)

    orders_data.append({
        "order_id": f"ORD-{i:06d}",
        "customer_id": cid,
        "amount": round(amount, 2),
        "status": np.random.choice(['completed', 'pending', 'cancelled'], p=[0.85, 0.10, 0.05]),
        "order_date": fake.date_between(start_date=START_DATE, end_date=END_DATE),
    })

orders_pdf = pd.DataFrame(orders_data)
print(f"  Created {len(orders_pdf):,} orders")

# =============================================================================
# 3. TICKETS (References Customers, with incident spike)
# =============================================================================
print("Generating tickets...")

def get_daily_volume(date, base=25):
    vol = base * (0.6 if date.weekday() >= 5 else 1.0)
    if date in US_HOLIDAYS:
        vol *= 0.3  # Even lower on holidays
    if INCIDENT_START <= date <= INCIDENT_END:
        vol *= 3.0
    return int(vol * np.random.normal(1, 0.15))

# Distribute tickets across dates
tickets_data = []
ticket_idx = 0
for day in pd.date_range(START_DATE, END_DATE):
    daily_count = get_daily_volume(day.to_pydatetime())
    is_incident = INCIDENT_START <= day.to_pydatetime() <= INCIDENT_END

    for _ in range(daily_count):
        if ticket_idx >= N_TICKETS:
            break

        cid = np.random.choice(customer_ids, p=customer_weights)
        tier = customer_tier_map[cid]

        # Category - Auth dominates during incident
        if is_incident:
            category = np.random.choice(['Auth', 'Network', 'Billing', 'Account'], p=[0.65, 0.15, 0.1, 0.1])
        else:
            category = np.random.choice(['Auth', 'Network', 'Billing', 'Account'], p=[0.25, 0.30, 0.25, 0.20])

        # Priority correlates with tier
        priority = np.random.choice(['Critical', 'High', 'Medium'], p=[0.3, 0.5, 0.2]) if tier == 'Enterprise' \
                   else np.random.choice(['Critical', 'High', 'Medium', 'Low'], p=[0.05, 0.2, 0.45, 0.3])

        # Resolution time correlates with priority
        res_scale = {'Critical': 4, 'High': 12, 'Medium': 36, 'Low': 72}
        resolution = np.random.exponential(scale=res_scale[priority])

        # CSAT degrades during incident for Auth
        if is_incident and category == 'Auth':
            csat = np.random.choice([1, 2, 3, 4, 5], p=[0.15, 0.25, 0.35, 0.2, 0.05])
        else:
            csat = 5 if resolution < 4 else (4 if resolution < 12 else np.random.choice([2, 3, 4], p=[0.2, 0.5, 0.3]))

        tickets_data.append({
            "ticket_id": f"TKT-{ticket_idx:06d}",
            "customer_id": cid,
            "category": category,
            "priority": priority,
            "resolution_hours": round(resolution, 1),
            "csat_score": csat,
            "created_at": day.strftime("%Y-%m-%d"),
        })
        ticket_idx += 1

    if ticket_idx >= N_TICKETS:
        break

tickets_pdf = pd.DataFrame(tickets_data)
print(f"  Created {len(tickets_pdf):,} tickets")

# =============================================================================
# 4. SAVE TO VOLUME
# =============================================================================
print(f"\nSaving to {VOLUME_PATH}...")

spark.createDataFrame(customers_pdf).write.mode("overwrite").parquet(f"{VOLUME_PATH}/customers")
spark.createDataFrame(orders_pdf).write.mode("overwrite").parquet(f"{VOLUME_PATH}/orders")
spark.createDataFrame(tickets_pdf).write.mode("overwrite").parquet(f"{VOLUME_PATH}/tickets")

print("Done!")

# =============================================================================
# 5. VALIDATION
# =============================================================================
print("\n=== VALIDATION ===")
print(f"Tier distribution: {customers_pdf['tier'].value_counts(normalize=True).to_dict()}")
print(f"Avg order by tier: {orders_pdf.merge(customers_pdf[['customer_id', 'tier']]).groupby('tier')['amount'].mean().to_dict()}")

incident_tickets = tickets_pdf[tickets_pdf['created_at'].between(
    INCIDENT_START.strftime("%Y-%m-%d"), INCIDENT_END.strftime("%Y-%m-%d")
)]
print(f"Incident period tickets: {len(incident_tickets):,} ({len(incident_tickets)/len(tickets_pdf)*100:.1f}%)")
print(f"Incident Auth %: {(incident_tickets['category'] == 'Auth').mean()*100:.1f}%")
```

## Execution

Execute using `run_python_file_on_databricks` tool:
- `file_path`: "scripts/generate_data.py"

If it fails, edit the file and re-run with the same `cluster_id` and `context_id`.

## Validation

After successful execution, use `get_volume_folder_details` tool to verify the generated data:
- `volume_path`: "my_catalog/my_schema/raw_data/customers"
- `format`: "parquet"
- `table_stat_level`: "SIMPLE"

This returns schema, row counts, and column statistics to confirm the data was written correctly.
