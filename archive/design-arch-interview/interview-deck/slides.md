---
theme: default
addons:
  - slidev-addon-excalidraw
title: Databricks SA — Design & Architecture
info: |
  ## Databricks Solutions Architect
  Design & Architecture Interview — FinServ Vertical
drawings:
  persist: true
  presenterOnly: false
  syncAll: true
highlighter: shiki
transition: slide-left
mdc: true
---

# Databricks SA — Design & Architecture

**Financial Services Vertical**

SteveLysik | SA Candidate

<div class="pt-12">
  <span class="px-2 py-1 rounded cursor-pointer" hover="bg-white bg-opacity-10">
    Press Space for next slide <carbon:arrow-right class="inline"/>
  </span>
</div>

<!--
Opening slide. Set the stage: FinServ focus, DW migration expertise (8 years IBM/Netezza).
Key message: I bring deep data warehousing DNA to the Databricks platform.
-->

---
transition: fade-out
---

# Medallion Architecture — FinServ ETL Pipeline

<MedallionPipeline
  title="FinServ ETL Pipeline - Medallion Architecture"
  subtitle="Databricks Lakehouse | Unity Catalog | Serverless"
  :sources="['Card Networks', 'POS Terminals', 'Foo','Mobile Wallets']"
  :bronze="{
    label: 'BRONZE',
    desc: 'Raw Streaming Ingestion',
    stats: 'transactions',
    bullets: [
      'ACID / exactly-once',
      'Partitioned by date',
      'Immutable audit trail',
      'Time travel enabled'
    ]
  }"
  :silver="{
    label: 'SILVER',
    desc: 'Cleanse / Validate / Mask',
    stats: '45,244 transactions',
    bullets: [
      'PII masked (PCI-DSS)',
      'DQ validation + quarantine',
      'Risk score enrichment',
      'MERGE INTO (upserts)'
    ]
  }"
  :gold="{
    label: 'GOLD',
    desc: 'Aggregates + ML Features',
    bullets: [
      'cardholder_features (10)',
      'merchant_risk (500)',
      'hourly_volume (20)',
      '22+ ML features/user',
      'Z-ORDER optimized'
    ]
  }"
  :ml="{
    label: 'MLflow',
    desc: 'Fraud Detection Model',
    bullets: [
      'GradientBoosting',
      'RandomForest',
      'Experiment tracking',
      'Model comparison',
      'Batch inference > Delta'
    ]
  }"
  governance="Unity Catalog — Governance | Lineage | RBAC | Column Masks | Audit"
  :serving="['Power BI / Genie AI', 'DBSQL Dashboards', 'Fraud Predictions']"
  :serverlessFixes="[
    'availableNow trigger',
    'UC Volume checkpoints',
    'tableExists() not isDelta',
    'Class balance fix',
    'MLflow registry fallback',
    'Missing F import'
  ]"
/>

<!--
Walk through the medallion architecture:
- Bronze: Raw streaming ingest (availableNow=True for serverless)
- Silver: PII masking, data validation, SCD Type 2
- Gold: Business aggregations, feature engineering
- ML: MLflow fraud detection model → model registry → serving

Key callout: This isn't just theory — I've built this end-to-end in my demo workspace.
Catalog: dbx_weg with bronze/silver/gold schemas.
-->

---

# Lakehouse Architecture — Full Stack View

<Excalidraw drawFilePath="finserv-architecture.excalidraw" class="w-full h-[420px]" :darkMode="false" />

<!--
Detailed component view:
- Unity Catalog governance layer
- Spark Structured Streaming for real-time ingest
- Delta Lake ACID transactions
- MLflow experiment tracking + model registry
- Serverless compute (SQL warehouses + jobs)

Emphasize: Single source of truth across analytics, ML, and governance.
-->

---

# Architecture Whiteboard

<Excalidraw drawFilePath="architecture-whiteboard.excalidraw" class="w-full h-[420px]" :darkMode="false" />

<!--
General-purpose architecture whiteboard.
Use this as a base to draw additional components during discussion.
Can annotate live with the drawing toolbar.
-->

---
layout: two-cols
layoutClass: gap-16
---

# Streaming Pipeline Design

```mermaid {theme: 'neutral', scale: 0.65}
graph TD
    subgraph Sources
        S1[Core Banking<br/>CDC Stream]
        S2[Card Transactions<br/>Real-time]
        S3[Market Data<br/>Vendor Feed]
    end

    subgraph Bronze["Bronze Layer"]
        B1[Raw Append-Only<br/>Delta Tables]
        B2[Schema Registry<br/>Enforcement]
    end

    subgraph Silver["Silver Layer"]
        SV1[PII Tokenization<br/>Column Masking]
        SV2[Data Quality<br/>Expectations]
        SV3[SCD Type 2<br/>History]
    end

    S1 --> B1
    S2 --> B1
    S3 --> B1
    B1 --> B2
    B2 --> SV1
    SV1 --> SV2
    SV2 --> SV3
```

::right::

## Key Design Decisions

<v-clicks>

- **availableNow=True** over processingTime (serverless-compatible)
- **Delta Lake checkpoints** in Unity Catalog Volumes
- **Schema enforcement** at Bronze boundary
- **Column-level masking** for PII in Silver
- **Expectations** for data quality gates

</v-clicks>

<!--
Streaming design rationale:
- availableNow=True: processes all available data then stops. Works with serverless jobs.
- Checkpoints in UC Volumes: portable, governed, not tied to DBFS.
- Schema enforcement early: fail fast on bad data.
- PII masking in Silver: Bronze keeps raw for audit/replay.
-->

---

# Unity Catalog Governance Model

```mermaid {theme: 'neutral', scale: 0.6}
graph TB
    subgraph Metastore["Unity Catalog Metastore"]
        subgraph Cat["dbx_weg Catalog"]
            subgraph Br["bronze schema"]
                BT1[raw_transactions]
                BT2[raw_accounts]
                BT3[raw_market_data]
            end
            subgraph Si["silver schema"]
                ST1[cleaned_transactions]
                ST2[validated_accounts]
            end
            subgraph Go["gold schema"]
                GT1[daily_risk_metrics]
                GT2[fraud_features]
                GT3[customer_360]
            end
        end
    end

    subgraph Access["Access Control"]
        R1[Data Engineers<br/>bronze + silver]
        R2[Data Scientists<br/>gold + ML]
        R3[Analysts<br/>gold read-only]
        R4[Auditors<br/>bronze read-only]
    end

    Cat --> R1
    Cat --> R2
    Cat --> R3
    Cat --> R4
```

<!--
Unity Catalog 3-level namespace: catalog.schema.table
- Role-based access: engineers get bronze/silver, scientists get gold + ML
- Auditors get read-only bronze (raw data for compliance)
- Column-level masking + row-level security available
- Data lineage tracked automatically across the pipeline
-->

---

# Teradata → Databricks Migration

<Excalidraw drawFilePath="teradata-migration-pitfalls.excalidraw" class="w-full h-[420px]" :darkMode="false" />

<!--
The 4 Silent Killers from my Teradata migration research:
1. PK/Uniqueness — Teradata enforces, Delta doesn't → use MERGE + AUTO CDC
2. Duplicate Rejection — SET tables silently dedup → add explicit dedup logic
3. Collation — Teradata case-insensitive by default → COLLATE UTF8_LCASE
4. DECIMAL Precision — double CAST pattern to avoid silent truncation

This is where my 8 years of DW experience (IBM/Netezza) becomes the differentiator.
I've lived through these exact migration pain points.
-->

---
layout: two-cols
layoutClass: gap-16
---

# Fraud Detection ML Pipeline

```mermaid {theme: 'neutral', scale: 0.6}
graph TD
    subgraph Features["Feature Engineering"]
        F1[Transaction Velocity]
        F2[Geo-anomaly Score]
        F3[Amount Deviation]
        F4[Merchant Category Risk]
    end

    subgraph Training["Model Training"]
        T1[MLflow Experiment<br/>Tracking]
        T2[Hyperparameter<br/>Tuning]
        T3[Cross-validation]
    end

    subgraph Registry["MLflow Registry"]
        M1[Champion Model]
        M2[Challenger Model]
    end

    subgraph Serving["Model Serving"]
        SE1[Real-time Endpoint]
        SE2[Batch Scoring]
    end

    F1 --> T1
    F2 --> T1
    F3 --> T1
    F4 --> T1
    T1 --> T2
    T2 --> T3
    T3 --> M1
    T3 --> M2
    M1 --> SE1
    M2 --> SE2
```

::right::

## MLflow Integration

<v-clicks>

- **Experiment**: `/Users/slysik@gmail.com/finserv-fraud-detection`
- **Champion/Challenger** pattern for safe deployments
- **Feature Store** integration with gold layer tables
- **Real-time serving** for transaction scoring
- **Batch scoring** for overnight risk reports
- **A/B testing** via traffic splitting on endpoints

</v-clicks>

<!--
ML pipeline connects directly to gold layer:
- Features computed in Gold schema (fraud_features table)
- MLflow tracks all experiments, parameters, metrics
- Model Registry manages promotion: None → Staging → Production
- Serving endpoint for real-time fraud scoring on new transactions
- Latency target: <100ms p99 for real-time scoring
-->

---
layout: center
class: text-center
---

# Live Whiteboard

<div class="text-2xl text-gray-400 mb-8">
  Click the pen icon in the toolbar to draw
</div>

<div class="border-2 border-dashed border-gray-600 rounded-lg w-[800px] h-[400px] flex items-center justify-center text-gray-500">
  Draw your architecture here
</div>

<!--
Blank canvas for ad-hoc whiteboarding during the interview.
Use the built-in drawing tools to sketch architecture on the fly.
Drawings persist — you can come back to this slide.

Good for:
- Answering "how would you design X?" questions
- Sketching alternative approaches
- Diagramming data flows for specific scenarios
-->

---
layout: center
class: text-center
---

# Live Whiteboard — Scenario 2

<div class="text-2xl text-gray-400 mb-8">
  Second blank canvas for additional scenarios
</div>

<div class="border-2 border-dashed border-gray-600 rounded-lg w-[800px] h-[400px] flex items-center justify-center text-gray-500">
  Draw your architecture here
</div>

<!--
Second whiteboard slide for a different scenario question.
Keep slides separate so you can reference both drawings later.
-->

---
layout: end
---

# Thank You

Steve Lysik — Databricks Solutions Architect

<div class="text-gray-400 mt-4">
  8 years data warehousing (IBM/Netezza) → Databricks Lakehouse
</div>
