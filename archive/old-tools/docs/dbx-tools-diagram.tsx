import React, { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";

const nodeStyle: React.CSSProperties = {
  padding: 12,
  width: 220,
  borderRadius: 12,
  border: "1px solid #2563eb",
  background: "#f8fafc",
  fontSize: 12,
  lineHeight: 1.4,
  boxShadow: "0 4px 10px rgba(37, 99, 235, 0.08)",
};

const sectionStyle: React.CSSProperties = {
  ...nodeStyle,
  border: "1px solid #0ea5e9",
  background: "#f0f9ff",
};

const toolStyle: React.CSSProperties = {
  ...nodeStyle,
  border: "1px solid #16a34a",
  background: "#f0fdf4",
};

const externalStyle: React.CSSProperties = {
  ...nodeStyle,
  border: "1px solid #78350f",
  background: "#fffbeb",
};

const legendStyle: React.CSSProperties = {
  ...nodeStyle,
  border: "1px solid #475569",
  background: "#e2e8f0",
};

const DbxToolsDiagram: React.FC = () => {
  const initialNodes = useMemo(
    () => [
      {
        id: "root",
        type: "input",
        position: { x: 0, y: 0 },
        data: {
          label: (
            <div>
              <strong>dbx-tools.ts extension</strong>
              <div>Registers Databricks helper tools for interview automation</div>
            </div>
          ),
        },
        style: sectionStyle,
      },
      {
        id: "legend",
        position: { x: 320, y: -20 },
        data: {
          label: (
            <div>
              <strong>Legend</strong>
              <ul style={{ paddingLeft: 16, margin: 0 }}>
                <li>Blue: Core wiring</li>
                <li>Green: Registered pi tools</li>
                <li>Amber: External Databricks surface</li>
              </ul>
            </div>
          ),
        },
        style: legendStyle,
      },
      {
        id: "profiles",
        position: { x: -300, y: 110 },
        data: {
          label: (
            <div>
              <strong>Active profile state</strong>
              <div>PRIMARY: slysik</div>
              <div>FALLBACK: slysik-sp</div>
              <div>Sticky failover after auth errors</div>
            </div>
          ),
        },
        style: sectionStyle,
      },
      {
        id: "helpers",
        position: { x: -50, y: 110 },
        data: {
          label: (
            <div>
              <strong>Helper functions</strong>
              <ul style={{ paddingLeft: 16, margin: 0 }}>
                <li>isAuthError()</li>
                <li>dbxExec()</li>
                <li>dbxApi()</li>
                <li>runSql()</li>
              </ul>
            </div>
          ),
        },
        style: sectionStyle,
      },
      {
        id: "dbxExec",
        position: { x: -300, y: 260 },
        data: {
          label: (
            <div>
              <strong>dbxExec()</strong>
              <div>pi.exec → databricks CLI</div>
              <div>Retries with SP profile when auth fails</div>
            </div>
          ),
        },
        style: sectionStyle,
      },
      {
        id: "dbxApi",
        position: { x: -50, y: 260 },
        data: {
          label: (
            <div>
              <strong>dbxApi()</strong>
              <div>REST helper building on dbxExec</div>
              <div>Parses JSON + failover</div>
            </div>
          ),
        },
        style: sectionStyle,
      },
      {
        id: "runSql",
        position: { x: 240, y: 340 },
        data: {
          label: (
            <div>
              <strong>runSql()</strong>
              <div>Statements API</div>
              <div>Returns rows + schema</div>
            </div>
          ),
        },
        style: sectionStyle,
      },
      {
        id: "cli",
        position: { x: -300, y: 420 },
        data: {
          label: (
            <div>
              <strong>Databricks CLI</strong>
              <div>Executes auth describe, cat files, etc.</div>
            </div>
          ),
        },
        style: externalStyle,
      },
      {
        id: "api",
        position: { x: -50, y: 420 },
        data: {
          label: (
            <div>
              <strong>Databricks REST API</strong>
              <div>/jobs, /pipelines, /sql endpoints</div>
            </div>
          ),
        },
        style: externalStyle,
      },
      {
        id: "warehouse",
        position: { x: 240, y: 500 },
        data: {
          label: (
            <div>
              <strong>Serverless SQL Warehouse</strong>
              <div>ID b89b264d78f9d52e (default)</div>
            </div>
          ),
        },
        style: externalStyle,
      },
      {
        id: "tool-auth",
        position: { x: 320, y: 80 },
        data: {
          label: (
            <div>
              <strong>dbx_auth_check</strong>
              <div>Ensures PAT works, triggers failover</div>
            </div>
          ),
        },
        style: toolStyle,
      },
      {
        id: "tool-cluster",
        position: { x: 520, y: 120 },
        data: {
          label: (
            <div>
              <strong>dbx_cluster_status</strong>
              <div>GET /clusters/get</div>
            </div>
          ),
        },
        style: toolStyle,
      },
      {
        id: "tool-run-notebook",
        position: { x: 520, y: 200 },
        data: {
          label: (
            <div>
              <strong>dbx_run_notebook</strong>
              <div>Submits + polls /jobs/runs</div>
            </div>
          ),
        },
        style: toolStyle,
      },
      {
        id: "tool-pipeline",
        position: { x: 520, y: 280 },
        data: {
          label: (
            <div>
              <strong>dbx_poll_pipeline</strong>
              <div>Manages Lakeflow updates</div>
            </div>
          ),
        },
        style: toolStyle,
      },
      {
        id: "tool-validate",
        position: { x: 720, y: 180 },
        data: {
          label: (
            <div>
              <strong>dbx_validate_tables</strong>
              <div>Counts Bronze/Silver/Gold rows</div>
            </div>
          ),
        },
        style: toolStyle,
      },
      {
        id: "tool-sql",
        position: { x: 720, y: 260 },
        data: {
          label: (
            <div>
              <strong>dbx_sql</strong>
              <div>Single SQL statement executor</div>
            </div>
          ),
        },
        style: toolStyle,
      },
      {
        id: "tool-dashboard",
        position: { x: 520, y: 360 },
        data: {
          label: (
            <div>
              <strong>dbx_deploy_dashboard</strong>
              <div>Create/patch + publish Lakeview</div>
            </div>
          ),
        },
        style: toolStyle,
      },
      {
        id: "tool-cleanup",
        position: { x: 720, y: 340 },
        data: {
          label: (
            <div>
              <strong>dbx_cleanup</strong>
              <div>Orchestrates env teardown</div>
            </div>
          ),
        },
        style: toolStyle,
      },
    ],
    []
  );

  const initialEdges = useMemo(
    () => [
      { id: "root-profiles", source: "root", target: "profiles", animated: true, label: "tracks active profile" },
      { id: "root-helpers", source: "root", target: "helpers", animated: true, label: "shared helpers" },
      { id: "helpers-dbxExec", source: "helpers", target: "dbxExec", label: "wraps pi.exec" },
      { id: "helpers-dbxApi", source: "helpers", target: "dbxApi", label: "REST wrapper" },
      { id: "dbxExec-cli", source: "dbxExec", target: "cli", label: "databricks -p <profile>" },
      { id: "dbxApi-api", source: "dbxApi", target: "api", label: "api METHOD PATH" },
      { id: "dbxApi-runSql", source: "dbxApi", target: "runSql", label: "POST /sql/statements" },
      { id: "runSql-warehouse", source: "runSql", target: "warehouse", label: "executes on" },
      { id: "root-auth", source: "root", target: "tool-auth", label: "pi.registerTool" },
      { id: "root-cluster", source: "root", target: "tool-cluster" },
      { id: "root-run-notebook", source: "root", target: "tool-run-notebook" },
      { id: "root-pipeline", source: "root", target: "tool-pipeline" },
      { id: "root-validate", source: "root", target: "tool-validate" },
      { id: "root-sql", source: "root", target: "tool-sql" },
      { id: "root-dashboard", source: "root", target: "tool-dashboard" },
      { id: "root-cleanup", source: "root", target: "tool-cleanup" },
      { id: "dbxApi-cluster", source: "dbxApi", target: "tool-cluster", label: "GET /clusters/get" },
      { id: "dbxApi-run", source: "dbxApi", target: "tool-run-notebook", label: "POST /jobs" },
      { id: "dbxApi-pipeline", source: "dbxApi", target: "tool-pipeline", label: "Pipelines API" },
      { id: "runSql-validate", source: "runSql", target: "tool-validate", label: "SELECT COUNT(*)" },
      { id: "runSql-sql", source: "runSql", target: "tool-sql", label: "results" },
      { id: "dbxApi-dashboard", source: "dbxApi", target: "tool-dashboard", label: "Lakeview REST" },
      { id: "runSql-cleanup", source: "runSql", target: "tool-cleanup", label: "DROP TABLE/VIEW" },
      { id: "dbxApi-cleanup", source: "dbxApi", target: "tool-cleanup", label: "Pipelines/Jobs APIs" },
    ],
    []
  );

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div style={{ width: "100%", height: "100vh", background: "#0f172a" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        fitViewOptions={{ padding: 0.2 }}
      >
        <Background gap={16} color="#1d4ed8" />
        <MiniMap pannable zoomable />
        <Controls />
      </ReactFlow>
    </div>
  );
};

export default DbxToolsDiagram;
