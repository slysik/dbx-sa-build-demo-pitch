# Practice Problem 1: Synthetic Data Generation

## Day 1 Goal
Get comfortable generating realistic datasets with Faker and loading them into Delta tables.

## The Prompt (simulate what an interviewer might say)

> "We have a retail banking customer who wants to analyze their credit card transaction 
> data for fraud patterns. Can you generate a realistic dataset we can use to build 
> a pipeline?"

## Your Task

1. **Ask clarifying questions** (practice out loud!):
   - How many customers? → 1,000
   - How many transactions? → 50,000
   - Time range? → Last 12 months
   - What fraud rate? → ~1-2% realistic
   - Any specific columns? → Standard banking fields

2. **Generate these tables using Faker + Python**:
   - `customers` — 1,000 rows (customer_id, name, DOB, address, credit_score, segment)
   - `transactions` — 50,000 rows (txn_id, customer_id, amount, date, merchant, category, is_fraud)
   - `accounts` — ~1,500 rows (account_id, customer_id, type, balance, status)

3. **Save each as a Delta table** in your Databricks workspace

4. **Verify** with basic SQL:
   ```sql
   SELECT COUNT(*) FROM customers;
   SELECT merchant_category, COUNT(*), AVG(amount) FROM transactions GROUP BY merchant_category;
   SELECT is_fraud, COUNT(*), AVG(amount) FROM transactions GROUP BY is_fraud;
   ```

## What to Practice Saying Out Loud

- "I'm using log-normal distribution for amounts because real purchases cluster around small values"
- "I'm seeding the generators so this is reproducible"  
- "Fraud is only 1.5% — class imbalance is realistic"
- "I'm using DECIMAL, not FLOAT, for monetary values"
- "Let me verify the data looks right before moving on..."

## Success Criteria
- [ ] Generated all 3 tables with realistic distributions
- [ ] Saved as Delta tables in Databricks
- [ ] Verified row counts and basic distributions
- [ ] Narrated your process out loud the entire time
- [ ] Completed in under 15 minutes (interview Phase 1 budget)
