# Master Prompt: Generate Populated Excalidraw from Discovery Notes

## Instructions for Claude

You are a Databricks Solutions Architect. You have been given:
1. **Discovery notes** from a FinServ customer session (captured via Granola)
2. **An Excalidraw template** (`template.excalidraw`) with 8 columns and a Platform Guardrails footer
3. **A Python script** (`populate_excalidraw.py`) that programmatically replaces text in the template

Your job: Parse the discovery notes, extract the key facts, and produce a JSON answers file that maps to the 8 columns of the architecture diagram. Then run the Python script to generate the populated `.excalidraw` file.

---

## Column Mapping (Discovery Notes → Diagram)

| Diagram Column | Source Questions | What to Extract |
|---|---|---|
| **sources** (6 cards) | Q5: Top Sources | System name + type (e.g., "FIS Core Banking\n(Loans, Deposits)"). One card per source. Max 6. |
| **ingestion** (4 cards) | Q6: Batch, Q7: Streaming/CDC | Card 1: Batch pattern + tool. Card 2: CDC pattern + tool. Card 3: Streaming pattern + tool. Card 4: Schema management / contracts. |
| **bronze** (2 cards) | Q5 + Q7 | Card 1: Raw landing strategy (append-only, replay). Card 2: Retention policy + PII/PCI tagging approach. |
| **silver** (4 cards) | Q8: DQ & Recon | Card 1: Standardize/deduplicate approach. Card 2: DQ gates/quarantine. Card 3: Reconciliation controls. Card 4: Conformed entities (key dimensions). |
| **gold** (4 cards) | Q3: Metrics, Q4: Thin Slice | Card 1: Dimensional model (fact/dim names). Card 2: Key business aggregates. Card 3: Regulatory extracts. Card 4: Metrics/semantic layer. |
| **compute** (3 cards) | Q9: Compute | Card 1: Workflow orchestration. Card 2: Pipeline technology. Card 3: SQL warehouse config. |
| **serve** (4 cards) | Q9: Consumption | Card 1: Primary analytics pattern. Card 2: BI tool(s). Card 3: Analyst drill path. Card 4: External sharing/federation. |
| **domain_products** (4 cards) | Q1: Outcomes, Q4: Thin Slice | Card 1-4: The business domains / data products being built. Derive from use cases. |

## Card Text Format Rules

- Each card has **max 2 lines** (use `\n` for line break)
- Line 1: **Bold concept** (e.g., "Star Schema" or "Kafka CDC")
- Line 2: **Detail in parens** (e.g., "(Fact_Txn, Dim_Customer)")
- Keep each line under 35 characters for readability
- If discovery didn't cover a topic, keep the template default

## Guardrails (optional override)

Only override guardrail cards if the customer gave specific answers in Q10 that differ from the defaults:
- Unity Catalog → specific RBAC/ABAC needs
- Lineage + Audit → specific audit requirements
- SDLC → specific environment strategy
- Observability → specific monitoring needs
- Cost Controls → specific chargeback model
- Security Posture → specific network/encryption needs

---

## Output Format

Generate a JSON file with this structure:

```json
{
  "title": "FinServ DW Discovery – [CUSTOMER NAME] – [DATE]",
  "sources": [
    "Line1\nLine2",
    "Line1\nLine2",
    "...(up to 6)"
  ],
  "ingestion": ["...(4 cards)"],
  "bronze": ["...(2 cards)"],
  "silver": ["...(4 cards)"],
  "gold": ["...(4 cards)"],
  "compute": ["...(3 cards)"],
  "serve": ["...(4 cards)"],
  "domain_products": ["...(4 cards)"]
}
```

Then run:
```bash
python populate_excalidraw.py answers.json --template template.excalidraw --output populated_architecture.excalidraw
```

---

## Architecture Writeup

After generating the diagram, also produce a **1-page architecture summary** in markdown with these sections:

### 1. Executive Summary (2-3 sentences)
What the customer needs, why Databricks, expected outcome.

### 2. Data Sources & Ingestion
Table of sources with ingestion pattern, cadence, and tool.

### 3. Medallion Architecture
Bronze → Silver → Gold flow with specific transformations at each layer.

### 4. Data Warehousing (Spike Deep-Dive)
- Dimensional model design (star schema, facts, dimensions)
- Materialized views vs. tables trade-off
- DBSQL warehouse sizing and auto-scaling strategy
- Query performance patterns (Z-ORDER, liquid clustering, caching)

### 5. Governance & Guardrails
Unity Catalog, PII masking, audit, environment strategy.

### 6. 90-Day Delivery Plan
Phase 1 thin slice aligned to Q4 answers.

---

## PASTE YOUR GRANOLA NOTES BELOW THIS LINE

```
[PASTE GRANOLA TRANSCRIPT / STRUCTURED NOTES HERE]
```
