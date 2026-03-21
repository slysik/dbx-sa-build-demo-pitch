# Test Prompts: spark-declarative-pipelines

Fixed validation data. Do not modify.

---

## Prompt 1: Silver transform with data quality

Build a Silver Materialized View called `finserv.banking.silver_transactions` that reads from `finserv.banking.bronze_fact_transactions`. Cast `txn_date` to DATE, `amount` to DECIMAL(18,2), drop nulls on `txn_id`, and drop rows where `amount <= 0`.

**EXPECT:** CREATE OR REFRESH MATERIALIZED VIEW, DECIMAL(18,2), WHERE txn_id IS NOT NULL, WHERE amount > 0, finserv.banking.silver_transactions

---

## Prompt 2: Schema evolution in streaming tables

I have a streaming table that reads JSON files from cloud storage. The source schema changed (new column added). My streaming table broke when I re-ran the pipeline. What do I do? Do I need to drop and recreate? Will I lose history?

**EXPECT:** schema evolution, streaming table, incompatible change, full refresh, drop and recreate, will lose, history, schema change

---

## Prompt 3: ai_summarize in pipeline vs notebook

I want to use `ai_summarize()` to create per-customer interaction summaries inside my SDP pipeline as a Materialized View. Is this valid? If not, what's the right approach?

**EXPECT:** non-deterministic, notebook, COLLECT_LIST, Delta table, not in Materialized View, plain Delta

---

## Prompt 4: Streaming table with Auto Loader from cloud storage

I'm setting up a streaming table with Auto Loader to ingest JSON files from cloud storage. I see examples of `read_files()` but I need streaming ingestion. Should I wrap it with STREAM? Where do I put the schema location? What configuration is needed?

**EXPECT:** STREAM read_files(), streaming table, cloudFiles, schemaLocation, schema location, VOLUMES, metadata, Auto Loader, streaming

---

## Prompt 5: CDC vs SCD Type 2 decision

I have a source table with changes (updates and deletes). I've heard about both `create_auto_cdc_flow()` and SCD Type 2 with `TRACK HISTORY`. What's the difference between them and when should I use each approach?

**EXPECT:** AUTO CDC, create_auto_cdc_flow, TRACK HISTORY, SCD Type 2, apply_as_deletes, sequence_by, difference, when to use, change data capture
