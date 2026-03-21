# Test Prompts: databricks-genie

Fixed validation data. Do not modify.

---

## Prompt 1: Create a Genie Space via API

Create a Genie Space called "Banking Risk Intelligence" with tables `finserv.banking.gold_churn_risk`, `finserv.banking.gold_segment_kpis`, and `finserv.banking.silver_transactions`. Use warehouse `4bbaafe9538467a0`. Show the complete API call.

**EXPECT:** POST /api/2.0/genie/spaces, serialized_space, table_identifiers, warehouse_id, sorted alphabetically

---

## Prompt 2: serialized_space format

What is the exact JSON structure required in the `serialized_space` field when creating a Genie Space? Include a sample question.

**EXPECT:** version: 2, data_sources, tables, identifier, config, sample_questions, id 32hex, question list, json.dumps

---

## Prompt 3: Table sort order requirement

I'm creating a Genie Space with 4 tables. Does the order of tables in `serialized_space` matter? What happens if I pass them unsorted?

**EXPECT:** alphabetically sorted, identifier, must be sorted, proto3

---

## Prompt 4: Ask a question via Genie API

After creating a Genie Space with ID `01f123af4575169f84599de01de4855c`, how do I ask it "Which customer segments have the highest churn risk?" programmatically?

**EXPECT:** ask_genie, conversation, /api/2.0/genie/rooms, question, space_id, message

---

## Prompt 5: Genie permissions model

Can I set permissions on a Genie Space via the `/api/2.0/permissions/data-rooms/{id}` endpoint? What is the correct approach?

**EXPECT:** data-rooms NOT valid, 400 error, workspace admin, implicit access, collaborators, no explicit ACL
