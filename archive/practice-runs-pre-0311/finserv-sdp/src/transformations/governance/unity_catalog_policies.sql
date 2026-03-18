-- =============================================================================
-- UNITY CATALOG: Governance Policies
-- Column Masks + Row Filters — evaluated at query time per caller identity
-- Run once by a metastore admin after pipeline creates the tables
-- =============================================================================

-- ── 0. Roles referenced by policies ────────────────────────────────────────
-- CREATE ROLE finserv_compliance_full;    -- Full PII access (compliance team)
-- CREATE ROLE finserv_bi_developer;       -- Hashed PII (BI developers)
-- CREATE ROLE finserv_eu_analyst;         -- EU-region data only (GDPR scope)
-- (Role creation handled by IT/AAD group mapping — shown here for reference)


-- ── 1. Column Mask: card_last4 ─────────────────────────────────────────────
-- PCI-DSS DSS Requirement 3.3: Mask PAN on display
-- Compliance team sees real value; all others see '****'
CREATE OR REPLACE FUNCTION dbx_weg.silver.mask_card_last4(card_last4 STRING)
  RETURN CASE
    WHEN is_account_group_member('finserv_compliance_full') THEN card_last4
    ELSE '****'
  END;

ALTER TABLE dbx_weg.silver.silver_transactions
  ALTER COLUMN card_last4
  SET MASK dbx_weg.silver.mask_card_last4;


-- ── 2. Column Mask: national_id (GDPR Art. 9 — special category data) ──────
-- Only compliance role sees real value; BI devs get SHA-256 hash; others masked
CREATE OR REPLACE FUNCTION dbx_weg.silver.mask_national_id(national_id STRING)
  RETURN CASE
    WHEN is_account_group_member('finserv_compliance_full') THEN national_id
    WHEN is_account_group_member('finserv_bi_developer')    THEN sha2(national_id, 256)
    ELSE '***MASKED***'
  END;

ALTER TABLE dbx_weg.silver.silver_customers
  ALTER COLUMN national_id
  SET MASK dbx_weg.silver.mask_national_id;

-- Apply same mask to Gold dim (inherited via policy reference)
ALTER TABLE dbx_weg.gold.dim_customer
  ALTER COLUMN national_id
  SET MASK dbx_weg.silver.mask_national_id;


-- ── 3. Column Mask: email + phone_number ───────────────────────────────────
CREATE OR REPLACE FUNCTION dbx_weg.silver.mask_email(email STRING)
  RETURN CASE
    WHEN is_account_group_member('finserv_compliance_full') THEN email
    WHEN is_account_group_member('finserv_bi_developer')    THEN
      concat(left(email, 2), '***@', split_part(email, '@', 2))
    ELSE '***@***.***'
  END;

ALTER TABLE dbx_weg.silver.silver_customers
  ALTER COLUMN email SET MASK dbx_weg.silver.mask_email;
ALTER TABLE dbx_weg.gold.dim_customer
  ALTER COLUMN email SET MASK dbx_weg.silver.mask_email;


-- ── 4. Row Filter: GDPR Region Isolation ───────────────────────────────────
-- EU analysts can only see EU customer records (country_code in EU27)
-- Global analysts see all records (no filter)
CREATE OR REPLACE FUNCTION dbx_weg.silver.filter_by_region(country_code STRING)
  RETURN CASE
    -- Global roles: no restriction
    WHEN is_account_group_member('finserv_global_analyst') THEN TRUE
    WHEN is_account_group_member('finserv_compliance_full') THEN TRUE
    -- EU-only role: restrict to EU27 country codes
    WHEN is_account_group_member('finserv_eu_analyst') THEN country_code IN (
      'AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE',
      'GR','HU','IE','IT','LV','LT','LU','MT','NL','PL','PT',
      'RO','SK','SI','ES','SE'
    )
    -- Default deny for unrecognised roles
    ELSE FALSE
  END;

ALTER TABLE dbx_weg.silver.silver_customers
  SET ROW FILTER dbx_weg.silver.filter_by_region ON (country_code);

ALTER TABLE dbx_weg.gold.dim_customer
  SET ROW FILTER dbx_weg.silver.filter_by_region ON (country_code);

ALTER TABLE dbx_weg.gold.fact_transactions
  SET ROW FILTER dbx_weg.silver.filter_by_region ON (country_code);


-- ── 5. Verify lineage is being tracked ─────────────────────────────────────
-- Column-level lineage is automatic in Unity Catalog (no config needed)
-- Validate in UI: Catalog Explorer → table → Lineage tab
-- Or via system tables:
SELECT
  source_table_full_name,
  target_table_full_name,
  source_column_name,
  target_column_name
FROM system.access.column_lineage
WHERE target_table_full_name LIKE 'dbx_weg.gold.%'
ORDER BY event_time DESC
LIMIT 50;
