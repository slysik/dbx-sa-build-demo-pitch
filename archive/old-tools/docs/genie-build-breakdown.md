# Genie Space Build Breakdown — Full Session Trace

## Final Deliverable
**Retail Analytics Explorer** — Genie Space with 4 Gold tables, 15 sample questions, 8 SQL instructions, 3 text instructions, chart-oriented prompts.

---

## Phase-by-Phase Matrix

### Phase 0: Pre-Flight & Auth
| # | Action | Tool | Result | Tokens (est.) | Wall Time |
|---|--------|------|--------|---------------|-----------|
| 1 | Read justfile | `Read` | ✅ | 2K | 1s |
| 2 | Run preflight | `Bash` | ⚠️ PAT failed (SCIM) | 3K | 5s |
| 3 | Check auth via dbx-tools | `dbx_auth_check` | ✅ SP failover | 1K | 2s |
| 4 | Check cluster | `dbx_cluster_status` | TERMINATED | 0.5K | 1s |
| 5 | OAuth re-login | `Bash` | ✅ PAT restored | 1K | 3s |
| 6 | Verify PAT | `Bash` | ✅ | 0.5K | 1s |
| | **Subtotal** | **6 calls** | **1 failure** | **~8K** | **~13s** |

### Phase 1: Skill Loading & Data Exploration
| # | Action | Tool | Result | Tokens (est.) | Wall Time |
|---|--------|------|--------|---------------|-----------|
| 7 | Read Genie SKILL.md | `Read` | ✅ | 4K | 1s |
| 8 | Validate existing tables | `dbx_validate_tables` | 3 Bronze tables found | 1K | 3s |
| 9 | Read spaces.md | `Read` | ✅ | 5K | 1s |
| 10 | Read conversation.md | `Read` | ✅ | 4K | 1s |
| 11 | DESCRIBE bronze_stores | `dbx_sql` | ✅ 5 cols | 1K | 2s |
| 12 | DESCRIBE bronze_products | `dbx_sql` | ✅ 5 cols | 1K | 2s |
| 13 | DESCRIBE bronze_transactions | `dbx_sql` | ✅ 18 cols | 1K | 2s |
| 14 | SELECT DISTINCT region | `dbx_sql` | 5 values | 0.5K | 2s |
| 15 | SELECT DISTINCT category | `dbx_sql` | 6 values | 0.5K | 2s |
| 16 | SELECT DISTINCT store_format | `dbx_sql` | 3 values | 0.5K | 2s |
| 17 | SELECT DISTINCT payment_method | `dbx_sql` | 4 values | 0.5K | 2s |
| 18 | SELECT MIN/MAX/COUNT aggregates | `dbx_sql` | $57.7M, 100K rows | 0.5K | 2s |
| | **Subtotal** | **12 calls** | **0 failures** | **~20K** | **~22s** |

### Phase 2: Gold Table Creation
| # | Action | Tool | Result | Tokens (est.) | Wall Time |
|---|--------|------|--------|---------------|-----------|
| 19 | CREATE gold_daily_sales | `dbx_sql` | ✅ 48,797 rows | 2K | 5s |
| 20 | CREATE gold_product_performance | `dbx_sql` | ✅ 98,730 rows | 2K | 5s |
| 21 | CREATE gold_store_performance | `dbx_sql` | ✅ 50 rows | 2K | 5s |
| 22 | CREATE gold_monthly_trends | `dbx_sql` | ✅ 804 rows | 2K | 5s |
| 23 | COMMENT ON gold_daily_sales | `dbx_sql` | ✅ | 0.5K | 1s |
| 24 | COMMENT ON gold_product_performance | `dbx_sql` | ✅ | 0.5K | 1s |
| 25 | COMMENT ON gold_store_performance | `dbx_sql` | ✅ | 0.5K | 1s |
| 26 | COMMENT ON gold_monthly_trends | `dbx_sql` | ✅ | 0.5K | 1s |
| 27 | Validate all tables | `dbx_validate_tables` | ✅ 7 tables | 1K | 3s |
| | **Subtotal** | **9 calls** | **0 failures** | **~11.5K** | **~27s** |

### Phase 3: Genie Space Creation (REST API reverse-engineering) ⚠️
| # | Action | Tool | Result | Tokens (est.) | Wall Time |
|---|--------|------|--------|---------------|-----------|
| 28 | Write payload JSON | `Bash` | ✅ | 2K | 1s |
| 29 | POST /genie/spaces | `Bash` | ❌ needs serialized_space | 2K | 3s |
| 30 | POST with serialized_space | `Bash` | ❌ display_name not in proto | 2K | 3s |
| 31 | POST with title field | `Bash` | ❌ still needs serialized_space | 2K | 3s |
| 32 | POST with data_sources.tables | `Bash` | ❌ tables not in proto | 2K | 3s |
| 33 | POST with empty space | `Bash` | ❌ version 0 not supported | 1K | 2s |
| 34 | POST with version: 2 | `Bash` | ✅ Empty space created! | 1K | 3s |
| 35 | GET space details | `Bash` | ✅ confirmed structure | 1K | 2s |
| 36 | DELETE test + try catalog_name | `Bash` | ❌ catalog_name not in Table | 2K | 3s |
| 37 | Try full_name, then identifier | `Bash` | ❌/✅ identifier works! | 2K | 3s |
| 38 | DELETE test space | `Bash` | ✅ | 0.5K | 1s |
| 39 | Create with sample_questions | `Bash` | ❌ not in GenieSpaceExport | 3K | 3s |
| 40 | Create without sample_questions | `Bash` | ❌ tables must be sorted | 3K | 3s |
| 41 | Create with sorted tables | `Bash` | ✅ Space created! | 3K | 5s |
| 42 | Try curated_questions update | `Bash` | ❌ not in proto | 2K | 3s |
| 43 | Try suggested_questions | `Bash` | ❌ not in proto | 2K | 3s |
| 44 | Try REST sample-questions | `Bash` | ❌ no such endpoint | 1K | 2s |
| | **Subtotal** | **17 calls** | **12 failures** | **~32K** | **~46s** |

### Phase 4: Permission Fixes (Round 1)
| # | Action | Tool | Result | Tokens (est.) | Wall Time |
|---|--------|------|--------|---------------|-----------|
| 45 | GRANT SELECT gold_daily_sales | `dbx_sql` | ✅ | 0.5K | 2s |
| 46 | GRANT SELECT gold_monthly_trends | `dbx_sql` | ✅ | 0.5K | 2s |
| 47 | GRANT SELECT gold_product_performance | `dbx_sql` | ✅ | 0.5K | 2s |
| 48 | GRANT SELECT gold_store_performance | `dbx_sql` | ✅ | 0.5K | 2s |
| 49 | GRANT USE SCHEMA | `dbx_sql` | ❌ no MANAGE | 0.5K | 2s |
| 50 | GRANT USE CATALOG | `dbx_sql` | ❌ no MANAGE | 0.5K | 2s |
| 51-54 | GRANT SELECT account users ×4 | `dbx_sql` | ✅ | 2K | 8s |
| | **Subtotal** | **10 calls** | **2 failures** | **~5.5K** | **~22s** |

### Phase 5: Initial Testing
| # | Action | Tool | Result | Tokens (est.) | Wall Time |
|---|--------|------|--------|---------------|-----------|
| 55 | SDK test (PAT profile) | `Bash` | ❌ permission error | 3K | 15s |
| 56 | REST start-conversation | `Bash` | ❌ parse error (PAT empty) | 2K | 5s |
| 57 | REST poll message | `Bash` | ❌ SELECT permission | 2K | 12s |
| | **Subtotal** | **3 calls** | **3 failures** | **~7K** | **~32s** |

### Phase 6: Permission Fixes (Round 2 — Ownership Transfer)
| # | Action | Tool | Result | Tokens (est.) | Wall Time |
|---|--------|------|--------|---------------|-----------|
| 58 | SHOW GRANTS gold_daily_sales | `dbx_sql` | ✅ audit | 1K | 2s |
| 59 | SELECT current_user() | `dbx_sql` | SP confirmed | 0.5K | 2s |
| 60-63 | SHOW GRANTS ×4 tables + schema + catalog | `dbx_sql` | ✅ found gap | 3K | 10s |
| 64 | ALTER TABLE OWNER gold_daily_sales | `dbx_sql` | ✅ | 0.5K | 2s |
| 65 | ALTER TABLE OWNER gold_monthly_trends | `dbx_sql` | ✅ | 0.5K | 2s |
| 66 | ALTER TABLE OWNER gold_product_performance | `dbx_sql` | ✅ | 0.5K | 2s |
| 67 | ALTER TABLE OWNER gold_store_performance | `dbx_sql` | ✅ | 0.5K | 2s |
| 68 | ALTER TABLE OWNER bronze ×3 | `dbx_sql` | ❌ already owned by user | 1.5K | 4s |
| 69 | DESCRIBE EXTENDED bronze_transactions | `dbx_sql` | ✅ confirmed ownership | 1K | 2s |
| 70 | Verify all table ownership | `dbx_sql` | ✅ all 7 = slysik@gmail.com | 1K | 2s |
| | **Subtotal** | **13 calls** | **3 failures** | **~10.5K** | **~30s** |

### Phase 7: Successful Testing
| # | Action | Tool | Result | Tokens (est.) | Wall Time |
|---|--------|------|--------|---------------|-----------|
| 71 | Test query as slysik (PAT) | `Bash` | ✅ $57.7M | 2K | 5s |
| 72 | Verify Genie Space details | `Bash` | ✅ parent_path correct | 1K | 2s |
| 73 | Test 3 questions via SDK | `Bash` | ✅ all COMPLETED | 4K | 40s |
| | **Subtotal** | **3 calls** | **0 failures** | **~7K** | **~47s** |

### Phase 8: Enhancement (Sample Questions + Instructions)
| # | Action | Tool | Result | Tokens (est.) | Wall Time |
|---|--------|------|--------|---------------|-----------|
| 74 | Explore MCP genie.py source | `Read` + `Bash` | Found data-rooms API | 6K | 5s |
| 75 | Read manager.py (genie methods) | `Read` | Found question/instruction APIs | 4K | 3s |
| 76 | Read manager.py (batch methods) | `Read` | Full API surface mapped | 4K | 3s |
| 77 | Update space metadata | `Bash` (SDK api_client.do) | ✅ | 4K | 5s |
| 78 | Add 15 sample questions (batch) | `Bash` (SDK api_client.do) | ✅ | 4K | 5s |
| 79 | Add 8 SQL instructions | `Bash` (SDK api_client.do) | ✅ all 8 | 5K | 10s |
| 80 | Add 3 text instructions | `Bash` (SDK api_client.do) | ✅ all 3 | 3K | 5s |
| 81 | Test 3 chart questions (SP) | `Bash` (SDK) | ✅ all COMPLETED | 4K | 35s |
| | **Subtotal** | **8 calls** | **0 failures** | **~34K** | **~71s** |

---

## Grand Total

| Phase | Calls | Failures | Tokens (est.) | Wall Time | Success Rate |
|-------|:-----:|:--------:|:-------------:|:---------:|:------------:|
| 0. Auth & Pre-flight | 6 | 1 | 8K | 13s | 83% |
| 1. Skill Load & Exploration | 12 | 0 | 20K | 22s | 100% |
| 2. Gold Table Creation | 9 | 0 | 11.5K | 27s | 100% |
| 3. Genie Space (REST r/e) | 17 | **12** | 32K | 46s | **29%** |
| 4. Permissions (Round 1) | 10 | 2 | 5.5K | 22s | 80% |
| 5. Initial Testing | 3 | 3 | 7K | 32s | 0% |
| 6. Permissions (Round 2) | 13 | 3 | 10.5K | 30s | 77% |
| 7. Successful Testing | 3 | 0 | 7K | 47s | 100% |
| 8. Enhancement | 8 | 0 | 34K | 71s | 100% |
| **TOTAL** | **81** | **21** | **~136K** | **~5 min 10s** | **74%** |

---

## Failure Analysis

| Failure Category | Count | Root Cause | Avoidable With |
|---|:---:|---|---|
| **Proto format discovery** | 8 | Undocumented `serialized_space` fields | MCP `create_or_update_genie` |
| **Proto feature gaps** | 4 | sample_questions not in export proto | MCP (uses `/api/2.0/data-rooms/` API) |
| **SCIM auth deactivation** | 4 | Personal MS account → SCIM `active: false` | SP-owned space or org account |
| **Permission denied** | 3 | SP-created tables, user lacks SELECT | CREATE tables as user, or pre-grant |
| **CLI/SDK misuse** | 2 | GRANT USE SCHEMA needs MANAGE | Schema owner should run grants |
| **TOTAL** | **21** | | |

### What MCP Would Have Eliminated

| Failures | Count | MCP Solution |
|---|:---:|---|
| Proto format discovery (8) | → 0 | `create_or_update_genie(table_identifiers=[...])` |
| Proto feature gaps (4) | → 0 | Handles sample_questions + sorted tables internally |
| **Total eliminated** | **12 of 21** | **57% of all failures** |

### What MCP Would NOT Have Fixed

| Failures | Count | Still Needed |
|---|:---:|---|
| SCIM auth (4) | 4 | `databricks auth login -p slysik-oauth` |
| Permission denied (3) | 3 | `ALTER TABLE OWNER` or pre-grant |
| CLI/SDK misuse (2) | 2 | Different approach to grants |

---

## Hypothetical MCP Build Path

| Phase | Calls | Failures | Tokens (est.) | Wall Time |
|-------|:-----:|:--------:|:-------------:|:---------:|
| 0. Auth & Pre-flight | 3 | 0 | 4K | 5s |
| 1. Exploration | 2 | 0 | 6K | 5s |
| 2. Gold Tables | 9 | 0 | 11.5K | 27s |
| 3. Genie Space | **1** | **0** | **3K** | **5s** |
| 4. Permissions | 4 | 0 | 2K | 8s |
| 5. Testing | 3 | 0 | 4K | 35s |
| 6. Enhancement | 0 | 0 | 0K | 0s |
| **TOTAL** | **22** | **0** | **~30.5K** | **~1 min 25s** |

*Phase 6 is 0 because MCP `create_or_update_genie` handles sample questions in the initial call.*

---

## Comparison Summary

| Metric | Actual (dbx-tools) | Hypothetical (MCP) | Savings |
|--------|:---:|:---:|:---:|
| **Total calls** | 81 | 22 | **73%** |
| **Failures** | 21 | 0 | **100%** |
| **Tokens** | ~136K | ~30.5K | **78%** |
| **Wall time** | 5m 10s | 1m 25s | **73%** |
| **Genie creation calls** | 17 | 1 | **94%** |
| **Human interventions** | 2 (auth + perms screenshot) | 1 (auth only) | 50% |

---

## Optimal Hybrid Strategy

```
Phase           Tool Choice        Reason
─────────────   ─────────────────  ──────────────────────────────────
Auth check      dbx_auth_check     SP auto-failover
Exploration     MCP get_table_details   One call = schemas + stats
Gold tables     dbx_sql            Auth failover on SQL
Genie create    MCP create_or_update_genie   Abstracts proto + questions
Permissions     dbx_sql            Auth failover on GRANT
Testing         MCP ask_genie      Structured response with data
Validation      dbx_validate_tables   One-shot row counts
Cleanup         dbx_cleanup        Correct deletion order
```
