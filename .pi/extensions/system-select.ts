/**
 * System Select — Switch the system prompt via /system
 *
 * Scans .pi/agents/, .claude/agents/ for agent definition .md files.
 * /system opens a select dialog to pick a system prompt.
 *
 * Usage: Auto-loaded from .pi/extensions/
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { readdirSync, readFileSync, existsSync } from "node:fs";
import { join, basename } from "node:path";
import { homedir } from "node:os";

interface AgentDef {
	name: string;
	description: string;
	tools: string[];
	body: string;
	source: string;
}

function parseFrontmatter(raw: string): { fields: Record<string, string>; body: string } {
	const match = raw.match(/^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)$/);
	if (!match) return { fields: {}, body: raw };
	const fields: Record<string, string> = {};
	for (const line of match[1].split("\n")) {
		const idx = line.indexOf(":");
		if (idx > 0) fields[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
	}
	return { fields, body: match[2] };
}

function scanAgents(dir: string, source: string): AgentDef[] {
	if (!existsSync(dir)) return [];
	const agents: AgentDef[] = [];
	try {
		for (const file of readdirSync(dir)) {
			if (!file.endsWith(".md")) continue;
			const raw = readFileSync(join(dir, file), "utf-8");
			const { fields, body } = parseFrontmatter(raw);
			agents.push({
				name: fields.name || basename(file, ".md"),
				description: fields.description || "",
				tools: fields.tools ? fields.tools.split(",").map((t) => t.trim()) : [],
				body: body.trim(),
				source,
			});
		}
	} catch {}
	return agents;
}

function displayName(name: string): string {
	return name
		.split("-")
		.map((w) => w.charAt(0).toUpperCase() + w.slice(1))
		.join(" ");
}

export default function (pi: ExtensionAPI) {
	let activeAgent: AgentDef | null = null;
	let allAgents: AgentDef[] = [];
	let defaultTools: string[] = [];

	pi.on("session_start", async (_event, ctx) => {
		activeAgent = null;
		allAgents = [];

		const home = homedir();
		const cwd = ctx.cwd;

		const dirs: [string, string][] = [
			[join(cwd, ".pi", "agents"), ".pi"],
			[join(cwd, ".claude", "agents"), ".claude"],
			[join(home, ".pi", "agent", "agents"), "~/.pi"],
			[join(home, ".claude", "agents"), "~/.claude"],
		];

		const seen = new Set<string>();
		for (const [dir, source] of dirs) {
			for (const agent of scanAgents(dir, source)) {
				const key = agent.name.toLowerCase();
				if (seen.has(key)) continue;
				seen.add(key);
				allAgents.push(agent);
			}
		}

		defaultTools = pi.getActiveTools();
		ctx.ui.setStatus("system-prompt", "Agent: Default");
		ctx.ui.notify(`Loaded ${allAgents.length} agents. Use /system to switch.`, "info");
	});

	pi.registerCommand("system", {
		description: "Select a system prompt from discovered agents",
		handler: async (_args, ctx) => {
			if (allAgents.length === 0) {
				ctx.ui.notify("No agents found in .pi/agents/ or .claude/agents/", "warning");
				return;
			}

			const options = [
				"Reset to Default",
				...allAgents.map((a) => `${displayName(a.name)} — ${a.description} [${a.source}]`),
			];

			const choice = await ctx.ui.select("Select Agent", options);
			if (choice === undefined) return;

			if (choice === options[0]) {
				activeAgent = null;
				pi.setActiveTools(defaultTools);
				ctx.ui.setStatus("system-prompt", "Agent: Default");
				ctx.ui.notify("Reset to Default agent", "success");
				return;
			}

			const idx = options.indexOf(choice) - 1;
			const agent = allAgents[idx];
			activeAgent = agent;

			if (agent.tools.length > 0) {
				pi.setActiveTools(agent.tools);
			} else {
				pi.setActiveTools(defaultTools);
			}

			ctx.ui.setStatus("system-prompt", `Agent: ${displayName(agent.name)}`);
			ctx.ui.notify(`Switched to: ${displayName(agent.name)}`, "success");
		},
	});

	pi.on("before_agent_start", async (event, _ctx) => {
		if (!activeAgent) return;
		return {
			systemPrompt: activeAgent.body + "\n\n" + event.systemPrompt,
		};
	});
}
