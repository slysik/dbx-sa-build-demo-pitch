# Retail Client — Global Sales Platform | Databricks SA Interview
*Last updated: 2026-03-02 | Interviewer: Steve Lysik*

## Discovery Status
| Category | Status | Key Facts |
|----------|--------|-----------|
| Business Problem | ✅ | Replace SQL Server on-prem + SSIS. Ingest POS REST API at 100M records/hr. |
| Current Stack | ✅ | SQL Server on-prem (OLTP/DW) + SSIS jobs + Third-party POS REST API |
| Cloud & Region | ⏳ | Assuming Azure — confirm region for data residency |
| Data Volume | ✅ | 100M records/hour from POS REST API. SQL Server volume TBD. |
| API Constraint | ✅ | 50 concurrent connections max → Spark parallelism = exactly 50 |
| Latency Needs | ⏳ | Assuming near-real-time BI (<15 min). Confirm. |
| Compliance | ⏳ | PCI-DSS assumed (POS = card data). Confirm GDPR for EU stores. |
| Consumers | ✅ | High-performance BI reporting + ML models |

---

## Proposed Architecture

```mermaid
flowchart TD

  %% ── Styles ──────────────────────────────────────────────────
  classDef srcStyle  fill:#a5d8ff,stroke:#4a9eed,stroke-width:2px,color:#1e3a5f
  classDef ingStyle  fill:#ffd8a8,stroke:#f59e0b,stroke-width:2px,color:#7c4a00
  classDef bronzeStyle fill:#ffe8cc,stroke:#b45309,stroke-width:2px,color:#7c2d12
  classDef silverStyle fill:#e8e8e8,stroke:#757575,stroke-width:2px,color:#374151
  classDef goldStyle fill:#fff3bf,stroke:#b45309,stroke-width:2px,color:#78350f
  classDef govStyle  fill:#d0bfff,stroke:#8b5cf6,stroke-width:2px,color:#3b0764
  classDef conStyle  fill:#c3fae8,stroke:#06b6d4,stroke-width:2px,color:#0e4f5c
  classDef warnStyle fill:#ffc9c9,stroke:#ef4444,stroke-width:2px,color:#7f1d1d

  %% ══════════════════════════════════════════════════════════════
  %% SOURCES
  %% ══════════════════════════════════════════════════════════════
  subgraph SRC["📥 SOURCES"]
    direction TB
    sql["🗄️ SQL Server On-Prem\nOLTP + Legacy DW\nSSIS jobs today\n(CDC via transaction log)"]
    pos["🏪 Third-Party POS\nREST API\n100M records / hour\n⚠️ 50 concurrent connections max"]
  end

  %% ══════════════════════════════════════════════════════════════
  %% NETWORK / CONNECTIVITY
  %% ══════════════════════════════════════════════════════════════
  subgraph NET["🔒 Network Path (On-Prem → Azure)"]
    direction LR
    expr["Azure ExpressRoute\n(production FinServ)\nor Site-to-Site VPN"]
    agent["LakeFlow Connect\nSelf-hosted Agent\n(deployed in DC\nHTTPS outbound only)"]
  end

  %% ══════════════════════════════════════════════════════════════
  %% INGESTION — TWO SOURCES, THREE PATHS
  %% ══════════════════════════════════════════════════════════════
  subgraph ING["⚡ INGESTION"]
    direction TB

    subgraph SQL_ING["SQL Server Path"]
      lfc["LakeFlow Connect CDC\n────────────────\nReads SQL Server\ntransaction log\nExactly-once delivery\nReplaces ALL SSIS\nextract jobs\nZero OLTP impact"]
    end

    subgraph API_ING["REST API — Path A ✅ Preferred"]
      evh["Azure Event Hubs\n────────────────\nPOS pushes events\nPartitioned by store_id\nNo connection limit\nStructured Streaming\nconsumes each partition"]
    end

    subgraph API_ING2["REST API — Path B ⚠️ Fallback (pull)"]
      poller["Parallelized Spark Poller\n────────────────\nrepartition(50) hard ceiling\n50 tasks = 50 connections\nEach task owns a store range\nDelta control table\ntracks offset per partition\nExponential backoff on 429"]
    end
  end

  %% ══════════════════════════════════════════════════════════════
  %% BRONZE
  %% ══════════════════════════════════════════════════════════════
  subgraph BRZ["🥉 BRONZE — Delta Lake on ADLS Gen2"]
    direction LR
    b1["bronze_sql_transactions\n────────────────\nRaw CDC events\nINSERT/UPDATE/DELETE\nwith LSN + commit_ts\nAppend-only\nCDF enabled"]
    b2["bronze_pos_events\n────────────────\nRaw JSON from POS\nAppend-only\n_ingest_ts\n_source_partition\nCDF enabled"]
  end

  %% ══════════════════════════════════════════════════════════════
  %% SILVER (SDP)
  %% ══════════════════════════════════════════════════════════════
  subgraph SLV["🥈 SILVER — SDP Materialized Views"]
    direction TB
    sv["silver_sales_unified\n────────────────\nMerge both Bronze sources\nDedup on transaction_id\nFlatten POS JSON\nType casting + validation\nEXPECT DQ gates\nSCD Type 2: Product · Store\nLiquid Clustered:\ntxn_date + store_id"]
  end

  %% ══════════════════════════════════════════════════════════════
  %% GOLD (SDP)
  %% ══════════════════════════════════════════════════════════════
  subgraph GLD["🥇 GOLD — Kimball Star Schema"]
    direction TB
    g1["fact_sales\n────────────────\nTransaction grain\nLiquid Clustered:\ntxn_date · store_id\nPhoton-optimised"]
    g2["dim_store · dim_product\ndim_date · dim_customer\n────────────────\nConformed dimensions\nSCD Type 2 history"]
    g3["MV: daily_regional_sales\nMV: product_performance\nMV: store_ranking\n────────────────\nPre-aggregated\nReplaces SSIS\nnightly summary jobs"]
    g4["ML Feature Tables\n────────────────\ncustomer_features\nproduct_features\nstore_features\n(different grain from BI)"]
  end

  %% ══════════════════════════════════════════════════════════════
  %% GOVERNANCE
  %% ══════════════════════════════════════════════════════════════
  subgraph GOV["🛡️ Unity Catalog Governance"]
    direction LR
    uc1["Column Masks\nPCI-DSS: card numbers\nmasked for non-compliance roles"]
    uc2["Auto Lineage\nPOS API → Bronze\n→ Silver → Gold\nfull column-level"]
    uc3["SSIS Retirement Tracker\nwhich tables migrated\nvs. still on SQL Server"]
  end

  %% ══════════════════════════════════════════════════════════════
  %% COMPUTE
  %% ══════════════════════════════════════════════════════════════
  subgraph COMP["⚙️ COMPUTE"]
    direction LR
    wh["Serverless SQL Warehouse\n+ Photon\nAuto-scale: Black Friday peak\n<2s dashboard response"]
    job["Databricks Jobs\nReplaces SQL Agent\nOrchestrates:\nLFC → SDP → ML retrain"]
    sdp["Lakeflow Pipelines (SDP)\nBronze → Silver → Gold\nPipeline compute (serverless)"]
  end

  %% ══════════════════════════════════════════════════════════════
  %% CONSUMPTION
  %% ══════════════════════════════════════════════════════════════
  subgraph CON["📊 CONSUMPTION"]
    direction TB
    pbi["Power BI\nDirect Query\nExecutive dashboards\nRegional sales KPIs"]
    genie["AI/BI Genie\nNL → SQL\nSelf-service analytics"]
    ml["MLflow\nFeature Store → Training\nModel Serving endpoint\n(demand forecast · fraud)"]
  end

  %% ══════════════════════════════════════════════════════════════
  %% MIGRATION LAYER
  %% ══════════════════════════════════════════════════════════════
  subgraph MIG["🔄 SSIS MIGRATION PATTERN"]
    direction LR
    fed["Lakehouse Federation\nQuery SQL Server in place\nduring coexistence"]
    lb["Lakebridge\nT-SQL stored proc\ntranspiler\n~80% auto-converted"]
    ctl["Delta Control Table\nSSIS retirement tracker\noffset per partition\n(Path B poller)"]
  end

  %% ══════════════════════════════════════════════════════════════
  %% FLOW
  %% ══════════════════════════════════════════════════════════════
  sql -->|"CDC via transaction log"| expr
  expr --> agent
  agent --> lfc
  lfc --> b1

  pos -->|"Path A — push events"| evh
  pos -->|"Path B — pull fallback"| poller
  evh --> b2
  poller --> b2

  b1 --> sv
  b2 --> sv
  sv --> g1
  sv --> g2
  sv --> g3
  sv --> g4

  g1 & g2 & g3 --> wh
  g4 --> ml
  wh --> pbi
  wh --> genie

  sql -.->|"coexistence queries"| fed
  sql -.->|"stored proc migration"| lb

  %% Styles
  class sql,pos srcStyle
  class lfc,evh,poller ingStyle
  class b1,b2 bronzeStyle
  class sv silverStyle
  class g1,g2,g3,g4 goldStyle
  class uc1,uc2,uc3 govStyle
  class pbi,genie,ml conStyle
  class poller warnStyle
```

---

## Key Architecture Decisions

| Decision | Choice | Rationale | Trade-off |
|----------|--------|-----------|-----------|
| **SQL Server ingestion** | LakeFlow Connect CDC | Reads transaction log — no OLTP impact, sub-minute latency, replaces all SSIS extract jobs | Requires CDC enabled on SQL Server + network path |
| **Network path** | ExpressRoute + self-hosted agent | Private connectivity — no data on public internet (PCI-DSS) | ExpressRoute provisioning lead time — start this conversation day 1 |
| **REST API — Path A** | Event Hubs → Structured Streaming | Push-based — no connection limit problem, partitioned by store_id, exactly-once | Requires POS vendor cooperation |
| **REST API — Path B** | Parallelized Spark poller | `repartition(50)` = exactly 50 connections, Delta control table tracks offsets per partition | Complex ops, vendor SLA dependent, misses deletes |
| **Silver merge** | Unified silver_sales from both sources | Single clean table downstream — BI and ML don't care which system the record came from | Dedup complexity at Silver — worth it |
| **Gold for BI** | Kimball Star + Materialized Views | BI tools optimized for star schema. MVs replace SSIS nightly summary jobs. | MV recompute cost — offset by eliminating batch window |
| **Gold for ML** | Separate feature tables | ML needs customer/product grain, not transaction grain. Isolates ML from BI schema changes. | Dual Gold maintenance |
| **SSIS retirement** | Phased — extract first, transform second | Never big-bang. LFC replaces extract immediately. SDP replaces transforms as validated. | Coexistence period adds dual-run cost |

## Open Questions
- [ ] Is SQL Server CDC enabled today? If not — can the DBA enable it?
- [ ] Can POS vendor push to Event Hubs? (determines Path A vs B)
- [ ] What's the API page size? (affects Path B math — need ≥1,000 records/call)
- [ ] Historical backfill required? How many years?
- [ ] How many SQL Server tables in scope for migration?
- [ ] GDPR in scope for EU store data?

## SSIS Retirement Map
| SSIS Component | Databricks Replacement | When |
|---|---|---|
| Extract jobs (SQL Server → staging) | LakeFlow Connect CDC | Phase 1 — immediate |
| Transform data flows | SDP Silver MV | Phase 1 — parallel run |
| Aggregate/load to DW | SDP Gold MV | Phase 2 — after Silver validated |
| SQL Agent schedules | Databricks Jobs | Phase 2 — cutover |
| T-SQL stored procedures | Lakebridge transpiler | Phase 3 — decommission |

## Steve's Talking Points
- **Lead with:** "Two sources, two ingestion patterns, one Bronze layer, one unified Silver. The architecture doesn't care where the record came from by the time it hits Silver."
- **On SSIS:** "SSIS fails silently. LakeFlow Connect emits health metrics to Azure Monitor natively — lag, throughput, connection status. You go from finding out at report time to finding out in real time."
- **On 50 connections:** "50 concurrent connections doesn't break the architecture — it defines the Spark parallelism. `repartition(50)` and a Delta control table is all you need."
- **Watch out for:** Jumping to Auto Loader before addressing the network path from on-prem SQL Server. That's the first blocker in every real migration.
