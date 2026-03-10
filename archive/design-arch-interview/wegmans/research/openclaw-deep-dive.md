# OpenClaw: Comprehensive Technical Deep Dive

## Research Task
Research the openclaw GitHub repository (https://github.com/openclaw/openclaw) to understand its architecture, Slack integration, AI model usage, prompting methods, security model, tech stack, deployment, and notable design patterns -- with the goal of informing the design of a similar but custom solution.

## Summary

OpenClaw is a self-hosted, single-user AI assistant platform that aggregates 15+ messaging channels (Slack, Discord, Telegram, WhatsApp, iMessage, Teams, etc.) into a unified inbox backed by an AI agent. It runs on your own hardware via a local WebSocket gateway, uses Anthropic's Claude as its recommended LLM (with multi-provider fallback), and provides the agent with a rich tool system (browser control, web search, file ops, cron, TTS, subagents). The Slack integration uses Slack Bolt 4.6.0 with bot/app tokens and implements streaming block-coalesced responses. The codebase is a TypeScript monorepo (~155 gateway files, ~366 agent files, 37 channel extensions, 51 skills) running on Node.js >= 22.

## Detailed Findings

### 1. What Is OpenClaw?

OpenClaw is a **personal, single-user AI assistant** designed to run locally on your devices<sup>[1](#sources)</sup>. It was originally developed as the engine behind "Molty, a space lobster AI assistant." Key characteristics:

- **Multi-channel inbox**: Consolidates WhatsApp, Telegram, Slack, Discord, Google Chat, Signal, iMessage, Microsoft Teams, Matrix, Zalo, IRC, Line, Nostr, and WebChat into one AI-powered assistant<sup>[1](#sources)</sup>
- **Local-first**: Operates through a WebSocket control plane on the user's own hardware rather than cloud infrastructure<sup>[1](#sources)</sup>
- **Always-on**: Runs as a system daemon (launchd on macOS, systemd on Linux, Task Scheduler on Windows)<sup>[5](#sources)</sup>
- **Voice-enabled**: Supports wake word detection, live talk mode via ElevenLabs TTS<sup>[1](#sources)</sup>
- **Canvas workspace**: An agent-driven visual workspace with A2UI (Agent-to-UI) support<sup>[1](#sources)</sup>
- **Companion apps**: macOS menu bar app, iOS and Android nodes for system-level actions<sup>[1](#sources)</sup>

### 2. Slack Integration

The Slack integration is implemented as a **channel extension plugin** at `extensions/slack/`<sup>[2](#sources)</sup>.

**Architecture:**
- Uses **Slack Bolt 4.6.0** (`@slack/bolt`) as the bot framework<sup>[3](#sources)</sup>
- Plugin structure: `index.ts` (entry point), `src/channel.ts` (~410 lines, main implementation), `src/runtime.ts` (runtime singleton), `openclaw.plugin.json` (plugin metadata)<sup>[2](#sources)</sup>
- Registers as a `ChannelPlugin` conforming to OpenClaw's plugin interface<sup>[2](#sources)</sup>

**Token Management:**
- `getTokenForOperation()` selects between **user tokens** (preferred for write operations) and **bot tokens** (fallback)<sup>[2](#sources)</sup>
- Supports both bot tokens and app-level tokens for different API scopes<sup>[2](#sources)</sup>

**Key Capabilities:**
- Direct messages, channels, and threads<sup>[2](#sources)</sup>
- Reactions (emoji acknowledgments for processing state)<sup>[2](#sources)</sup>
- Media support (images, files)<sup>[2](#sources)</sup>
- **Streaming responses**: Block coalescing with 1,500-character minimum and 1,000ms idle threshold before flushing<sup>[2](#sources)</sup>
- 4,000-character text limit per outbound message<sup>[2](#sources)</sup>

**Security in Slack:**
- DM policy resolution with mention requirements<sup>[2](#sources)</sup>
- Allowlist configurations for permitted channels/users<sup>[2](#sources)</sup>
- User approval notifications via Slack DMs for pairing<sup>[2](#sources)</sup>

**Plugin Configuration (openclaw.plugin.json):**
```json
{
  "id": "slack",
  "channels": ["slack"],
  "configSchema": {
    "type": "object",
    "additionalProperties": false,
    "properties": {}
  }
}
```

### 3. AI Models and APIs

**Recommended Model:** Anthropic's Claude Opus 4.6, cited for "long-context strength and better prompt-injection resistance"<sup>[1](#sources)</sup>

**Multi-Provider Support:**
The model catalog (`src/agents/model-catalog.ts`) dynamically discovers available models<sup>[4](#sources)</sup>:
- **Anthropic** (Claude family) -- primary
- **OpenAI** (GPT family, Codex) -- with a "spark" variant fallback
- **Google** (Gemini) -- with function-call sequencing handling
- **GitHub Copilot** -- with dedicated auth/token management (`github-copilot-auth.ts`, `github-copilot-token.ts`)
- **Qwen** -- via OAuth portal integration
- **AWS Bedrock** -- via `@aws-sdk/client-bedrock-runtime`
- **Ollama** -- local model support (dev dependency)
- **Vision support** detection per model via `modelSupportsVision()`<sup>[4](#sources)</sup>

**Model Selection System (`src/agents/model-selection.ts`):**
- `ModelRef` type with provider + model ID<sup>[4](#sources)</sup>
- Provider alias normalization (e.g., "z.ai" -> "zai", "opencode-zen" -> "opencode")<sup>[4](#sources)</sup>
- Configuration-driven model aliasing<sup>[4](#sources)</sup>
- **Allowlist enforcement**: Three modes -- allow-any, configured allowlist, or catalog-only<sup>[4](#sources)</sup>
- Automatic **auth profile rotation**: When one profile fails, cycles to the next available<sup>[6](#sources)</sup>
- **Model fallback**: Throws `FailoverError` to trigger provider/model switching on failure<sup>[6](#sources)</sup>

**Embedding Providers (for memory/search):**
- OpenAI embeddings
- Google Gemini embeddings
- Voyage AI embeddings
- Batch processing support for all three<sup>[7](#sources)</sup>

### 4. Architecture

```
                    +-------------------+
                    |   Messaging Apps   |
                    | Slack/Discord/TG   |
                    +--------+----------+
                             |
                    +--------v----------+
                    |  Channel Plugins   |  (37 extensions)
                    |  (Slack Bolt, etc) |
                    +--------+----------+
                             |
                    +--------v----------+
                    |  Auto-Reply Layer  |  (dispatch -> directives -> reply)
                    |  Command Gating    |
                    |  Mention Gating    |
                    +--------+----------+
                             |
                    +--------v----------+
                    |   Gateway Server   |  (Express 5.2 + WebSocket)
                    |   155 files        |
                    |   Auth, Rate Limit |
                    +--------+----------+
                             |
              +--------------+--------------+
              |                             |
    +---------v---------+        +---------v---------+
    |  Agent Runner      |        |  Session Manager  |
    |  (pi-embedded)     |        |  Send Policy      |
    |  366 files         |        |  Input Provenance  |
    +--------+-----------+        +-------------------+
             |
    +--------v-----------+
    |  AI Provider APIs   |
    |  Anthropic/OpenAI/  |
    |  Gemini/Bedrock/etc |
    +--------------------+
             |
    +--------v-----------+
    |  Tool System        |
    |  Browser, Web,      |
    |  Canvas, TTS,       |
    |  Cron, Subagents    |
    +--------------------+
             |
    +--------v-----------+
    |  Memory Layer       |
    |  SQLite + sqlite-vec|
    |  Multi-provider     |
    |  embeddings         |
    +--------------------+
```

**Core Components:**

| Component | Location | Description |
|-----------|----------|-------------|
| Gateway Server | `src/gateway/` (155 files) | Express 5.2 + WebSocket server, auth, rate limiting, HTTP endpoints |
| Agent Runner | `src/agents/` (366 files) | AI execution engine, tool loop, context window management |
| Channel Plugins | `extensions/` (37 dirs) | Messaging platform adapters (Slack, Discord, etc.) |
| Auto-Reply | `src/auto-reply/` (78 files) | Message dispatch, directive parsing, command handling |
| Memory | `src/memory/` (67 files) | SQLite + vector embeddings, hybrid search |
| Daemon | `src/daemon/` (32 files) | Cross-platform background service (launchd/systemd/schtasks) |
| CLI | `src/cli/` (119 files) | Comprehensive command-line interface |
| Plugin SDK | `src/plugin-sdk/` (17 files) | Extension development framework |
| Skills | `skills/` (51 dirs) | Modular capability extensions |

### 5. AI Prompting and Methods

**System Prompt Construction (`src/agents/pi-embedded-runner/system-prompt.ts`):**

The `buildEmbeddedSystemPrompt()` function dynamically constructs prompts from<sup>[6](#sources)</sup>:
- Workspace configuration (directory, notes)
- Agent thinking/reasoning levels
- Runtime information (agent ID, host, OS, model)
- Tool definitions and summaries
- User context (timezone, time format)
- Context files and memory citations mode
- Delegates to `buildAgentSystemPrompt()` for final assembly

**Prompt Override System:**
- `createSystemPromptOverride()` -- wraps custom prompt text
- `applySystemPromptOverrideToSession()` -- applies overrides to live `AgentSession` instances, manipulating `_baseSystemPrompt` and `_rebuildSystemPrompt`<sup>[6](#sources)</sup>

**Conversation History Management (`agent-prompt.ts`):**
- `buildAgentMessageFromConversationEntries()` processes conversation entries (user/assistant/tool roles)
- Prioritizes the **last user or tool entry** as the "current message" so the agent responds to the latest input<sup>[8](#sources)</sup>
- Builds history context from all preceding entries

**Directive System (inline commands in messages):**
- `extractElevatedDirective` -- escalate permissions
- `extractReasoningDirective` -- enable extended reasoning
- `extractThinkDirective` -- enable thinking mode
- `extractVerboseDirective` -- increase output detail
- `extractExecDirective` -- execute commands
- `extractQueueDirective` -- queue operations<sup>[9](#sources)</sup>

**Context Window Protection:<sup>[6](#sources)</sup>**
- Warns when context usage approaches limits
- Blocks models with insufficient context windows
- Automatic **session compaction** when overflow detected
- **Tool result truncation** as fallback recovery
- Compaction safety timeouts to prevent infinite loops

**Prompt Sanitization:**
- Anthropic-specific sanitization to prevent "refusal token poisoning"<sup>[6](#sources)</sup>
- Output format adaptation (markdown vs. plain text) based on channel capabilities

### 6. Security and Authentication

**Gateway Authentication (`src/gateway/auth.ts`):**

Four authentication modes<sup>[10](#sources)</sup>:

| Mode | Description |
|------|-------------|
| `none` | No authentication (local-only) |
| `token` | Bearer token via `OPENCLAW_GATEWAY_TOKEN` env var |
| `password` | Password-based via `OPENCLAW_GATEWAY_PASSWORD` env var |
| `trusted-proxy` | Reverse proxy authentication with per-header validation |

**Additional Security Layers:**
- **Tailscale integration**: Device identity verification via whois lookup for network-level auth<sup>[10](#sources)</sup>
- **Rate limiting**: Per-IP with retry-after tracking<sup>[10](#sources)</sup>
- **Timing-safe comparison**: `safeEqualSecret()` for credential validation<sup>[10](#sources)</sup>
- **Origin checking**: `origin-check.ts` in the gateway<sup>[5](#sources)</sup>

**Channel-Level Security:**
- **DM policies**: Per-channel configuration requiring pairing codes or explicit allowlisting<sup>[1](#sources)</sup>
- **Mention gating**: Group messages only processed when bot is @mentioned, with configurable bypass for authorized text commands<sup>[11](#sources)</sup>
- **Send policies**: Rule-based allow/deny decisions matching channels, chat types, and session key patterns<sup>[12](#sources)</sup>
- **Command gating**: `command-gating.ts` controls which commands are available in which contexts<sup>[5](#sources)</sup>
- **Group sandboxing**: Non-primary sessions can run in sandboxed Docker environments<sup>[1](#sources)</sup>

**Threat Model:**
- Formal **MITRE ATLAS-based threat model** documented at `docs/security/THREAT-MODEL-ATLAS.md`<sup>[13](#sources)</sup>
- 13 major threat categories identified: prompt injection (P0 critical), malicious skill installation, credential harvesting, token theft, etc.
- Known limitation: ClawHub skill marketplace moderation uses "simple regex easily bypassed"<sup>[13](#sources)</sup>
- Skills execute with agent privileges (no sandboxing yet -- noted as a gap)<sup>[13](#sources)</sup>

### 7. Key Features and Capabilities

**Agent Tools (`src/agents/openclaw-tools.ts`):**

| Tool | Capability |
|------|-----------|
| Browser | Playwright-based web automation and control |
| Canvas | Agent-driven visual workspace |
| Web Search/Fetch | Internet search and page retrieval |
| TTS | Text-to-speech via ElevenLabs / Edge TTS |
| Cron | Scheduled task execution |
| Message | Cross-channel messaging |
| Image | Media processing (when agent directory specified) |
| Sessions | List, history, send, spawn subagent sessions |
| Subagents | Multi-agent coordination and workflows |
| Nodes | Remote device control (camera, screen, etc.) |
| Bash | Shell command execution |
| File Read/Write | File system operations |

**Skills Platform (51 skills):**
Categories include productivity (Apple Notes, Notion, Obsidian, Trello), media (Spotify, Sonos), AI tools (Coding Agent, Gemini), communication (1Password, email via Himalaya), and more<sup>[14](#sources)</sup>.

**Memory System:**
- **SQLite** with **sqlite-vec** for vector storage<sup>[7](#sources)</sup>
- Hybrid search (keyword + semantic)
- Multi-provider embeddings (OpenAI, Gemini, Voyage)
- Batch processing for efficiency
- Session-file sync and index management

**Auto-Reply Pipeline:**
- Inbound debouncing to prevent duplicate processing<sup>[9](#sources)</sup>
- Command detection and routing
- Directive parsing (elevation, reasoning, model selection)
- Agent runner execution with streaming response delivery
- Reply threading and chunking for large responses

### 8. Tech Stack

| Category | Technology |
|----------|-----------|
| **Language** | TypeScript (5.9.3) |
| **Runtime** | Node.js >= 22.12.0 |
| **Package Manager** | pnpm 10.23.0 (primary), npm/bun supported |
| **Web Framework** | Express 5.2.1 |
| **Bundler** | Rolldown 1.0.0-rc.4 + tsdown |
| **Test Framework** | Vitest (unit, e2e, live, gateway configs) |
| **Linter** | oxlint + oxfmt |
| **Slack Bot** | @slack/bolt 4.6.0 |
| **Telegram Bot** | Grammy 1.40.0 |
| **Discord Bot** | Discord.js-compatible APIs |
| **Line Bot** | Line Bot SDK 10.6.0 |
| **Browser Automation** | Playwright Core 1.58.2 |
| **Image Processing** | Sharp 0.34.5 |
| **AI SDK** | Anthropic Agent Core/TUI/Coding Agent v0.52.12 |
| **Cloud AI** | AWS Bedrock client |
| **Local AI** | Ollama (dev) |
| **Database** | SQLite + sqlite-vec |
| **TTS** | ElevenLabs, Node Edge TTS |
| **PDF** | PDF.js |
| **iOS/macOS** | Swift (SwiftLint/SwiftFormat) |
| **Monorepo** | pnpm workspaces |

### 9. Deployment and Running

**Installation:**
```bash
npm install -g openclaw@latest
openclaw onboard --install-daemon
```

**Daemon Management:**
- **macOS**: launchd plist (`launchd.ts`, `launchd-plist.ts`)<sup>[5](#sources)</sup>
- **Linux**: systemd unit files with user linger support<sup>[5](#sources)</sup>
- **Windows**: Task Scheduler via schtasks<sup>[5](#sources)</sup>

**Release Channels:**
- `latest` (stable tagged releases)
- `beta` (prerelease versions)
- `dev` (moving head of main branch)<sup>[1](#sources)</sup>

**CLI Commands:**
- `openclaw onboard --install-daemon` -- initial setup wizard
- Gateway, daemon, browser, channels, models, nodes, config, and cron CLI subcommands<sup>[5](#sources)</sup>

**Companion Apps:**
- macOS menu bar app
- iOS and Android node apps (for device-level actions like camera, screen recording)

### 10. Notable Design Patterns Worth Borrowing

1. **Channel Plugin Abstraction**: The `ChannelPlugin` interface (`types.plugin.ts`) defines a comprehensive contract -- capabilities, config adapters, message handling, security, directory services, threading -- that all 37 channel extensions implement. This makes adding new channels straightforward<sup>[15](#sources)</sup>.

2. **Streaming Block Coalescing**: Rather than sending every token, Slack responses are buffered with a 1,500-char minimum and 1,000ms idle threshold before flushing. This prevents message flickering and respects rate limits<sup>[2](#sources)</sup>.

3. **Auth Profile Rotation**: The agent runner automatically rotates through auth profiles when API calls fail, tracking cooldowns and marking profiles as good/bad. Graceful degradation to fallback models on `FailoverError`<sup>[6](#sources)</sup>.

4. **Context Window Guards**: Multiple layers of protection -- warn at threshold, block insufficient models, auto-compact sessions, truncate tool results as last resort. Prevents the common "context overflow crash" problem<sup>[6](#sources)</sup>.

5. **Mention Gating for Groups**: In group chats, messages are only processed if the bot is @mentioned. Authorized text commands can bypass this via a multi-condition check. Prevents the bot from responding to every message<sup>[11](#sources)</sup>.

6. **Send Policy Engine**: Rule-based allow/deny system that matches channels, chat types, and session key patterns. Creates a flexible permission layer for controlling what the agent can do where<sup>[12](#sources)</sup>.

7. **Plugin SDK with Runtime Singleton**: The Slack runtime pattern (`runtime.ts`) uses a module-level singleton with explicit init/get functions. Simple but effective for extension lifecycle management<sup>[2](#sources)</sup>.

8. **Dynamic System Prompt Assembly**: System prompts are constructed from multiple contextual pieces (workspace, user timezone, tools, agent identity, memory mode) rather than being static strings. Enables per-session customization<sup>[6](#sources)</sup>.

9. **Directive Extraction**: Users can embed inline directives in messages (e.g., to switch models, enable reasoning, elevate permissions) that are parsed before the message reaches the agent. This gives power users control without a separate settings UI<sup>[9](#sources)</sup>.

10. **Hybrid Memory Search**: Combining SQLite full-text search with vector embeddings (via sqlite-vec) enables both keyword and semantic retrieval without external services<sup>[7](#sources)</sup>.

11. **MITRE ATLAS Threat Modeling**: Formal adversarial threat model as part of the project documentation. Unusual for an open-source project and valuable for security-conscious deployments<sup>[13](#sources)</sup>.

12. **Barrel Export Pattern**: Extensive use of TypeScript barrel exports (e.g., `reply.ts`, `pi-embedded-runner.ts`) to create clean public APIs while keeping implementation details in subdirectories<sup>[9](#sources)</sup>.

## Concerns/Notes

- **Skills run with full agent privileges** -- the threat model explicitly flags this as a P0 risk with no sandboxing yet<sup>[13](#sources)</sup>
- **ClawHub moderation** relies on "simple regex easily bypassed" -- acknowledged limitation<sup>[13](#sources)</sup>
- **Prompt injection** is rated as Critical (P0) residual risk even with mitigations<sup>[13](#sources)</sup>
- The project is very large (~1,000+ source files) and moves fast -- the version was `2026.2.16` (date-based versioning), suggesting daily releases
- The Slack plugin config schema is currently empty (`"properties": {}`) -- all actual configuration appears to be handled through the broader OpenClaw config system rather than per-plugin schemas
- The project is **single-user** by design -- not built for multi-tenant/team scenarios
- Anthropic's Agent Core SDK (v0.52.12) is deeply integrated -- this is a significant dependency to be aware of if building something similar

## Sources

1. OpenClaw README - https://github.com/openclaw/openclaw/blob/main/README.md
2. Slack Extension Source - https://github.com/openclaw/openclaw/tree/main/extensions/slack
3. Root package.json - https://github.com/openclaw/openclaw/blob/main/package.json
4. Model Catalog & Selection - https://github.com/openclaw/openclaw/blob/main/src/agents/model-catalog.ts
5. Daemon & CLI - https://github.com/openclaw/openclaw/tree/main/src/daemon
6. Agent Runner (pi-embedded-runner) - https://github.com/openclaw/openclaw/tree/main/src/agents/pi-embedded-runner
7. Memory System - https://github.com/openclaw/openclaw/tree/main/src/memory
8. Agent Prompt Builder - https://github.com/openclaw/openclaw/blob/main/src/gateway/agent-prompt.ts
9. Auto-Reply System - https://github.com/openclaw/openclaw/tree/main/src/auto-reply
10. Gateway Authentication - https://github.com/openclaw/openclaw/blob/main/src/gateway/auth.ts
11. Mention Gating - https://github.com/openclaw/openclaw/blob/main/src/channels/mention-gating.ts
12. Send Policy - https://github.com/openclaw/openclaw/blob/main/src/sessions/send-policy.ts
13. Threat Model - https://github.com/openclaw/openclaw/blob/main/docs/security/THREAT-MODEL-ATLAS.md
14. Skills Platform - https://github.com/openclaw/openclaw/tree/main/skills
15. Channel Plugin Types - https://github.com/openclaw/openclaw/blob/main/src/channels/plugins/types.plugin.ts
