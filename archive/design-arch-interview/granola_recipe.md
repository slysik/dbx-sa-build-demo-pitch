# FinServ DW Discovery – Granola Recipe

## Template Title
**FinServ DW / GSI Discovery Architecture**

## Instructions
Ask these 10 questions during the discovery session. Granola will capture the answers. After the session, the structured notes feed into the architecture diagram prompt.

---

## Q1: BUSINESS OUTCOMES & NON-NEGOTIABLES
> "Let's start with what success looks like. What are the 2–3 priority use cases or reports that absolutely cannot miss their SLA? Who owns the escalation if they do?"

**Capture:**
- Priority use cases / reports (2-3)
- Executive pressure owner
- SLA failure impact (regulatory fine, revenue loss, etc.)

---

## Q2: SLAs & AUDITABILITY
> "For each of those use cases, what are the refresh targets — are we talking end-of-day, intraday, near-real-time? And what does your audit team need to see as evidence?"

**Capture:**
- Refresh cadence per use case (EOD, T+1, intraday, streaming)
- Availability / RTO / RPO targets
- Audit evidence requirements (lineage, access logs, reconciliation)

---

## Q3: GOLDEN METRICS & SIGN-OFF
> "Which 2–3 finance or risk metrics does the CFO/CRO actually look at? Where does the authoritative number come from today, and who signs off that it's correct?"

**Capture:**
- Golden metrics (name, source system, owner)
- Definition vs. calculation ownership
- Current pain points with metric consistency

---

## Q4: 90-DAY GOLD THIN SLICE
> "If we had to get one subject area into production Gold in 90 days, which would it be? What's the minimum set of tables and the hero dashboard that proves value?"

**Capture:**
- Priority subject area for first delivery
- Minimum production tables / KPIs
- Hero dashboard or report name

---

## Q5: TOP DATA SOURCES & OWNERSHIP
> "Walk me through your top 5 source systems. For each one — who owns it, what's the refresh cadence, and where does the data land today?"

**Capture:**
- DS1: Name | Owner | Cadence | Current landing zone
- DS2: Name | Owner | Cadence | Current landing zone
- DS3: Name | Owner | Cadence | Current landing zone
- DS4: Name | Owner | Cadence | Current landing zone
- DS5: Name | Owner | Cadence | Current landing zone

---

## Q6: INGESTION – BATCH PATTERNS
> "For your batch loads — what tools are you using today? What are the load windows, and are there any constraints like mainframe offload times or vendor delivery schedules?"

**Capture:**
- Current batch tools (Informatica, ADF, SSIS, Autoloader, etc.)
- Load windows / frequency
- Hard constraints (mainframe windows, vendor SFTPs, etc.)

---

## Q7: INGESTION – STREAMING & CDC
> "Do any of these sources need near-real-time or CDC? What's the latency target, and do you need replay capability if something fails?"

**Capture:**
- Sources needing CDC or streaming
- Current CDC tools (Debezium, Qlik Replicate, HVR, etc.)
- Latency target
- Replay / reprocessing requirements

---

## Q8: DATA QUALITY & RECONCILIATION
> "How do you validate data today? Are there reconciliation controls — like GL tie-outs or balance checks — that must carry over into the new platform?"

**Capture:**
- Current DQ approach (Great Expectations, custom SQL, manual)
- Reconciliation controls (GL balances, row counts, checksums)
- Quarantine / remediation process

---

## Q9: COMPUTE & CONSUMPTION PATTERNS
> "Who are the consumers of this data? What BI tools are in play, and what does the compute profile look like — heavy batch transforms, interactive queries, or both?"

**Capture:**
- BI tools (Power BI, Tableau, Looker, etc.)
- Personas (analysts, data scientists, executives, regulators)
- Compute needs: batch ETL, streaming, interactive SQL, ML
- Current warehouse / cluster sizing

---

## Q10: GOVERNANCE, SECURITY & COMPLIANCE
> "What are the regulatory guardrails? PII/PCI masking requirements, row-level security, audit retention — what does your compliance team need on day one?"

**Capture:**
- PII/PCI handling requirements
- RBAC / ABAC / row-level / column-level security needs
- Audit retention period
- Regulatory frameworks (SOX, GDPR, CCPA, OCC/Fed, etc.)
- Environment strategy (Dev/Test/Prod isolation)
