---
name: databricks-aibi-dashboards
description: "Create Databricks AI/BI dashboards. CRITICAL: You MUST test ALL SQL queries via execute_sql BEFORE deploying. Follow guidelines strictly."
---

# AI/BI Dashboard Skill

Create Databricks AI/BI dashboards (formerly Lakeview dashboards). **Follow these guidelines strictly.**

## Reference Files

| File | When to Read |
|------|-------------|
| [references/complete-example.md](references/complete-example.md) | Building a full dashboard from scratch |
| [references/widget-patterns.md](references/widget-patterns.md) | Need specific widget JSON structure |
| [references/troubleshooting.md](references/troubleshooting.md) | Dashboard creation/update failing |

## CRITICAL: MANDATORY VALIDATION WORKFLOW

**You MUST follow this workflow exactly. Skipping validation causes broken dashboards.**

```
STEP 1: Get table schemas via get_table_details(catalog, schema)
STEP 2: Write SQL queries for each dataset
STEP 3: TEST EVERY QUERY via execute_sql() -- DO NOT SKIP!
        - If query fails, FIX IT before proceeding
        - Verify column names match what widgets will reference
        - Verify data types are correct (dates, numbers, strings)
STEP 4: Build dashboard JSON using ONLY verified queries
STEP 5: Deploy via create_or_update_dashboard()
```

**WARNING: If you deploy without testing queries, widgets WILL show "Invalid widget definition" errors!**

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `get_table_details` | **STEP 1**: Get table schemas for designing queries |
| `execute_sql` | **STEP 3**: Test SQL queries - MANDATORY before deployment! |
| `get_best_warehouse` | Get available warehouse ID |
| `create_or_update_dashboard` | **STEP 5**: Deploy dashboard JSON (only after validation!) |
| `get_dashboard` | Get dashboard details by ID, or list all dashboards (omit dashboard_id) |
| `delete_dashboard` | Move dashboard to trash |
| `publish_dashboard` | Publish (`publish=True`) or unpublish (`publish=False`) a dashboard |

---

## Implementation Guidelines

### 1) DATASET ARCHITECTURE (STRICT)

- **One dataset per domain** (e.g., orders, customers, products)
- **Exactly ONE valid SQL query per dataset** (no multiple queries separated by `;`)
- Always use **fully-qualified table names**: `catalog.schema.table_name`
- SELECT must include all dimensions needed by widgets and all derived columns via `AS` aliases
- Put ALL business logic (CASE/WHEN, COALESCE, ratios) into the dataset SELECT with explicit aliases
- **Contract rule**: Every widget `fieldName` must exactly match a dataset column or alias

### 2) WIDGET FIELD EXPRESSIONS

> **CRITICAL: Field Name Matching Rule**
> The `name` in `query.fields` MUST exactly match the `fieldName` in `encodings`.
> If they don't match, the widget shows "no selected fields to visualize" error!

**Correct pattern for aggregations:**
```json
// In query.fields:
{"name": "sum(spend)", "expression": "SUM(`spend`)"}

// In encodings (must match!):
{"fieldName": "sum(spend)", "displayName": "Total Spend"}
```

**WRONG - names don't match:**
```json
// In query.fields:
{"name": "spend", "expression": "SUM(`spend`)"}  // name is "spend"

// In encodings:
{"fieldName": "sum(spend)", ...}  // ERROR: "sum(spend)" != "spend"
```

Allowed expressions in widget queries (you CANNOT use CAST or other SQL in expressions):

**For numbers:**
```json
{"name": "sum(revenue)", "expression": "SUM(`revenue`)"}
{"name": "avg(price)", "expression": "AVG(`price`)"}
{"name": "count(orders)", "expression": "COUNT(`order_id`)"}
{"name": "countdistinct(customers)", "expression": "COUNT(DISTINCT `customer_id`)"}
{"name": "min(date)", "expression": "MIN(`order_date`)"}
{"name": "max(date)", "expression": "MAX(`order_date`)"}
```

**For dates** (use daily for timeseries, weekly/monthly for grouped comparisons):
```json
{"name": "daily(date)", "expression": "DATE_TRUNC(\"DAY\", `date`)"}
{"name": "weekly(date)", "expression": "DATE_TRUNC(\"WEEK\", `date`)"}
{"name": "monthly(date)", "expression": "DATE_TRUNC(\"MONTH\", `date`)"}
```

**Simple field reference** (for pre-aggregated data):
```json
{"name": "category", "expression": "`category`"}
```

If you need conditional logic or multi-field formulas, compute a derived column in the dataset SQL first.

### 3) SPARK SQL PATTERNS

- Date math: `date_sub(current_date(), N)` for days, `add_months(current_date(), -N)` for months
- Date truncation: `DATE_TRUNC('DAY'|'WEEK'|'MONTH'|'QUARTER'|'YEAR', column)`
- **AVOID** `INTERVAL` syntax - use functions instead

### 4) LAYOUT (6-Column Grid, NO GAPS)

Each widget has a position: `{"x": 0, "y": 0, "width": 2, "height": 4}`

**CRITICAL**: Each row must fill width=6 exactly. No gaps allowed.

**Recommended widget sizes:**

| Widget Type | Width | Height | Notes |
|-------------|-------|--------|-------|
| Text header | 6 | 1 | Full width; use SEPARATE widgets for title and subtitle |
| Counter/KPI | 2 | **3-4** | **NEVER height=2** - too cramped! |
| Line/Bar chart | 3 | **5-6** | Pair side-by-side to fill row |
| Pie chart | 3 | **5-6** | Needs space for legend |
| Full-width chart | 6 | 5-7 | For detailed time series |
| Table | 6 | 5-8 | Full width for readability |

**Standard dashboard structure:**
```text
y=0:  Title (w=6, h=1) - Dashboard title (use separate widget!)
y=1:  Subtitle (w=6, h=1) - Description (use separate widget!)
y=2:  KPIs (w=2 each, h=3) - 3 key metrics side-by-side
y=5:  Section header (w=6, h=1) - "Trends" or similar
y=6:  Charts (w=3 each, h=5) - Two charts side-by-side
y=11: Section header (w=6, h=1) - "Details"
y=12: Table (w=6, h=6) - Detailed data
```

### 5) CARDINALITY & READABILITY (CRITICAL)

**Dashboard readability depends on limiting distinct values:**

| Dimension Type | Max Values | Examples |
|----------------|------------|----------|
| Chart color/groups | **3-8** | 4 regions, 5 product lines, 3 tiers |
| Filters | 4-10 | 8 countries, 5 channels |
| High cardinality | **Table only** | customer_id, order_id, SKU |

**Before creating any chart with color/grouping:**
1. Check column cardinality (use `get_table_details` to see distinct values)
2. If >10 distinct values, aggregate to higher level OR use TOP-N + "Other" bucket
3. For high-cardinality dimensions, use a table widget instead of a chart

### 6) WIDGET TYPE QUICK REFERENCE

**Widget Naming Convention (CRITICAL):**
- `widget.name`: alphanumeric + hyphens + underscores ONLY (no spaces, parentheses, colons)
- `frame.title`: human-readable name (any characters allowed)
- `widget.queries[0].name`: always use `"main_query"`

**Version Requirements:**

| Widget Type | Version | Key Notes |
|-------------|---------|-----------|
| text | N/A | No `spec` block - use `multilineTextboxSpec` directly on widget |
| counter | 2 | Use `disaggregated: true` for 1-row datasets, `false` with aggregation for multi-row |
| table | 2 | Columns only need `fieldName` + `displayName` |
| filter-multi-select | 2 | Use `disaggregated: false`; include `frame` with `showTitle: true` |
| filter-single-select | 2 | Same as multi-select but single selection |
| filter-date-range-picker | 2 | For DATE/TIMESTAMP fields |
| bar | 3 | Stacked default; add `"mark": {"layout": "group"}` for grouped |
| line | 3 | Use `x`, `y`, optional `color` encodings |
| pie | 3 | Use `angle` (quantitative) + `color` (categorical); limit 3-8 categories |

> For detailed JSON structures of each widget type, see [references/widget-patterns.md](references/widget-patterns.md).

### 7) FILTERS QUICK REFERENCE

> **CRITICAL**: Do NOT use `widgetType: "filter"` - this does not exist!
> Valid types: `filter-multi-select`, `filter-single-select`, `filter-date-range-picker`
> Do NOT use `associative_filter_predicate_group` - it causes SQL errors!

| Type | Placement | Scope |
|------|-----------|-------|
| **Global Filter** | Dedicated page with `"pageType": "PAGE_TYPE_GLOBAL_FILTERS"` | All pages with matching dataset fields |
| **Page-Level Filter** | Regular `PAGE_TYPE_CANVAS` page | Only widgets on that page |

**Key Insight**: A filter only affects datasets that contain the filter field.

> For complete filter JSON patterns, see [references/widget-patterns.md](references/widget-patterns.md#filters).

### 8) QUALITY CHECKLIST

Before deploying, verify:
1. All widget names use only alphanumeric + hyphens + underscores
2. All rows sum to width=6 with no gaps
3. KPIs use height 3-4, charts use height 5-6
4. Chart dimensions have <=8 distinct values
5. All widget fieldNames match dataset columns exactly
6. **Field `name` in query.fields matches `fieldName` in encodings exactly** (e.g., both `"sum(spend)"`)
7. Counter datasets: use `disaggregated: true` for 1-row datasets, `disaggregated: false` with aggregation for multi-row
8. Percent values are 0-1 (not 0-100)
9. SQL uses Spark syntax (date_sub, not INTERVAL)
10. **All SQL queries tested via `execute_sql` and return expected data**

---

## Related Skills

- **[databricks-unity-catalog](../databricks-unity-catalog/SKILL.md)** - for querying the underlying data and system tables
- **[databricks-spark-declarative-pipelines](../databricks-spark-declarative-pipelines/SKILL.md)** - for building the data pipelines that feed dashboards
- **[databricks-jobs](../databricks-jobs/SKILL.md)** - for scheduling dashboard data refreshes
