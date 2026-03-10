# Databricks DW Reference Architecture — Content File
<!--
  HOW TO USE
  ──────────
  1. Edit any section below with customer-specific text
  2. Run: python3 scripts/rebuild_arch.py
  3. Refresh live-arch-viewer.html (⌘R) to see the HTML update
  4. Open ref-arch-customer.excalidraw for the polished leave-behind diagram

  RULES
  ──────────
  • Section headers  (## SECTION)  → map to diagram boxes — DO NOT rename them
  • Sub-keys         (### key)     → individual text blocks per box cell
  • Content          (plain text)  → what appears inside the box
  • Blank lines within a ### block are preserved as line breaks in the diagram
  • Vendor-specific icons (Power BI logo, Excel, Tableau) are intentionally absent
    from the TEMPLATE — fill in the BI REPORTING section with text during discovery

  BLANK TEMPLATE defaults are shown. Replace with customer content.
  Run rebuild_arch.py after EVERY save to regenerate both Excalidraw + HTML.
-->

---

## CUSTOMER

### name
[Customer Name]

### cloud
On-Prem  ·  Cloud  ·  SaaS

### compliance
[ GDPR  ·  PCI-DSS  ·  Basel IV  ·  SOX  ·  OCC  ·  BSA/AML ]

### timeline
[ Timeline / hard deadline ]

---

## SOURCES
<!--
  DEFAULT: 5 boxes  (covers ~95% of DW scenarios)
  ADD box: paste a new ### srcN block below the last one
  REMOVE box: delete the ### srcN block — generator re-spaces automatically
  MAX recommended: 7  (sidebar gets crowded above that)

  EXAMPLE for FinServ customer:
    ### src1
    🗄️ IBM Db2 Warehouse
    120TB · 8yr history

    ### src2
    🏦 FIS Modern Banking
    Core banking OLTP

    ### src3
    🔍 NICE Actimize
    Transaction monitoring

    ### src4
    ☁️ Salesforce FSC
    Customer profiles

    ### src5
    📋 FinCEN / OFAC
    Watchlist flat files
-->

### src1
🗄️ Data Warehouses
[ legacy EDW / cloud DW ]

### src2
🏢 On-Premises Systems
[ core banking / ERP / OLTP ]

### src3
☁️ SaaS Applications
[ CRM / HR / finance apps ]

### src4
⚡ Streaming / Events
[ Kafka / Event Hubs / CDC ]

### src5
📁 Files  ·  IoT  ·  APIs
[ flat files / devices / REST ]

<!--  ADD A 6th SOURCE: uncomment and fill in
### src6
📱 Mobile & IoT Data
[ devices / sensors / feeds ]
-->

---

## INGESTION

### batch
⏱️ Batch Ingestion
Auto Loader
[ scheduled sources ]

### cdc
🔄 CDC Ingestion
LakeFlow Connect
[ operational databases ]

### stream
🌊 Streaming Ingestion
Structured Streaming
[ event / message sources ]

---

## MEDALLION

### raw
RAW ZONE
Delta · Append-only
Source schema as-is
No transforms · Full audit trail
[ volume · retention ]

### ods
ODS / SILVER
Standardise + Cleanse
DQ rules · PII masking
SCD Type 2 via AUTO CDC
[ key transforms ]

### dims
Dimensions
SCD Type 2
Liquid Clustered
[ business key dims ]

### facts
Facts
Liquid Clustered
Photon-optimised
[ transaction grain ]

### datamarts
Datamarts
Materialized Views
Business aggregates
[ named marts ]

---

## DATA_ENGINEERING

### de
Spark Declarative Pipelines
Declarative ETL · Built-in lineage
Schema evolution auto
DQ expectations enforced
[ pipeline description ]

---

## AI_ML

### aiml
MLflow · Model Registry
Train · Score · Serve
[ use case 1 · use case 2 ]
Model outputs → Gold layer

---

## QUERY

### q5
Databricks SQL
Serverless · Photon
IWM auto-scale
High-concurrency
[ user count · SLA ]

---

## DASHBOARDS

### q6
AI/BI Dashboards
NL → chart · AI-assisted
[ BI tool — fill during discovery ]
[ user count · dashboard count ]

---

## SERVE

### q7
Delta Sharing
Downstream apps · APIs
Notebooks
[ sharing targets ]

---

## NLQ

### q8
Genie Space
Natural Language → SQL
Self-service · No SQL required
[ topics / use cases ]

---

## GOVERNANCE

### gov
Unity Catalog
──────────────────
Access control · Column lineage
Auditing · Classification
Row filters · Column masks
ABAC tag policies
[ compliance requirements ]

---

## OPEN_STORAGE

### store
Delta Lake  ·  Parquet  ·  Iceberg
──────────────────
Open formats · Vendor-neutral
ACID · Time Travel
[ cloud storage / region ]

---

## OUTPUTS

### out1
🖥️ External Apps
[ app names ]

### out2
🗄️ Operational Databases
[ downstream systems ]

### out3
🤝 Data Sharing
& Collaboration
[ sharing targets ]

### out4
👤 Business Users
[ user groups ]

### out5
📊 BI Reporting
[ fill during discovery ]
[ tool names here ]

---
<!-- END OF CONTENT FILE — run: python3 scripts/rebuild_arch.py -->
