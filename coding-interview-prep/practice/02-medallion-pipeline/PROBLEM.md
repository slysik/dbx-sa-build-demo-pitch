# Practice Problem 2: Full Medallion Pipeline

## Day 2 Goal
Build a complete Bronze → Silver → Gold pipeline using SQL transforms.

## The Prompt

> "Using the banking dataset you generated, build a data pipeline that:
> 1. Lands the raw data (Bronze)
> 2. Cleans and validates (Silver)  
> 3. Creates business-ready aggregation tables (Gold)
>
> A fraud analyst and a business dashboard need to consume the Gold layer."

## Your Task

### Bronze Layer
- Tables already exist from Day 1 — but practice explaining WHY Bronze exists
- "Bronze is our raw, unmodified system of record"

### Silver Layer — Build these SQL transforms:

**silver.customers**
- Deduplicate on customer_id
- Cast date_of_birth to DATE
- Validate credit_score between 300-850 (clip or filter outliers)
- Standardize state to uppercase
- Add constraint: customer_id NOT NULL

**silver.transactions**
- Deduplicate on transaction_id (keep latest)
- Cast amount to DECIMAL(12,2)
- Filter: amount > 0 AND transaction_id IS NOT NULL
- Normalize merchant_category to UPPER/TRIM
- Handle null channels with COALESCE
- Add ingestion timestamp: `current_timestamp() AS processed_at`

### Gold Layer — Build these business tables:

**gold.customer_360** (one row per customer)
- customer_id, name, segment, credit_score
- total_transactions, total_spend, avg_transaction_amount
- days_since_last_transaction
- fraud_count, fraud_rate_pct

**gold.daily_fraud_summary** (one row per day)
- date, total_transactions, total_amount
- fraud_transactions, fraud_amount, fraud_rate
- top_fraud_category (which merchant category has most fraud that day)

**gold.transaction_features** (ML feature table, one row per transaction)
- All transaction fields PLUS:
- rolling_avg_amount_5 (last 5 txns per customer)
- txn_count_24h (velocity — transactions in last 24 hours)
- deviation_from_customer_avg (amount - customer's avg)
- is_weekend flag
- hour_of_day

## What to Practice

1. **Narrate every SQL block** — explain WHAT it does and WHY
2. **Point out Spark execution**: "This GROUP BY will shuffle..."
3. **Show results** after each layer: `SELECT * FROM ... LIMIT 10`
4. **Time yourself**: Bronze (2 min) + Silver (10 min) + Gold (15 min) = ~27 min

## Success Criteria
- [ ] 2 Silver tables with proper cleaning/validation
- [ ] 3 Gold tables with business aggregations  
- [ ] Used window functions in at least one Gold table
- [ ] Added at least one Delta constraint
- [ ] Narrated the entire build process out loud
- [ ] Completed in under 30 minutes
