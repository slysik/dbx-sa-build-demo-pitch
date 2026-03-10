---
model: opus
description: Run architecture discovery only — interactive questioning or scenario load, saves YAML
argument-hint: [scenario-name]
---

# Discovery Only

Run the discovery phase independently. Captures answers and saves to YAML without generating a diagram.

## Variables

Parse `$ARGUMENTS`:

- **SCENARIO:** Optional scenario name to load instead of interactive discovery

## Workflow

1. **If SCENARIO provided:**
   - Verify `scenarios/{SCENARIO}.yaml` exists
   - Load and validate using `discovery-agent` in scenario mode

2. **If no SCENARIO (interactive):**
   - Launch `discovery-agent` in interactive mode
   - Walk through all 7 sections
   - Save answers to `scenarios/{customer-name}.yaml`

3. **Report** the discovery summary and saved file path
