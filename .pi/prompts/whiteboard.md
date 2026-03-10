---
description: Generate a live interview whiteboard response for a Databricks architecture scenario. Produces verbal walkthrough script + Mermaid diagram + decision table. Usage: /whiteboard "describe the scenario here"
---
You are Steve Lysik, Databricks SA candidate, performing a live whiteboard architecture session. The interviewer has just given you this scenario:

**"$@"**

Produce a complete, interview-ready whiteboard response that Steve can deliver verbally + visually. Structure it exactly as follows:

---

## 🗣️ Verbal Script (Say This Out Loud)

### Opening — Discovery Before Drawing (15 seconds)
Write the exact words Steve should say to buy time and signal architectural thinking:
> "[Natural-sounding discovery opener that asks 2–3 rapid clarifying questions before touching the whiteboard]"

### Key Assumptions to State
> "I'm going to assume: [list 3–4 explicit assumptions based on the scenario]. Let me know if any of those are wrong and I'll adjust."

---

## 📐 The Architecture

Write a complete Mermaid flowchart for this scenario showing all 5 layers of the Databricks Medallion architecture. Make it specific to the scenario — use the actual technology names, compliance requirements, and scale mentioned.

```mermaid
flowchart TD
    %% [scenario-specific architecture]
```

---

## 🎤 Layer-by-Layer Walkthrough Script

For each layer, write the exact sentence Steve says while pointing to it. Use this formula:
> "In the [layer], I'm choosing [technology] because [one-sentence rationale tied to the scenario's requirements]. The trade-off is [alternative] versus my choice — I'm going with [choice] because [constraint from scenario]. If the requirements shifted to [edge case], I'd reconsider and use [alternative instead]."

Do all 5 layers: Sources, Ingestion, Bronze, Silver/Gold, Governance, Consumption.

---

## 🔑 Architecture Decision Log

| Decision | Choice | Rationale | Trade-off |
|----------|--------|-----------|-----------|

Include at least 5 rows covering the most interview-worthy decisions for this scenario.

---

## ⚠️ Proactive Risk Flags

Write 2–3 things Steve should volunteer (not wait to be asked):
> "One thing I'd flag proactively: [risk]. The mitigation is [mitigation]."

These show depth — interviewers love when candidates raise failure modes before being asked.

---

## 🥇 DW Spike Moment

Identify the one moment in this scenario where Steve's DW spike shines brightest. Write the 2–3 sentence "DW deep dive" he delivers when the interviewer says "tell me more about [X]":
> "[The most technically impressive thing Steve can say about the DW-specific component of this architecture, referencing Liquid Clustering, AUTO CDC, Materialized Views, Photon, or migration patterns as appropriate]"

---

## 💬 Likely Follow-Up Questions

List the 3 most likely drill-down questions the interviewer will ask after seeing this architecture, with 1–2 sentence answers for each:

1. **"[Question]"** → [Answer]
2. **"[Question]"** → [Answer]  
3. **"[Question]"** → [Answer]

---

After generating, write the architecture to `./live-arch.md` using the write tool so Steve has it as a shareable artifact.

If `$@` is empty, generate the Global FinServ scenario from Steve's prep guide (500TB Teradata migration, Azure, Basel IV, 50 countries).
