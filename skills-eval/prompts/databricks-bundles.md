# Test Prompts: databricks-bundles

Real user questions extracted from:
- finserv_lakehouse multi-workspace deployments
- CLAUDE.md documented gotchas
- Production deployment failures

---

## Prompt 1: Multi-target bundle for two workspaces

Write a `databricks.yml` with a `dev` target (primary workspace) and a `prod` target (different host, different catalog/schema/warehouse). Both targets share the same pipeline and job code but use different variables.

**EXPECT:** targets, dev, prod, host, workspace, variables, warehouse_id, catalog, schema, ${var.}, deploy -t dev, deploy -t prod

---

## Prompt 2: Permission error during bundle deploy (Workspace Admin ≠ UC Grants)

I added my service principal to the workspace admins group. But `databricks bundle deploy` fails with `PERMISSION_DENIED` on schema creation. The error says the SP doesn't have `CREATE_SCHEMA` privilege. I'm an admin—why doesn't this work? What's the fix?

**EXPECT:** workspace admin, UC access, GRANT ALL PRIVILEGES ON CATALOG, catalog owner, separate grant, before deploy, CREATE_SCHEMA, permission denied

---

## Prompt 3: Running single task in orchestration job

I have a bundle job with 3 tasks: `generate_bronze` → `run_pipeline` → `train_model`. During development I want to run just `generate_bronze` to test data generation quickly. How do I run a single task via CLI?

**EXPECT:** --only, task_key, generate_bronze, databricks bundle run, not --task, single task, orchestration

---

## Prompt 4: Troubleshooting serverless notebook task in bundle

I have a notebook task in my bundle job but the job definition keeps failing. I need to configure it for serverless compute (no cluster). What fields are required vs forbidden in the notebook_task definition?

**EXPECT:** serverless, notebook_task, notebook_path, source WORKSPACE, queue enabled, no existing_cluster_id, no new_cluster, queue: enabled

---

## Prompt 5: Deploy failure with stale Terraform state

My `databricks bundle deploy` fails with a permission error on the pipeline resource, even though permissions look correct. Someone mentioned "stale Terraform state"—what is this? How do I fix it?

**EXPECT:** stale tfstate, terraform.tfstate, .databricks/bundle/dev/terraform, delete, redeploy, permission error, recover, fresh state
