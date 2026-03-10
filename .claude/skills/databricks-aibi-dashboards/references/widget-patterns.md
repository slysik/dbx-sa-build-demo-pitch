# Widget Patterns Reference

Detailed JSON structures for every AI/BI dashboard widget type.

## Table of Contents

- [Text (Headers/Descriptions)](#text-headersdescriptions)
- [Counter (KPI)](#counter-kpi)
  - [Pattern 1: Pre-aggregated dataset](#pattern-1-pre-aggregated-dataset-1-row-no-filters)
  - [Pattern 2: Aggregating widget](#pattern-2-aggregating-widget-multi-row-supports-filters)
- [Table](#table)
- [Line / Bar Charts](#line--bar-charts)
  - [Multi-Y Fields](#multi-y-fields)
  - [Color Grouping](#color-grouping)
  - [Bar Chart Modes](#bar-chart-modes)
- [Pie Chart](#pie-chart)
- [Filters](#filters)
  - [Filter Widget Types](#filter-widget-types)
  - [Global vs Page-Level Filters](#global-vs-page-level-filters)
  - [Filter Widget Structure](#filter-widget-structure)
  - [Global Filter Example](#global-filter-example)
  - [Page-Level Filter Example](#page-level-filter-example)
  - [Filter Layout Guidelines](#filter-layout-guidelines)

---

## Text (Headers/Descriptions)

- **CRITICAL: Text widgets do NOT use a spec block!**
- Use `multilineTextboxSpec` directly on the widget
- Supports markdown: `#`, `##`, `###`, `**bold**`, `*italic*`
- **CRITICAL: Multiple items in the `lines` array are concatenated on a single line, NOT displayed as separate lines!**
- For title + subtitle, use **separate text widgets** at different y positions

```json
// CORRECT: Separate widgets for title and subtitle
{
  "widget": {
    "name": "title",
    "multilineTextboxSpec": {
      "lines": ["## Dashboard Title"]
    }
  },
  "position": {"x": 0, "y": 0, "width": 6, "height": 1}
},
{
  "widget": {
    "name": "subtitle",
    "multilineTextboxSpec": {
      "lines": ["Description text here"]
    }
  },
  "position": {"x": 0, "y": 1, "width": 6, "height": 1}
}

// WRONG: Multiple lines concatenate into one line!
{
  "widget": {
    "name": "title-widget",
    "multilineTextboxSpec": {
      "lines": ["## Dashboard Title", "Description text here"]  // Becomes "## Dashboard TitleDescription text here"
    }
  },
  "position": {"x": 0, "y": 0, "width": 6, "height": 2}
}
```

---

## Counter (KPI)

- `version`: **2** (NOT 3!)
- `widgetType`: "counter"
- **Percent values must be 0-1** in the data (not 0-100)

### Pattern 1: Pre-aggregated dataset (1 row, no filters)

- Dataset returns exactly 1 row
- Use `"disaggregated": true` and simple field reference
- Field `name` matches dataset column directly

```json
{
  "widget": {
    "name": "total-revenue",
    "queries": [{
      "name": "main_query",
      "query": {
        "datasetName": "summary_ds",
        "fields": [{"name": "revenue", "expression": "`revenue`"}],
        "disaggregated": true
      }
    }],
    "spec": {
      "version": 2,
      "widgetType": "counter",
      "encodings": {
        "value": {"fieldName": "revenue", "displayName": "Total Revenue"}
      },
      "frame": {"showTitle": true, "title": "Total Revenue"}
    }
  },
  "position": {"x": 0, "y": 0, "width": 2, "height": 3}
}
```

### Pattern 2: Aggregating widget (multi-row, supports filters)

- Dataset returns multiple rows (e.g., grouped by a filter dimension)
- Use `"disaggregated": false` and aggregation expression
- **CRITICAL**: Field `name` MUST match `fieldName` exactly (e.g., `"sum(spend)"`)

```json
{
  "widget": {
    "name": "total-spend",
    "queries": [{
      "name": "main_query",
      "query": {
        "datasetName": "by_category",
        "fields": [{"name": "sum(spend)", "expression": "SUM(`spend`)"}],
        "disaggregated": false
      }
    }],
    "spec": {
      "version": 2,
      "widgetType": "counter",
      "encodings": {
        "value": {"fieldName": "sum(spend)", "displayName": "Total Spend"}
      },
      "frame": {"showTitle": true, "title": "Total Spend"}
    }
  },
  "position": {"x": 0, "y": 0, "width": 2, "height": 3}
}
```

---

## Table

- `version`: **2** (NOT 1 or 3!)
- `widgetType`: "table"
- **Columns only need `fieldName` and `displayName`** - no other properties!
- Use `"disaggregated": true` for raw rows

```json
{
  "widget": {
    "name": "details-table",
    "queries": [{
      "name": "main_query",
      "query": {
        "datasetName": "details_ds",
        "fields": [
          {"name": "name", "expression": "`name`"},
          {"name": "value", "expression": "`value`"}
        ],
        "disaggregated": true
      }
    }],
    "spec": {
      "version": 2,
      "widgetType": "table",
      "encodings": {
        "columns": [
          {"fieldName": "name", "displayName": "Name"},
          {"fieldName": "value", "displayName": "Value"}
        ]
      },
      "frame": {"showTitle": true, "title": "Details"}
    }
  },
  "position": {"x": 0, "y": 0, "width": 6, "height": 6}
}
```

---

## Line / Bar Charts

- `version`: **3**
- `widgetType`: "line" or "bar"
- Use `x`, `y`, optional `color` encodings
- `scale.type`: `"temporal"` (dates), `"quantitative"` (numbers), `"categorical"` (strings)
- Use `"disaggregated": true` with pre-aggregated dataset data

### Multi-Y Fields

Different metrics on same chart:

```json
"y": {
  "scale": {"type": "quantitative"},
  "fields": [
    {"fieldName": "sum(orders)", "displayName": "Orders"},
    {"fieldName": "sum(returns)", "displayName": "Returns"}
  ]
}
```

### Color Grouping

Same metric split by dimension:

```json
"y": {"fieldName": "sum(revenue)", "scale": {"type": "quantitative"}},
"color": {"fieldName": "region", "scale": {"type": "categorical"}, "displayName": "Region"}
```

### Bar Chart Modes

- **Stacked** (default): No `mark` field - bars stack on top of each other
- **Grouped**: Add `"mark": {"layout": "group"}` - bars side-by-side for comparison

---

## Pie Chart

- `version`: **3**
- `widgetType`: "pie"
- `angle`: quantitative aggregate
- `color`: categorical dimension
- Limit to 3-8 categories for readability

---

## Filters

### Filter Widget Types

> **CRITICAL**: Filter widgets use DIFFERENT widget types than charts!
> - Valid types: `filter-multi-select`, `filter-single-select`, `filter-date-range-picker`
> - **DO NOT** use `widgetType: "filter"` - this does not exist and will cause errors
> - Filters use `spec.version: 2`
> - **ALWAYS include `frame` with `showTitle: true`** for filter widgets

- `filter-date-range-picker`: for DATE/TIMESTAMP fields
- `filter-single-select`: categorical with single selection
- `filter-multi-select`: categorical with multiple selections

### Global vs Page-Level Filters

| Type | Placement | Scope | Use Case |
|------|-----------|-------|----------|
| **Global Filter** | Dedicated page with `"pageType": "PAGE_TYPE_GLOBAL_FILTERS"` | Affects ALL pages that have datasets with the filter field | Cross-dashboard filtering (e.g., date range, campaign) |
| **Page-Level Filter** | Regular page with `"pageType": "PAGE_TYPE_CANVAS"` | Affects ONLY widgets on that same page | Page-specific filtering (e.g., platform filter on breakdown page only) |

**Key Insight**: A filter only affects datasets that contain the filter field. To have a filter affect only specific pages:
1. Include the filter dimension in datasets for pages that should be filtered
2. Exclude the filter dimension from datasets for pages that should NOT be filtered

### Filter Widget Structure

> **CRITICAL**: Do NOT use `associative_filter_predicate_group` - it causes SQL errors!
> Use a simple field expression instead.

```json
{
  "widget": {
    "name": "filter_region",
    "queries": [{
      "name": "ds_data_region",
      "query": {
        "datasetName": "ds_data",
        "fields": [
          {"name": "region", "expression": "`region`"}
        ],
        "disaggregated": false
      }
    }],
    "spec": {
      "version": 2,
      "widgetType": "filter-multi-select",
      "encodings": {
        "fields": [{
          "fieldName": "region",
          "displayName": "Region",
          "queryName": "ds_data_region"
        }]
      },
      "frame": {"showTitle": true, "title": "Region"}
    }
  },
  "position": {"x": 0, "y": 0, "width": 2, "height": 2}
}
```

### Global Filter Example

Place on a dedicated filter page:

```json
{
  "name": "filters",
  "displayName": "Filters",
  "pageType": "PAGE_TYPE_GLOBAL_FILTERS",
  "layout": [
    {
      "widget": {
        "name": "filter_campaign",
        "queries": [{
          "name": "ds_campaign",
          "query": {
            "datasetName": "overview",
            "fields": [{"name": "campaign_name", "expression": "`campaign_name`"}],
            "disaggregated": false
          }
        }],
        "spec": {
          "version": 2,
          "widgetType": "filter-multi-select",
          "encodings": {
            "fields": [{
              "fieldName": "campaign_name",
              "displayName": "Campaign",
              "queryName": "ds_campaign"
            }]
          },
          "frame": {"showTitle": true, "title": "Campaign"}
        }
      },
      "position": {"x": 0, "y": 0, "width": 2, "height": 2}
    }
  ]
}
```

### Page-Level Filter Example

Place directly on a canvas page (affects only that page):

```json
{
  "name": "platform_breakdown",
  "displayName": "Platform Breakdown",
  "pageType": "PAGE_TYPE_CANVAS",
  "layout": [
    {
      "widget": {
        "name": "page-title",
        "multilineTextboxSpec": {"lines": ["## Platform Breakdown"]}
      },
      "position": {"x": 0, "y": 0, "width": 4, "height": 1}
    },
    {
      "widget": {
        "name": "filter_platform",
        "queries": [{
          "name": "ds_platform",
          "query": {
            "datasetName": "platform_data",
            "fields": [{"name": "platform", "expression": "`platform`"}],
            "disaggregated": false
          }
        }],
        "spec": {
          "version": 2,
          "widgetType": "filter-multi-select",
          "encodings": {
            "fields": [{
              "fieldName": "platform",
              "displayName": "Platform",
              "queryName": "ds_platform"
            }]
          },
          "frame": {"showTitle": true, "title": "Platform"}
        }
      },
      "position": {"x": 4, "y": 0, "width": 2, "height": 2}
    }
  ]
}
```

### Filter Layout Guidelines

- Global filters: Position on dedicated filter page, stack vertically at `x=0`
- Page-level filters: Position in header area of page (e.g., top-right corner)
- Typical sizing: `width: 2, height: 2`
