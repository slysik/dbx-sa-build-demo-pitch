---
model: opus
description: Full Databricks architecture pipeline — discovery, mapping, Excalidraw diagram, and optional refinement
argument-hint: [scenario-name | "interactive"] [refine]
---

# Architect Pipeline

Full pipeline orchestrator for Databricks Lakehouse architecture generation. Runs discovery (or loads a scenario), maps answers to components, generates an Excalidraw diagram, and optionally enters a refinement loop.

## Variables

Parse `$ARGUMENTS` to extract:

- **SCENARIO:** First argument — a scenario name (e.g., `finserv`, `wegmans`, `dw-migration`) or `interactive` for live discovery. Default: `interactive`
- **REFINE:** Keyword detection — if `refine` appears in arguments, enable refinement loop. Default: `false`

## Workflow

### Phase 1: Parse Arguments

1. If no `$ARGUMENTS`, default to interactive mode
2. Extract SCENARIO from first argument
3. Check for `refine` keyword in remaining arguments

### Phase 2: Discovery

**If SCENARIO is a file name (not "interactive"):**
1. Verify `scenarios/{SCENARIO}.yaml` exists using Glob
2. If not found, list available scenarios and stop with error
3. Load the scenario — use the `discovery-agent` (Task tool, subagent_type: `discovery-agent`) in scenario mode

**If SCENARIO is "interactive":**
1. Launch `discovery-agent` (Task tool, subagent_type: `discovery-agent`) in interactive mode
2. Wait for discovery to complete and YAML to be saved

### Phase 3: Map and Diagram

1. Determine the YAML path from Phase 2 output
2. Launch `diagram-agent` (Task tool, subagent_type: `diagram-agent`) with:
   - ANSWERS_FILE = path to saved YAML
   - REFINE = value from Phase 1 parse

### Phase 4: Report

Combine outputs from both agents:

```
ARCHITECT PIPELINE COMPLETE

Mode: {scenario|interactive}
Customer: {name}
Discovery: scenarios/{file}.yaml
Diagram: Rendered on Excalidraw canvas

Components: {total} across 6 lanes
Refinement: {enabled|disabled}

Next steps:
  - View diagram in Excalidraw
  - Run `/architect:diagram {scenario}` to re-generate
  - Run `/architect:discovery` to start a new discovery
```
