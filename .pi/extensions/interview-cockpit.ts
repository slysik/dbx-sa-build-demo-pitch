/**
 * Interview Cockpit — Passive awareness for Databricks coding interviews
 *
 * Three features, zero blocking:
 *   1. Footer: elapsed timer (green→yellow→red) + model + context %
 *              + Databricks workspace connection badge
 *   2. Widget: interview prompt captured from first user message
 *   3. /phase: quick narration hint lookup (optional, no enforcement)
 *
 * Theme: loads "databricks" theme (Databricks orange brand palette)
 * Title: "◆ Databricks Interview"
 *
 * Usage: pi -e .pi/extensions/interview-cockpit.ts
 */

import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { truncateToWidth, visibleWidth } from "@mariozechner/pi-tui";

// ── Databricks brand colors (inline — no dependency on themeMap) ──

// Databricks Orange #FF3621
function dbOrange(s: string): string {
	return `\x1b[38;2;255;54;33m${s}\x1b[39m`;
}
function dbOrangeBg(s: string): string {
	return `\x1b[48;2;255;54;33m\x1b[38;2;255;255;255m${s}\x1b[39m\x1b[49m`;
}
// Dark surface for widget bar
function bgDark(s: string): string {
	return `\x1b[48;2;30;28;28m${s}\x1b[49m`;
}
function green(s: string): string {
	return `\x1b[38;2;0;212;170m${s}\x1b[39m`;
}
function yellow(s: string): string {
	return `\x1b[38;2;255;171;0m${s}\x1b[39m`;
}
function red(s: string): string {
	return `\x1b[38;2;219;30;35m${s}\x1b[39m`;
}
function cyan(s: string): string {
	return `\x1b[38;2;0;188;212m${s}\x1b[39m`;
}
function dim(s: string): string {
	return `\x1b[38;2;114;114;126m${s}\x1b[39m`;
}
function white(s: string): string {
	return `\x1b[38;2;245;245;245m${s}\x1b[39m`;
}
function bold(s: string): string {
	return `\x1b[1m${s}\x1b[22m`;
}

// ── Phase Hints ──────────────────────────────────────────────────

const PHASE_HINTS: Record<string, string> = {
	discovery: "🔍 Ask: business key? volume? batch vs streaming? what does 'correct' mean?",
	datagen:   "🧪 spark.range() + hash. FK by construction. Bronze governance columns.",
	bronze:    "🥉 .saveAsTable() → managed Delta. Liquid Clustering. TBLPROPERTIES. DESCRIBE HISTORY.",
	silver:    "🥈 ROW_NUMBER dedup. Expectations ON VIOLATION DROP ROW. Explicit CAST. LC on query pattern.",
	gold:      "🥇 Pre-aggregate for BI. Liquid Clustering narration. NULLIF. Clean joins.",
	validate:  "✅ Row counts across layers. DESCRIBE DETAIL. EXPLAIN for data skipping. Batch consistency.",
	discuss:   "💬 Narrow vs wide. Shuffle. Join strategy. LC vs partitioning. Scale to 1B. Streaming pivot.",
};

// ── Workspace config ─────────────────────────────────────────────

const WORKSPACE = {
	host: "adb-7405619449104571.11",
	name: "dbx-interview",
	catalog: "interview",
	schema: "retail",
};

export default function (pi: ExtensionAPI) {
	let interviewPrompt: string | undefined;
	const startTime = Date.now();

	// ── Pipeline status checkmarks (updated by tool_result) ──────
	const pipeStatus: Record<string, boolean> = {};

	// ── Track tool results for pipeline status ──────────────────

	pi.on("tool_result", async (event) => {
		const text = Array.isArray((event as any).content)
			? (event as any).content.map((c: any) => c?.text ?? "").join("")
			: "";
		if (event.toolName === "dbx_auth_check" && text.includes("Auth OK")) pipeStatus.auth = true;
		if (event.toolName === "dbx_cluster_status" && text.includes("RUNNING")) pipeStatus.cluster = true;
		if (event.toolName === "dbx_sql" && /bronze|CREATE|100000/.test(text)) pipeStatus.bronze = true;
		if (event.toolName === "dbx_run_notebook" && text.includes("completed")) pipeStatus.bronze = true;
		if (event.toolName === "dbx_validate_tables" && /bronze/.test(text)) pipeStatus.bronze = true;
		if (event.toolName === "dbx_validate_tables" && /silver/.test(text)) pipeStatus.silver = true;
		if (event.toolName === "dbx_validate_tables" && /gold/.test(text)) pipeStatus.gold = true;
		if (event.toolName === "dbx_poll_pipeline" && text.includes("completed")) { pipeStatus.silver = true; pipeStatus.gold = true; }
		if (event.toolName === "dbx_deploy_dashboard" && text.includes("deployed")) pipeStatus.dash = true;
	});

	// ── Auto-capture prompt from first user message ──────────────

	pi.on("input", async (event) => {
		if (!interviewPrompt && event.text && event.text.length > 20) {
			interviewPrompt = event.text.slice(0, 200);
		}
		return { action: "continue" as const };
	});

	// ── /prompt — manually set/update the interview prompt ───────

	pi.registerCommand("prompt", {
		description: "Set or update the interview prompt",
		handler: async (args, ctx) => {
			if (args.trim()) {
				interviewPrompt = args.trim();
				ctx.ui.notify("Prompt updated", "success");
			} else {
				const answer = await ctx.ui.input("Interview Prompt", "Paste the interviewer's prompt");
				if (answer?.trim()) {
					interviewPrompt = answer.trim();
					ctx.ui.notify("Prompt captured", "success");
				}
			}
		},
	});

	// ── /phase — show narration hint for a phase ─────────────────

	pi.registerCommand("phase", {
		description: "Show narration hint: discovery|datagen|bronze|silver|gold|validate|discuss",
		getArgumentCompletions: (prefix: string) => {
			const phases = Object.keys(PHASE_HINTS);
			const filtered = phases
				.filter((p) => p.startsWith(prefix))
				.map((p) => ({ value: p, label: `${p} — ${PHASE_HINTS[p].slice(0, 60)}` }));
			return filtered.length > 0 ? filtered : null;
		},
		handler: async (args, ctx) => {
			const phase = args.trim().toLowerCase();
			if (phase in PHASE_HINTS) {
				ctx.ui.notify(PHASE_HINTS[phase], "info");
			} else {
				const choices = Object.entries(PHASE_HINTS).map(
					([k, v]) => `${k} — ${v}`
				);
				const choice = await ctx.ui.select("Phase Hint", choices);
				if (choice) {
					ctx.ui.notify(choice, "info");
				}
			}
		},
	});

	// ── /theme — switch theme on the fly ─────────────────────────

	pi.registerCommand("theme", {
		description: "Switch theme: databricks|midnight-ocean|cyberpunk|tokyo-night",
		getArgumentCompletions: (prefix: string) => {
			const themes = ["databricks", "midnight-ocean", "cyberpunk", "tokyo-night"];
			const filtered = themes
				.filter((t) => t.startsWith(prefix))
				.map((t) => ({ value: t, label: t }));
			return filtered.length > 0 ? filtered : null;
		},
		handler: async (args, ctx) => {
			if (!ctx.hasUI) return;
			const name = args.trim();
			if (name) {
				const result = ctx.ui.setTheme(name);
				if (result.success) {
					ctx.ui.notify(`Theme: ${name}`, "success");
				} else {
					ctx.ui.notify(`Theme not found: ${name}`, "error");
				}
			} else {
				const themes = ctx.ui.getAllThemes();
				const items = themes.map((t) => {
					const active = t.name === ctx.ui.theme.name ? " ◀" : "";
					return `${t.name}${active}`;
				});
				const choice = await ctx.ui.select("Select Theme", items);
				if (choice) {
					const selected = choice.replace(" ◀", "");
					const result = ctx.ui.setTheme(selected);
					if (result.success) ctx.ui.notify(`Theme: ${selected}`, "success");
				}
			}
		},
	});

	// ── /ws — show workspace info ────────────────────────────────

	pi.registerCommand("ws", {
		description: "Show Databricks workspace connection info",
		handler: async (_args, ctx) => {
			ctx.ui.notify(
				`◆ ${WORKSPACE.name}\n` +
				`  Host: ${WORKSPACE.host}.azuredatabricks.net\n` +
				`  Catalog: ${WORKSPACE.catalog}\n` +
				`  Schema: ${WORKSPACE.schema}`,
				"info"
			);
		},
	});

	// ── Session start: theme + title + widget + footer ───────────

	pi.on("session_start", async (_event, ctx) => {
		if (!ctx.hasUI) return;

		// Apply Databricks theme
		const themeResult = ctx.ui.setTheme("databricks");
		if (!themeResult.success) {
			// Fallback — theme file might not exist yet
			ctx.ui.notify("databricks theme not found, using default", "warning");
		}

		// Terminal title
		setTimeout(() => ctx.ui.setTitle("◆ Databricks Interview"), 150);

		// Status line: workspace badge
		ctx.ui.setStatus("workspace",
			`◆ ${WORKSPACE.host} | ${WORKSPACE.catalog}.${WORKSPACE.schema}`
		);

		// ── Widget: interview prompt ─────────────────────────────

		ctx.ui.setWidget("interview-prompt", () => ({
			render(width: number): string[] {
				if (!interviewPrompt) return [];
				const pad = bgDark(" ".repeat(width));
				const badge = dbOrangeBg(" ◆ PROMPT ");
				const line = bgDark(
					truncateToWidth(
						"  " + badge + "  " + white(interviewPrompt!) + " ".repeat(width),
						width,
						""
					)
				);
				return [pad, line, pad];
			},
			invalidate() {},
		}));

		// ── Footer: timer + workspace + model + context % ────────

		ctx.ui.setFooter((_tui, theme) => ({
			dispose: () => {},
			invalidate() {},
			render(width: number): string[] {
				// Timer with color coding
				const elapsedMs = Date.now() - startTime;
				const mins = Math.floor(elapsedMs / 60000);
				const secs = Math.floor((elapsedMs % 60000) / 1000);
				const timeStr = `${mins}:${secs.toString().padStart(2, "0")}`;
				const timeColor = mins >= 50 ? red : mins >= 35 ? yellow : green;

				// Context meter
				const usage = ctx.getContextUsage();
				const pct = usage ? Math.round(usage.percent) : 0;
				const filled = Math.round(pct / 10);
				const bar = "█".repeat(filled) + "░".repeat(10 - filled);
				const barColor = pct >= 80 ? red : pct >= 60 ? yellow : green;

				// Model
				const model = ctx.model?.id?.replace(/^.*\//, "") || "—";

				// Line 1: timer + model + context
				const l1Left =
					dim(" ") +
					timeColor(bold(`⏱ ${timeStr}`)) +
					dim("  ") +
					dim(model) +
					dim("  ") +
					barColor(bar) +
					dim(` ${pct}%`);

				const l1Right = interviewPrompt
					? dim(`🎯 prompt captured `)
					: yellow(`⚠ awaiting prompt `);

				const pad1 = " ".repeat(Math.max(1, width - visibleWidth(l1Left) - visibleWidth(l1Right)));
				const line1 = truncateToWidth(l1Left + pad1 + l1Right, width, "");

				// Line 2: workspace badge
				const wsBadge = dbOrange("◆") + dim(` ${WORKSPACE.host}`);
				const catBadge = cyan(`${WORKSPACE.catalog}`) + dim(".") + white(`${WORKSPACE.schema}`);
				const l2Left = dim(" ") + wsBadge + dim("  ") + catBadge;

				// Pipeline checkmarks
				const ck = (key: string, label: string) =>
					(pipeStatus[key] ? green("✓") : dim("○")) + dim(" " + label);
				const sep = dim(" │ ");
				const l2Right = ck("auth", "auth") + sep + ck("cluster", "cluster") + sep + ck("bronze", "bronze") + sep + ck("silver", "silver") + sep + ck("gold", "gold") + sep + ck("dash", "dash") + " ";

				const pad2 = " ".repeat(Math.max(1, width - visibleWidth(l2Left) - visibleWidth(l2Right)));
				const line2 = truncateToWidth(l2Left + pad2 + l2Right, width, "");

				return [line1, line2];
			},
		}));
	});
}
