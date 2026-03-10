# FinServ Medallion SDP — Spark Declarative Pipeline

**Scenario**: FinServ Bank Corp — Regulatory reporting acceleration + real-time risk  
**Cloud**: Azure | **Catalog**: `dbx_weg` | **Compute**: Serverless  
**Compliance**: GDPR · PCI-DSS · SOX · Basel IV

---

## Pipeline Architecture

```
SOURCES                    INGESTION              MEDALLION                      GOVERNANCE              CONSUMPTION
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Temenos (CDC Parquet)  →  Auto Loader         →  🥉 bronze_transactions      →  Unity Catalog        →  Power BI (DQ)
Fiserv  (CDC Parquet)  →  Auto Loader         →  🥉 bronze_customers         →  Column Masks         →  Genie (NL→SQL)
Bloomberg (Event Hub)  →  Structured Streaming →  🥉 bronze_market_data      →  Row Filters (GDPR)   →  MLflow (risk)
                                                                                                        
                                               →  🥈 silver_transactions (DQ gates + MCC enrichment)
                                               →  🥈 silver_customers     (SCD Type 2 via AUTO CDC)
                                                                                                        
                                               →  🥇 dim_customer         (MV — current state)
                                               →  🥇 fact_transactions    (MV — Basel IV RWA)
                                               →  🥇 mv_daily_account_exposure    (replaces SSIS)
                                               →  🥇 mv_monthly_regulatory_summary
                                               →  🥇 mv_executive_kpis    (replaces VB6 reports)
                                               →  🥇 mv_gdpr_retention_status
```

---

## File Structure

```
finserv-sdp/
├── databricks.yml                              # Bundle config — dev / prod targets
├── resources/
│   └── finserv_pipeline.yml                    # Pipeline resource definition (serverless)
└── src/transformations/
    ├── bronze/
    │   ├── bronze_transactions.sql             # Auto Loader — Temenos CDC (Parquet)
    │   ├── bronze_customers.sql                # Auto Loader — Customer CDC (Parquet)
    │   └── bronze_market_data.sql              # Event Hub — Bloomberg real-time
    ├── silver/
    │   ├── silver_transactions.sql             # DQ gates + MCC enrichment
    │   └── silver_customers.sql                # AUTO CDC → SCD Type 2
    ├── gold/
    │   ├── gold_dim_customer.sql               # MV — current-state customer dim
    │   ├── gold_fact_transactions.sql          # MV — atomic fact + Basel IV RWA
    │   └── gold_mv_regulatory.sql              # 4x MVs for regulatory reporting
    └── governance/
        └── unity_catalog_policies.sql          # Column masks + row filters (run once)
```

---

## Key Patterns Demonstrated

| Pattern | Where | Why |
|---------|-------|-----|
| **Auto Loader streaming table** | Bronze | Incremental file pickup from ADLS — replaces SSIS extract jobs |
| **Event Hub streaming** | Bronze | Bloomberg near-real-time — no Kafka cluster to manage |
| **EXPECT DQ constraints** | Silver | DROP ROW on null keys; WARN on MCC format — quarantine without blocking |
| **AUTO CDC → SCD Type 2** | Silver customers | Handles out-of-order CDC; 500 lines of MERGE → 8 lines declarative |
| **Materialized View** | Gold | Incremental aggregation — replaces SSIS nightly batch window |
| **Liquid Clustering** | Bronze, Silver, Gold | Replaces PARTITION BY + Z-ORDER; reclusters only new data |
| **Point-in-time join** | Gold fact | `__START_AT / __END_AT` prevents retroactive customer attribute changes |
| **Column masks (UC)** | Silver + Gold | PCI-DSS card masking; GDPR national_id masking — evaluated at query time |
| **Row filters (UC)** | Silver + Gold | GDPR region isolation — EU analysts see only EU records |
| **Basel IV RWA weight** | Gold fact | BIS CRE20 risk-weight bucket assignment at transaction grain |
| **GDPR retention MV** | Gold | Right-to-erasure + SOX 7-year retention eligibility tracking |

---

## Deploy Commands

```bash
# Validate bundle (check YAML + variable resolution)
databricks bundle validate

# Deploy to dev (default target)
databricks bundle deploy

# Run the pipeline
databricks bundle run finserv_medallion

# Deploy to production
databricks bundle deploy --target prod

# Tail pipeline events (useful for demos)
databricks pipelines get-update --pipeline-id <id> --update-id <uid>
```

---

## Interview Talking Points

### On SCD Type 2 (if they go deep)
> "The `SEQUENCE BY last_updated_ts` is the key clause — it means SDP can receive CDC events
> out of order and still reconstruct correct history. In classic SSIS you'd need a separate
> watermark table and complex retry logic. Here it's one clause."

### On Materialized Views replacing SSIS
> "The `mv_monthly_regulatory_summary` replaces a nightly SSIS package that takes 4 hours
> to compute. Because it's a Materialized View on a Liquid Clustered fact table, Photon
> incremental refresh runs in minutes, not hours."

### On Basel IV RWA
> "The `rwa_weight` column assigns BIS CRE20 standardised approach risk weights at the
> transaction grain. That means capital adequacy rolls up with a single SUM — no post-hoc
> lookup joins needed at report time."

### On column masks
> "The column mask function is a SQL UDF that evaluates `is_account_group_member()` at
> query time. The BI developer doesn't need to know a mask exists — they run the same
> SELECT and get hashed email. The compliance analyst runs the same SELECT and gets the
> real value. One policy, zero application changes."
