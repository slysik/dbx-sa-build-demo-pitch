# Faker Patterns for Synthetic Data Generation

## Installation (Databricks Free Edition)
```python
# Run this in the first cell of your notebook
%pip install faker
```

## Basic Setup
```python
from faker import Faker
import random
from datetime import datetime, timedelta
from pyspark.sql.types import *

fake = Faker()
Faker.seed(42)        # Reproducible results
random.seed(42)
```

## Pattern 1: Customer Table
```python
# Generate customer records
# WHY: Faker gives realistic names/addresses, we add business-relevant fields
def generate_customers(n=1000):
    customers = []
    for i in range(n):
        customers.append({
            "customer_id": f"CUST-{i+1:06d}",              # Padded ID for readability
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "address": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip_code": fake.zipcode(),
            "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=85),
            "account_open_date": fake.date_between(start_date="-10y", end_date="today"),
            "customer_segment": random.choices(                # Weighted distribution
                ["Premium", "Standard", "Basic"],              # NOT uniform — realistic!
                weights=[15, 50, 35], k=1
            )[0],
            "credit_score": int(random.gauss(700, 80)),        # Normal distribution ~700
        })
    return customers

# Create Spark DataFrame and save as Delta table
customers_data = generate_customers(1000)
df_customers = spark.createDataFrame(customers_data)
df_customers.write.format("delta").mode("overwrite").saveAsTable("customers")
```

## Pattern 2: Transactions Table (with realistic distributions)
```python
# Generate transaction records
# WHY: Real transactions are NOT uniformly distributed
#   - Most transactions are small ($5-$50)
#   - Some medium ($50-$500)
#   - Few large ($500+)
#   - Fraud is rare (~1-2%)
def generate_transactions(n=10000, num_customers=1000):
    transactions = []
    for i in range(n):
        # Amount follows log-normal distribution (realistic for purchases)
        amount = round(random.lognormvariate(3.5, 1.2), 2)   # Most $5-$100, some large
        amount = min(amount, 50000)                            # Cap at $50k

        # Fraud is RARE — only ~1.5% of transactions
        is_fraud = random.random() < 0.015

        # If fraud, amounts tend to be higher
        if is_fraud:
            amount = round(random.uniform(500, 10000), 2)

        transactions.append({
            "transaction_id": f"TXN-{i+1:08d}",
            "customer_id": f"CUST-{random.randint(1, num_customers):06d}",
            "transaction_date": fake.date_time_between(start_date="-1y", end_date="now"),
            "amount": amount,
            "merchant_name": fake.company(),
            "merchant_category": random.choices(
                ["Grocery", "Gas", "Restaurant", "Online", "Travel", "Healthcare", "Entertainment"],
                weights=[25, 15, 20, 20, 8, 7, 5], k=1
            )[0],
            "transaction_type": random.choices(
                ["purchase", "refund", "transfer", "withdrawal"],
                weights=[80, 5, 10, 5], k=1
            )[0],
            "channel": random.choices(
                ["in_store", "online", "mobile", "atm"],
                weights=[35, 30, 25, 10], k=1
            )[0],
            "is_fraud": is_fraud,
        })
    return transactions

transactions_data = generate_transactions(10000)
df_transactions = spark.createDataFrame(transactions_data)
df_transactions.write.format("delta").mode("overwrite").saveAsTable("transactions")
```

## Pattern 3: Accounts Table
```python
def generate_accounts(num_customers=1000):
    accounts = []
    account_types = ["Checking", "Savings", "Credit Card", "Mortgage", "Auto Loan"]
    for i in range(num_customers):
        # Each customer gets 1-3 accounts
        num_accounts = random.choices([1, 2, 3], weights=[50, 35, 15], k=1)[0]
        for j in range(num_accounts):
            acct_type = random.choice(account_types)
            accounts.append({
                "account_id": f"ACCT-{len(accounts)+1:06d}",
                "customer_id": f"CUST-{i+1:06d}",
                "account_type": acct_type,
                "balance": round(random.lognormvariate(8, 1.5), 2),  # Skewed balances
                "status": random.choices(
                    ["active", "inactive", "closed"],
                    weights=[85, 10, 5], k=1
                )[0],
                "opened_date": fake.date_between(start_date="-10y", end_date="today"),
            })
    return accounts

accounts_data = generate_accounts(1000)
df_accounts = spark.createDataFrame(accounts_data)
df_accounts.write.format("delta").mode("overwrite").saveAsTable("accounts")
```

## Key Things to Narrate

1. **"I'm using weighted random.choices, not uniform random"** — shows you understand real data
2. **"Fraud is only 1.5% — class imbalance is realistic"** — domain knowledge
3. **"Amounts use log-normal distribution"** — most small, few large, like real purchases
4. **"Credit scores use gaussian/normal distribution centered at 700"** — realistic
5. **"I'm seeding the random generators for reproducibility"** — best practice
