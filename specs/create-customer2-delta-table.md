# Plan: Create customer2 Delta Table

## Task Description
Create a second FinServ customer Delta table (`interview_prep.default.customer2`) with 100 rows of synthetic data. The table uses the same schema as the existing `interview_prep.default.customers` table but contains entirely different customer records. This is for Databricks coding interview practice.

## Objective
A fully populated `interview_prep.default.customer2` table with 100 rows of realistic FinServ customer data, matching the schema of `customers` but with unique names, emails, and varied distributions across account types, risk tiers, and geographies.

## Relevant Files

- `notebooks/01_Bronze_FinServ_Streaming.py` - Reference for FinServ data patterns
- `.mcp.json` - Databricks MCP server config (profile: `slysik`)

### New Files
- None — all work is done via SQL executed through the Databricks MCP server

## Existing Schema Reference

The `interview_prep.default.customers` table has this schema (customer2 must match exactly):

```sql
CREATE TABLE interview_prep.default.customer2 (
  customer_id INT,
  first_name STRING,
  last_name STRING,
  email STRING,
  phone STRING,
  date_of_birth DATE,
  ssn_last4 STRING,
  address STRING,
  city STRING,
  state STRING,
  zip_code STRING,
  account_type STRING,       -- Values: Checking, Savings, Investment, Wealth Mgmt
  credit_score INT,          -- Range: 530-850
  risk_tier STRING,          -- Values: Low, Medium, High
  branch STRING,             -- Format: CITY_CODE-Area (e.g., NYC-Manhattan)
  account_open_date DATE,
  annual_income DECIMAL(12,2),
  is_active BOOLEAN,         -- ~3% inactive
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
USING DELTA
COMMENT 'FinServ customer dimension table 2 for interview practice'
```

## Data Requirements

- **100 unique rows** with `customer_id` starting at 101 (to avoid overlap if tables are ever unioned)
- **Different names/emails** than the existing customers table
- **Similar distributions**: ~4 account types, 3 risk tiers, ~30 states, 3 inactive customers
- **Realistic FinServ data**: credit scores correlate with risk tiers, income correlates with account type (Wealth Mgmt > Investment > others)

## Team Orchestration

- You operate as the team lead and orchestrate the team to execute the plan.
- You NEVER operate directly on the codebase. You use `Task` and `Task*` tools to deploy team members.
- Communication is paramount. Use Task* Tools to coordinate.

### Team Members

- Builder
  - Name: builder-sql
  - Role: Execute SQL via Databricks MCP to create the table and insert 100 rows
  - Agent Type: builder
  - Resume: true

- Validator
  - Name: validator-data
  - Role: Verify table exists with correct schema, row count, and data quality
  - Agent Type: validator
  - Resume: false

## Step by Step Tasks

### 1. Create customer2 Delta Table
- **Task ID**: create-table
- **Depends On**: none
- **Assigned To**: builder-sql
- **Agent Type**: builder
- **Parallel**: false
- Use `mcp__databricks__execute_sql` to run the CREATE TABLE statement above
- Verify the table was created successfully (no errors)

### 2. Insert 100 Rows of FinServ Data
- **Task ID**: insert-data
- **Depends On**: create-table
- **Assigned To**: builder-sql
- **Agent Type**: builder
- **Parallel**: false
- Use `mcp__databricks__execute_sql` to INSERT 100 rows with `customer_id` 101-200
- Use different names, cities, and data than the existing customers table
- Maintain realistic distributions:
  - Account types: ~30 Checking, ~25 Savings, ~25 Investment, ~20 Wealth Mgmt
  - Risk tiers: ~50 Low, ~30 Medium, ~20 High
  - Credit scores: High (750+) for Low risk, Medium (650-749) for Medium risk, Low (<650) for High risk
  - Annual income: Wealth Mgmt ($250k+), Investment ($120k-250k), Checking/Savings ($30k-120k)
  - 3 inactive customers (is_active = false)
  - Dates: account_open_date between 2008-2023, dob between 1968-1998

### 3. Validate Table and Data Quality
- **Task ID**: validate-all
- **Depends On**: insert-data
- **Assigned To**: validator-data
- **Agent Type**: validator
- **Parallel**: false
- Run `SELECT count(*) FROM interview_prep.default.customer2` — expect 100
- Run `DESCRIBE TABLE interview_prep.default.customer2` — verify all 20 columns match schema
- Run distribution checks:
  - `SELECT account_type, count(*) FROM interview_prep.default.customer2 GROUP BY 1`
  - `SELECT risk_tier, count(*) FROM interview_prep.default.customer2 GROUP BY 1`
  - `SELECT is_active, count(*) FROM interview_prep.default.customer2 GROUP BY 1`
  - `SELECT min(customer_id), max(customer_id) FROM interview_prep.default.customer2` — expect 101, 200
- Verify no duplicate customer_ids
- Verify no NULL values in required columns

## Acceptance Criteria
- Table `interview_prep.default.customer2` exists as a Delta table
- Exactly 100 rows with customer_id 101-200
- Schema matches `interview_prep.default.customers` exactly (all 20 columns, same types)
- Realistic FinServ data distributions (account types, risk tiers, credit scores)
- No duplicate customer_ids
- No NULL values in any column
- 3 inactive customers

## Validation Commands
Execute these commands to validate the task is complete:

- `SELECT count(*) as total FROM interview_prep.default.customer2` — Should return 100
- `SELECT count(distinct customer_id) as unique_ids FROM interview_prep.default.customer2` — Should return 100
- `SELECT min(customer_id) as min_id, max(customer_id) as max_id FROM interview_prep.default.customer2` — Should return 101, 200
- `SELECT account_type, count(*) as cnt FROM interview_prep.default.customer2 GROUP BY 1 ORDER BY 1` — Should show 4 types
- `SELECT risk_tier, count(*) as cnt FROM interview_prep.default.customer2 GROUP BY 1 ORDER BY 1` — Should show 3 tiers
- `SELECT is_active, count(*) as cnt FROM interview_prep.default.customer2 GROUP BY 1` — Should show ~97 true, 3 false

## Notes
- No libraries or local files needed — all work is SQL via MCP
- customer_id starts at 101 to avoid overlap with the existing customers table (IDs 1-100)
- The Databricks MCP server uses the `slysik` profile and auto-selects a serverless warehouse
