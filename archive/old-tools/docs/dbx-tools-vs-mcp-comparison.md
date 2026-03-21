# dbx-tools vs MCP: Genie Space Build Comparison

## Task: Create Genie Space with 4 Gold Tables, 15 Sample Questions, Test 3 Queries

---

## Phase-by-Phase Breakdown

### Phase 1: Data Exploration

| Step | dbx-tools | MCP | Winner |
|------|-----------|-----|--------|
| Read skill docs | 3 file reads | 1 file read | MCP — `get_table_details` returns schemas + stats in one call |
| Inspect table schemas | 3× `dbx_sql` (DESCRIBE) | 1× `get_table_details(catalog, schema)` | **MCP** |
| Check cardinality | 4× `dbx_sql` (SELECT DISTINCT) | Included in `get_table_details` | **MCP** |
| Check data range | 1× `dbx_sql` (MIN/MAX/COUNT) | Included in `get_table_details` | **MCP** |
| **Subtotal** | **3 reads + 8 tool calls** | **1 read + 1 tool call** | **MCP 8:1** |

### Phase 2: Gold Table Creation (identical — both use SQL)

| Step | dbx-tools | MCP | Winner |
|------|-----------|-----|--------|
| CREATE TABLE ×4 | 4× `dbx_sql` | 4× `execute_sql` | Tie |
| COMMENT ON TABLE ×4 | 4× `dbx_sql` | 4× `execute_sql` | Tie |
| Validate | 1× `dbx_validate_tables` | 1× `execute_sql` (manual counts) | **dbx-tools** (one-shot) |
| **Subtotal** | **9 tool calls** | **9 tool calls** | **Tie** |

### Phase 3: Genie Space Creation ⚠️ THE BIG DIVERGENCE

| Step | dbx-tools (REST/SDK) | MCP | Winner |
|------|---------------------|-----|--------|
| Create space | 17 calls (12 failures + 5 discovery) | 1× `create_or_update_genie()` | **MCP** |
| Add sample questions | 3 calls (all failed — proto doesn't support it) | Included in create call | **MCP** |
| Delete test spaces | 2 calls | 0 | **MCP** |
| **Subtotal** | **22 tool calls, 15 failures** | **1 tool call, 0 failures** | **MCP 22:1** |

**Why dbx-tools failed here:**
- `/api/2.0/genie/spaces` requires `serialized_space` — an opaque protobuf JSON blob
- Field names are undocumented: `identifier` not `full_name`, not `table_identifier`, not `catalog_name`
- Tables must be sorted alphabetically (runtime error)
- `sample_questions` is not in the `GenieSpaceExport` proto — needs a separate API
- MCP uses `/api/2.0/data-rooms/` — a higher-level API with simple `table_identifiers: string[]`

### Phase 4: Permission Fixes

| Step | dbx-tools | MCP | Winner |
|------|-----------|-----|--------|
| GRANT SELECT ×4 | 4× `dbx_sql` | 4× `execute_sql` | Tie |
| GRANT USE SCHEMA (failed) | 2× `dbx_sql` (denied) | Same issue | Tie |
| ALTER TABLE OWNER ×4 | 4× `dbx_sql` | 4× `execute_sql` | Tie |
| **Subtotal** | **10 tool calls** | **10 tool calls** | **Tie** |

### Phase 5: Testing

| Step | dbx-tools (REST/SDK) | MCP | Winner |
|------|---------------------|-----|--------|
| Test conversation (initial fail) | 3 calls (auth/permission debug) | 0 | **MCP** |
| Test 3 questions | 1× `Bash` (SDK script) | 3× `ask_genie()` | **MCP** (cleaner) |
| View results | Manual JSON parsing | Structured response with columns/data | **MCP** |
| **Subtotal** | **4 tool calls** | **3 tool calls** | **MCP** |

---

## Summary Scorecard

| Metric | dbx-tools (REST/SDK) | MCP | Delta |
|--------|---------------------|-----|-------|
| **Total tool calls** | **53** | **24** | MCP saves 55% |
| **Failed calls** | **17** | **0** | MCP eliminates all failures |
| **Exploration calls** | 8 | 1 | MCP 8× more efficient |
| **Genie creation calls** | 22 | 1 | MCP 22× more efficient |
| **Est. input tokens** | ~85K | ~25K | MCP saves ~70% |
| **Est. output tokens** | ~35K | ~8K | MCP saves ~77% |
| **Est. wall-clock time** | ~12 min | ~3 min | MCP 4× faster |
| **Human intervention needed** | 1 (permission fix screenshot) | 1 (same) | Tie |
| **Auth failover** | ✅ Built-in SP fallback | ❌ Single profile | **dbx-tools** |
| **Cleanup orchestration** | ✅ `dbx_cleanup` (all-in-one) | ❌ Manual deletes | **dbx-tools** |
| **Pipeline polling** | ✅ `dbx_poll_pipeline` | ❌ Not available | **dbx-tools** |
| **Notebook execution** | ✅ `dbx_run_notebook` | ❌ Not available | **dbx-tools** |
| **Schema validation** | ✅ `dbx_validate_tables` | ❌ Manual SQL counts | **dbx-tools** |

---

## Decision Matrix: When to Use Which

| Task | Best Tool | Why |
|------|-----------|-----|
| **SQL execution** | Either (tie) | Both wrap `/api/2.0/sql/statements` |
| **Genie Space CRUD** | **MCP** | Abstracts `serialized_space` proto, handles sample questions |
| **AI/BI Dashboard** | **MCP** | `create_or_update_dashboard` handles serialization |
| **Table exploration** | **MCP** | `get_table_details` = schemas + stats + cardinality in one call |
| **Vector Search** | **MCP** | Endpoint + index CRUD in dedicated tools |
| **Agent Bricks (KA/MAS)** | **MCP** | Complex multi-step provisioning abstracted |
| **Model Serving queries** | **MCP** | `query_serving_endpoint` with structured response |
| **Pipeline creation + polling** | **dbx-tools** | `dbx_poll_pipeline` — MCP has no equivalent |
| **Notebook execution** | **dbx-tools** | `dbx_run_notebook` — MCP has no equivalent |
| **Cluster management** | **dbx-tools** | `dbx_cluster_status` — MCP has no equivalent |
| **Full workspace cleanup** | **dbx-tools** | `dbx_cleanup` — correct deletion order in one call |
| **Schema validation** | **dbx-tools** | `dbx_validate_tables` — one-shot row counts |
| **Auth with failover** | **dbx-tools** | Auto SP fallback on SCIM failures |
| **Lakebase management** | **MCP** | Dedicated create/branch/credential tools |
| **Volume file operations** | **MCP** | Upload/download/list files |

---

## Recommended Hybrid Configuration

```
┌─────────────────────────────────────────────────────────┐
│  ALWAYS LOAD (pi extensions)                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │ dbx-tools.ts                                      │  │
│  │  • dbx_auth_check (with SP failover)              │  │
│  │  • dbx_cluster_status                             │  │
│  │  • dbx_run_notebook                               │  │
│  │  • dbx_poll_pipeline                              │  │
│  │  • dbx_validate_tables                            │  │
│  │  • dbx_sql (with SP failover)                     │  │
│  │  • dbx_cleanup                                    │  │
│  │  • dbx_deploy_dashboard                           │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  LOAD ON-DEMAND (MCP — defer_loading: true)             │
│  ┌───────────────────────────────────────────────────┐  │
│  │ databricks MCP server                             │  │
│  │  • create_or_update_genie / ask_genie             │  │
│  │  • get_table_details (schema + stats)             │  │
│  │  • create_or_update_dashboard                     │  │
│  │  • vector search CRUD                             │  │
│  │  • agent bricks (KA / MAS)                        │  │
│  │  • model serving queries                          │  │
│  │  • lakebase management                            │  │
│  │  • volume file operations                         │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Selection Heuristic (how the agent should decide)

```
IF task involves:
  - Genie, Dashboard, Vector Search, Agent Bricks, Serving → USE MCP
  - Table schema exploration → USE MCP (get_table_details)
  - Pipeline run/poll, notebook exec, cluster ops → USE dbx-tools
  - Cleanup, validation → USE dbx-tools
  - SQL execution → USE dbx-tools (has auth failover)
  - Auth check → USE dbx-tools (has SP failover)

IF both could work:
  - Prefer MCP for CRUD on complex resources (proto/serialization)
  - Prefer dbx-tools for polling/orchestration workflows
  - Prefer dbx-tools when auth stability matters
```

### Tool Overlap (use dbx-tools to avoid duplication)

| Capability | dbx-tools | MCP | Use |
|------------|-----------|-----|-----|
| SQL execution | `dbx_sql` | `execute_sql` | **dbx-tools** (auth failover) |
| Dashboard deploy | `dbx_deploy_dashboard` | `create_or_update_dashboard` | MCP for creation, dbx-tools if auth flakes |

---

## Key Insight

**MCP excels at complex resource CRUD** (Genie, Dashboards, Vector Search, Agent Bricks) where the REST API has opaque serialization formats. It abstracts proto schemas and multi-step workflows into single calls.

**dbx-tools excels at operational workflows** (polling, cleanup, validation, auth failover) where reliability and orchestration matter more than API abstraction.

**The optimal setup is both loaded together**, with the agent choosing based on task type. The 22:1 call reduction on Genie creation alone justifies having MCP available.
