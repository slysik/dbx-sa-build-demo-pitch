# Databricks notebook source

# COMMAND ----------
# %md
# # Apex Banking — Internal Policy Document Loader
#
# **The "untapped asset" layer.**
# Years of internal documents — retention playbooks, product guides, complaint
# policies — that exist in SharePoint and email threads but are impossible to
# query at scale. This notebook ingests them into Delta, making them searchable
# and usable as grounding context for AI-generated recommendations.
#
# **In production:** Auto Loader reads PDFs from `/Volumes/finserv/banking/policy_docs/`
# using `ai_parse_document()`. Here we use pre-written text to keep the demo fast.
#
# **Output:** `finserv.banking.bronze_policy_docs` — chunked, queryable policy corpus

# COMMAND ----------
import pyspark.sql.functions as F
from pyspark.sql import Row

CATALOG = "finserv"
SCHEMA  = "banking"

# COMMAND ----------
# %md ## The Documents
# Three real document types every retail bank has — and nobody can query.

# COMMAND ----------
DOCS = [
    # ── Doc 1: Customer Retention Playbook ────────────────────────────────────
    {
        "doc_name": "Customer Retention Playbook v2.4",
        "doc_category": "retention",
        "chunks": [
            "RETENTION OVERVIEW: Apex Banking's retention strategy prioritizes proactive intervention before customers close accounts. Relationship managers must act within 48 hours of a HIGH churn risk flag. Premium and Private segment customers require direct phone outreach; Retail customers may be handled via personalized email campaigns.",

            "FEE WAIVER POLICY: Customers with 2 or more fee-related complaints in a rolling 90-day window are eligible for a one-time courtesy fee waiver of up to $150. Premium customers are eligible for up to $300. Waivers must be logged in Salesforce within 24 hours. A second waiver within 12 months requires VP approval.",

            "ATM FEE COMPLAINTS: Out-of-network ATM fee complaints are the #1 driver of Retail churn. Standard response: offer 3 months of ATM fee reimbursement (up to $15/month). For Premium customers: offer unlimited ATM fee reimbursement for 6 months plus upgrade to Apex Preferred checking at no additional cost.",

            "ESCALATION PROTOCOL: If a customer has filed 3+ complaints in 90 days OR explicitly mentioned a competitor by name, escalate to a Senior Relationship Manager immediately. Do not attempt retention via automated channel. These customers require a human conversation within 24 hours.",

            "CHURN RECOVERY INCENTIVES: For HIGH-risk Premium customers: (1) dedicated relationship manager assignment, (2) annual fee waiver on investment accounts, (3) priority branch access, (4) complimentary wealth management consultation. Present all four as a bundled retention offer — do not offer piecemeal.",
        ]
    },
    # ── Doc 2: Premium Banking Product Guide ──────────────────────────────────
    {
        "doc_name": "Premium Banking Product Guide 2025",
        "doc_category": "product",
        "chunks": [
            "PREMIUM SEGMENT DEFINITION: Customers with $50,000+ in combined deposits OR $250,000+ in total assets with Apex Banking qualify for Premium status. Premium customers receive a dedicated relationship manager, priority phone support (< 2 min wait), and access to exclusive investment products.",

            "PREMIUM CHECKING ACCOUNT: No monthly maintenance fees. Unlimited out-of-network ATM fee reimbursements. Free wire transfers (domestic and international). Overdraft protection up to $2,500 with no overdraft fees. Complimentary cashier's checks and money orders.",

            "PREMIUM SAVINGS & INVESTMENT: Premium customers receive 0.25% above the standard savings rate. Access to Apex Wealth Management services with no minimum investment for the first consultation. Preferred rates on CDs (3-month, 6-month, 12-month). Early access to new investment products before general availability.",

            "PREMIUM MORTGAGE BENEFITS: 0.125% rate discount on new mortgage originations. Expedited underwriting (5 business days vs. 15 standard). Dedicated mortgage specialist. Free appraisal on refinance. No origination fee for loan amounts over $500,000.",

            "PREMIUM SUPPORT SLA: All Premium customer issues must be resolved or escalated within 24 hours of first contact. Relationship managers are responsible for proactive monthly check-ins. Annual relationship review meetings required. Customer satisfaction score below 7/10 triggers automatic senior manager review.",
        ]
    },
    # ── Doc 3: Complaint Handling & Regulatory Policy ─────────────────────────
    {
        "doc_name": "Complaint Handling & Regulatory Compliance Policy",
        "doc_category": "compliance",
        "chunks": [
            "CFPB COMPLIANCE: All customer complaints must be logged in the central complaint management system within 1 business day of receipt. Under Regulation E and CFPB guidelines, disputed electronic fund transfer complaints must receive a provisional credit within 10 business days while investigation is ongoing.",

            "UNAUTHORIZED TRANSACTION POLICY: When a customer reports unauthorized charges, immediately initiate a fraud investigation and issue a temporary card block. Provisional credit must be issued within 5 business days for amounts under $1,000; 10 business days for larger amounts. Investigation must complete within 45 days. Customer must be notified of outcome in writing.",

            "COMPLAINT ESCALATION THRESHOLDS: Single complaint > $5,000: VP escalation required. Three or more complaints from same customer in 90 days: Senior Relationship Manager review. Any complaint mentioning legal action or regulatory agency (CFPB, OCC, FDIC): Legal team notification within 2 hours. Social media mentions of complaints: Communications team alert.",

            "COMPLAINT RESOLUTION STANDARDS: First-contact resolution target is 70% for Retail, 85% for Premium, 95% for Private segment. Average resolution time targets: Retail 5 business days, Premium 2 business days, Private 1 business day. All resolutions must include a root-cause log entry to enable trend analysis.",

            "IDENTITY THEFT RESPONSE: Customer reporting identity theft triggers immediate account freeze, fraud alert placement with credit bureaus, and escalation to the Identity Theft Response Team. Customer receives dedicated case manager within 4 hours. Full resolution support including credit bureau dispute assistance is provided at no cost.",
        ]
    }
]

# COMMAND ----------
# %md ## Chunk and write to Bronze

# COMMAND ----------
rows = []
for doc in DOCS:
    for i, chunk in enumerate(doc["chunks"]):
        rows.append(Row(
            doc_id       = f"{doc['doc_category'][:3].upper()}-{i+1:03d}",
            doc_name     = doc["doc_name"],
            doc_category = doc["doc_category"],
            chunk_id     = i + 1,
            chunk_text   = chunk,
            source_system= "internal_policy_vault",
        ))

policy_df = (
    spark.createDataFrame(rows)
    .withColumn("ingest_ts", F.current_timestamp())
)

policy_df.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_policy_docs")

print(f"✓ bronze_policy_docs: {policy_df.count()} chunks across {len(DOCS)} documents")
policy_df.select("doc_name", "doc_category", "chunk_id").show(20, truncate=False)

# COMMAND ----------
# %md
# ## RAG Demo — Grounded Policy Recommendations
#
# Retrieval: `ai_similarity()` scores every chunk against the question.
# Generation: `ai_query()` receives the top-3 chunks as context.
# No Vector Search endpoint needed for this corpus size.
# In production: replace `ai_similarity()` with Vector Search for sub-second retrieval at scale.

# COMMAND ----------

QUESTION = "What is the retention strategy for a Premium customer who has complained about ATM fees twice and is flagged as high churn risk?"

rag_result = spark.sql(f"""
WITH ranked_chunks AS (
  SELECT
    doc_name,
    doc_category,
    chunk_text,
    ai_similarity(
      '{QUESTION}',
      chunk_text
    ) AS relevance_score
  FROM {CATALOG}.{SCHEMA}.bronze_policy_docs
),
top_context AS (
  SELECT CONCAT_WS('\n\n', COLLECT_LIST(chunk_text)) AS policy_context
  FROM (
    SELECT chunk_text
    FROM ranked_chunks
    ORDER BY relevance_score DESC
    LIMIT 3
  )
)
SELECT
  ai_query(
    'databricks-meta-llama-3-3-70b-instruct',
    CONCAT(
      'You are an Apex Banking relationship manager assistant. ',
      'Answer the question using ONLY the internal policies below. ',
      'Be specific and actionable. Keep the answer under 120 words.\n\n',
      'INTERNAL POLICIES:\n', policy_context,
      '\n\nQUESTION: ', '{QUESTION}'
    )
  ) AS recommendation
FROM top_context
""")

print(f"Question: {QUESTION}")
print()
result = rag_result.collect()[0]["recommendation"]
print(f"AI Recommendation (grounded in policy):\n{result}")
