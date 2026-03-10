# Plan: Interview Architecture Builder

## Task Description
Evolve the existing `whiteboard-builder.html` into an interactive interview practice tool that maps discovery answers to auto-generated Databricks Lakehouse architecture diagrams rendered on Excalidraw canvas. The tool mirrors the exact 3-phase flow of the Databricks SA Design & Architecture Interview (Discovery → Architecture Reveal → Refinement), training the candidate to start with discovery, present a justified architecture, and iterate based on feedback.

## Objective
Deliver a working single-file HTML tool (`whiteboard-builder.html`) with Excalidraw MCP integration that:
1. Guides structured discovery with coach questions, chips, and text inputs (presentable to interviewer via screen share)
2. Silently builds a component mapping from answers while diagram remains hidden
3. On "Reveal Architecture" click, pushes a clean left-to-right diagram to Excalidraw canvas with only use-case-specific components
4. Supports Phase 3 refinement via click-to-toggle components + text command box that update the Excalidraw canvas live
5. Uses warm tonal colors (Anthropic/Databricks palette, no Azure/Microsoft colors)

## Problem Statement
The Databricks SA Design & Architecture Interview requires candidates to:
- Lead structured discovery (not jump to whiteboarding)
- Build a production-ready architecture from requirements
- Visually diagram choices and justify trade-offs
- Iterate on the design based on interviewer feedback

Current `whiteboard-builder.html` has excellent discovery (7 sections, 160+ components, follow-up rules, scenarios) but lacks the critical link: **auto-generating a clean architecture diagram from captured answers**. The candidate must practice the full loop: discover → map → present → refine.

## Solution Approach
Extend the existing HTML with three new subsystems:
1. **Mapping Engine** — Pure JS function that reads answer state and produces a component list with lane assignments
2. **Excalidraw Renderer** — Calls Excalidraw MCP tools (`batch_create_elements`, `create_element`) to draw the diagram with warm-toned swim lanes, boxes, and arrows in a left-to-right layout
3. **Edit Panel** — UI for Phase 3 refinement that sends updates to Excalidraw via MCP tools

The Excalidraw canvas server must be running (localhost:3000) for diagram rendering. The HTML app works standalone for discovery.

## Relevant Files

### Existing Files
- `whiteboard-builder.html` — Main app to evolve. Contains discovery panel, coach questions, chip options, component library, follow-up rules, scenarios (FinServ, Wegmans), and drag-drop canvas. ~2000 lines.
- `.claude/skills/excalidraw-mcp/references/cheatsheet.md` — MCP tool reference for Excalidraw integration
- `.claude/skills/excalidraw-mcp/scripts/healthcheck.cjs` — Check Excalidraw canvas server status
- `.claude/skills/excalidraw-mcp/scripts/clear-canvas.cjs` — Clear Excalidraw canvas
- `.claude/skills/excalidraw-mcp/scripts/export-elements.cjs` — Export diagram to JSON
- `Design & Architecture Interview_Candidate Prep.pdf` — Interview format reference (3 phases, evaluation criteria)

### New Files
- `mapping-rules.js` (embedded in HTML) — Answer-to-component mapping engine
- `excalidraw-bridge.js` (embedded in HTML) — Functions to call Excalidraw MCP REST API endpoints

### Reference
- Microsoft Lakehouse Reference Architecture: https://learn.microsoft.com/en-us/azure/databricks/lakehouse-architecture/reference

## Implementation Phases

### Phase 1: Foundation
- Restructure the existing HTML to support 3 interview phases (Discovery → Reveal → Refinement)
- Add phase navigation with clear visual state transitions
- Clean up the discovery panel for screen-share presentation quality
- Ensure Excalidraw canvas server connectivity check on startup

### Phase 2: Core Implementation
- Build the mapping engine: answer data → component list with lane assignments
- Build the Excalidraw renderer: component list → REST API calls → left-to-right diagram
- Implement "Reveal Architecture" transition that pushes diagram to Excalidraw
- Build the edit panel for Phase 3 refinement

### Phase 3: Integration & Polish
- Wire up the full loop: discovery → mapping → render → edit → re-render
- Apply warm tonal color palette to Excalidraw elements
- Test with both pre-built scenarios (FinServ, Wegmans)
- Export-to-file functionality for saving diagrams
- Validate the full interview simulation flow end-to-end

## Design Specifications

### Architecture Swim Lanes (Left-to-Right)

Based on Microsoft Databricks Lakehouse reference architecture:

| Lane | Position | Description |
|------|----------|-------------|
| Source | Column 1 | External systems (databases, SaaS, IoT, files) |
| Ingest | Column 2 | Lakeflow Connect, Auto Loader, Structured Streaming |
| Transform/Process | Column 3 | Pipelines (SDP), Spark, Photon, SQL |
| Serve | Column 4 | SQL Warehouses, Model Serving, Lakebase |
| Analysis | Column 5 | BI tools, Dashboards, AI Apps |
| Governance | Spanning bar (bottom) | Unity Catalog, Data Quality, Security |

### Color Palette (Warm Tonal — Anthropic/Databricks)

| Element | Color | Hex |
|---------|-------|-----|
| Source lane background | Warm sand | `#F4E4C1` |
| Ingest lane background | Soft coral | `#E07A5F` |
| Transform lane background | Databricks red-orange | `#FF3621` |
| Serve lane background | Warm terracotta | `#C1666B` |
| Analysis lane background | Muted gold | `#D4A574` |
| Governance bar | Deep warm charcoal | `#3D405B` |
| Component boxes | Cream fill | `#FAF3E8` |
| Arrows/connectors | Warm gray stroke | `#5C5C5C` |
| Text labels | Near-black warm | `#2B2D42` |
| Lane header text | White | `#FFFFFF` |

### Mapping Engine Rules

The mapping engine converts captured answers to Excalidraw components. Core rules:

```javascript
// Source lane mappings
answer.sources contains "Netezza"     → { lane: "source", label: "Netezza" }
answer.sources contains "SAP"         → { lane: "source", label: "SAP ERP" }
answer.sources contains "Kafka"       → { lane: "source", label: "Kafka" }
answer.sources contains "Salesforce"  → { lane: "source", label: "Salesforce" }
// ... pattern: any named source system maps to Source lane

// Ingest lane mappings (latency-driven)
answer.latency includes "Real-time"       → { lane: "ingest", label: "Structured Streaming" }
answer.latency includes "Near-real-time"  → { lane: "ingest", label: "Structured Streaming" }
answer.latency includes "Daily batch"     → { lane: "ingest", label: "Auto Loader" }
answer.latency includes "Hourly"          → { lane: "ingest", label: "Lakeflow Connect" }
answer.formats includes "Streaming/IoT"   → { lane: "ingest", label: "Event Hub / Kafka Ingest" }
// CDC detected                           → { lane: "ingest", label: "Change Data Capture" }

// Transform lane mappings
answer.dw_approach any                    → { lane: "transform", label: "Pipelines (SDP)" }
answer.modeling_pref includes "Star"      → { lane: "transform", label: "Gold: Star Schema" }
answer.modeling_pref includes "Data Vault" → { lane: "transform", label: "Silver: Data Vault" }
answer.use_cases includes "ML/AI"         → { lane: "transform", label: "Feature Engineering" }
// Always present                         → { lane: "transform", label: "Bronze → Silver → Gold" }

// Serve lane mappings
answer.query_slas present               → { lane: "serve", label: "SQL Warehouse" }
answer.use_cases includes "ML/AI"       → { lane: "serve", label: "Model Serving" }
answer.use_cases includes "ML/AI"       → { lane: "serve", label: "Feature Store" }
answer.use_cases includes "Real-time KPIs" → { lane: "serve", label: "Serverless SQL" }
// If operational DB needed              → { lane: "serve", label: "Lakebase" }

// Analysis lane mappings
answer.bi_tools or consumers            → { lane: "analysis", label: "Power BI" } // or Tableau etc.
answer.use_cases includes "Self-service" → { lane: "analysis", label: "Databricks SQL Editor" }
answer.use_cases includes "ML/AI"       → { lane: "analysis", label: "ML Notebooks" }
answer.consumers includes "Apps/APIs"   → { lane: "analysis", label: "Databricks Apps" }
// Always if dashboards mentioned        → { lane: "analysis", label: "AI/BI Dashboards" }

// Governance (always present, details vary)
answer.catalog_strategy any             → { lane: "governance", label: "Unity Catalog" }
answer.compliance includes "GDPR"       → { lane: "governance", label: "Data Masking / PII" }
answer.compliance includes "PCI-DSS"    → { lane: "governance", label: "Encryption" }
answer.access_model any                 → { lane: "governance", label: "Access Control (RBAC/ABAC)" }
// Always present                       → { lane: "governance", label: "Data Lineage" }
```

### Excalidraw Layout Algorithm

Left-to-right diagram with auto-spacing:

```
Layout constants:
  LANE_WIDTH = 220
  LANE_GAP = 40
  BOX_WIDTH = 180
  BOX_HEIGHT = 50
  BOX_GAP = 15
  LANE_HEADER_HEIGHT = 40
  GOVERNANCE_BAR_HEIGHT = 60
  START_X = 50
  START_Y = 50

For each lane (left to right):
  1. Draw lane header rectangle (colored background, white text)
  2. Stack component boxes vertically within the lane
  3. Auto-distribute using Excalidraw align/distribute tools

After all lanes:
  4. Draw governance bar spanning full width at bottom
  5. Draw left-to-right arrows connecting lanes
  6. Max 4 boxes per lane (keeps diagram clean)
  7. If more than 4 components in a lane, group secondary items with "+" notation
```

### Excalidraw REST API Integration

The HTML app communicates with Excalidraw canvas via HTTP:

```javascript
const EXCALIDRAW_URL = 'http://localhost:3000';

// Health check on startup
GET ${EXCALIDRAW_URL}/health

// Clear canvas before rendering
POST ${EXCALIDRAW_URL}/api/elements/sync  (empty array to clear)

// Batch create all elements
POST ${EXCALIDRAW_URL}/api/elements/batch  (array of elements)

// Update single element (Phase 3 edits)
PUT ${EXCALIDRAW_URL}/api/elements/:id

// Delete element (Phase 3 removal)
DELETE ${EXCALIDRAW_URL}/api/elements/:id

// Export current state
GET ${EXCALIDRAW_URL}/api/elements
```

### Phase Flow in the HTML App

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: DISCOVERY                                          │
│                                                              │
│ ┌──────────┐  ┌────────────────────────┐  ┌──────────────┐ │
│ │  Coach    │  │  Answer Form           │  │  Summary     │ │
│ │  Panel    │  │  (chips, text, drag)   │  │  Sidebar     │ │
│ │           │  │                        │  │              │ │
│ │  Questions│  │  7-step wizard         │  │  Running     │ │
│ │  + tips   │  │  with progress bar     │  │  list of     │ │
│ │           │  │                        │  │  captured    │ │
│ │           │  │                        │  │  answers     │ │
│ └──────────┘  └────────────────────────┘  └──────────────┘ │
│                                                              │
│  [Load Scenario ▾]           [✓ Reveal Architecture →]      │
└─────────────────────────────────────────────────────────────┘

Phase transition: "Reveal Architecture" button
  1. Runs mapping engine on captured answer data
  2. Checks Excalidraw health
  3. Clears Excalidraw canvas
  4. Pushes components via batch_create
  5. Switches HTML to Phase 2 view

┌─────────────────────────────────────────────────────────────┐
│ Phase 2: ARCHITECTURE PRESENTATION                          │
│                                                              │
│ ┌──────────────────────────────────┐  ┌──────────────────┐ │
│ │  Excalidraw Canvas               │  │  Component List  │ │
│ │  (separate window/tab)           │  │                  │ │
│ │                                  │  │  ☑ Netezza       │ │
│ │  Source → Ingest → Transform →   │  │  ☑ Kafka         │ │
│ │  Serve → Analysis                │  │  ☑ Struct Stream │ │
│ │                                  │  │  ☑ Pipelines     │ │
│ │  [Governance bar at bottom]      │  │  ☑ SQL Warehouse │ │
│ │                                  │  │  ☑ Power BI      │ │
│ └──────────────────────────────────┘  │  ☑ Unity Catalog │ │
│                                        └──────────────────┘ │
│                                                              │
│  [← Back to Discovery]       [Edit Mode →]                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Phase 3: REFINEMENT                                         │
│                                                              │
│ ┌──────────────────────────────────┐  ┌──────────────────┐ │
│ │  Excalidraw Canvas               │  │  Edit Panel      │ │
│ │  (live updates)                  │  │                  │ │
│ │                                  │  │  Toggle:         │ │
│ │                                  │  │  ☑ Netezza       │ │
│ │                                  │  │  ☐ Feature Store │ │
│ │                                  │  │  ☑ Struct Stream │ │
│ │                                  │  │                  │ │
│ │                                  │  │  Add Component:  │ │
│ │                                  │  │  [dropdown ▾]    │ │
│ │                                  │  │                  │ │
│ │                                  │  │  Text Command:   │ │
│ │                                  │  │  [_____________] │ │
│ │                                  │  │                  │ │
│ └──────────────────────────────────┘  │  [Refresh ↻]     │ │
│                                        │  [Export .json]  │ │
│  [← Back to Presentation]             └──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Text Command Parser (Phase 3)

Simple keyword-based parser for natural language edits:

```javascript
// Supported patterns:
"add Feature Store"           → create_element in Serve lane
"add Kafka to Source"         → create_element in Source lane
"remove Auto Loader"          → delete_element matching label
"swap batch for streaming"    → delete Auto Loader, add Structured Streaming
"move X to Serve"             → update_element lane assignment
```

## Team Orchestration

- You operate as the team lead and orchestrate the team to execute the plan.
- You're responsible for deploying the right team members with the right context to execute the plan.
- IMPORTANT: You NEVER operate directly on the codebase. You use `Task` and `Task*` tools to deploy team members to do the building, validating, testing, deploying, and other tasks.

### Team Members

- Builder
  - Name: builder-html
  - Role: Implement all HTML/CSS/JS changes to whiteboard-builder.html — phase navigation, mapping engine, Excalidraw REST bridge, edit panel
  - Agent Type: builder
  - Resume: true

- Builder
  - Name: builder-excalidraw
  - Role: Implement the Excalidraw layout renderer — element creation, positioning algorithm, color palette, arrow connections
  - Agent Type: builder
  - Resume: true

- Validator
  - Name: validator-e2e
  - Role: Validate the complete flow works end-to-end — discovery → mapping → Excalidraw render → edit → re-render
  - Agent Type: validator
  - Resume: false

## Step by Step Tasks

### 1. Add Phase Navigation to HTML
- **Task ID**: phase-navigation
- **Depends On**: none
- **Assigned To**: builder-html
- **Agent Type**: builder
- **Parallel**: true
- Add 3-phase tab system to the HTML header: Discovery | Architecture | Refinement
- Phase 2 and 3 tabs are disabled/hidden until "Reveal Architecture" is clicked
- Add "Reveal Architecture" button to Discovery phase (appears after minimum answers captured)
- Add "Back" navigation between phases
- Clean up discovery panel CSS for screen-share quality (tighter spacing, professional look)
- Add answer summary sidebar that shows captured data in real-time during Phase 1
- Add Excalidraw connection status indicator in header (green dot = connected, red = offline)

### 2. Build Mapping Engine
- **Task ID**: mapping-engine
- **Depends On**: none
- **Assigned To**: builder-html
- **Agent Type**: builder
- **Parallel**: true (can start alongside task 1)
- Implement `buildComponentMap(answerData)` function that reads all chip selections and text inputs
- Return array of `{ lane, label, type, priority }` objects
- Implement all mapping rules from the Design Specifications section above
- Handle edge cases: no answers for a lane = lane stays empty, too many components per lane = group with "+" notation (max 4 per lane)
- Include deduplication logic (same component shouldn't appear twice)
- Add unit-testable structure (pure function, no DOM dependency)

### 3. Build Excalidraw REST Bridge
- **Task ID**: excalidraw-bridge
- **Depends On**: none
- **Assigned To**: builder-excalidraw
- **Agent Type**: builder
- **Parallel**: true (can start alongside tasks 1 and 2)
- Implement `ExcalidrawBridge` class with methods: `checkHealth()`, `clearCanvas()`, `batchCreate(elements)`, `createElement(element)`, `updateElement(id, props)`, `deleteElement(id)`, `exportElements()`
- All methods call Excalidraw REST API at `http://localhost:3000`
- Include error handling and retry logic for failed API calls
- Implement the layout algorithm from Design Specifications: lane positions, box sizing, auto-spacing
- Apply warm tonal color palette from Design Specifications to all created elements
- Implement arrow creation connecting lanes left-to-right
- Implement governance bar spanning full width at bottom

### 4. Wire Reveal Architecture Flow
- **Task ID**: reveal-flow
- **Depends On**: phase-navigation, mapping-engine, excalidraw-bridge
- **Assigned To**: builder-html
- **Agent Type**: builder
- **Parallel**: false
- Connect "Reveal Architecture" button click handler to: run mapping engine → check Excalidraw health → clear canvas → batch create elements → switch to Phase 2 view
- Populate Phase 2 component list sidebar from mapping engine output (checkboxes for each component)
- Handle Excalidraw offline gracefully (show error message, suggest starting server)
- Add loading state while diagram renders

### 5. Build Phase 3 Edit Panel
- **Task ID**: edit-panel
- **Depends On**: reveal-flow
- **Assigned To**: builder-html
- **Agent Type**: builder
- **Parallel**: false
- Implement component toggle checkboxes that add/remove elements from Excalidraw canvas on toggle
- Implement "Add Component" dropdown grouped by lane (Source, Ingest, Transform, Serve, Analysis, Governance)
- Implement text command box with simple keyword parser: "add X", "remove X", "swap X for Y"
- Implement "Refresh Diagram" button that re-runs the full layout algorithm (repositions after adds/removes)
- Implement "Export" button that fetches current elements from Excalidraw and saves as `.excalidraw` JSON file
- Track element IDs returned by Excalidraw so toggle/remove operations target correct elements

### 6. Test with Pre-built Scenarios
- **Task ID**: scenario-test
- **Depends On**: edit-panel
- **Assigned To**: builder-html
- **Agent Type**: builder
- **Parallel**: false
- Load the FinServ scenario and verify: all answers populate correctly, mapping engine produces expected components, Excalidraw diagram renders clean left-to-right layout
- Load the Wegmans scenario and verify the same
- Verify Phase 3 edits work: toggle a component off, add a new one, use text command, refresh diagram
- Fix any issues discovered during testing

### 7. End-to-End Validation
- **Task ID**: validate-all
- **Depends On**: scenario-test
- **Assigned To**: validator-e2e
- **Agent Type**: validator
- **Parallel**: false
- Verify Phase 1: discovery panel loads, all 7 sections work, chips toggle, text inputs capture, answer summary updates
- Verify Phase 2: "Reveal Architecture" calls Excalidraw API, diagram has correct lanes, components match answers, colors match warm tonal palette
- Verify Phase 3: component toggles update Excalidraw, text commands parse correctly, export produces valid JSON
- Verify navigation: phase transitions work, back buttons work, re-reveal after edits works
- Verify graceful degradation: Excalidraw offline shows clear error message
- Check diagram simplicity: max 4 boxes per lane, only answer-driven components appear, clean arrows

## Acceptance Criteria

1. Phase 1 (Discovery) displays cleanly for screen sharing — professional dark theme, tight spacing, no dev-tool appearance
2. Answers captured via chips, text inputs, and existing component library are all fed to mapping engine
3. "Reveal Architecture" button produces a left-to-right Excalidraw diagram with:
   - 6 labeled swim lane columns (Source, Ingest, Transform, Serve, Analysis) + Governance bar
   - Only components justified by answers (no answer = no component)
   - Max 4 component boxes per lane
   - Warm tonal color palette (no Azure/Microsoft blues)
   - Arrows connecting the flow left-to-right
4. Phase 3 edit panel allows: toggle components on/off, add new components via dropdown, text commands for quick edits
5. Each edit updates the live Excalidraw canvas without full page refresh
6. Export button saves current diagram as `.excalidraw` JSON
7. Both pre-built scenarios (FinServ, Wegmans) produce clean, readable diagrams
8. Excalidraw offline is handled gracefully with clear error messaging
9. All changes contained within single `whiteboard-builder.html` file (no external JS files needed)

## Validation Commands

- `node /Users/slysik/.claude/skills/excalidraw-mcp/scripts/healthcheck.cjs` — Verify Excalidraw canvas server is running
- `open /Users/slysik/databricks/whiteboard-builder.html` — Open the app in browser
- `node /Users/slysik/.claude/skills/excalidraw-mcp/scripts/export-elements.cjs --out /tmp/test-export.json` — Verify export produces valid JSON
- Visual inspection: Load FinServ scenario → Reveal Architecture → verify clean left-to-right diagram in Excalidraw
- Visual inspection: Toggle a component off in Phase 3 → verify it disappears from Excalidraw canvas
- Visual inspection: Type "add Feature Store" in text command → verify it appears in Serve lane

## Notes

- The Excalidraw canvas server must be running at `localhost:3000` for diagram rendering. The HTML app's discovery phase works standalone without it.
- The existing `whiteboard-builder.html` is ~2000 lines. This plan adds approximately 1000-1500 lines for the mapping engine, Excalidraw bridge, edit panel, and phase navigation. Total will be ~3000-3500 lines.
- The mapping engine rules should be easily extensible — new answer patterns can be added by appending to a rules array, not modifying core logic.
- For the interview itself, Steve would: (1) open the HTML in one window, (2) open Excalidraw in another, (3) share the HTML screen during discovery, (4) share Excalidraw screen during architecture presentation and refinement.
- The text command parser in Phase 3 is intentionally simple — keyword matching, not NLP. It handles the 80% case (add/remove/swap) and the dropdown handles the rest.
