# Discovery Framework — Databricks SA Interview

## The Golden Rule
**Discovery before whiteboard. Always. No exceptions.**

Opening line: *"Before I start drawing anything, I'd like to ask a few questions to make sure I'm designing for your actual constraints — not a generic reference architecture."*

---

## Category 1: Business Context (Ask FIRST — 5 minutes)

| Question | What It Uncovers |
|----------|-----------------|
| "What's the primary business problem you're trying to solve?" | Differentiates tactical fix from strategic initiative |
| "Who are the end consumers of this data? Analysts? ML models? Regulators? Executives?" | Drives Gold layer design and consumption pattern |
| "What does success look like 6 months from now? What metric moves?" | Reveals true business outcome vs. technical deliverable |
| "What's the timeline? Is there a regulatory deadline or business milestone driving this?" | Exposes urgency and sequencing constraints |
| "What's failed before or caused pain?" | **Gold question** — reveals hidden requirements and landmines |

---

## Category 2: Current State (10 minutes)

| Question | What It Uncovers |
|----------|-----------------|
| "What systems are you running today?" | Legacy DW (Teradata/Netezza/Redshift), Hadoop, SaaS apps |
| "What's your cloud footprint?" | Azure/AWS/GCP mandate, multi-cloud reality |
| "Where does the data live right now?" | On-prem DBs, S3/ADLS, SaaS APIs, mainframes |
| "What BI tools are your users on today?" | Power BI, Tableau, Looker — affects Gold modeling |
| "How are you handling ETL/ELT today?" | Informatica, SSIS, Airflow, manual scripts — sizing the migration |
| "Do you have existing cloud DW contracts?" | Snowflake, Redshift, Synapse — competitive landscape |

---

## Category 3: Data Characteristics (5 minutes)

| Question | What It Uncovers |
|----------|-----------------|
| "What are the key data domains?" | Transactions, customers, products, events — drives Silver modeling |
| "What's the data volume? How fast is it growing?" | GB/TB/PB + growth rate — cluster sizing, storage tier |
| "What's the latency requirement?" | Real-time/near-RT/hourly/daily — drives streaming vs. batch choice |
| "What data formats?" | Structured, semi-structured/JSON, unstructured — affects Bronze design |
| "How many source systems are feeding into this?" | 5? 50? 500? — Data Vault vs. star schema threshold |

---

## Category 4: Non-Functional Requirements (5 minutes)

| Question | What It Uncovers |
|----------|-----------------|
| "What governance/compliance requirements?" | GDPR, CCPA, PCI-DSS, SOX, HIPAA, Basel III/IV — Unity Catalog design |
| "What's the disaster recovery expectation?" | RPO/RTO — backup strategy, cross-region replication |
| "How many concurrent users query this?" | 10 analysts vs. 10,000 dashboard viewers — warehouse sizing |
| "What's your budget model?" | CapEx vs. OpEx, department chargebacks — serverless vs. classic |
| "Who manages this day-to-day?" | Central platform team vs. decentralized — governance model |

---

## Category 5: Constraints & Preferences (5 minutes)

| Question | What It Uncovers |
|----------|-----------------|
| "Are there technology mandates from your CTO/CIO?" | Must-be-Azure, must-use-Kubernetes, etc. |
| "Are there existing contracts or commitments?" | Microsoft EA, Snowflake contract, Oracle license — competitive positioning |
| "What's the team's skill set?" | SQL-heavy vs. Python vs. Spark — affects tooling choices |
| "What's failed before?" | **Always ask this** — surfaces real constraints not in the RFP |

---

## Pro Discovery Techniques

### Repeat Back
> "So if I'm understanding correctly, the core need is **[X]**, constrained by **[Y]**, and the primary users are **[Z]**. Is that right?"

### State Assumptions Explicitly
> "I'm going to assume **[Azure, Basel III compliance, Teradata as source]** — let me know if any of those are off base."

### Challenge Vague Requirements
> "You mentioned real-time — is that a true sub-second requirement, or would 5-minute latency actually work for your use case?"

### Ask About Failures
> "You mentioned a previous data warehouse project — what went wrong there? What would you not repeat?"

---

## FinServ-Specific Discovery Questions

| Topic | Question |
|-------|----------|
| Regulatory | "Which regulatory bodies are primary — OCC, ECB, local central banks?" |
| Risk | "Is risk calculation real-time? What's the VaR computation SLA?" |
| Data residency | "Are there data residency requirements by country or jurisdiction?" |
| Access model | "Is access control centralized or federated by line of business?" |
| Audit trail | "How long do you need to retain the full audit trail for regulatory evidence?" |
| Migration | "What's the migration timeline — big bang or phased by domain?" |
| BI | "Are you standardizing on Power BI or is Tableau/Looker in scope?" |
| Snowflake | "Are there existing Snowflake investments you want to preserve during transition?" |
