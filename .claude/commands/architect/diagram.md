---
model: opus
description: Generate Excalidraw architecture diagram from saved discovery answers
argument-hint: <scenario-name> [refine]
---

# Diagram from Answers

Generate an Excalidraw Lakehouse architecture diagram from a previously saved discovery YAML.

## Variables

Parse `$ARGUMENTS`:

- **SCENARIO:** (required) Name of scenario file (e.g., `finserv`)
- **REFINE:** Keyword detection — if `refine` appears, enable interactive refinement

## Workflow

1. **Validate:** Check that `scenarios/{SCENARIO}.yaml` exists
2. **Generate:** Launch `diagram-agent` with:
   - ANSWERS_FILE = `scenarios/{SCENARIO}.yaml`
   - REFINE = true if refine keyword detected
3. **Report** the diagram summary with component counts per lane
