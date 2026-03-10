/**
 * arch-diagram.ts — Databricks SA Interview Architecture Diagram Generator
 *
 * Registers a `generate_databricks_arch` tool that takes discovery answers
 * (captured live during the interview) and writes a beautiful Mermaid-powered
 * Databricks architecture document to ./live-arch.md.
 *
 * Features:
 *   - generate_databricks_arch tool: converts structured discovery into Mermaid diagrams
 *   - /watch-arch command: watches live-arch.md and pings in chat on every save
 *   - session_start hook: restores last generated diagram info
 *   - Inline renderResult with diagram preview in the Pi chat
 *
 * Run: pi -e extensions/arch-diagram.ts
 */

import type {
  ExtensionAPI,
  ExtensionContext,
  ExtensionCommandContext,
} from "@mariozechner/pi-coding-agent";
import { Type, type Static } from "@sinclair/typebox";
import { StringEnum } from "@mariozechner/pi-ai";
import { Text, Box } from "@mariozechner/pi-tui";
import * as fs from "fs";
import * as path from "path";

// ─── Schemas ─────────────────────────────────────────────────────────────────

const SourceNodeSchema = Type.Object({
  id: Type.String({ description: "Unique camelCase node ID, e.g. 'teradataEDW'" }),
  label: Type.String({ description: "Human-readable label, e.g. 'Teradata EDW\\n500TB'" }),
  type: StringEnum(
    ["legacy_dw", "oltp", "saas", "streaming", "file_storage", "external_api"],
    "Category of source system"
  ),
});

const IngestionPatternSchema = Type.Object({
  id: Type.String(),
  label: Type.String({ description: "e.g. 'LakeFlow Connect\\n(CDC)'" }),
  pattern: StringEnum(
    ["lakeflow_connect", "auto_loader", "structured_streaming", "lakebridge", "delta_sharing", "manual"],
    "Ingestion mechanism"
  ),
});

const GoldLayerSchema = Type.Object({
  modeling: StringEnum(
    ["star_schema", "one_big_table", "data_vault_marts", "hybrid"],
    "Modeling pattern in the Gold layer"
  ),
  liquid_cluster_keys: Type.Array(Type.String(), {
    description: "Top 1-4 columns to cluster fact tables on, e.g. ['transaction_date', 'customer_id']",
  }),
  use_materialized_views: Type.Boolean({
    description: "True if heavy aggregations warrant Materialized Views",
  }),
});

const ConsumptionNodeSchema = Type.Object({
  id: Type.String(),
  label: Type.String(),
  type: StringEnum(
    ["power_bi", "tableau", "looker", "dbsql", "mlflow", "delta_sharing", "api", "genie"],
    "Consumption layer tool"
  ),
});

const GovernanceSchema = Type.Object({
  row_filters: Type.Boolean({ description: "Apply Unity Catalog row filters (GDPR/PCI/Basel)" }),
  column_masks: Type.Boolean({ description: "Apply column masks for PII fields" }),
  abac_tags: Type.Boolean({ description: "Use ABAC tag-based policies (multi-jurisdiction)" }),
  compliance: Type.Array(Type.String(), {
    description: "Compliance regimes, e.g. ['GDPR', 'PCI-DSS', 'Basel IV']",
  }),
});

const SilverModelingSchema = StringEnum(
  ["data_vault", "3nf", "scd2_only", "hybrid"],
  "Integration modeling pattern in the Silver layer"
);

const DiscoveryAnswersSchema = Type.Object({
  customer_name: Type.String({ description: "Customer or prospect name" }),
  cloud: StringEnum(["Azure", "AWS", "GCP", "Multi-cloud"], "Primary cloud platform"),
  sources: Type.Array(SourceNodeSchema, { description: "Source systems feeding the lakehouse" }),
  ingestion: Type.Array(IngestionPatternSchema, { description: "Ingestion patterns by source" }),
  silver_modeling: SilverModelingSchema,
  gold: GoldLayerSchema,
  governance: GovernanceSchema,
  consumption: Type.Array(ConsumptionNodeSchema),
  output_path: Type.String({
    description: "File path to write the architecture MD. Default: ./live-arch.md",
    default: "./live-arch.md",
  }),
});

const GenerateArchSchema = Type.Object({
  discovery_answers: DiscoveryAnswersSchema,
});

type DiscoveryAnswersType = Static<typeof DiscoveryAnswersSchema>;
type GenerateArchParams = Static<typeof GenerateArchSchema>;
type SourceNode = Static<typeof SourceNodeSchema>;
type IngestionPattern = Static<typeof IngestionPatternSchema>;
type ConsumptionNode = Static<typeof ConsumptionNodeSchema>;

// ─── Mermaid diagram generator ────────────────────────────────────────────────

function sourceIcon(type: SourceNode["type"]): string {
  const icons: Record<SourceNode["type"], string> = {
    legacy_dw: "🏛️",
    oltp: "⚙️",
    saas: "☁️",
    streaming: "🌊",
    file_storage: "📁",
    external_api: "🔗",
  };
  return icons[type] ?? "📦";
}

function ingestionIcon(pattern: IngestionPattern["pattern"]): string {
  const icons: Record<IngestionPattern["pattern"], string> = {
    lakeflow_connect: "🔄",
    auto_loader: "📂",
    structured_streaming: "🌊",
    lakebridge: "🌉",
    delta_sharing: "🔀",
    manual: "✋",
  };
  return icons[pattern] ?? "⚡";
}

function consumptionIcon(type: ConsumptionNode["type"]): string {
  const icons: Record<ConsumptionNode["type"], string> = {
    power_bi: "📊",
    tableau: "📈",
    looker: "🔍",
    dbsql: "⚡",
    mlflow: "🤖",
    delta_sharing: "🔀",
    api: "🔌",
    genie: "💬",
  };
  return icons[type] ?? "📊";
}

function silverLabel(modeling: DiscoveryAnswersType["silver_modeling"]): string {
  const labels: Record<DiscoveryAnswersType["silver_modeling"], string> = {
    data_vault: "Data Vault 2.0\\nHubs · Links · Satellites",
    "3nf": "3NF Integration\\nSingle source of truth",
    scd2_only: "SCD Type 2 via AUTO CDC\\nTrack history on business keys",
    hybrid: "Hybrid: DV Hubs + Star Satellites\\nBest of both worlds",
  };
  return labels[modeling];
}

function goldLabel(gold: DiscoveryAnswersType["gold"]): string {
  const modelLabel: Record<DiscoveryAnswersType["gold"]["modeling"], string> = {
    star_schema: "Star Schema (Kimball)",
    one_big_table: "One Big Table (OBT)",
    data_vault_marts: "DV-sourced Data Marts",
    hybrid: "Star Schema + OBTs",
  };
  const clusterKeys = gold.liquid_cluster_keys.slice(0, 4).join(", ");
  const mv = gold.use_materialized_views ? "\\nMaterialized Views: ✅" : "";
  return `${modelLabel[gold.modeling]}\\nLiquid Clustered: (${clusterKeys})${mv}`;
}

function governanceNodes(gov: DiscoveryAnswersType["governance"]): string[] {
  const nodes: string[] = [];
  const compliance = gov.compliance.join(", ") || "Standard";
  if (gov.row_filters) nodes.push(`    UC_RF["🔒 Row Filters\\n${compliance}"]`);
  if (gov.column_masks) nodes.push(`    UC_CM["🎭 Column Masks\\nPII Fields"]`);
  nodes.push(`    UC_LIN["🔍 Column Lineage\\nAuto-captured (GA)"]`);
  if (gov.abac_tags) nodes.push(`    UC_ABAC["🏷️ ABAC Tag Policies\\nMulti-jurisdiction"]`);
  else nodes.push(`    UC_RBAC["👥 RBAC\\nRole-based access"]`);
  return nodes;
}

function buildMermaid(d: DiscoveryAnswersType): string {
  const sourceNodes = d.sources
    .map((s) => `    ${s.id}["${sourceIcon(s.type)} ${s.label}"]`)
    .join("\n");

  const ingestionNodes = d.ingestion
    .map((i) => `    ${i.id}["${ingestionIcon(i.pattern)} ${i.label}"]`)
    .join("\n");

  const sourceToIngestion = d.sources
    .map((s, idx) => {
      const ing = d.ingestion[idx % d.ingestion.length];
      return `    ${s.id} --> ${ing.id}`;
    })
    .join("\n");

  const ingestionToBronze = d.ingestion
    .map((i) => `    ${i.id} --> B`)
    .join("\n");

  const consumptionNodes = d.consumption
    .map((c) => `    ${c.id}["${consumptionIcon(c.type)} ${c.label}"]`)
    .join("\n");

  const goldToConsumption = d.consumption
    .map((c) => `    G --> ${c.id}`)
    .join("\n");

  const govNodes = governanceNodes(d.governance).join("\n");

  return `flowchart TD
    subgraph SOURCES["📥 Sources"]
${sourceNodes}
    end

    subgraph INGESTION["⚡ Ingestion — LakeFlow & Partners"]
${ingestionNodes}
    end

    subgraph MEDALLION["🏅 Databricks Lakehouse on ${d.cloud} — Open Delta Lake Format"]
        direction TB
        B["🥉 Bronze\\nRaw Delta · Append-only\\nAudit trail · No PII masking"]
        Sv["🥈 Silver\\n${silverLabel(d.silver_modeling)}\\nColumn masks on PII"]
        G["🥇 Gold\\n${goldLabel(d.gold)}\\nPhoton-optimized · Serverless SQL"]
        B --> Sv --> G
    end

    subgraph GOVERNANCE["🛡️ Unity Catalog — Single Governance Layer"]
${govNodes}
    end

    subgraph CONSUMPTION["📊 Consumption Layer"]
${consumptionNodes}
    end

${sourceToIngestion}
${ingestionToBronze}
    MEDALLION --> GOVERNANCE
${goldToConsumption}`;
}

// ─── Markdown document builder ────────────────────────────────────────────────

function buildArchDocument(d: DiscoveryAnswersType, mermaid: string): string {
  const now = new Date().toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const compliance = d.governance.compliance.join(", ") || "Standard";
  const sourceList = d.sources.map((s) => `${s.label.replace(/\\n/g, " ")} (${s.type})`).join(", ");
  const goldKeys = d.gold.liquid_cluster_keys.slice(0, 4).join(", ");

  const silverDetails: Record<DiscoveryAnswersType["silver_modeling"], string> = {
    data_vault: `**Data Vault 2.0** — chosen because of multiple source systems requiring full auditability and parallel team loading. Hubs hold business keys, Links capture relationships, Satellites store context with full history via \`TRACK HISTORY ON\` in AUTO CDC.`,
    "3nf": `**3NF Integration** — chosen for moderate source count with stable schemas. SCD Type 2 applied on business-critical entities via \`AUTO CDC INTO ... STORED AS SCD TYPE 2\`.`,
    scd2_only: `**SCD Type 2 via LakeFlow AUTO CDC** — declarative \`STORED AS SCD TYPE 2 TRACK HISTORY ON\` with automatic out-of-order handling via \`SEQUENCE BY\`. Eliminates custom MERGE logic.`,
    hybrid: `**Hybrid** — Data Vault Hubs/Links for integration, star schema Satellites in Gold for consumption. Best of both auditability and query performance.`,
  };

  const goldModelDetails: Record<DiscoveryAnswersType["gold"]["modeling"], string> = {
    star_schema: `**Star Schema (Kimball)** — optimized for known BI query patterns. Photon delivers up to 18x performance on star joins. Fact tables Liquid Clustered on \`(${goldKeys})\`.`,
    one_big_table: `**One Big Table** — pre-joined for single-purpose analytics. Eliminates shuffle-intensive joins. Liquid Clustering on \`(${goldKeys})\` yielded >20x task speedup in benchmarks.`,
    data_vault_marts: `**DV-sourced Data Marts** — Gold layer pulls from Silver Data Vault via PIT/Bridge tables, then exposes dimensional marts for BI consumption.`,
    hybrid: `**Hybrid** — star schema for BI dashboards + OBTs for specific high-volume dashboard queries. Modeling choice per use case rather than one-size-fits-all.`,
  };

  return `# ${d.customer_name} — Databricks Lakehouse Architecture
*Generated: ${now} | Steve Lysik, Databricks SA Candidate | DW Spike*

---

## Architecture Diagram

\`\`\`mermaid
${mermaid}
\`\`\`

---

## Discovery Summary

| Category | Status | Details |
|----------|--------|---------|
| Cloud Platform | ✅ | ${d.cloud} |
| Source Systems | ✅ | ${sourceList} |
| Ingestion Patterns | ✅ | ${d.ingestion.map((i) => i.pattern.replace(/_/g, " ")).join(", ")} |
| Silver Modeling | ✅ | ${d.silver_modeling.replace(/_/g, " ")} |
| Gold Modeling | ✅ | ${d.gold.modeling.replace(/_/g, " ")} |
| Compliance | ✅ | ${compliance} |
| Consumption Tools | ✅ | ${d.consumption.map((c) => c.label.replace(/\\n/g, " ")).join(", ")} |
| Governance Model | ✅ | Row Filters: ${d.governance.row_filters ? "✅" : "❌"} · Column Masks: ${d.governance.column_masks ? "✅" : "❌"} · ABAC: ${d.governance.abac_tags ? "✅ (Preview)" : "❌"} |

---

## Architecture Decision Log

| Layer | Decision | Choice | Rationale | Trade-off |
|-------|----------|--------|-----------|-----------|
| Ingestion | CDC mechanism | ${d.ingestion[0]?.pattern.replace(/_/g, " ") ?? "LakeFlow Connect"} | Managed connectors reduce operational burden | Less flexible than custom Kafka, but operational simplicity wins |
| Silver | Integration modeling | ${d.silver_modeling.replace(/_/g, " ")} | ${d.silver_modeling === "data_vault" ? "Multiple sources + auditability requirement" : "Moderate source count, stable schemas"} | ${d.silver_modeling === "data_vault" ? "More complex than 3NF, pays off for regulatory traceability" : "Less flexible for future source additions vs Data Vault"} |
| Gold | Consumption modeling | ${d.gold.modeling.replace(/_/g, " ")} | ${d.gold.modeling.includes("star") ? "Known BI query patterns, Photon 18x on star joins" : "Single-purpose analytics, eliminate join overhead"} | ${d.gold.modeling.includes("star") ? "Less flexible for ad-hoc vs Data Vault, but dramatically faster for dashboards" : "Large scans expensive without clustering"} |
| Gold | Physical layout | Liquid Clustering on (${goldKeys}) | Replaces Z-ORDER + partitioning; incremental; changeable without rewrite | Higher DBU on first OPTIMIZE vs partition pruning |
| Governance | Access control | Unity Catalog ${d.governance.abac_tags ? "+ ABAC (Preview)" : "+ RBAC (GA)"} | Single governance layer across all data assets and languages | ${d.governance.abac_tags ? "ABAC is Public Preview — maintain row filter fallback" : "RBAC requires explicit grants per role vs tag inheritance"} |
| Compute | SQL Warehouse type | Serverless (IWM + PQE + Photon) | 40% perf improvement in 2025; 2–6s startup; zero idle costs | Higher per-DBU than Classic; lower TCO for bursty BI workloads |

---

## DW Modeling Detail

### Silver Layer
${silverDetails[d.silver_modeling]}

### Gold Layer
${goldModelDetails[d.gold.modeling]}

${d.gold.use_materialized_views ? `### Materialized Views
Recommended for heavy aggregations on this workload. Use \`CREATE MATERIALIZED VIEW\` backed by serverless DLT for incremental refresh.
> **Requirement**: Enable row tracking on source Delta tables: \`ALTER TABLE ... SET TBLPROPERTIES ('delta.enableRowTracking' = 'true')\`
` : ""}

---

## Governance Design

**Compliance requirements**: ${compliance}

${d.governance.row_filters ? `**Row Filters (GA)**: SQL UDFs that evaluate at query time based on caller identity. Apply at Silver layer for jurisdiction/LOB-level access control.

\`\`\`sql
CREATE FUNCTION security.jurisdiction_filter(jurisdiction STRING)
RETURN is_member('admin') OR current_user() IN (
  SELECT user FROM security.jurisdiction_access WHERE jurisdiction_code = jurisdiction
);
ALTER TABLE silver.fact_positions SET ROW FILTER security.jurisdiction_filter ON (jurisdiction_code);
\`\`\`
` : ""}

${d.governance.column_masks ? `**Column Masks (GA)**: Replace sensitive column values at query time. Apply to PII columns in Silver.

\`\`\`sql
CREATE FUNCTION security.mask_pii(val STRING)
RETURN CASE WHEN is_member('pii_access') THEN val ELSE '***REDACTED***' END;
\`\`\`
` : ""}

${d.governance.abac_tags ? `**ABAC Tag Policies (Public Preview)**: Tag-based policies that inherit through the catalog hierarchy. Assign tags to schemas/tables; policies apply automatically.
> ⚠️ Public Preview — maintain row filter fallbacks for production.
` : ""}

---

## Steve's SA Talking Points for This Customer

- **Lead with**: The open format advantage — Delta Lake means zero vendor lock-in on the data itself. If ${d.customer_name} ever wants to switch tools, the data stays theirs.
- **Performance proof point**: Serverless SQL with Photon + IWM delivered a 40% automatic perf gain in 2025 — no query rewrites, no tuning.
- **Governance angle**: Unity Catalog is the only platform with a single governance layer spanning DE, DW, AND ML — ${d.governance.compliance.length > 0 ? `critical for ${compliance} compliance` : "critical for enterprise governance"}.
- **Migration angle**: Lakebridge Federation means zero disruption migration — query the legacy system in place while migrating incrementally. No big bang cutover.
- **Steve's personal angle**: "I spent 8 years on the IBM/Netezza side — I know exactly where the migration bodies are buried. That's why I'd recommend Federation-First."

---

## Open Questions (Still Need in Discovery)

- [ ] How many concurrent users will hit the Gold layer simultaneously? (Determines warehouse sizing)
- [ ] Is there a hard deadline driving this — regulatory submission, contract expiry, board commitment?
- [ ] What BI tools are actually *mandated* vs. just in use? (Could be consolidation opportunity)
- [ ] What has failed in a previous data platform initiative at ${d.customer_name}? (Hidden requirements)
- [ ] Who is the executive sponsor and what does THEIR success metric look like?

---

*Generated by the Databricks SA Interview Copilot — Pi extension \`arch-diagram.ts\`*
`;
}

// ─── Inline preview renderer ──────────────────────────────────────────────────

function renderDiagramPreview(
  customerName: string,
  outputPath: string,
  sourceCount: number,
  mermaidSnippet: string,
  theme: any
): string[] {
  const lines: string[] = [];
  const checkmark = theme.fg("success", "✓");
  const label = theme.fg("accent", "Databricks Architecture");
  const name = theme.fg("mdHeading", customerName);
  const pathStr = theme.fg("dim", `→ ${outputPath}`);

  lines.push(`  ${checkmark} ${label}  ${name}  ${theme.fg("dim", `(${sourceCount} sources)`)}`);
  lines.push(`  ${pathStr}`);
  lines.push(theme.fg("dim", "  " + "─".repeat(50)));

  const mermaidLines = mermaidSnippet
    .split("\n")
    .filter((l) => l.trim() && !l.startsWith("flowchart") && !l.startsWith("subgraph") && !l.startsWith("end"))
    .slice(0, 6);

  for (const line of mermaidLines) {
    const trimmed = line.trim();
    if (trimmed.includes("-->")) {
      const parts = trimmed.split("-->");
      const from = theme.fg("accent", parts[0]?.trim().replace(/["\[\]]/g, "") ?? "");
      const to = theme.fg("success", parts[1]?.trim().replace(/["\[\]]/g, "") ?? "");
      lines.push(`  ${from} ${theme.fg("dim", "──▶")} ${to}`);
    } else if (trimmed.startsWith('"') || trimmed.match(/^\w+\[/)) {
      const label2 = trimmed.replace(/^\w+\["?/, "").replace(/"?\]$/, "").replace(/\\n/g, " · ");
      lines.push(`  ${theme.fg("text", "  · " + label2.slice(0, 48))}`);
    }
  }

  lines.push(theme.fg("dim", `  (Ctrl+O to expand · open live-arch.md for full render)`));
  return lines;
}

// ─── File watcher state ───────────────────────────────────────────────────────

let activeWatcher: fs.FSWatcher | null = null;
let watchedFile: string | null = null;

function stopWatcher(ctx: ExtensionContext): void {
  if (activeWatcher) {
    activeWatcher.close();
    activeWatcher = null;
    watchedFile = null;
    ctx.ui.clearStatus("arch-watch");
  }
}

function startWatcher(filePath: string, ctx: ExtensionContext, pi: ExtensionAPI): void {
  stopWatcher(ctx);

  const absPath = path.resolve(filePath);
  if (!fs.existsSync(absPath)) {
    fs.writeFileSync(absPath, `# Live Architecture\n*Waiting for first diagram generation...*\n`);
  }

  watchedFile = absPath;
  const shortName = path.basename(absPath);

  ctx.ui.setStatus("arch-watch", ctx.ui.theme.fg("accent", `◉ watching ${shortName}`));

  activeWatcher = fs.watch(absPath, (eventType: string) => {
    if (eventType !== "change") return;
    try {
      const content = fs.readFileSync(absPath, "utf-8");
      const titleMatch = content.match(/^# (.+?) —/m);
      const title = titleMatch?.[1] ?? shortName;
      const ts = new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
      pi.sendMessage({
        customType: "arch-watch-update",
        content: `◉ ${shortName} updated at ${ts} — ${title}`,
        display: true,
        details: { file: absPath, title, timestamp: ts },
      }, { triggerTurn: false });
    } catch {
      // File briefly missing during atomic save — ignore
    }
  });
}

// ─── Extension entry point ────────────────────────────────────────────────────

export default function setup(pi: ExtensionAPI): void {

  // ── generate_databricks_arch tool ──────────────────────────────────────────
  // NOTE: registerTool takes a single ToolDefinition object (Pi v0.54+ API).
  // All fields (name, label, description, parameters, execute, renderCall,
  // renderResult) must be in one object. "parameters" replaces old "inputSchema".

  pi.registerTool({
    name: "generate_databricks_arch",
    label: "Generate Databricks Architecture",
    description:
      "Generate a complete Databricks Medallion architecture document with Mermaid diagram from live interview discovery answers. Writes a shareable live-arch.md file. Call this as soon as you have enough discovery information to propose an architecture — you can call it multiple times as discovery progresses.",
    parameters: GenerateArchSchema,

    async execute(toolCallId, params: GenerateArchParams, signal, onUpdate, ctx) {
      const d = params.discovery_answers;
      const outputPath = path.resolve(d.output_path || "./live-arch.md");

      onUpdate?.({ text: `Building ${d.customer_name} architecture diagram...` });

      if (signal?.aborted) {
        return { isError: true, content: "Cancelled." };
      }

      // Validate connections
      for (const ing of d.ingestion) {
        if (!ing.id) {
          return { isError: true, content: "Each ingestion node must have a unique id." };
        }
      }

      onUpdate?.({ text: "Generating Mermaid diagram..." });
      const mermaid = buildMermaid(d);

      onUpdate?.({ text: `Writing to ${outputPath}...` });
      const document = buildArchDocument(d, mermaid);

      try {
        fs.mkdirSync(path.dirname(outputPath), { recursive: true });
        fs.writeFileSync(outputPath, document, "utf-8");
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        return { isError: true, content: `Failed to write ${outputPath}: ${msg}` };
      }

      const preview = mermaid.split("\n").slice(0, 20).join("\n");

      const entry = {
        customerName: d.customer_name,
        outputPath,
        sourceCount: d.sources.length,
        cloud: d.cloud,
        mermaidPreview: preview,
        timestamp: new Date().toISOString(),
      };

      // Store in session for persistence
      pi.appendEntry("databricks-arch", entry);

      // Send inline message card
      ctx.sendMessage(
        {
          customType: "databricks-arch",
          content: `Architecture diagram generated for ${d.customer_name} → ${outputPath}`,
          display: true,
          details: entry,
        },
        { triggerTurn: false }
      );

      return {
        content: `✓ Architecture written to ${outputPath}\n\nOpen it in your browser:\n  bash .pi/skills/databricks-sa/scripts/open-live.sh "${outputPath}"\n\nOr watch it live:\n  /watch-arch "${outputPath}"`,
        details: entry,
      };
    },

    renderCall(args: GenerateArchParams, theme: any) {
      const d = args.discovery_answers;
      const name = d?.customer_name ?? "Customer";
      const sources = d?.sources?.length ?? 0;
      const out = d?.output_path ?? "live-arch.md";
      return new Box(
        [
          new Text(
            `${theme.fg("toolName", "generate_databricks_arch")}  ` +
            `${theme.fg("accent", name)} · ${sources} sources`,
            0, 0
          ),
          new Text(theme.fg("dim", `  → ${out}`), 0, 0),
        ],
        0, 0
      );
    },

    renderResult(result: any, { expanded }: { expanded: boolean; isPartial: boolean }, theme: any) {
      if (result.isError) {
        return new Text(theme.fg("error", `  ✗ ${result.content}`), 0, 0);
      }
      const entry = result.details;
      if (!entry) {
        return new Text(theme.fg("dim", "  ✓ Architecture generated"), 0, 0);
      }

      const previewLines = renderDiagramPreview(
        entry.customerName,
        entry.outputPath,
        entry.sourceCount,
        entry.mermaidPreview ?? "",
        theme
      );

      if (expanded) {
        const mermaidLines = (entry.mermaidPreview ?? "").split("\n").map(
          (l: string) => theme.fg("dim", "  " + l)
        );
        return new Box(
          [...previewLines, ...mermaidLines].map((l) => new Text(l, 0, 0)),
          0, 0
        );
      }

      return new Box(
        previewLines.map((l) => new Text(l, 0, 0)),
        0, 0
      );
    },
  });

  // ── Custom message renderers ───────────────────────────────────────────────

  pi.registerMessageRenderer(
    "databricks-arch",
    (message: any, { expanded }: { expanded: boolean }, theme: any) => {
      const entry = message.details;
      if (!entry) return new Text(theme.fg("dim", message.content ?? ""), 0, 0);

      const lines = renderDiagramPreview(
        entry.customerName,
        entry.outputPath,
        entry.sourceCount,
        entry.mermaidPreview ?? "",
        theme
      );

      return new Box(lines.map((l: string) => new Text(l, 0, 0)), 0, 0);
    }
  );

  pi.registerMessageRenderer(
    "arch-watch-update",
    (message: any, _opts: any, theme: any) => {
      const d = message.details;
      const ts = d?.timestamp ?? "";
      const file = d?.file ? path.basename(d.file) : "live-arch.md";
      return new Text(
        `  ${theme.fg("accent", "◉")} ${theme.fg("text", file)} updated ${theme.fg("dim", ts)} — ${theme.fg("mdHeading", d?.title ?? "")}`,
        0, 0
      );
    }
  );

  // ── /watch-arch command ────────────────────────────────────────────────────

  pi.registerCommand("watch-arch", {
    handler: async (args: string, ctx: ExtensionCommandContext) => {
      const trimmed = args.trim();

      if (trimmed === "stop") {
        stopWatcher(ctx as unknown as ExtensionContext);
        pi.appendEntry("system", { content: "◉ Stopped watching live-arch.md" });
        return;
      }

      const filePath = trimmed || "./live-arch.md";
      startWatcher(filePath, ctx as unknown as ExtensionContext, pi);

      pi.appendEntry("system", {
        content: `◉ Watching ${path.resolve(filePath)} — any save will ping in chat.`,
      });
    },
  });

  // ── session_start hook — restore last diagram info ─────────────────────────

  pi.on("session_start", async (_event, ctx) => {
    const entries = ctx.sessionManager
      .getEntries()
      .filter((e: any) => e.type === "custom" && e.customType === "databricks-arch");

    if (entries.length > 0) {
      const last = entries[entries.length - 1] as any;
      const d = last.details;
      if (d?.outputPath && fs.existsSync(d.outputPath)) {
        ctx.ui.setStatus(
          "arch-last",
          ctx.ui.theme.fg("dim", `last arch: ${path.basename(d.outputPath)}`)
        );
      }
    }
  });

  // ── session_shutdown hook — close watcher ──────────────────────────────────

  pi.on("session_shutdown", async (_event, ctx) => {
    stopWatcher(ctx);
  });
}
