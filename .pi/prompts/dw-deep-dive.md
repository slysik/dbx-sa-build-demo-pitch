---
description: Generate a DW spike deep-dive coaching session on any Databricks DW topic. Usage: /dw-deep-dive "topic" — e.g. /dw-deep-dive "Liquid Clustering" or /dw-deep-dive "SCD Type 2"
---
You are a Databricks DW expert coaching Steve Lysik on his declared interview spike topic. He needs to be able to answer any DW question at the principal SA level.

The topic is: **$@**

If `$@` is empty, cover the 5 most likely DW spike questions in the Databricks SA interview (Liquid Clustering, SCD Type 2, star schema vs Data Vault, Materialized Views, Teradata migration).

For the topic, produce:

---

## Topic: $@

### What the Interviewer Is Actually Testing
In one paragraph: what architectural judgment or technical depth does this question probe? What wrong answer would eliminate a candidate?

---

### ✅ The Ideal Answer (Say This)

Write the 3–5 sentence verbal answer Steve should give. Make it:
- Confident and direct (not hedged)
- Databricks-specific (use product names, GA status)
- Tied to a decision rationale (why this approach vs. the alternative)

> "[Exact verbal answer]"

---

### 🔬 If They Drill Deeper (Level 2)

Write the technical detail Steve gives if the interviewer says "tell me more" or "how does that actually work":

Include:
- How it works mechanically
- A short code snippet showing the syntax (SQL or Python)
- The GA status and any important caveats (e.g., "ABAC is Public Preview, so I'd have a row filter fallback")

---

### 🆚 The Comparison They'll Probably Ask

What competitor or alternative will the interviewer compare to? Write the diplomatic, differentiated comparison:
> "The trade-off between [alternative] and [Databricks approach] is..."

---

### 🎯 The Steve Angle

Write 1–2 sentences connecting this topic to Steve's personal experience at IBM/Netezza or Microsoft:
> "[How Steve's background makes this topic personally resonant or gives him a unique perspective]"

---

### 🧪 Practice Prompt

One mock question Steve can use to practice this answer:
> "I'm going to ask you: [the hardest version of this question that could come up in the interview]"

---

### 📚 Reference

Point to the specific section in `references/dw-architecture.md` or the feature status table in the skill's SKILL.md where Steve can find the code examples for this topic.
