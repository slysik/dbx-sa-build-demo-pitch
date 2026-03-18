/**
 * dbx-tools — Custom Databricks tools for interview automation
 *
 * Eliminates CLI parsing brittleness by wrapping Databricks operations
 * in reliable pi tools. Handles polling, auth checks, validation, and
 * dashboard deployment in single tool calls.
 *
 * Tools:
 *   dbx_auth_check    — Verify PAT token is working
 *   dbx_cluster_status — Check cluster state (RUNNING/PENDING/TERMINATED)
 *   dbx_run_notebook   — Submit notebook and poll to completion
 *   dbx_poll_pipeline  — Start or poll SDP pipeline to completion
 *   dbx_validate_tables — Verify row counts across medallion layers
 *   dbx_sql            — Execute SQL via Statements API
 *   dbx_deploy_dashboard — Deploy + publish dashboard in one call
 *   dbx_cleanup        — Clean workspace artifacts (pipelines, jobs, dashboards, tables)
 *
 * All tools use URL query params (not --query) to avoid macOS Python 3.9 CLI bug.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";

const PRIMARY_PROFILE = "slysik";
const FALLBACK_PROFILE = "slysik-sp";
const WS_HOST = "https://adb-7405619449104571.11.azuredatabricks.net";
const DEFAULT_WAREHOUSE = "b89b264d78f9d52e";
const DEFAULT_CLUSTER = "0310-193517-r0u8giyo";

// Auth error patterns that trigger failover to SP profile
const AUTH_ERRORS = ["does not belong to workspace", "Invalid access token", "401", "403", "SCIM", "principal inactive", "Token expired"];

export default function (pi: ExtensionAPI) {

  // Track which profile is active (sticky after failover)
  let activeProfile = PRIMARY_PROFILE;

  function isAuthError(output: string): boolean {
    return AUTH_ERRORS.some(e => output.includes(e));
  }

  // ── Helper: run databricks CLI command with failover ───────────
  async function dbxExec(args: string, timeout = 30000): Promise<{ stdout: string; stderr: string; code: number }> {
    const result = await pi.exec("databricks", ["-p", activeProfile, ...args.split(/\s+/)], { timeout });
    // Failover: if primary fails with auth error, retry with SP
    if (result.code !== 0 && activeProfile === PRIMARY_PROFILE && isAuthError(result.stdout + result.stderr)) {
      activeProfile = FALLBACK_PROFILE;
      const retry = await pi.exec("databricks", ["-p", activeProfile, ...args.split(/\s+/)], { timeout });
      return { stdout: `⚡ Failover to SP profile\n${retry.stdout}`, stderr: retry.stderr, code: retry.code };
    }
    return { stdout: result.stdout, stderr: result.stderr, code: result.code };
  }

  // ── Helper: run databricks API call with failover ──────────────
  async function dbxApi(method: string, path: string, body?: object, timeout = 30000): Promise<any> {
    async function tryApi(profile: string): Promise<{ parsed: any; raw: string; err: string; code: number }> {
      const args = ["-p", profile, "api", method, path];
      if (body) {
        args.push("--json", JSON.stringify(body));
      }
      const result = await pi.exec("databricks", args, { timeout });
      try {
        return { parsed: JSON.parse(result.stdout), raw: result.stdout, err: result.stderr, code: result.code };
      } catch {
        return { parsed: null, raw: result.stdout, err: result.stderr, code: result.code || 1 };
      }
    }

    const result = await tryApi(activeProfile);
    // Failover: if primary fails with auth error, retry with SP
    if (result.parsed === null && activeProfile === PRIMARY_PROFILE && isAuthError(result.raw + result.err)) {
      activeProfile = FALLBACK_PROFILE;
      const retry = await tryApi(activeProfile);
      if (retry.parsed !== null) return retry.parsed;
      throw new Error(`API ${method} ${path} failed (after SP failover): ${retry.err || retry.raw}`);
    }
    if (result.parsed !== null) return result.parsed;
    throw new Error(`API ${method} ${path} failed: ${result.err || result.raw}`);
  }

  // ── Helper: run SQL via Statements API ─────────────────────────
  async function runSql(sql: string, warehouseId = DEFAULT_WAREHOUSE): Promise<{ state: string; data?: string[][]; columns?: any[]; error?: string }> {
    const resp = await dbxApi("post", "/api/2.0/sql/statements", {
      warehouse_id: warehouseId,
      statement: sql,
      wait_timeout: "30s",
    }, 45000);
    const state = resp?.status?.state || "UNKNOWN";
    if (state === "SUCCEEDED") {
      return {
        state,
        data: resp.result?.data_array || [],
        columns: resp.manifest?.schema?.columns || [],
      };
    }
    return {
      state,
      error: resp?.status?.error?.message || "Unknown error",
    };
  }

  // ══════════════════════════════════════════════════════════════
  // TOOL: dbx_auth_check
  // ══════════════════════════════════════════════════════════════
  pi.registerTool({
    name: "dbx_auth_check",
    label: "Databricks Auth Check",
    description: "Verify Databricks PAT token is working. Returns auth status, user, and host.",
    parameters: Type.Object({}),
    async execute() {
      // Try primary first
      const primary = await pi.exec("databricks", ["-p", PRIMARY_PROFILE, "auth", "describe"], { timeout: 10000 });
      const primaryOut = primary.stdout + primary.stderr;
      const primaryOk = primaryOut.includes("Authenticated with:") && !isAuthError(primaryOut);

      if (primaryOk) {
        activeProfile = PRIMARY_PROFILE;
        return {
          content: [{ type: "text", text: `✅ Auth OK (profile: ${PRIMARY_PROFILE})\n${primaryOut}` }],
          details: { authenticated: true, profile: PRIMARY_PROFILE, output: primaryOut },
        };
      }

      // Primary failed — try SP fallback
      const fallback = await pi.exec("databricks", ["-p", FALLBACK_PROFILE, "auth", "describe"], { timeout: 10000 });
      const fallbackOut = fallback.stdout + fallback.stderr;
      const fallbackOk = fallbackOut.includes("Authenticated with:");

      if (fallbackOk) {
        activeProfile = FALLBACK_PROFILE;
        return {
          content: [{ type: "text", text: `⚡ PAT auth failed — auto-failover to SP profile (${FALLBACK_PROFILE})\n${fallbackOut}` }],
          details: { authenticated: true, profile: FALLBACK_PROFILE, failover: true, output: fallbackOut },
        };
      }

      return {
        content: [{ type: "text", text: `❌ Auth FAILED on both profiles\nPrimary (${PRIMARY_PROFILE}):\n${primaryOut}\nFallback (${FALLBACK_PROFILE}):\n${fallbackOut}` }],
        details: { authenticated: false, output: primaryOut + "\n" + fallbackOut },
      };
    },
  });

  // ══════════════════════════════════════════════════════════════
  // TOOL: dbx_cluster_status
  // ══════════════════════════════════════════════════════════════
  pi.registerTool({
    name: "dbx_cluster_status",
    label: "Databricks Cluster Status",
    description: "Check interview cluster state. Returns RUNNING, PENDING, TERMINATED, etc.",
    parameters: Type.Object({
      cluster_id: Type.Optional(Type.String({ description: "Cluster ID (defaults to interview-cluster)" })),
    }),
    async execute(_id, params) {
      const clusterId = params.cluster_id || DEFAULT_CLUSTER;
      const resp = await dbxApi("get", `/api/2.0/clusters/get?cluster_id=${clusterId}`);
      const state = resp?.state || "UNKNOWN";
      const name = resp?.cluster_name || "?";
      return {
        content: [{ type: "text", text: `Cluster: ${name} | State: ${state}` }],
        details: { cluster_name: name, state, cluster_id: clusterId },
      };
    },
  });

  // ══════════════════════════════════════════════════════════════
  // TOOL: dbx_run_notebook
  // ══════════════════════════════════════════════════════════════
  pi.registerTool({
    name: "dbx_run_notebook",
    label: "Run Databricks Notebook",
    description: "Submit a notebook to run on a cluster and poll until completion. Returns SUCCESS or FAILED with output.",
    parameters: Type.Object({
      notebook_path: Type.String({ description: "Workspace path to notebook (e.g., /Users/slysik@gmail.com/media_lakehouse/01_generate_bronze)" }),
      cluster_id: Type.Optional(Type.String({ description: "Cluster ID (defaults to interview-cluster)" })),
      poll_interval_sec: Type.Optional(Type.Number({ description: "Poll interval in seconds (default 10)" })),
      timeout_sec: Type.Optional(Type.Number({ description: "Max wait time in seconds (default 600)" })),
    }),
    async execute(_id, params, signal, onUpdate) {
      const clusterId = params.cluster_id || DEFAULT_CLUSTER;
      const pollInterval = (params.poll_interval_sec || 10) * 1000;
      const timeoutMs = (params.timeout_sec || 600) * 1000;

      // Submit run
      const submitResp = await dbxApi("post", "/api/2.1/jobs/runs/submit", {
        run_name: "pi_notebook_run",
        existing_cluster_id: clusterId,
        notebook_task: { notebook_path: params.notebook_path },
      });
      const runId = submitResp?.run_id;
      if (!runId) {
        return {
          content: [{ type: "text", text: `❌ Failed to submit: ${JSON.stringify(submitResp)}` }],
          details: { error: "submit_failed" },
        };
      }

      onUpdate?.({ content: [{ type: "text", text: `Submitted run ${runId}, polling...` }] });

      // Poll
      const startTime = Date.now();
      while (Date.now() - startTime < timeoutMs) {
        if (signal?.aborted) {
          return { content: [{ type: "text", text: "Cancelled" }], details: { run_id: runId, state: "CANCELLED" } };
        }

        await new Promise(r => setTimeout(r, pollInterval));

        const runResp = await dbxApi("get", `/api/2.1/jobs/runs/get?run_id=${runId}`);
        const lifecycle = runResp?.state?.life_cycle_state || "?";
        const resultState = runResp?.state?.result_state || "";
        const elapsed = Math.round((Date.now() - startTime) / 1000);

        onUpdate?.({ content: [{ type: "text", text: `Run ${runId}: ${lifecycle} ${resultState} (${elapsed}s)` }] });

        if (lifecycle === "TERMINATED" || lifecycle === "INTERNAL_ERROR") {
          const ok = resultState === "SUCCESS";
          return {
            content: [{ type: "text", text: ok ? `✅ Notebook completed in ${elapsed}s` : `❌ Notebook failed: ${resultState} — ${runResp?.state?.state_message || ""}` }],
            details: { run_id: runId, state: resultState, elapsed_sec: elapsed },
          };
        }
      }

      return {
        content: [{ type: "text", text: `⏱ Timeout after ${params.timeout_sec || 600}s. Run ${runId} still ${await dbxApi("get", `/api/2.1/jobs/runs/get?run_id=${runId}`).then(r => r?.state?.life_cycle_state)}` }],
        details: { run_id: runId, state: "TIMEOUT" },
      };
    },
  });

  // ══════════════════════════════════════════════════════════════
  // TOOL: dbx_poll_pipeline
  // ══════════════════════════════════════════════════════════════
  pi.registerTool({
    name: "dbx_poll_pipeline",
    label: "Poll SDP Pipeline",
    description: "Start a full refresh on an SDP pipeline and poll until IDLE or FAILED. Pass pipeline_id or find by name.",
    parameters: Type.Object({
      pipeline_id: Type.Optional(Type.String({ description: "Pipeline ID" })),
      pipeline_name: Type.Optional(Type.String({ description: "Pipeline name (partial match)" })),
      start_refresh: Type.Optional(Type.Boolean({ description: "Start a full refresh before polling (default true)" })),
      poll_interval_sec: Type.Optional(Type.Number({ description: "Poll interval in seconds (default 15)" })),
      timeout_sec: Type.Optional(Type.Number({ description: "Max wait time in seconds (default 300)" })),
    }),
    async execute(_id, params, signal, onUpdate) {
      let pipelineId = params.pipeline_id;
      const pollInterval = (params.poll_interval_sec || 15) * 1000;
      const timeoutMs = (params.timeout_sec || 300) * 1000;

      // Find by name if no ID
      if (!pipelineId && params.pipeline_name) {
        const list = await dbxApi("get", "/api/2.0/pipelines");
        const pipelines = Array.isArray(list) ? list : (list?.statuses || []);
        const match = pipelines.find((p: any) => p.name?.includes(params.pipeline_name));
        if (match) {
          pipelineId = match.pipeline_id;
        } else {
          return { content: [{ type: "text", text: `❌ No pipeline matching "${params.pipeline_name}"` }], details: { error: "not_found" } };
        }
      }

      if (!pipelineId) {
        return { content: [{ type: "text", text: "❌ Provide pipeline_id or pipeline_name" }], details: { error: "no_id" } };
      }

      // Start refresh
      if (params.start_refresh !== false) {
        await dbxApi("post", `/api/2.0/pipelines/${pipelineId}/updates`, { full_refresh: true });
        onUpdate?.({ content: [{ type: "text", text: `Started full refresh on ${pipelineId}` }] });
      }

      // Poll
      const startTime = Date.now();
      while (Date.now() - startTime < timeoutMs) {
        if (signal?.aborted) {
          return { content: [{ type: "text", text: "Cancelled" }], details: { pipeline_id: pipelineId, state: "CANCELLED" } };
        }

        await new Promise(r => setTimeout(r, pollInterval));

        const resp = await dbxApi("get", `/api/2.0/pipelines/${pipelineId}`);
        const state = resp?.state || "?";
        const elapsed = Math.round((Date.now() - startTime) / 1000);

        onUpdate?.({ content: [{ type: "text", text: `Pipeline ${pipelineId}: ${state} (${elapsed}s)` }] });

        if (state === "IDLE") {
          return {
            content: [{ type: "text", text: `✅ Pipeline completed in ${elapsed}s` }],
            details: { pipeline_id: pipelineId, state, elapsed_sec: elapsed },
          };
        }
        if (state === "FAILED") {
          return {
            content: [{ type: "text", text: `❌ Pipeline FAILED after ${elapsed}s` }],
            details: { pipeline_id: pipelineId, state, elapsed_sec: elapsed },
          };
        }
      }

      return {
        content: [{ type: "text", text: `⏱ Timeout after ${params.timeout_sec || 300}s` }],
        details: { pipeline_id: pipelineId, state: "TIMEOUT" },
      };
    },
  });

  // ══════════════════════════════════════════════════════════════
  // TOOL: dbx_validate_tables
  // ══════════════════════════════════════════════════════════════
  pi.registerTool({
    name: "dbx_validate_tables",
    label: "Validate Medallion Tables",
    description: "Check row counts across Bronze/Silver/Gold tables in a schema. One-shot validation.",
    parameters: Type.Object({
      catalog: Type.String({ description: "Catalog name (e.g., interview)" }),
      schema: Type.String({ description: "Schema name (e.g., media)" }),
      tables: Type.Optional(Type.Array(Type.String(), { description: "Specific table names to check. If omitted, checks all tables in schema." })),
    }),
    async execute(_id, params) {
      let tables = params.tables;

      // If no tables specified, discover all
      if (!tables || tables.length === 0) {
        const result = await runSql(
          `SELECT table_name FROM ${params.catalog}.information_schema.tables WHERE table_schema = '${params.schema}' AND table_name NOT LIKE '__materialization%' ORDER BY table_name`
        );
        if (result.state !== "SUCCEEDED") {
          return { content: [{ type: "text", text: `❌ Failed to list tables: ${result.error}` }], details: { error: result.error } };
        }
        tables = (result.data || []).map(r => r[0]);
      }

      if (tables.length === 0) {
        return { content: [{ type: "text", text: `⚠ No tables found in ${params.catalog}.${params.schema}` }], details: { tables: [] } };
      }

      // Count each table
      const results: { table: string; count: string; layer: string }[] = [];
      for (const tbl of tables) {
        const layer = tbl.startsWith("bronze_") ? "bronze" : tbl.startsWith("silver_") ? "silver" : tbl.startsWith("gold_") ? "gold" : "other";
        const result = await runSql(`SELECT COUNT(*) FROM ${params.catalog}.${params.schema}.\`${tbl}\``);
        const count = result.state === "SUCCEEDED" ? (result.data?.[0]?.[0] || "?") : `ERROR: ${result.error}`;
        results.push({ table: tbl, count, layer });
      }

      // Format output
      const lines = results.map(r => `  ${r.layer.padEnd(8)} ${r.table.padEnd(40)} ${r.count}`);
      const output = `Validation: ${params.catalog}.${params.schema}\n${"─".repeat(60)}\n  Layer    Table${" ".repeat(36)}Rows\n${"─".repeat(60)}\n${lines.join("\n")}`;

      return {
        content: [{ type: "text", text: output }],
        details: { catalog: params.catalog, schema: params.schema, results },
      };
    },
  });

  // ══════════════════════════════════════════════════════════════
  // TOOL: dbx_sql
  // ══════════════════════════════════════════════════════════════
  pi.registerTool({
    name: "dbx_sql",
    label: "Run Databricks SQL",
    description: "Execute a single SQL statement via the Statements API on the serverless warehouse. Returns results or error.",
    parameters: Type.Object({
      sql: Type.String({ description: "SQL statement to execute" }),
      warehouse_id: Type.Optional(Type.String({ description: "SQL warehouse ID (defaults to serverless starter)" })),
    }),
    async execute(_id, params) {
      const result = await runSql(params.sql, params.warehouse_id || DEFAULT_WAREHOUSE);
      if (result.state === "SUCCEEDED") {
        const colNames = (result.columns || []).map((c: any) => c.name);
        const header = colNames.length > 0 ? colNames.join(" | ") + "\n" + "─".repeat(colNames.join(" | ").length) + "\n" : "";
        const rows = (result.data || []).map(r => r.join(" | ")).join("\n");
        return {
          content: [{ type: "text", text: `✅ ${(result.data || []).length} rows\n${header}${rows}` }],
          details: { state: result.state, row_count: (result.data || []).length, columns: colNames },
        };
      }
      return {
        content: [{ type: "text", text: `❌ ${result.state}: ${result.error}` }],
        details: { state: result.state, error: result.error },
      };
    },
  });

  // ══════════════════════════════════════════════════════════════
  // TOOL: dbx_deploy_dashboard
  // ══════════════════════════════════════════════════════════════
  pi.registerTool({
    name: "dbx_deploy_dashboard",
    label: "Deploy Dashboard",
    description: "Create or update a Databricks AI/BI dashboard, then publish with embed_credentials=false. Pass the dashboard JSON file path.",
    parameters: Type.Object({
      display_name: Type.String({ description: "Dashboard display name" }),
      dashboard_json_path: Type.String({ description: "Local path to dashboard JSON file" }),
      warehouse_id: Type.Optional(Type.String({ description: "SQL warehouse ID" })),
    }),
    async execute(_id, params) {
      const warehouseId = params.warehouse_id || DEFAULT_WAREHOUSE;

      // Read dashboard JSON
      const readResult = await pi.exec("cat", [params.dashboard_json_path], { timeout: 5000 });
      if (readResult.code !== 0) {
        return { content: [{ type: "text", text: `❌ Cannot read ${params.dashboard_json_path}` }], details: { error: "file_not_found" } };
      }

      let dashJson: string;
      try {
        const parsed = JSON.parse(readResult.stdout);
        dashJson = JSON.stringify(parsed);
      } catch {
        return { content: [{ type: "text", text: `❌ Invalid JSON in ${params.dashboard_json_path}` }], details: { error: "invalid_json" } };
      }

      // Check for existing dashboard with same name
      const existing = await dbxApi("get", "/api/2.0/lakeview/dashboards");
      const match = (existing?.dashboards || []).find((d: any) => d.display_name === params.display_name);

      let dashId: string;
      if (match) {
        // Update existing
        const resp = await dbxApi("patch", `/api/2.0/lakeview/dashboards/${match.dashboard_id}`, {
          display_name: params.display_name,
          serialized_dashboard: dashJson,
          warehouse_id: warehouseId,
        });
        dashId = resp?.dashboard_id || match.dashboard_id;
      } else {
        // Create new
        const resp = await dbxApi("post", "/api/2.0/lakeview/dashboards", {
          display_name: params.display_name,
          parent_path: "/Users/slysik@gmail.com",
          serialized_dashboard: dashJson,
          warehouse_id: warehouseId,
        });
        dashId = resp?.dashboard_id;
      }

      if (!dashId) {
        return { content: [{ type: "text", text: "❌ Failed to create/update dashboard" }], details: { error: "deploy_failed" } };
      }

      // Publish with embed_credentials=false (CRITICAL for this workspace)
      await dbxApi("post", `/api/2.0/lakeview/dashboards/${dashId}/published`, {
        embed_credentials: false,
        warehouse_id: warehouseId,
      });

      const url = `${WS_HOST}/sql/dashboards/${dashId}`;
      return {
        content: [{ type: "text", text: `✅ Dashboard deployed + published\n  ID: ${dashId}\n  URL: ${url}` }],
        details: { dashboard_id: dashId, url, action: match ? "updated" : "created" },
      };
    },
  });

  // ══════════════════════════════════════════════════════════════
  // TOOL: dbx_cleanup
  // ══════════════════════════════════════════════════════════════
  pi.registerTool({
    name: "dbx_cleanup",
    label: "Cleanup Workspace",
    description: "Delete old pipelines, jobs, dashboards, and orphaned tables from a schema. Use before a fresh interview run.",
    parameters: Type.Object({
      catalog: Type.String({ description: "Catalog name" }),
      schema: Type.String({ description: "Schema name" }),
      delete_pipelines: Type.Optional(Type.Boolean({ description: "Delete all SDP pipelines (default true)" })),
      delete_jobs: Type.Optional(Type.Boolean({ description: "Delete all jobs (default true)" })),
      delete_dashboards: Type.Optional(Type.Boolean({ description: "Delete all dashboards (default true)" })),
      drop_tables: Type.Optional(Type.Boolean({ description: "Drop all tables in schema (default true)" })),
    }),
    async execute(_id, params, _signal, onUpdate) {
      const log: string[] = [];
      const doPipelines = params.delete_pipelines !== false;
      const doJobs = params.delete_jobs !== false;
      const doDashboards = params.delete_dashboards !== false;
      const doTables = params.drop_tables !== false;

      // 1. Delete pipelines (FIRST — releases table ownership)
      if (doPipelines) {
        const list = await dbxApi("get", "/api/2.0/pipelines");
        const pipelines = Array.isArray(list) ? list : (list?.statuses || []);
        for (const p of pipelines) {
          try {
            await dbxApi("delete", `/api/2.0/pipelines/${p.pipeline_id}`);
            log.push(`  Deleted pipeline: ${p.name}`);
          } catch (e: any) {
            log.push(`  ⚠ Failed to delete pipeline ${p.name}: ${e.message}`);
          }
        }
        if (pipelines.length === 0) log.push("  No pipelines to delete");
        onUpdate?.({ content: [{ type: "text", text: `Pipelines: ${pipelines.length} deleted` }] });
      }

      // 2. Drop tables
      if (doTables) {
        const result = await runSql(
          `SELECT table_name, table_type FROM ${params.catalog}.information_schema.tables WHERE table_schema = '${params.schema}'`
        );
        if (result.state === "SUCCEEDED" && result.data) {
          for (const [tblName, tblType] of result.data) {
            const dropCmd = tblType === "VIEW" ? "DROP VIEW" : "DROP TABLE";
            const dropResult = await runSql(`${dropCmd} IF EXISTS ${params.catalog}.${params.schema}.\`${tblName}\``);
            log.push(`  ${dropCmd} ${tblName}: ${dropResult.state}`);
          }
          if (result.data.length === 0) log.push("  No tables to drop");
        }
        onUpdate?.({ content: [{ type: "text", text: `Tables: ${(result.data || []).length} dropped` }] });
      }

      // 3. Delete jobs
      if (doJobs) {
        const jobsResp = await dbxApi("get", "/api/2.1/jobs/list");
        const jobs = jobsResp?.jobs || [];
        for (const j of jobs) {
          try {
            await dbxApi("post", "/api/2.1/jobs/delete", { job_id: j.job_id });
            log.push(`  Deleted job: ${j.settings?.name}`);
          } catch (e: any) {
            log.push(`  ⚠ Failed to delete job: ${e.message}`);
          }
        }
        if (jobs.length === 0) log.push("  No jobs to delete");
      }

      // 4. Delete dashboards
      if (doDashboards) {
        const dashResp = await dbxApi("get", "/api/2.0/lakeview/dashboards");
        const dashboards = dashResp?.dashboards || [];
        for (const d of dashboards) {
          try {
            await dbxApi("delete", `/api/2.0/lakeview/dashboards/${d.dashboard_id}`);
            log.push(`  Deleted dashboard: ${d.display_name}`);
          } catch (e: any) {
            log.push(`  ⚠ Failed to delete dashboard: ${e.message}`);
          }
        }
        if (dashboards.length === 0) log.push("  No dashboards to delete");
      }

      return {
        content: [{ type: "text", text: `Cleanup complete:\n${log.join("\n")}` }],
        details: { log },
      };
    },
  });
}
