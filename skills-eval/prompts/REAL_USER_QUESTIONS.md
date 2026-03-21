# Real User Questions — Extracted from finserv_lakehouse + CLAUDE.md

These replace synthetic prompts with actual pain points from:
- SA interview builds (finserv_lakehouse)
- Documented gotchas (CLAUDE.md)
- Multi-workspace deployments
- Production failure modes

---

## DATABRICKS-BUNDLES Real Questions

### Q1: Multi-Target Deployment (dev/prod with different configs)
**Source:** finserv_lakehouse uses separate dev and backup workspaces with different warehouse IDs, catalogs, schemas

**Real User Question:**
> "I built a bundle with a pipeline and job in my dev workspace. Now I need the same infrastructure in production, but production uses a different catalog, different warehouse, different schema. How do I structure the `databricks.yml` so dev and prod use the same resource definitions but different configs?"

**Context:** User has:
- `src/pipeline/transform.sql` (shared code)
- `src/notebooks/bronze.py` (shared code)
- `resources/pipeline.yml` (shared definition)
- But `dev_catalog.dev_schema` in dev vs `prod_catalog.prod_schema` in prod
- And different warehouse IDs: dev=`4bbaafe9538467a0`, prod=`xyz123`

**EXPECT:** 
`targets`, `variables`, `${var.catalog}`, `${var.schema}`, `${var.warehouse_id}`, `dev`, `prod`, `database lookup`, separate deployments, `-t dev`, `-t prod`

---

### Q2: Permission Errors During Deploy (Workspace Admin ≠ UC Grants)
**Source:** CLAUDE.md: "Workspace admin ≠ UC CREATE SCHEMA — SP needs GRANT ALL PRIVILEGES ON CATALOG"

**Real User Question:**
> "I added my service principal to the workspace admins group. But when I try to `databricks bundle deploy`, the pipeline creation fails with `PERMISSION_DENIED` on the schema. The error says the principal doesn't have CREATE_SCHEMA privilege. I'm an admin — why doesn't this work?"

**Context:** User:
- Added SP to admins group ✅
- Tried to deploy pipeline that creates tables in Unity Catalog schema
- Got permission error on schema creation
- Doesn't understand why workspace admin isn't enough

**EXPECT:**
`workspace admin`, `UC access`, `GRANT ALL PRIVILEGES ON CATALOG`, `catalog owner`, `separate step`, `GRANT`, `before deploy`, `catalog`, `schema`, `permission_denied`

---

### Q3: Running Single Task in Orchestration Job
**Source:** finserv_lakehouse has job with 2 tasks: `generate_bronze` → `run_pipeline`

**Real User Question:**
> "I have an orchestration job with 3 tasks: generate_bronze, run_pipeline, train_model. During development, I want to run just the generate_bronze task to test data generation without waiting for the full pipeline and training. How do I run a single task from my job via CLI?"

**Context:** User:
- Already has job defined in bundle
- Wants to iterate on Bronze generation
- Doesn't want to wait for full DAG
- Needs quick feedback loop during development

**EXPECT:**
`--only`, `task_key`, `generate_bronze`, `databricks bundle run`, `single task`, `not --task`, `job_name`, `orchestration`

---

### Q4: Troubleshooting Serverless Notebook Task in Bundle
**Source:** CLAUDE.md: "dbx_run_notebook BROKEN for serverless — use direct API with queue enabled"

**Real User Question:**
> "I have a notebook task in my bundle job that generates the Bronze data. The job definition keeps failing because I'm not sure how to configure it for serverless compute. Do I need a cluster configuration? What fields are required vs forbidden?"

**Context:** User:
- Has notebook that works fine manually
- Trying to add it as a job task in the bundle
- Doesn't have a cluster configured (serverless workspace)
- Not sure whether to use `existing_cluster_id` or `new_cluster`

**EXPECT:**
`serverless`, `notebook_task`, `notebook_path`, `source: WORKSPACE`, `queue: enabled`, `no existing_cluster_id`, `no new_cluster`, `queue enabled`, `notebook_path`, `first-try execution`

---

### Q5: Deploy Failure with Stale Terraform State
**Source:** CLAUDE.md: "Stale tfstate" — documented solution

**Real User Question:**
> "My `databricks bundle deploy` is failing with a permission error on the pipeline resource, even though the permissions look right. Someone mentioned something about 'stale Terraform state'—what's happening and how do I fix it?"

**Context:** User:
- Had successful deployment before
- Made a change to bundle YAML
- Deploy now fails with permission error
- Doesn't understand Terraform state
- Needs clear troubleshooting steps

**EXPECT:**
`stale tfstate`, `terraform.tfstate`, `.databricks/bundle/dev/terraform`, `delete`, `redeploy`, `permission error`, `fresh state`, `recover`

---

## SPARK-DECLARATIVE-PIPELINES Real Questions

### Q1: Schema Evolution in Streaming Tables
**Source:** Real pain point when Bronze schema changes but streaming table is already created

**Real User Question:**
> "I have a streaming table that reads from a cloud storage path. The source schema changed (a new column was added to the source). My streaming table broke when I re-ran the pipeline. What do I do? Do I need to drop the table and recreate it? Will I lose history?"

**Context:** User:
- Bronze streaming table ingests from cloud files
- Source data structure evolved
- Streaming table won't accept new column
- Afraid of losing data/history
- Not sure if this is expected behavior

**EXPECT:**
`schema evolution`, `streaming table`, `incompatible change`, `full refresh`, `drop and recreate`, `will lose`, `ALTER TABLE`, `schema change`

---

### Q2: AI Functions in Materialized Views vs Notebooks
**Source:** CLAUDE.md gotcha: "ai_summarize non-deterministic → INVALID in Materialized Views"

**Real User Question:**
> "I want to use `ai_summarize()` to create a per-customer summary of their interaction history in my pipeline. I tried adding it to a Materialized View definition, but it failed at pipeline deployment. Can I use AI functions in Materialized Views, or do I need a different approach?"

**Context:** User:
- Knows about ai_summarize, ai_classify, etc.
- Tried to use in MV
- Got deployment error (non-determinism)
- Doesn't know alternative pattern
- Needs guidance on when AI functions work in pipeline

**EXPECT:**
`ai_summarize`, `materialized view`, `non-deterministic`, `invalid`, `notebook`, `COLLECT_LIST`, `Delta table`, `not in MV`, `after pipeline`, `plain Delta`

---

### Q3: Bronze Generation at Scale with Proper Joins
**Source:** finserv_lakehouse pattern: spark.range() with broadcast dim joins

**Real User Question:**
> "I'm generating Bronze data with 100K transactions. I need to join dimension tables (customers, accounts) to add attributes. How should I structure this in my pipeline? Do I use broadcast joins? What's the pattern for keeping the FK columns?"

**Context:** User:
- New to spark.range() synthetic data
- Understanding medallion layer
- Wants to follow best practices
- Concerned about scale and performance
- Needs clear pattern for Bronze → Silver transition

**EXPECT:**
`spark.range()`, `broadcast`, `dimension`, `join`, `customer_id`, `account_id`, `FK columns`, `SELECT`, `explicit`, `keys aligned`

---

### Q4: Serverless Streaming Table with Auto Loader
**Source:** finserv_lakehouse uses Auto Loader for file ingestion

**Real User Question:**
> "I'm setting up a streaming table with Auto Loader to ingest JSON files from cloud storage. The SQL examples show `read_files()` but I need streaming. Should I wrap it with STREAM? Where do I put the schema location? Do I need special configuration?"

**Context:** User:
- Choosing between batch and streaming for file ingestion
- Knows Auto Loader exists
- Not sure of syntax for streaming + Auto Loader
- Concerned about schema management
- Wants to know configuration requirements

**EXPECT:**
`STREAM read_files()`, `streaming table`, `cloudFiles`, `schemaLocation`, `schema location`, `VOLUMES`, `metadata`, `Auto Loader`

---

### Q5: When to Use CDC vs SCD Type 2
**Source:** Both Auto CDC and SCD Type 2 options in pipeline

**Real User Question:**
> "I have a source table with changes (updates and deletes). Should I use `create_auto_cdc_flow()` or `TRACK HISTORY` for SCD Type 2? What's the difference and when should I use each?"

**Context:** User:
- Has source with change data
- Aware both patterns exist
- Doesn't understand the distinction
- Needs decision framework
- Concerned about correctness

**EXPECT:**
`AUTO CDC`, `create_auto_cdc_flow`, `TRACK HISTORY`, `SCD Type 2`, `apply_as_deletes`, `sequence_by`, `difference`, `when to use`, `change data capture`

---

## Metadata

**Extraction sources:**
- finserv_lakehouse actual patterns + demo guide
- CLAUDE.md documented gotchas (permissions, serverless, tfstate, schema evolution, AI functions)
- Multi-workspace deployments (dev/prod, backup workspace)
- Common interview blocking points

**Replacement strategy:**
- Bundles: Replace prompts 2, 3, 4, 5 (keep 1 as multi-target anchor)
- SDP: Replace prompts 2, 4, 5 (keep 1, 3 as high performers)
