---
name: excalidraw-architect
description: Generate Databricks Lakehouse architecture diagrams on Excalidraw canvas from structured discovery answers. Pre-defined shell with dynamic component placement. Keywords - excalidraw, architecture, diagram, whiteboard, lakehouse, databricks.
---

# Excalidraw Architect

## Purpose

Generate clean, professional Databricks Lakehouse architecture diagrams on the Excalidraw canvas. The diagram uses a pre-defined shell (title bar, swim lanes, governance bar) with dynamic component placement driven by discovery answers.

**Key principle:** The shell is static. Only the components inside each lane are dynamic.

## Pre-flight Check

Before generating any diagram, verify Excalidraw MCP tools are available:
1. Call `mcp__excalidraw__query_elements` with a simple query to check connectivity
2. If tools are unavailable, stop and inform the user: "Excalidraw MCP server must be running. Start it and try again."

## Variables

- **ANSWERS_FILE:** Path to discovery answers YAML file (e.g., `scenarios/finserv.yaml`)
- **TITLE:** Diagram title (default: `{customer_name} — Databricks Lakehouse Architecture`)
- **CLEAR_FIRST:** `true` (default) — clear canvas before rendering

## Input: Discovery Answers

The architect expects a YAML file describing the customer scenario. This is the sole input that drives component selection and placement.

### Expected YAML Structure

```yaml
customer_name: "Acme Corp"
use_case: "Real-time fraud detection"
sources:
  - name: "Transaction Events"
    type: "kafka"
  - name: "Customer Master"
    type: "rdbms"
ingestion:
  - name: "Auto Loader"
    pattern: "streaming"
  - name: "Lakehouse Federation"
    pattern: "federated"
transformation:
  - name: "Bronze -> Silver DLT"
    pattern: "declarative_pipeline"
  - name: "Feature Engineering"
    pattern: "spark_sql"
serving:
  - name: "Model Serving"
    type: "endpoint"
  - name: "Gold Tables"
    type: "delta"
analysis:
  - name: "AI/BI Dashboard"
    type: "dashboard"
  - name: "Genie Space"
    type: "genie"
governance:
  - "Unity Catalog"
  - "Row/Column Security"
```

### Field Semantics

- **customer_name** (string) — used in the title bar; falls back to "Customer" if missing
- **use_case** (string) — free-text summary; not directly rendered but informs component selection heuristics
- **sources[]** — external systems feeding data into the lakehouse; each entry needs `name` and `type`
- **ingestion[]** — Databricks ingestion mechanisms; each entry needs `name` and `pattern`
- **transformation[]** — processing/ETL steps; each entry needs `name` and `pattern`
- **serving[]** — how downstream consumers access data; each entry needs `name` and `type`
- **analysis[]** — BI tools, dashboards, notebooks; each entry needs `name` and `type`
- **governance[]** — flat list of governance/security labels (strings, not objects)

### Two Input Modes

1. **File mode** — read YAML from `ANSWERS_FILE` path and parse
2. **Inline mode** — if no file is provided, accept discovery answers as structured data in the conversation and construct the mapping in memory

## Mapping Engine

The mapping engine translates YAML fields into diagram lanes and component boxes. Each YAML array maps to exactly one swim lane.

### YAML-to-Lane Mapping

| YAML Field | Diagram Lane | Component Style | Placement |
|---|---|---|---|
| `sources[]` | Source | External system boxes (cream fill) | Stacked vertically |
| `ingestion[]` | Ingest | Databricks service boxes (cream fill) | Stacked vertically |
| `transformation[]` | Transform | Pipeline/processing boxes (cream fill) | Stacked vertically |
| `serving[]` | Serve | Endpoint/table boxes (cream fill) | Stacked vertically |
| `analysis[]` | Analysis | Dashboard/app boxes (cream fill) | Stacked vertically |
| `governance[]` | Governance Bar | Smaller boxes (dark fill, white text) | Distributed horizontally |

### Component Resolution

For each YAML entry, the mapping engine:
1. Takes the `name` field as the box label text
2. Takes the `type` or `pattern` field for optional icon/style hints (future use)
3. Assigns the component to its lane based on which YAML array it came from
4. Cross-references against `components.md` priority table to determine render order
5. If a YAML entry name fuzzy-matches a `components.md` entry, inherit its priority; otherwise default priority = 2

### Priority Sorting Within Lanes

- Components are sorted by priority (1 = highest) before placement
- Equal-priority components maintain their YAML order
- Only the top `MAX_BOXES` (4) are rendered as individual boxes
- Remaining components are collapsed into the overflow box

### Governance Mapping

- Governance entries are simple strings, not objects
- Each string becomes a horizontal box inside the governance bar
- Max 5 visible governance boxes; overflow as "+N" text at right edge
- "Unity Catalog" and "Data Lineage" are always prepended if not already present

## Edge Cases

- **Empty lane** — render the lane header rectangle but place no component boxes; arrows still connect through it
- **>4 components in a lane** — show top 4 by priority + a dashed "+N more" summary box listing overflow names (see `template.md` overflow_box template)
- **Missing governance field** — default to `["Unity Catalog", "Data Lineage"]`
- **Missing customer_name** — title falls back to "Databricks Lakehouse Architecture"
- **Empty sources array** — render Source lane header with no boxes; this is valid for internally-generated-data scenarios
- **No discovery file and no inline data** — prompt user: "Provide a discovery YAML file path or describe the architecture interactively." Do not render an empty diagram.
- **Duplicate component names** — deduplicate by name within each lane; keep the first occurrence
- **Very long component names** — truncate label text at 25 characters with ellipsis ("...") for rendering; full name available on hover/tooltip if Excalidraw supports it

## Workflow

### Phase 1: Clear Canvas

If CLEAR_FIRST is true:
1. Query all existing elements: `mcp__excalidraw__query_elements`
2. Delete each element: `mcp__excalidraw__delete_element`
3. Verify canvas is empty

### Phase 2: Render Shell

Using the layout constants from `template.md`:
1. Create the title bar element at the top
2. Create 5 swim lane header rectangles (colored backgrounds, white text labels)
3. Create the governance bar spanning full width at the bottom
4. All shell elements use the warm tonal color palette

### Phase 3: Place Components

For each component from the mapping engine output:
1. Determine which lane it belongs to
2. Calculate Y position based on existing components in that lane (stack vertically)
3. Create the component box element (cream fill, warm text)
4. Enforce max 4 boxes per lane — if more than 4, group remaining as "+N more" box
5. Use `mcp__excalidraw__create_element` for each component

### Phase 4: Add Arrows

1. Create left-to-right arrow elements connecting adjacent lane headers
2. Arrows go: Source -> Ingest -> Transform -> Serve -> Analysis
3. Use warm gray stroke color (#5C5C5C)

### Phase 5: Report

Output a summary:
```
DIAGRAM GENERATED

Title: {title}
Components: {total_count}
  Source: {count} | Ingest: {count} | Transform: {count} | Serve: {count} | Analysis: {count}
  Governance: {count}
Elements created: {total_excalidraw_elements}
```

## Layout Reference

See `template.md` for exact positions, sizes, and colors.
See `components.md` for the component library with lane assignments.

## Refinement

After initial generation, the user may request changes:
- **"Add {component} to {lane}"** — Create new element in specified lane, reflow
- **"Remove {component}"** — Delete element by label match
- **"Swap {A} for {B}"** — Delete A, create B in same position
- **"Reflow"** — Recalculate all positions (useful after multiple adds/removes)

For each change, update the Excalidraw canvas live using MCP tools.
