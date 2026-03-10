# Component Library

## Overview

Each component has: name, lane assignment, inclusion conditions, and Excalidraw rendering properties. Components are only placed on the diagram when their conditions are met by discovery answers.

Max 4 visible boxes per lane. Overflow is grouped into a "+N more" dashed box.

---

## Source Lane Components

| Component | Condition | Priority |
|-----------|-----------|----------|
| SAP ERP | sources contains "SAP" | 1 |
| Oracle DB | sources contains "Oracle" | 1 |
| Salesforce | sources contains "Salesforce" | 1 |
| Snowflake | sources contains "Snowflake" | 1 |
| SQL Server | sources contains "SQL Server" | 2 |
| PostgreSQL | sources contains "Postgres" | 2 |
| MongoDB | sources contains "MongoDB" | 2 |
| Kafka | sources contains "Kafka" | 1 |
| S3 / Data Lake | sources contains "S3" | 2 |
| Azure Blob | cloud includes "Azure" AND sources contains "Blob" or "ADLS" | 2 |
| Teradata EDW | sources contains "Teradata" | 1 |
| Netezza | sources contains "Netezza" | 1 |
| Mainframe | sources contains "Mainframe" | 1 |
| Workday | sources contains "Workday" | 2 |
| Bloomberg | sources contains "Bloomberg" | 2 |
| IoT Sensors | formats includes "Streaming/IoT" | 1 |
| EDI / X12 | sources contains "EDI" | 2 |
| REST APIs | sources contains "REST" or "API" | 2 |
| SFTP/File Drop | sources contains "SFTP" or "file drop" | 2 |
| Excel/CSV | sources contains "Excel" or "CSV" | 3 |

**Overflow rule:** Show top 4 by priority (lower number = higher priority), group rest as "+N more".

---

## Ingest Lane Components

| Component | Condition | Priority |
|-----------|-----------|----------|
| Structured Streaming | latency includes "Real-time" | 1 |
| Auto Loader + DLT | latency includes "Near-real-time" | 1 |
| Scheduled DLT | latency includes "Hourly" | 2 |
| COPY INTO / Jobs | latency includes "Daily batch" | 2 |
| Event Hub / Kafka Ingest | formats includes "Streaming/IoT" | 1 |
| LakeFlow Connect | use_cases includes "Legacy Migration" OR num_sources > 30 | 1 |
| Lakebridge + Federation | sources contains "teradata" or "netezza" | 1 |
| Auto Loader (files) | sources contains "S3" or "ADLS" or "SFTP" | 2 |
| Change Data Capture | sources mentions "CDC" | 2 |

---

## Transform/Process Lane Components

| Component | Condition | Priority |
|-----------|-----------|----------|
| Pipelines (SDP) | Always present | 1 |
| Bronze / Silver / Gold | Always present | 1 |
| Gold: Star Schema | modeling_pref includes "Star/Dimensional" | 1 |
| Silver: Data Vault 2.0 | modeling_pref includes "Data Vault" | 1 |
| Silver: Normalized | modeling_pref includes "Normalized/3NF" | 2 |
| Gold: Wide Fact Tables | modeling_pref includes "One Big Table" | 2 |
| Feature Engineering | use_cases includes "ML/AI Platform" | 1 |
| Photon Engine | cost_sensitivity includes "Performance-first" | 2 |
| dbt Transformations | skills includes "dbt" | 2 |
| Liquid Clustering | modeling_pref includes "Star/Dimensional" | 3 |

---

## Serve Lane Components

| Component | Condition | Priority |
|-----------|-----------|----------|
| SQL Warehouse | query_slas present OR users present | 1 |
| Serverless SQL | use_cases includes "Real-time KPIs" | 1 |
| Model Serving | use_cases includes "ML/AI Platform" | 1 |
| Feature Store | use_cases includes "ML/AI Platform" | 2 |
| Lakebase | consumers includes "Apps/APIs" | 2 |
| Streaming Tables | latency includes "Real-time" | 2 |
| Vector Search | use_cases includes "Customer 360" or "Fraud Detection" | 3 |

---

## Analysis Lane Components

| Component | Condition | Priority |
|-----------|-----------|----------|
| Power BI | bi_tools contains "Power BI" | 1 |
| Tableau | bi_tools contains "Tableau" | 1 |
| Looker | bi_tools contains "Looker" | 1 |
| AI/BI Dashboards | use_cases includes "Real-time KPIs" | 1 |
| Databricks SQL Editor | use_cases includes "Self-service Analytics" | 2 |
| ML Notebooks | use_cases includes "ML/AI Platform" | 2 |
| Databricks Apps | consumers includes "Apps/APIs" | 2 |
| Executive Dashboards | consumers includes "Executives" | 2 |
| Genie Spaces | use_cases includes "Data Democratization" | 3 |

---

## Governance Components (horizontal in bar)

| Component | Condition | Priority |
|-----------|-----------|----------|
| Unity Catalog | Always present | 1 |
| Data Lineage | Always present | 1 |
| Data Masking / PII | compliance includes "GDPR" or "CCPA" | 1 |
| Encryption | compliance includes "PCI-DSS" or "HIPAA" | 1 |
| Access Control | access_model any (label includes model type) | 1 |
| Audit Logging | compliance includes "SOX" | 2 |
| Metastore Mgmt | catalog_strategy includes "Unity Catalog" | 2 |
| Env Isolation | environments includes "Dev/Test/Prod" | 2 |
| Data Quality | Always present | 2 |
| Budget Policies | cost_sensitivity includes "Cost-first" | 3 |

**Governance overflow:** Show top 5 in the bar, remaining listed as "+N" text.
