# Mock Interview 1: Healthcare Claims Pipeline

## ⏱ SET A 60-MINUTE TIMER BEFORE STARTING

## The Interviewer Prompt

> "A healthcare payer (insurance company) wants to analyze their claims data to identify 
> billing anomalies and provider fraud. They have claims data coming from multiple hospital 
> systems. Can you build a pipeline that ingests this data, cleans it, and produces an 
> analytics layer their fraud investigation team can query?"

---

## Phase 1: Discovery (0–10 min)

**Ask these clarifying questions** (practice out loud):
- What types of claims? (Medical, Pharmacy, Dental?)
- How many providers and members?
- What time range?
- What does "billing anomaly" mean to them? (Duplicate claims? Unusual amounts? Upcoding?)
- What does the fraud team want to see? (Provider-level metrics? Outlier detection?)
- Batch or streaming?

**Suggested scope** (after "hearing" answers):
- 500 providers, 10,000 members, 100,000 claims over 12 months
- Medical claims only
- Focus on: duplicate claims, unusual billing patterns, high-cost outliers
- Batch pipeline, Gold tables for analyst queries

## Phase 2: Generate Dataset (10–20 min)

Generate with Faker + Python:

**members** (10,000 rows)
- member_id, first_name, last_name, date_of_birth, gender, zip_code, plan_type

**providers** (500 rows)
- provider_id, provider_name, specialty, npi_number, city, state

**claims** (100,000 rows)
- claim_id, member_id, provider_id, service_date, claim_amount, diagnosis_code (ICD-10), 
  procedure_code (CPT), claim_status (paid/denied/pending), submitted_date, paid_date

**Realistic distributions to include**:
- Most claims $50-$500, some $500-$5000, rare $5000+
- ~5% denied claims
- ~2% duplicate claims (same member + provider + service_date + procedure)
- Some providers should have abnormally high average claim amounts (fraud signal)

## Phase 3: Build Pipeline (20–45 min)

### Bronze
- Save raw tables as Delta

### Silver
- Deduplicate claims
- Cast claim_amount to DECIMAL(10,2)
- Validate: claim_amount > 0, dates make sense (submitted_date >= service_date)
- Standardize diagnosis/procedure codes to uppercase

### Gold — Build at least 2 of these:

**gold.provider_fraud_metrics** (one row per provider)
```
- provider_id, name, specialty
- total_claims, total_billed_amount, avg_claim_amount
- denial_rate (% of claims denied)
- duplicate_claim_count
- std_dev_claim_amount (high variance = potential anomaly)
- claims_per_member (high ratio = potential churning)
- anomaly_flag (if avg_claim > 2x their specialty average)
```

**gold.claim_anomalies** (flagged suspicious claims)
```
- Claims where amount > 3 standard deviations from specialty average
- Duplicate claims (same member + provider + date + procedure)
- Claims submitted > 90 days after service date (late filing)
```

**gold.monthly_summary** (time series)
```
- month, specialty, total_claims, total_billed, avg_amount, denial_rate
```

## Phase 4: Discuss (45–60 min)

Be ready to explain:
- How would this scale to 10 million claims?
- How would you make this incremental (streaming)?
- What additional data would help catch fraud?
- How would you connect this to a dashboard?

---

## Self-Review After Completion

| Criteria | Score (1-5) | Notes |
|----------|-------------|-------|
| Clarifying questions quality | | |
| Data generation (realistic?) | | |
| Silver cleaning thoroughness | | |
| Gold business value | | |
| Narration quality | | |
| Time management | | |
| Bug recovery (if any) | | |
| Total time | _____ min | Target: < 60 min |
