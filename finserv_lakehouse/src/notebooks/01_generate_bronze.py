# Databricks notebook source

# COMMAND ----------
# %md
# # Apex Banking — Bronze Data Generation
#
# | Table | Source | Rows |
# |---|---|---|
# | `bronze_dim_customers` | Core Banking System (CBS) | 200 |
# | `bronze_dim_accounts` | Core Banking System (CBS) | 500 |
# | `bronze_fact_transactions` | Core Banking System (CBS) | 10,000 |
# | `bronze_crm_interactions` | Salesforce CRM Export | 500 |
#
# **Two sources, one entity:** customer + transaction unified at Bronze.
# Pattern: `spark.range()` → broadcast join → direct Delta write. Scale by changing `N_TRANSACTIONS` only.

# COMMAND ----------
import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark.sql import DataFrame

CATALOG        = "finserv"
SCHEMA         = "banking"
BATCH_ID       = "batch_001"

N_CUSTOMERS    = 200
N_ACCOUNTS     = 500
N_TRANSACTIONS = 10_000
N_INTERACTIONS = 500

START_DATE     = "2023-09-01"
DAYS_SPAN      = 540   # 18 months of history

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"Target: {CATALOG}.{SCHEMA}")
print(f"  Customers: {N_CUSTOMERS:,} | Accounts: {N_ACCOUNTS:,} | Transactions: {N_TRANSACTIONS:,} | Interactions: {N_INTERACTIONS:,}")

# COMMAND ----------
# %md ## Source 1 — Core Banking System: Customers, Accounts, Transactions

# COMMAND ----------
# Dim: Customers — segmented retail banking population
dim_customers = (
    spark.range(N_CUSTOMERS)
    .withColumn("customer_id",
        F.concat(F.lit("CUST-"), F.lpad(F.col("id").cast("string"), 5, "0")))
    .withColumn("_r", F.rand(seed=11))
    .withColumn("segment",
        F.when(F.col("_r") < 0.60, "Retail")
         .when(F.col("_r") < 0.85, "Premium")
         .otherwise("Private"))
    .withColumn("region",
        F.when(F.col("id") % 5 == 0, "Northeast")
         .when(F.col("id") % 5 == 1, "Southeast")
         .when(F.col("id") % 5 == 2, "Midwest")
         .when(F.col("id") % 5 == 3, "West")
         .otherwise("Southwest"))
    .withColumn("_r2", F.rand(seed=22))
    .withColumn("risk_tier",
        F.when(F.col("_r2") < 0.50, "LOW")
         .when(F.col("_r2") < 0.80, "MEDIUM")
         .otherwise("HIGH"))
    .withColumn("tenure_years", (F.col("id") % 15 + 1).cast("int"))
    .withColumn("age_band",
        F.when(F.col("id") % 4 == 0, "25-35")
         .when(F.col("id") % 4 == 1, "35-50")
         .when(F.col("id") % 4 == 2, "50-65")
         .otherwise("65+"))
    .drop("id", "_r", "_r2")
)

dim_customers.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_dim_customers")
display(dim_customers.limit(5))

# COMMAND ----------
# Dim: Accounts — multiple accounts per customer (~2.5 avg)
dim_accounts = (
    spark.range(N_ACCOUNTS)
    .withColumn("account_id",
        F.concat(F.lit("ACCT-"), F.lpad(F.col("id").cast("string"), 6, "0")))
    .withColumn("customer_id",
        F.concat(F.lit("CUST-"), F.lpad((F.col("id") % N_CUSTOMERS).cast("string"), 5, "0")))
    .withColumn("_r", F.rand(seed=33))
    .withColumn("account_type",
        F.when(F.col("_r") < 0.35, "Checking")
         .when(F.col("_r") < 0.60, "Savings")
         .when(F.col("_r") < 0.78, "Credit")
         .when(F.col("_r") < 0.90, "Mortgage")
         .otherwise("Investment"))
    .withColumn("branch",
        F.when(F.col("id") % 6 == 0, "New York")
         .when(F.col("id") % 6 == 1, "Los Angeles")
         .when(F.col("id") % 6 == 2, "Chicago")
         .when(F.col("id") % 6 == 3, "Houston")
         .when(F.col("id") % 6 == 4, "Phoenix")
         .otherwise("Miami"))
    .withColumn("_r2", F.rand(seed=44))
    .withColumn("account_status",
        F.when(F.col("_r2") < 0.80, "ACTIVE")
         .when(F.col("_r2") < 0.92, "DORMANT")
         .otherwise("CLOSED"))
    .withColumn("opened_date",
        F.date_add(F.lit("2010-01-01"), (F.col("id") % 5475).cast("int")))
    .drop("id", "_r", "_r2")
)

dim_accounts.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_dim_accounts")
display(dim_accounts.limit(5))

# COMMAND ----------
# Fact: Transactions — amount varies by category, status weighted 85/10/5
fact_txns = (
    spark.range(N_TRANSACTIONS)
    .withColumn("txn_id",
        F.concat(F.lit("TXN-"), F.lpad(F.col("id").cast("string"), 8, "0")))
    .withColumn("account_id",
        F.concat(F.lit("ACCT-"), F.lpad((F.col("id") % N_ACCOUNTS).cast("string"), 6, "0")))
    .withColumn("txn_date",
        F.date_add(F.lit(START_DATE), (F.rand(seed=55) * DAYS_SPAN).cast("int")))
    .withColumn("txn_ts",
        F.to_timestamp(F.concat(
            F.col("txn_date").cast("string"), F.lit(" "),
            F.lpad((F.rand(seed=66) * 24).cast("int").cast("string"), 2, "0"), F.lit(":"),
            F.lpad((F.rand(seed=77) * 60).cast("int").cast("string"), 2, "0"), F.lit(":00"))))
    .withColumn("_r", F.rand(seed=88))
    .withColumn("txn_category",
        F.when(F.col("_r") < 0.22, "grocery")
         .when(F.col("_r") < 0.38, "utilities")
         .when(F.col("_r") < 0.53, "dining")
         .when(F.col("_r") < 0.66, "retail")
         .when(F.col("_r") < 0.76, "healthcare")
         .when(F.col("_r") < 0.87, "travel")
         .otherwise("transfer"))
    .withColumn("amount",
        F.round(
            F.when(F.col("txn_category") == "travel",     F.rand(seed=91) * 1800 + 200)
             .when(F.col("txn_category") == "healthcare",  F.rand(seed=92) * 600  + 50)
             .when(F.col("txn_category") == "transfer",    F.rand(seed=93) * 4000 + 100)
             .otherwise(                                   F.rand(seed=94) * 280  + 10), 2))
    .withColumn("_r2", F.rand(seed=99))
    .withColumn("txn_status",
        F.when(F.col("_r2") < 0.85, "COMPLETED")
         .when(F.col("_r2") < 0.93, "PENDING")
         .otherwise("FAILED"))
    .withColumn("channel",
        F.when(F.col("id") % 5 == 0, "mobile")
         .when(F.col("id") % 5 == 1, "online")
         .when(F.col("id") % 5 == 2, "card")
         .when(F.col("id") % 5 == 3, "atm")
         .otherwise("branch"))
    .drop("_r", "_r2")
)

# Broadcast join dims → single enriched Bronze table
# No shuffle: dims are tiny, sent to every executor
bronze_txns = (
    fact_txns
    .join(F.broadcast(
        dim_accounts.select("account_id", "customer_id", "account_type", "branch", "account_status")),
        "account_id", "left")
    .join(F.broadcast(
        dim_customers.select("customer_id", "segment", "region", "risk_tier")),
        "customer_id", "left")
    .withColumn("ingest_ts",    F.current_timestamp())
    .withColumn("source_system", F.lit("core_banking_system"))
    .withColumn("batch_id",      F.lit(BATCH_ID))
)

(bronze_txns
    .write.format("delta")
    .mode("overwrite").option("overwriteSchema", "true")
    .saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_fact_transactions"))

# COMMAND ----------
# %md ## Source 2 — Salesforce CRM Export: Customer Interaction Notes
# Real pattern: Auto Loader on `/Volumes/finserv/banking/crm_export/` reading daily JSON blobs.
# Here: 8 realistic note templates cycle through customers via modulo.

# COMMAND ----------
# 8 interaction templates — realistic enough for ai_classify + ai_summarize
notes = F.array(
    F.lit("Customer called to dispute unauthorized charges totaling $847 on checking account. Requested immediate investigation and potential account freeze. Very upset, mentioned closing account if unresolved within 24 hours."),
    F.lit("Customer inquired about current mortgage refinancing rates and qualification requirements. Provided information on promotional rates. Customer satisfied and will schedule appointment with loan officer next week."),
    F.lit("Customer reporting potential identity theft — multiple unrecognized transactions in past 72 hours. Initiated fraud investigation protocol and temporarily suspended card. Customer notified of next steps."),
    F.lit("Customer called to share positive feedback about the new mobile banking app. Specifically praised the bill pay feature and improved load times. Has already recommended the bank to three colleagues."),
    F.lit("Escalation from branch manager: customer waiting 6 weeks for home equity line of credit decision. Customer threatening to contact CFPB. Escalated to senior lending team for immediate resolution."),
    F.lit("Routine inquiry about small business checking account options for a new LLC. Provided product comparison and fee schedule. Scheduled appointment with business banking specialist for next Tuesday."),
    F.lit("Customer complained about ATM fees at out-of-network locations — second complaint this quarter. Customer actively comparing fee structures with competitor banks. Offered fee waiver as retention measure."),
    F.lit("Customer requesting wealth management consultation and portfolio review. Interested in diversifying beyond savings account. Positive engagement — transferred to dedicated wealth advisor.")
)

bronze_interactions = (
    spark.range(N_INTERACTIONS)
    .withColumn("interaction_id",
        F.concat(F.lit("INT-"), F.lpad(F.col("id").cast("string"), 6, "0")))
    .withColumn("customer_id",
        F.concat(F.lit("CUST-"), F.lpad((F.col("id") % N_CUSTOMERS).cast("string"), 5, "0")))
    .withColumn("interaction_date",
        F.date_add(F.lit("2024-03-01"), (F.rand(seed=111) * 365).cast("int")))
    .withColumn("channel",
        F.when(F.col("id") % 5 == 0, "phone")
         .when(F.col("id") % 5 == 1, "email")
         .when(F.col("id") % 5 == 2, "chat")
         .when(F.col("id") % 5 == 3, "branch")
         .otherwise("app"))
    .withColumn("note_text", F.element_at(notes, (F.col("id") % 8 + 1).cast("int")))
    .withColumn("ingest_ts",    F.current_timestamp())
    .withColumn("source_system", F.lit("salesforce_crm_export"))
    .withColumn("batch_id",      F.lit(BATCH_ID))
    .drop("id")
)

bronze_interactions.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_crm_interactions")
display(bronze_interactions.limit(5))

# COMMAND ----------
# %md ## Validate — one pass across all four Bronze tables

# COMMAND ----------
print("Bronze row counts:")
for tbl, expected in [
    ("bronze_dim_customers",      N_CUSTOMERS),
    ("bronze_dim_accounts",       N_ACCOUNTS),
    ("bronze_fact_transactions",  N_TRANSACTIONS),
    ("bronze_crm_interactions",   N_INTERACTIONS),
]:
    cnt = spark.table(f"{CATALOG}.{SCHEMA}.{tbl}").count()
    status = "✓" if cnt == expected else "✗"
    print(f"  {status} {tbl}: {cnt:,}")

print("\nTransaction category mix:")
(spark.table(f"{CATALOG}.{SCHEMA}.bronze_fact_transactions")
    .groupBy("txn_category", "txn_status").count()
    .orderBy("txn_category").show(20, truncate=False))
