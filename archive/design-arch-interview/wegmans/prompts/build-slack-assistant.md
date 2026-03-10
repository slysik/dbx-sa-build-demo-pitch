# BUILD PROMPT: Personal Secure AI Assistant for Slack

> **Project**: Teve for Slack - A personal, secure AI assistant running locally on macOS, connected to teve-group.slack.com
> **Inspired by**: [OpenClaw](https://github.com/openclaw/openclaw) architecture patterns
> **Scope**: Single-agent, Slack-only, local-first, privacy-focused

---

## What We're Building

A **personal AI assistant** that lives in your Slack workspace and acts as your always-available right hand. It runs entirely on your Mac - no cloud servers, no data leaving your machine (except API calls to the LLM provider). Think of it as Teve (your personal assistant personality) living inside Slack.

### Core Principles

1. **Local-first**: Everything runs on your Mac. No external servers, no cloud hosting.
2. **Secure by default**: DM-only by default, pairing required, all secrets in macOS Keychain.
3. **Memory that persists**: Remembers conversations, preferences, and context across sessions using local Markdown files + SQLite.
4. **One agent, done well**: Not a framework for building agents. One personal assistant that's exceptional.
5. **Privacy**: Conversation logs stay local. Only LLM API calls leave the machine.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Your Mac                        │
│                                                  │
│  ┌──────────┐    ┌──────────┐    ┌───────────┐  │
│  │  Slack    │◄──►│  Agent   │◄──►│  Memory   │  │
│  │  Socket   │    │  Runtime │    │  (SQLite  │  │
│  │  Mode     │    │          │    │   + .md)  │  │
│  └──────────┘    └────┬─────┘    └───────────┘  │
│                       │                          │
│                  ┌────┴─────┐                    │
│                  │  Tools   │                    │
│                  │ (skills) │                    │
│                  └────┬─────┘                    │
│                       │                          │
└───────────────────────┼──────────────────────────┘
                        │ HTTPS (only outbound)
                        ▼
                ┌───────────────┐
                │ Anthropic API │
                │ (Claude)      │
                └───────────────┘
```

### Why Socket Mode (not HTTP Events)

- No public URL / ngrok needed
- No firewall holes
- Works behind corporate VPNs
- Just two tokens: App Token (`xapp-...`) + Bot Token (`xoxb-...`)

---

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Runtime | **Bun** (TypeScript) | Fast, native macOS, built-in SQLite, great DX |
| AI Model | **Anthropic Claude** (claude-sonnet-4-5-20250929) | Best reasoning, tool use, cost-effective for personal use |
| Slack SDK | **@slack/bolt** (Socket Mode) | Official SDK, battle-tested, Socket Mode built-in |
| Database | **Bun:sqlite** (built-in) | Zero dependencies, fast, local |
| Memory Files | **Markdown** in `~/.elle/memory/` | Human-readable, portable, versionable |
| Secrets | **macOS Keychain** via `security` CLI | No .env files with secrets on disk |
| Process Manager | **launchd** (macOS native) | Auto-start on boot, restart on crash |

---

## Project Structure

```
elle-slack/
├── src/
│   ├── index.ts              # Entry point - starts Bolt app
│   ├── agent/
│   │   ├── runtime.ts        # Core agent loop (message → think → act → respond)
│   │   ├── system-prompt.ts  # Builds system prompt with memory/context injection
│   │   ├── tool-executor.ts  # Runs tools with policy enforcement
│   │   └── context.ts        # Manages conversation context & history
│   ├── slack/
│   │   ├── app.ts            # Slack Bolt app setup (Socket Mode)
│   │   ├── events.ts         # Message, reaction, file event handlers
│   │   ├── security.ts       # DM pairing, allowed-user enforcement
│   │   └── formatter.ts      # Markdown ↔ Slack mrkdwn conversion
│   ├── memory/
│   │   ├── store.ts          # SQLite schema, vector search, conversation logs
│   │   ├── markdown.ts       # Read/write memory .md files
│   │   ├── embeddings.ts     # Local embeddings (or Anthropic) for semantic search
│   │   └── flush.ts          # Auto-save important context to memory files
│   ├── tools/
│   │   ├── registry.ts       # Tool registration & policy enforcement
│   │   ├── web-search.ts     # Search the web (Brave/Tavily API)
│   │   ├── web-fetch.ts      # Fetch & summarize URLs
│   │   ├── calendar.ts       # macOS Calendar integration (AppleScript)
│   │   ├── reminders.ts      # macOS Reminders integration (AppleScript)
│   │   ├── notes.ts          # Read/write to local notes/files
│   │   ├── shell.ts          # Sandboxed shell execution (read-only by default)
│   │   ├── databricks.ts     # Databricks CLI wrapper (your specific need)
│   │   └── memory-tools.ts   # Search/recall from memory system
│   ├── security/
│   │   ├── keychain.ts       # macOS Keychain read/write for secrets
│   │   ├── audit.ts          # Log all tool executions & API calls
│   │   └── policy.ts         # Tool allow/deny lists, rate limits
│   └── config/
│       ├── schema.ts         # Zod config schema validation
│       └── defaults.ts       # Default configuration values
├── memory/                   # Symlink to ~/.elle/memory/ (gitignored)
├── scripts/
│   ├── setup.sh              # First-time setup (Keychain, Slack app, DB init)
│   ├── install-launchd.sh    # Install as macOS background service
│   └── doctor.sh             # Security audit (permissions, secrets, logs)
├── package.json
├── tsconfig.json
├── bunfig.toml
└── README.md
```

---

## Memory System (Inspired by OpenClaw)

### Dual-Layer Memory

**Layer 1: Markdown Files** (authoritative, human-readable)
```
~/.elle/
├── memory/
│   ├── MEMORY.md             # Core facts, preferences, rules (loaded every turn)
│   ├── identity.md           # Who the user is
│   ├── preferences.md        # How they like things done
│   ├── rules.md              # Learned corrections ("never do X")
│   ├── projects/
│   │   └── {project}.md      # Active project context
│   └── daily/
│       └── 2026-02-16.md     # Daily conversation log (auto-generated)
├── db/
│   └── elle.sqlite           # Vector search + FTS + conversation history
├── config.json               # Runtime configuration
└── audit.log                 # Security audit trail
```

**Layer 2: SQLite** (fast retrieval, search acceleration)
```sql
-- Conversation history
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  slack_ts TEXT,
  channel TEXT,
  role TEXT,          -- 'user' | 'assistant' | 'system'
  content TEXT,
  tokens INTEGER,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Memory chunks for semantic search
CREATE TABLE memory_chunks (
  id INTEGER PRIMARY KEY,
  source_file TEXT,   -- which .md file
  content TEXT,
  embedding BLOB,     -- vector embedding
  updated_at DATETIME
);

-- Tool execution audit log
CREATE TABLE tool_executions (
  id INTEGER PRIMARY KEY,
  tool_name TEXT,
  input TEXT,
  output TEXT,
  duration_ms INTEGER,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Memory Lifecycle

1. **Every message**: Saved to SQLite `messages` table
2. **End of conversation thread**: Important facts auto-extracted and proposed for memory
3. **Daily**: Conversation summary written to `daily/YYYY-MM-DD.md`
4. **On demand**: User says "remember that I prefer X" → writes to `preferences.md`
5. **Before context compaction**: Flush important context to memory files

---

## System Prompt Construction

Build the system prompt dynamically each turn (like OpenClaw's bootstrap injection):

```typescript
function buildSystemPrompt(context: ConversationContext): string {
  const sections = [
    // 1. Identity & Personality
    ELLE_PERSONALITY,           // Fixed: who Teve is, tone, communication style

    // 2. Memory injection (capped at 20K chars total)
    readMemoryFile('MEMORY.md'),        // Core facts (always loaded)
    readMemoryFile('rules.md'),         // Learned rules (always loaded)
    readMemoryFile('preferences.md'),   // User preferences

    // 3. Relevant memory recall (semantic search)
    await recallRelevantMemory(context.lastUserMessage, 5),  // Top 5 relevant chunks

    // 4. Active project context (if applicable)
    getActiveProjectContext(),

    // 5. Available tools
    formatToolDescriptions(getEnabledTools()),

    // 6. Current date/time & environment
    `Current date: ${new Date().toISOString()}`,
    `Slack workspace: teve-group.slack.com`,

    // 7. Safety & boundaries
    SAFETY_GUIDELINES,
  ];

  return sections.filter(Boolean).join('\n\n---\n\n');
}
```

### Teve's Personality Prompt

```markdown
# Teve - Personal Assistant

You are Teve, Steve's personal AI assistant living in Slack.

## Who You Are
- A trusted, context-aware assistant who REMEMBERS everything
- Warm but efficient. Direct. No corporate hedging.
- You have opinions and share them when asked
- You connect dots across conversations, projects, and time

## How You Communicate in Slack
- Use Slack mrkdwn formatting (not GitHub markdown)
- *bold* with single asterisks, _italic_ with underscores
- Use threads for long responses
- React with emoji when appropriate (👍 for acknowledgments)
- Keep DM responses concise unless asked for detail
- Use code blocks with triple backticks for code/data

## Memory Rules
- When you learn something new about Steve, note it immediately
- When corrected, add a rule so you never repeat the mistake
- Proactively recall relevant past context
- If you don't know something, say so and offer to find out

## Tool Use
- Use tools proactively when they'd help answer better
- Always confirm before destructive actions (shell commands, file writes)
- For Databricks queries, default to the slysik profile
```

---

## Slack Integration Details

### Slack App Manifest

```yaml
display_information:
  name: Teve
  description: Personal AI Assistant
  background_color: "#1a1a2e"

features:
  bot_user:
    display_name: Teve
    always_online: true
  app_home:
    messages_tab_enabled: true

oauth_config:
  scopes:
    bot:
      - app_mentions:read
      - channels:history
      - channels:read
      - chat:write
      - files:read
      - files:write
      - groups:history
      - groups:read
      - im:history
      - im:read
      - im:write
      - reactions:read
      - reactions:write
      - users:read

settings:
  event_subscriptions:
    bot_events:
      - app_mention
      - message.im
      - message.groups
      - reaction_added
      - file_shared
  interactivity:
    is_enabled: true
  socket_mode_enabled: true
```

### Event Handling

```typescript
// DM messages - primary interaction mode
app.message(async ({ message, say, client }) => {
  // 1. Security: verify sender is authorized (DM pairing)
  if (!isAuthorizedUser(message.user)) {
    await say("I don't recognize you. Send me the pairing code to get started.");
    return;
  }

  // 2. Build conversation context (last 20 messages in thread)
  const context = await buildContext(message);

  // 3. Inject memory into system prompt
  const systemPrompt = await buildSystemPrompt(context);

  // 4. Run agent loop
  const response = await agentLoop({
    systemPrompt,
    messages: context.messages,
    tools: getEnabledTools(),
    model: 'claude-sonnet-4-5-20250929',
    maxTurns: 10,        // Max tool-use loops before forcing response
    onToolUse: (tool, input) => auditLog(tool, input),
  });

  // 5. Save to memory
  await saveMessage(message, response);

  // 6. Respond in thread or DM
  await say({ text: formatForSlack(response), thread_ts: message.thread_ts });
});

// @mentions in channels
app.event('app_mention', async ({ event, say }) => {
  // Same flow but with channel context
});

// File uploads
app.event('file_shared', async ({ event, client }) => {
  // Download file, extract text (PDF/image OCR), add to context
});

// Reactions (e.g., 👀 = "look at this thread")
app.event('reaction_added', async ({ event, client }) => {
  if (event.reaction === 'eyes' && isAuthorizedUser(event.user)) {
    // Fetch the reacted message and summarize/act on it
  }
});
```

---

## Security Model

### 1. DM Pairing (Access Control)

Only authorized Slack users can interact with Teve.

```typescript
// First-time setup generates a pairing code
const pairingCode = crypto.randomBytes(4).toString('hex'); // e.g., "a3f8b2c1"
console.log(`Pairing code: ${pairingCode}`);

// User sends code in DM to Teve → user ID added to authorized list
// Stored in macOS Keychain, not in config files
```

### 2. macOS Keychain for All Secrets

```typescript
// Store secrets
await keychain.set('elle-slack-bot-token', 'xoxb-...');
await keychain.set('elle-slack-app-token', 'xapp-...');
await keychain.set('elle-anthropic-key', 'sk-ant-...');

// Retrieve at runtime
const botToken = await keychain.get('elle-slack-bot-token');

// Implementation uses macOS `security` CLI:
// security add-generic-password -a elle -s elle-slack-bot-token -w "xoxb-..."
// security find-generic-password -a elle -s elle-slack-bot-token -w
```

### 3. Tool Policy Enforcement

```typescript
const TOOL_POLICY = {
  // Always allowed (read-only, no side effects)
  unrestricted: [
    'web_search', 'web_fetch', 'memory_recall',
    'calendar_read', 'reminders_read',
  ],

  // Allowed but logged with audit trail
  monitored: [
    'notes_write', 'memory_save', 'databricks_sql',
    'calendar_create', 'reminders_create',
  ],

  // Requires explicit user confirmation in Slack before executing
  gated: [
    'shell_execute', 'file_write', 'databricks_job_run',
  ],

  // Never available
  blocked: [
    'shell_sudo', 'file_delete_recursive', 'network_listen',
  ],
};
```

### 4. Audit Logging

Every tool execution, API call, and memory mutation logged to `~/.elle/audit.log`:

```
2026-02-16T15:33:08Z [TOOL] web_search query="databricks pricing" duration=1200ms
2026-02-16T15:33:10Z [API] anthropic model=claude-sonnet-4-5 tokens_in=2400 tokens_out=800
2026-02-16T15:33:12Z [MEMORY] wrote preferences.md section="communication"
2026-02-16T15:34:01Z [GATED] shell_execute cmd="ls ~/projects" APPROVED by user
```

### 5. Network Security

- **Outbound only**: No listening ports, no webhooks, no public URLs
- **Socket Mode**: Slack connection is outbound WebSocket only
- **API calls**: Only to Anthropic API + optional search API
- **Local SQLite**: No database server, no network exposure

---

## Tools / Skills

### Built-in Tools

```typescript
const TOOLS: Tool[] = [
  // --- Web ---
  {
    name: 'web_search',
    description: 'Search the web using Brave Search API',
    input: { query: string, count?: number },
  },
  {
    name: 'web_fetch',
    description: 'Fetch a URL and extract readable content',
    input: { url: string, prompt?: string },
  },

  // --- Memory ---
  {
    name: 'memory_recall',
    description: 'Search memory for relevant past context',
    input: { query: string, limit?: number },
  },
  {
    name: 'memory_save',
    description: 'Save important information to long-term memory',
    input: { content: string, file: string, section?: string },
  },

  // --- macOS Integration ---
  {
    name: 'calendar_read',
    description: 'Read upcoming calendar events',
    input: { days_ahead?: number },
    // Uses: osascript -e 'tell application "Calendar" ...'
  },
  {
    name: 'calendar_create',
    description: 'Create a calendar event',
    input: { title: string, date: string, duration_minutes: number },
  },
  {
    name: 'reminders_create',
    description: 'Create a reminder in macOS Reminders',
    input: { title: string, due_date?: string, list?: string },
  },

  // --- Databricks (your specific need) ---
  {
    name: 'databricks_sql',
    description: 'Run a SQL query on Databricks serverless warehouse',
    input: { query: string, catalog?: string },
    // Uses: databricks sql execute --profile slysik
  },
  {
    name: 'databricks_jobs',
    description: 'List or trigger Databricks jobs',
    input: { action: 'list' | 'run', job_id?: string },
  },

  // --- Utilities ---
  {
    name: 'shell_execute',
    description: 'Run a shell command (requires confirmation)',
    input: { command: string },
    policy: 'gated', // Must confirm in Slack before running
  },
  {
    name: 'file_read',
    description: 'Read a local file',
    input: { path: string },
  },
  {
    name: 'file_write',
    description: 'Write content to a local file (requires confirmation)',
    input: { path: string, content: string },
    policy: 'gated',
  },
];
```

---

## Agent Loop

The core runtime follows the ReAct pattern (like OpenClaw's pi-mono):

```typescript
async function agentLoop(params: {
  systemPrompt: string;
  messages: Message[];
  tools: Tool[];
  model: string;
  maxTurns: number;
  onToolUse: (tool: string, input: any) => void;
}): Promise<string> {

  let turns = 0;

  while (turns < params.maxTurns) {
    // 1. Call Claude with messages + tools
    const response = await anthropic.messages.create({
      model: params.model,
      max_tokens: 4096,
      system: params.systemPrompt,
      messages: params.messages,
      tools: params.tools.map(formatForClaude),
    });

    // 2. If response is text-only, we're done
    if (response.stop_reason === 'end_turn') {
      return extractText(response);
    }

    // 3. If tool_use, execute each tool call
    if (response.stop_reason === 'tool_use') {
      const toolResults = [];

      for (const block of response.content) {
        if (block.type === 'tool_use') {
          const tool = params.tools.find(t => t.name === block.name);

          // Policy check
          if (tool.policy === 'gated') {
            const approved = await requestApprovalInSlack(tool, block.input);
            if (!approved) {
              toolResults.push({ tool_use_id: block.id, content: 'User denied this action.' });
              continue;
            }
          }

          // Execute
          params.onToolUse(block.name, block.input);
          const result = await executeToolSandboxed(tool, block.input);
          toolResults.push({ tool_use_id: block.id, content: result });
        }
      }

      // 4. Append assistant message + tool results, loop
      params.messages.push({ role: 'assistant', content: response.content });
      params.messages.push({ role: 'user', content: toolResults });
      turns++;
    }
  }

  return "I hit my thinking limit. Let me know if you'd like me to continue.";
}
```

---

## Setup & Installation

### First-Time Setup Script (`scripts/setup.sh`)

```bash
#!/bin/bash
set -euo pipefail

echo "=== Teve Slack Assistant Setup ==="

# 1. Create data directory
mkdir -p ~/.elle/{memory/{projects,daily},db}

# 2. Prompt for secrets and store in Keychain
echo "Enter your Slack Bot Token (xoxb-...):"
read -s SLACK_BOT_TOKEN
security add-generic-password -a elle -s elle-slack-bot-token -w "$SLACK_BOT_TOKEN" -U

echo "Enter your Slack App Token (xapp-...):"
read -s SLACK_APP_TOKEN
security add-generic-password -a elle -s elle-slack-app-token -w "$SLACK_APP_TOKEN" -U

echo "Enter your Anthropic API Key (sk-ant-...):"
read -s ANTHROPIC_KEY
security add-generic-password -a elle -s elle-anthropic-key -w "$ANTHROPIC_KEY" -U

# 3. Generate pairing code
PAIRING_CODE=$(openssl rand -hex 4)
security add-generic-password -a elle -s elle-pairing-code -w "$PAIRING_CODE" -U
echo "Your pairing code is: $PAIRING_CODE"
echo "Send this to Teve in a Slack DM to authorize yourself."

# 4. Initialize SQLite database
bun run src/memory/init-db.ts

# 5. Initialize memory files
cat > ~/.elle/memory/MEMORY.md << 'EOF'
# Teve Memory

Core facts and context loaded every conversation turn.
This file is managed by Teve. Edit manually with care.
EOF

echo "Setup complete! Run 'bun run src/index.ts' to start Teve."
```

### launchd Service (`scripts/com.elle.assistant.plist`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.elle.assistant</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/slysik/.bun/bin/bun</string>
        <string>run</string>
        <string>/Users/slysik/projects/elle-slack/src/index.ts</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/slysik/.elle/elle.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/slysik/.elle/elle.stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>/Users/slysik</string>
    </dict>
</dict>
</plist>
```

---

## Development Workflow

```bash
# Install dependencies
bun install

# Run in development (hot reload)
bun run --watch src/index.ts

# Run tests
bun test

# Security audit
bun run scripts/doctor.ts

# Install as background service
./scripts/install-launchd.sh

# View logs
tail -f ~/.elle/elle.stdout.log
tail -f ~/.elle/audit.log
```

---

## What Teve Can Do (Example Interactions)

```
You: what's on my calendar this week?
Teve: Here's your week:
  • *Mon 2/17* - 10am Team standup, 2pm Client demo prep
  • *Tue 2/18* - 9am Wegmans interview (Design & Architecture)
  • *Wed 2/19* - No meetings 🎉
  • *Thu 2/20* - 11am 1:1 with Sarah
  You've got Tuesday morning blocked - want me to review your interview prep notes?

You: run this on databricks: SELECT COUNT(*) FROM dbx_weg.bronze.bronze_retail_transactions
Teve: Running query on serverless warehouse...
  Result: *500 rows* in `bronze_retail_transactions`
  This matches what we saw in the dashboard earlier today.

You: remember that I always want SQL results formatted as tables
Teve: Noted - I'll format all Databricks SQL results as tables going forward.
  _(saved to preferences.md)_

You: summarize this thread
Teve: [reacts with 👀, reads thread, provides summary]

You: remind me to follow up with the Wegmans team next Thursday
Teve: Created reminder: "Follow up with Wegmans team" for Thu Feb 20, 2026.
```

---

## Implementation Order

### Phase 1: Foundation (Day 1)
- [ ] Project scaffold (Bun, TypeScript, package.json)
- [ ] Keychain integration (read/write secrets)
- [ ] Slack Bolt app with Socket Mode
- [ ] Basic DM handler (echo messages back)
- [ ] DM pairing / authorized user check

### Phase 2: Agent Core (Day 2)
- [ ] Anthropic API integration with tool use
- [ ] Agent loop (ReAct pattern with max turns)
- [ ] System prompt builder with personality
- [ ] Conversation context (thread history)
- [ ] Slack mrkdwn formatting

### Phase 3: Memory (Day 3)
- [ ] SQLite schema + initialization
- [ ] Message persistence (save all conversations)
- [ ] Memory file read/write (MEMORY.md, preferences.md, etc.)
- [ ] Auto-extract facts from conversations
- [ ] Semantic search with embeddings

### Phase 4: Tools (Day 4)
- [ ] Tool registry + policy enforcement
- [ ] Web search (Brave API)
- [ ] Web fetch + summarize
- [ ] macOS Calendar integration
- [ ] macOS Reminders integration
- [ ] Databricks CLI wrapper
- [ ] Sandboxed shell execution with Slack approval

### Phase 5: Production (Day 5)
- [ ] launchd service installation
- [ ] Audit logging
- [ ] Security doctor script
- [ ] Error handling + graceful degradation
- [ ] Rate limiting (Anthropic API costs)
- [ ] Daily conversation log generation

---

## Key Differences from OpenClaw

| Aspect | OpenClaw | Teve |
|--------|----------|------|
| Scope | 20+ channels, multi-user | Slack only, single user |
| Complexity | 366 agent files, plugin SDK | ~20 files, no plugin system |
| Memory | 67-file memory subsystem | Simple dual-layer (5 files) |
| Security | Docker sandboxing, Gateway | macOS Keychain + tool policies |
| Models | 15+ providers, failover | Anthropic Claude only |
| Deployment | Cross-platform, Docker | macOS native (launchd) |
| Config | Complex JSON + env vars | Simple config.json + Keychain |

**We take OpenClaw's best ideas** (memory system, system prompt injection, tool policies, audit logging) **and strip away the complexity** that comes from supporting 20+ channels and multi-user scenarios.

---

## Cost Estimate

| Component | Monthly Cost |
|-----------|-------------|
| Anthropic API (Sonnet, ~50 conversations/day) | ~$15-30 |
| Brave Search API (free tier) | $0 |
| macOS Keychain | $0 |
| Slack (existing workspace) | $0 |
| **Total** | **~$15-30/month** |

---

## Security Checklist

- [ ] All secrets in macOS Keychain (never in files)
- [ ] DM pairing required for first interaction
- [ ] Only authorized Slack user IDs can interact
- [ ] Gated tools require in-Slack confirmation
- [ ] All tool executions logged to audit.log
- [ ] No listening ports / inbound connections
- [ ] Shell execution sandboxed (no sudo, no recursive delete)
- [ ] Conversation data stays local (only API calls leave machine)
- [ ] Memory files not synced to any cloud service
- [ ] Regular `doctor` audit script to verify security posture
