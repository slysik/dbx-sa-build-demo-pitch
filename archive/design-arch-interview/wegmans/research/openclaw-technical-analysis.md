# OpenClaw Technical Architecture Analysis

## Research Task
Research the GitHub repository https://github.com/openclaw/openclaw to understand: what OpenClaw is, its Slack integration, AI models/APIs used, architecture (agent framework, tools, memory system), prompt/system instruction handling, AI assistant patterns, security measures, and key files/configuration patterns.

## Summary
OpenClaw is a self-hosted, local-first personal AI assistant that connects to 20+ messaging platforms (WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Teams, etc.) through a unified WebSocket-based Gateway control plane. It wraps an embedded agent runtime derived from "pi-mono" and supports 15+ AI model providers including Anthropic, OpenAI, Google Gemini, and local models via Ollama. The project is MIT-licensed, has 201k+ GitHub stars, and is built as a TypeScript/Node.js monorepo with a plugin architecture for channels, skills, and extensions. Its key architectural differentiators are: (1) a hub-and-spoke Gateway model where all channels funnel through a single local process, (2) a hybrid memory system combining Markdown files with SQLite vector search, (3) a comprehensive security model with DM pairing, tool policies, Docker sandboxing, and audit tooling.

## Detailed Findings

### 1. What Is OpenClaw?

OpenClaw is a personal AI coding assistant that runs entirely on the user's own hardware<sup>[1](#sources)</sup>. It connects messaging platforms to an AI agent runtime, allowing users to interact with AI through their existing chat applications. The Gateway process runs locally at `ws://127.0.0.1:18789` and serves as the single source of truth for all sessions, routing, and channel connections<sup>[2](#sources)</sup>.

Key capabilities include:
- Multi-channel messaging (20+ platforms simultaneously)
- Voice Wake and Talk Mode (macOS/iOS/Android via ElevenLabs)
- Live Canvas with agent-driven visual workspace (A2UI)
- Browser control (dedicated Chrome/Chromium management)
- Cron jobs, webhooks, Gmail Pub/Sub automation
- Cross-platform apps (macOS menu bar, iOS/Android nodes, CLI, Web UI)

Installation requires Node >= 22:
```bash
npm install -g openclaw@latest
openclaw onboard --install-daemon
```

### 2. Slack Integration

The Slack extension is a plugin (`extensions/slack/`) built on the OpenClaw Plugin SDK<sup>[3](#sources)</sup>. It supports two connection methods:

**Socket Mode (Default):** Requires a Slack App Token (`xapp-...`) with `connections:write` scope and a Bot Token (`xoxb-...`). Uses WebSocket for real-time events<sup>[4](#sources)</sup>.

**HTTP Events API Mode:** Uses a Bot Token plus a signing secret, with a configurable webhook path (default `/slack/events`)<sup>[4](#sources)</sup>.

Key Slack features:
- **Threading**: Isolated thread sessions with configurable history limits (default 20 messages)
- **Access Control**: DM policies (pairing/allowlist/open/disabled) and channel policies (open/allowlist/disabled)
- **Media**: File attachment downloads up to 20MB, text chunking at 4000 characters
- **Commands**: Native Slack slash commands with ephemeral responses
- **Events**: Maps message edits/deletes, reactions, member changes, pins to system events
- **Multi-account**: Supports multiple Slack workspace accounts simultaneously
- **User Token**: Optional `xoxp-...` token for read operations (write capability configurable)

Source structure:
```
extensions/slack/
  index.ts              # Plugin entry point (registers channel via api.registerChannel())
  openclaw.plugin.json  # Plugin metadata: {"id": "slack", "channels": ["slack"]}
  package.json
  src/
    channel.ts          # Core channel implementation (auth, messaging, event handling)
    runtime.ts          # Lazy initialization pattern for PluginRuntime singleton
```

The channel implementation uses a token selection strategy: read operations prioritize user tokens (falling back to bot token), while write operations default to bot token unless explicitly configured otherwise<sup>[3](#sources)</sup>.

### 3. AI Models and APIs

OpenClaw supports 15+ AI model providers through a dynamic model catalog system<sup>[5](#sources)</sup><sup>[6](#sources)</sup>:

| Provider | Auth Method | Example Model |
|----------|------------|---------------|
| Anthropic | `ANTHROPIC_API_KEY` or setup token | `anthropic/claude-opus-4-6` |
| OpenAI | `OPENAI_API_KEY` | `openai/gpt-5.1-codex` |
| OpenAI Codex | OAuth (ChatGPT) | `openai-codex/gpt-5.3-codex` |
| Google Gemini (API) | `GEMINI_API_KEY` | `google/gemini-3-pro-preview` |
| Google Vertex | gcloud ADC | varies |
| OpenRouter | `OPENROUTER_API_KEY` | `openrouter/anthropic/claude-sonnet-4-5` |
| xAI | `XAI_API_KEY` | varies |
| Groq | `GROQ_API_KEY` | varies |
| Mistral | `MISTRAL_API_KEY` | varies |
| GitHub Copilot | `COPILOT_GITHUB_TOKEN` | varies |
| Hugging Face | `HUGGINGFACE_HUB_TOKEN` | varies |
| Ollama (local) | None | `ollama/llama3.3` |
| vLLM | Optional | `vllm/your-model-id` |
| Moonshot/Kimi | `MOONSHOT_API_KEY` | `moonshot/kimi-k2.5` |
| MiniMax | `MINIMAX_API_KEY` | varies |

Default model aliases<sup>[7](#sources)</sup>:
- `opus` -> `anthropic/claude-opus-4-6`
- `sonnet` -> `anthropic/claude-sonnet-4-5`
- `gpt` -> `openai/gpt-5.2`
- `gemini` -> `google/gemini-3-pro-preview`

Model references follow `provider/model` format. Custom OpenAI/Anthropic-compatible proxies can be added via the `models.providers` configuration.

**Embedding Providers** (for memory/vector search, auto-selected in priority order):
1. Local embeddings (if configured)
2. OpenAI
3. Gemini
4. Voyage

### 4. Architecture

#### 4a. Overall Architecture (Hub-and-Spoke)

```
Chat Apps/Plugins --> Gateway (ws://127.0.0.1:18789) --> Agent Runtime (pi-mono)
                                    |
                     +--------------+--------------+
                     |              |              |
                   CLI          Web UI        macOS App
                                              iOS/Android
```

The Gateway is the central control plane managing sessions, routing, and channel connections<sup>[2](#sources)</sup>. All channels, tools, and clients connect through it.

#### 4b. Agent Framework

The agent runtime is derived from "pi-mono" and runs as a single embedded agent<sup>[8](#sources)</sup>. Key components in `src/agents/` (366 files):

- **`pi-embedded-runner.ts`**: Core agent execution pipeline - processes messages via `runEmbeddedPiAgent`, queues via `queueEmbeddedPiMessage`
- **`model-catalog.ts`** / **`model-selection.ts`**: Dynamic model discovery and resolution with alias mapping and provider normalization
- **`tool-policy.ts`**: Four access profiles (minimal, coding, messaging, full) with group-based permissions
- **`subagent-registry.ts`** / **`subagent-depth.ts`**: Sub-agent spawning and orchestration
- **`session-write-lock.ts`**: Concurrency control for session state
- **`bash-tools.ts`**: Shell command execution tools

Tool profiles define access levels<sup>[9](#sources)</sup>:
- `minimal`: Only `session_status`
- `coding`: File system, runtime execution, sessions, memory
- `messaging`: Messaging and session management
- `full`: Unrestricted access

#### 4c. Tools System

The `src/agents/tools/` directory contains 68 files implementing agent capabilities<sup>[10](#sources)</sup>:

| Category | Tools |
|----------|-------|
| Communication | Discord, Slack, Telegram, WhatsApp actions, message tool |
| Web | Web fetch, search, browser control with schema |
| Session | Spawn, send, list, history, A2A protocol |
| System | Agent step, canvas, cron, gateway, memory, TTS |
| Integration | Nodes, subagents |

Core tools (read, exec, edit, write) are always available, subject to tool policy<sup>[8](#sources)</sup>.

#### 4d. Memory System

The memory system (`src/memory/`, 67 files) uses a dual-layer architecture<sup>[11](#sources)</sup>:

**Storage Layer** (Markdown-first):
- **Daily logs** (`memory/YYYY-MM-DD.md`): Append-only notes loaded at session start
- **Long-term memory** (`MEMORY.md`): Curated facts, preferences, decisions (private sessions only)
- Files reside in `~/.openclaw/workspace`

**Search Layer** (SQLite + Vector):
- `chunks_vec`: Vectorized content segments (~400 tokens, 80-token overlap)
- `chunks_fts`: Full-text search (BM25) index
- `embedding_cache`: Cached embeddings to reduce API calls
- **Hybrid search**: Combines vector similarity with BM25 keyword matching

**Memory Tools**:
- `memory_search`: Semantic search across Markdown chunks
- `memory_get`: Direct file read with optional line filtering

**Automatic Memory Flush**: Triggers before context compaction, prompting the model to preserve durable information<sup>[11](#sources)</sup>.

**Optional QMD Backend**: Local-first search sidecar combining BM25, vectors, and reranking under `~/.openclaw/agents/<agentId>/qmd/`.

#### 4e. Skills System

The `skills/` directory contains 51 skill modules<sup>[12](#sources)</sup> organized by category:

- **Integrations**: 1Password, GitHub, Notion, Trello, Obsidian, Spotify, Sonos
- **Apple ecosystem**: Notes, Reminders, Bear Notes, Things
- **Communication**: BlueBubbles, iMessage, Voice Call, WhatsApp CLI
- **Media**: GifGrep, Video Frames, Camsnap
- **Utilities**: Weather, Healthcheck, Summarize, Coding Agent
- **Custom**: Skill Creator for user-built skills

Skills are loaded from three locations: bundled installations, managed local directories, and workspace-specific folders<sup>[8](#sources)</sup>.

#### 4f. Plugin/Extension System

Extensions (`extensions/`, 37 directories) follow a consistent plugin SDK pattern<sup>[13](#sources)</sup>:
```typescript
// extensions/<name>/index.ts
export default {
  id: "slack",
  name: "Slack",
  configSchema: emptyPluginConfigSchema(),
  register(api: OpenClawPluginApi) {
    setSlackRuntime(api.runtime);
    api.registerChannel(slackPlugin);
  }
}
```

Each extension has: `index.ts` (entry), `openclaw.plugin.json` (metadata), `package.json`, and `src/` (implementation).

### 5. Prompts and System Instructions

OpenClaw constructs custom system prompts per agent run (not using the pi-coding-agent default)<sup>[14](#sources)</sup>. The prompt is assembled from fixed sections:

**Fixed Prompt Sections**:
- Tooling (current tool list with descriptions)
- Safety (guardrail reminders against power-seeking/oversight bypass)
- Skills (loading instructions)
- Self-Update guidance
- Workspace (working directory)
- Documentation (local docs path)
- Sandbox info (when enabled)
- Date/Time (user timezone)
- Reply tags (for supported providers)
- Heartbeats (prompt/ack behavior)
- Runtime (host, OS, node version, model, repo root, thinking level)

**Three Prompt Modes**:
- **Full** (default): All sections
- **Minimal**: For sub-agents; omits skills, self-update, reply tags, heartbeats
- **None**: Identity line only

**Bootstrap File Injection** (loaded into context on every turn):

| File | Purpose |
|------|---------|
| `AGENTS.md` | Operating instructions and memory |
| `SOUL.md` | Persona, boundaries, tone |
| `TOOLS.md` | User-maintained tool guidance |
| `IDENTITY.md` | Agent name and personality |
| `USER.md` | User profile information |
| `HEARTBEAT.md` | Heartbeat configuration |
| `BOOTSTRAP.md` | Bootstrap instructions |
| `MEMORY.md` | Curated long-term memory |

Per-file cap: 20,000 characters. Total cap: 150,000 characters. Oversized content is truncated<sup>[14](#sources)</sup>.

**Per-Channel Custom Prompts**: Slack (and other channels) support per-channel system prompt overrides via configuration.

### 6. AI Assistant Patterns

**Message Processing Pipeline**<sup>[8](#sources)</sup>:
1. Inbound message received via channel (e.g., Slack WebSocket)
2. Gateway routes to appropriate session
3. Agent runtime queues message via `queueEmbeddedPiMessage`
4. Bootstrap files injected into context
5. Model invoked with system prompt + conversation history
6. Tool calls executed (subject to policy/sandbox)
7. Response streamed back to channel

**Queue Modes** for handling concurrent inbound messages:
- **Steer**: Injects messages after each tool call, skipping remaining
- **Followup/Collect**: Queues messages until turn completion

**Context Management**:
- `limitHistoryTurns` with session-specific DM/group limits
- Context pruning mode: `"cache-ttl"` with 1-hour TTL (default)
- Compaction mode: `"safeguard"` (preserves critical context)
- Automatic memory flush before compaction

**Model Failover** (two-stage)<sup>[15](#sources)</sup>:
1. Auth profile rotation: Cycles through credentials for current provider
2. Model fallback: Switches to next model in `agents.defaults.model.fallbacks`
- Session stickiness: Pins auth profile per session for cache efficiency
- Exponential backoff: 1min -> 5min -> 25min -> 1hr cap (rate limits); 5hr -> 24hr cap (billing)

**Streaming/Chunking**: Block streaming sends completed assistant blocks as they finish (off by default). Configurable paragraph/sentence boundary splitting<sup>[8](#sources)</sup>.

### 7. Security Measures

**DM Pairing** (default for all channels)<sup>[1](#sources)</sup>:
- Unknown senders receive a pairing code before messages are processed
- Must be approved via `openclaw pairing approve <channel> <code>`
- Alternatives: allowlist, open (with explicit wildcard), disabled

**Tool Policy System** (`src/agents/tool-policy.ts`)<sup>[9](#sources)</sup>:
- Four access profiles: minimal, coding, messaging, full
- Tool groups for bulk permissions (`group:fs`, `group:runtime`)
- Allow/deny lists with expansion logic
- `tools.alsoAllow` for additive permissions
- Owner-only tool protection (e.g., `whatsapp_login`)

**Dangerous Tools Classification** (`src/security/dangerous-tools.ts`)<sup>[16](#sources)</sup>:

| Context | Restricted Tools | Reason |
|---------|-----------------|--------|
| Gateway HTTP | `sessions_spawn`, `sessions_send`, `gateway`, `whatsapp_login` | RCE risk, control-plane actions |
| ACP (Automation) | `exec`, `spawn`, `shell`, `sessions_spawn`, `sessions_send`, `gateway`, `fs_write`, `fs_delete`, `fs_move`, `apply_patch` | Silent approval rejected for mutations |

**Docker Sandboxing** (`sandbox` config)<sup>[17](#sources)</sup>:
- Three modes: off, non-main (default), all
- Container scope: session-level, agent-level, or shared
- Workspace access: none (default), read-only, read/write
- Custom host mounts with blocked dangerous sources (docker.sock, /etc, /proc, /sys, /dev)
- `tools.elevated` for explicit host execution escape hatch

**Security Audit System** (`src/security/`, 21 files)<sup>[18](#sources)</sup>:
- `openclaw doctor` surfaces risky configurations
- Audits: gateway config, filesystem permissions, tool policies, logging redaction, browser auth, channel plugin security, hook hardening, model hygiene, skill code safety
- Severity levels: critical, warn, info with remediation guidance
- Secret detection (`.detect-secrets.cfg`)
- Filesystem permission checks (world-writable, group-writable)
- Elevated tool execution allowlist size limits (>25 flagged)

**Logging Redaction**: Defaults to redacting sensitive data in tool outputs<sup>[7](#sources)</sup>.

**System Prompt Safety**: "Safety guardrails in the system prompt are advisory" -- hard enforcement requires tool policy, exec approvals, and sandboxing<sup>[14](#sources)</sup>.

### 8. Key Files and Configuration Patterns

**Configuration File**: `~/.openclaw/openclaw.json`<sup>[1](#sources)</sup>

Minimal example:
```json
{
  "agent": {
    "model": "anthropic/claude-opus-4-6"
  }
}
```

**Key Directory Structure**:
```
~/.openclaw/
  openclaw.json                              # Main config
  workspace/                                 # Agent workspace root
    memory/YYYY-MM-DD.md                     # Daily memory logs
    MEMORY.md                                # Long-term memory
    AGENTS.md, SOUL.md, TOOLS.md, etc.       # Bootstrap files
  agents/<agentId>/
    agent/auth-profiles.json                 # Credential storage
    sessions/<sessionId>.jsonl               # Session transcripts
    qmd/                                     # Optional QMD search sidecar
```

**Repository Structure** (key directories):
```
openclaw/openclaw/
  src/
    agents/       (366 files) Agent runtime, model catalog, tool policies, sub-agents
    memory/       (67 files)  Memory manager, embeddings, vector search, hybrid retrieval
    security/     (21 files)  Audit, dangerous tools, skill scanner, ACLs
    config/       (40+ files) Zod schemas, validation, env substitution, defaults
    channels/                 Core channel abstractions
    providers/                AI provider auth (Copilot, Google, Qwen)
    gateway/                  WebSocket Gateway server
    sessions/                 Session lifecycle management
    browser/                  Chrome/Chromium control
    pairing/                  DM pairing flow
  extensions/   (37 dirs)    Channel plugins (Slack, Discord, Telegram, etc.)
  skills/       (51 dirs)    Modular capabilities (GitHub, Spotify, Weather, etc.)
  packages/                  Sub-packages (clawdbot, moltbot)
  apps/                      Application code
  ui/                        Web UI dashboard
  docs/                      Documentation source
  vendor/a2ui/               A2UI visual workspace vendor
```

**Configuration Schema** (Zod-based validation):
- `zod-schema.providers.ts`: Provider configuration validation
- `zod-schema.channels.ts`: Channel-specific schemas
- Platform-specific type files for each supported channel
- `env-substitution.ts`: Environment variable interpolation in config
- `merge-config.ts`: Multi-source configuration merging

**Monorepo Tooling**: pnpm workspaces (`pnpm-workspace.yaml`), TypeScript throughout, vitest for testing.

## Concerns/Notes

- The repository name and URL (https://github.com/openclaw/openclaw) maps to a project with 201k+ stars, which is exceptionally high. The project appears to be a fork/rename of a well-known open-source AI assistant project.
- Documentation references both `openclaw.ai` and `docs.openclaw.ai` as official sites.
- The agent runtime is described as derived from "pi-mono," and the embedded runner references "Pi" -- suggesting the core AI agent engine predates the OpenClaw branding.
- System prompt safety guardrails are explicitly described as "advisory" -- the project relies on tool policies, sandbox isolation, and exec approvals for hard enforcement rather than prompt-level instructions.
- The 73 security advisories listed on GitHub warrant review for any production deployment.
- Memory system defaults to Markdown files as the source of truth, with vector/SQLite as a search acceleration layer -- this means memory is human-readable and portable but potentially large for long-running agents.

## Sources
1. OpenClaw GitHub Repository README - https://github.com/openclaw/openclaw
2. OpenClaw Documentation - Index/Overview - https://docs.openclaw.ai
3. Slack Extension Source Code - https://github.com/openclaw/openclaw/tree/main/extensions/slack
4. Slack Channel Documentation - https://docs.openclaw.ai/channels/slack
5. Model Providers Documentation - https://docs.openclaw.ai/concepts/model-providers
6. Model Catalog Source - https://github.com/openclaw/openclaw/blob/main/src/agents/model-catalog.ts
7. Configuration Defaults Source - https://github.com/openclaw/openclaw/blob/main/src/config/defaults.ts
8. Agent Runtime Documentation - https://docs.openclaw.ai/concepts/agent
9. Tool Policy Source - https://github.com/openclaw/openclaw/blob/main/src/agents/tool-policy.ts
10. Agent Tools Directory - https://github.com/openclaw/openclaw/tree/main/src/agents/tools
11. Memory System Documentation - https://docs.openclaw.ai/concepts/memory
12. Skills Directory - https://github.com/openclaw/openclaw/tree/main/skills
13. Extensions Directory - https://github.com/openclaw/openclaw/tree/main/extensions
14. System Prompt Documentation - https://docs.openclaw.ai/concepts/system-prompt
15. Model Failover Documentation - https://docs.openclaw.ai/concepts/model-failover
16. Dangerous Tools Source - https://github.com/openclaw/openclaw/blob/main/src/security/dangerous-tools.ts
17. Sandboxing Documentation - https://docs.openclaw.ai/gateway/sandboxing
18. Security Audit Source - https://github.com/openclaw/openclaw/tree/main/src/security
