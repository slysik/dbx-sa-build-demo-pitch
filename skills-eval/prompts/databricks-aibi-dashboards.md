# Test Prompts: databricks-aibi-dashboards

Fixed validation data. Do not modify.

---

## Prompt 1: Create a counter widget

Create an AI/BI dashboard counter widget that shows total transaction count from `finserv.banking.gold_segment_kpis`. The widget should be named `total_txn_count` and display with the title "Total Transactions".

**EXPECT:** version: 2, counterSpec, widgetType, name total_txn_count, frame title, query dataset

---

## Prompt 2: Deploy dashboard with correct publish settings

Show me the exact API call to create and then publish an AI/BI dashboard. What is the required `embed_credentials` value and where does `parent_path` point?

**EXPECT:** embed_credentials: false, parent_path, /Users/, lakeview/dashboards, POST, published

---

## Prompt 3: Bar chart widget for revenue by category

Add a bar chart widget to an existing dashboard showing revenue by `txn_category` from `finserv.banking.silver_transactions`. The x-axis should be category, y-axis should be SUM(amount).

**EXPECT:** version: 3, barSpec, x encoding, y encoding, fieldName, expression SUM, name

---

## Prompt 4: Debug "no selected fields to visualize" error

My dashboard counter widget shows "no selected fields to visualize". The query field is named `total_revenue` but the encoding uses `fieldName: "sum(revenue)"`. What is wrong and how do I fix it?

**EXPECT:** fieldName mismatch, name in fields must match fieldName in encodings, expression, exact match

---

## Prompt 5: Multi-page dashboard with global filter

Design a 2-page dashboard where page 1 has KPIs and page 2 has a detail table. Add a global filter on `segment` that applies to both pages. What widget type is the filter and what page type does it live on?

**EXPECT:** PAGE_TYPE_GLOBAL_FILTERS, filter-multi-select, version: 2, queryName, disaggregated: false
