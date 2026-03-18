"""Deploy Media Streaming AI/BI Dashboard with metric view integration."""
import json, subprocess, sys

PROFILE = "slysik"
WH_ID = "b89b264d78f9d52e"
USER = "slysik@gmail.com"
DASHBOARD_NAME = "Media Streaming Analytics"

def cli(*args):
    r = subprocess.run(["databricks", "-p", PROFILE] + list(args), capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERROR: {r.stderr[:300]}", file=sys.stderr)
    return r.stdout

def api_post(path, payload):
    return json.loads(cli("api", "post", path, "--json", json.dumps(payload)))

def api_get(path):
    return json.loads(cli("api", "get", path))

def api_patch(path, payload):
    return json.loads(cli("api", "patch", path, "--json", json.dumps(payload)))

# ══════════════════════════════════════════════════════════════
# Dashboard definition
# ══════════════════════════════════════════════════════════════
dashboard = {
    "datasets": [
        {
            "name": "kpi_summary",
            "displayName": "KPI Summary",
            "queryLines": [
                "SELECT ",
                "  SUM(view_count) AS total_views, ",
                "  SUM(unique_viewers) AS total_viewers, ",
                "  ROUND(AVG(avg_watch_min), 1) AS avg_watch_min, ",
                "  ROUND(AVG(completion_pct), 1) AS avg_completion_pct ",
                "FROM interview.media.gold_daily_streaming "
            ]
        },
        {
            "name": "daily_views",
            "displayName": "Daily Views",
            "queryLines": [
                "SELECT event_date, genre, ",
                "  SUM(view_count) AS views ",
                "FROM interview.media.gold_daily_streaming ",
                "GROUP BY event_date, genre ",
                "ORDER BY event_date "
            ]
        },
        {
            "name": "genre_performance",
            "displayName": "Genre Performance",
            "queryLines": [
                "SELECT genre, ",
                "  SUM(view_count) AS views, ",
                "  ROUND(AVG(completion_pct), 1) AS completion_pct, ",
                "  ROUND(AVG(avg_watch_min), 1) AS avg_watch_min ",
                "FROM interview.media.gold_daily_streaming ",
                "GROUP BY genre ORDER BY views DESC "
            ]
        },
        {
            "name": "plan_engagement",
            "displayName": "Plan Engagement",
            "queryLines": [
                "SELECT plan_type, ",
                "  SUM(view_count) AS views, ",
                "  ROUND(AVG(avg_watch_min), 1) AS avg_watch_min, ",
                "  ROUND(AVG(completion_pct), 1) AS completion_pct ",
                "FROM interview.media.gold_plan_engagement ",
                "GROUP BY plan_type ORDER BY views DESC "
            ]
        },
        {
            "name": "metric_view_quality",
            "displayName": "Quality by Plan (Metric View)",
            "queryLines": [
                "SELECT `Plan Type` AS plan_type, `Quality` AS quality, ",
                "  MEASURE(`View Count`) AS views, ",
                "  ROUND(MEASURE(`Avg Watch Minutes`), 1) AS avg_watch_min, ",
                "  ROUND(MEASURE(`Completion Rate`) * 100, 1) AS completion_pct ",
                "FROM interview.media.streaming_metrics ",
                "GROUP BY ALL ORDER BY views DESC "
            ]
        },
        {
            "name": "top_content",
            "displayName": "Top Content",
            "queryLines": [
                "SELECT title, genre, total_views, ",
                "  avg_watch_min, completion_pct ",
                "FROM interview.media.gold_content_popularity ",
                "ORDER BY total_views DESC LIMIT 15 "
            ]
        }
    ],
    "pages": [
        {
            "name": "overview",
            "displayName": "Streaming Overview",
            "pageType": "PAGE_TYPE_CANVAS",
            "layout": [
                # ── Row 0: Title ──
                {
                    "widget": {
                        "name": "title",
                        "multilineTextboxSpec": {
                            "lines": ["## 🎬 Media Streaming Analytics"]
                        }
                    },
                    "position": {"x": 0, "y": 0, "width": 6, "height": 1}
                },
                {
                    "widget": {
                        "name": "subtitle",
                        "multilineTextboxSpec": {
                            "lines": ["Gold layer KPIs + Unity Catalog Metric View | `interview.media.streaming_metrics`"]
                        }
                    },
                    "position": {"x": 0, "y": 1, "width": 6, "height": 1}
                },
                # ── Row 2: KPIs (4 counters) ──
                {
                    "widget": {
                        "name": "kpi-total-views",
                        "queries": [{"name": "main_query", "query": {
                            "datasetName": "kpi_summary",
                            "fields": [{"name": "total_views", "expression": "`total_views`"}],
                            "disaggregated": True
                        }}],
                        "spec": {
                            "version": 2, "widgetType": "counter",
                            "encodings": {"value": {"fieldName": "total_views", "displayName": "Total Views"}},
                            "frame": {"showTitle": True, "title": "Total Views"}
                        }
                    },
                    "position": {"x": 0, "y": 2, "width": 2, "height": 3}
                },
                {
                    "widget": {
                        "name": "kpi-unique-viewers",
                        "queries": [{"name": "main_query", "query": {
                            "datasetName": "kpi_summary",
                            "fields": [{"name": "total_viewers", "expression": "`total_viewers`"}],
                            "disaggregated": True
                        }}],
                        "spec": {
                            "version": 2, "widgetType": "counter",
                            "encodings": {"value": {"fieldName": "total_viewers", "displayName": "Unique Viewers"}},
                            "frame": {"showTitle": True, "title": "Unique Viewers"}
                        }
                    },
                    "position": {"x": 2, "y": 2, "width": 2, "height": 3}
                },
                {
                    "widget": {
                        "name": "kpi-avg-watch",
                        "queries": [{"name": "main_query", "query": {
                            "datasetName": "kpi_summary",
                            "fields": [{"name": "avg_watch_min", "expression": "`avg_watch_min`"}],
                            "disaggregated": True
                        }}],
                        "spec": {
                            "version": 2, "widgetType": "counter",
                            "encodings": {"value": {"fieldName": "avg_watch_min", "displayName": "Avg Watch (min)"}},
                            "frame": {"showTitle": True, "title": "Avg Watch (min)"}
                        }
                    },
                    "position": {"x": 4, "y": 2, "width": 2, "height": 3}
                },
                # ── Row 5: Section header ──
                {
                    "widget": {
                        "name": "section-trends",
                        "multilineTextboxSpec": {"lines": ["### Viewership Trends"]}
                    },
                    "position": {"x": 0, "y": 5, "width": 6, "height": 1}
                },
                # ── Row 6: Daily trend + Genre bar ──
                {
                    "widget": {
                        "name": "daily-views-trend",
                        "queries": [{"name": "main_query", "query": {
                            "datasetName": "daily_views",
                            "fields": [
                                {"name": "event_date", "expression": "`event_date`"},
                                {"name": "views", "expression": "`views`"},
                                {"name": "genre", "expression": "`genre`"}
                            ],
                            "disaggregated": True
                        }}],
                        "spec": {
                            "version": 3, "widgetType": "line",
                            "encodings": {
                                "x": {"fieldName": "event_date", "scale": {"type": "temporal"}, "displayName": "Date"},
                                "y": {"fieldName": "views", "scale": {"type": "quantitative"}, "displayName": "Views"},
                                "color": {"fieldName": "genre", "scale": {"type": "categorical"}, "displayName": "Genre"}
                            },
                            "frame": {"showTitle": True, "title": "Daily Views by Genre"}
                        }
                    },
                    "position": {"x": 0, "y": 6, "width": 6, "height": 6}
                },
                # ── Row 12: Genre bar + Plan bar ──
                {
                    "widget": {
                        "name": "genre-bar",
                        "queries": [{"name": "main_query", "query": {
                            "datasetName": "genre_performance",
                            "fields": [
                                {"name": "genre", "expression": "`genre`"},
                                {"name": "views", "expression": "`views`"},
                                {"name": "completion_pct", "expression": "`completion_pct`"}
                            ],
                            "disaggregated": True
                        }}],
                        "spec": {
                            "version": 3, "widgetType": "bar",
                            "encodings": {
                                "x": {"fieldName": "genre", "scale": {"type": "categorical"}, "displayName": "Genre"},
                                "y": {"fieldName": "views", "scale": {"type": "quantitative"}, "displayName": "Views"}
                            },
                            "frame": {"showTitle": True, "title": "Views by Genre"}
                        }
                    },
                    "position": {"x": 0, "y": 12, "width": 3, "height": 5}
                },
                {
                    "widget": {
                        "name": "plan-bar",
                        "queries": [{"name": "main_query", "query": {
                            "datasetName": "plan_engagement",
                            "fields": [
                                {"name": "plan_type", "expression": "`plan_type`"},
                                {"name": "views", "expression": "`views`"},
                                {"name": "avg_watch_min", "expression": "`avg_watch_min`"}
                            ],
                            "disaggregated": True
                        }}],
                        "spec": {
                            "version": 3, "widgetType": "bar",
                            "encodings": {
                                "x": {"fieldName": "plan_type", "scale": {"type": "categorical"}, "displayName": "Plan"},
                                "y": {"fieldName": "views", "scale": {"type": "quantitative"}, "displayName": "Views"}
                            },
                            "frame": {"showTitle": True, "title": "Views by Subscription Plan"}
                        }
                    },
                    "position": {"x": 3, "y": 12, "width": 3, "height": 5}
                },
                # ── Row 17: Metric View section ──
                {
                    "widget": {
                        "name": "section-metric-view",
                        "multilineTextboxSpec": {"lines": ["### Quality Analysis (from Metric View)"]}
                    },
                    "position": {"x": 0, "y": 17, "width": 6, "height": 1}
                },
                {
                    "widget": {
                        "name": "quality-by-plan",
                        "queries": [{"name": "main_query", "query": {
                            "datasetName": "metric_view_quality",
                            "fields": [
                                {"name": "plan_type", "expression": "`plan_type`"},
                                {"name": "quality", "expression": "`quality`"},
                                {"name": "views", "expression": "`views`"}
                            ],
                            "disaggregated": True
                        }}],
                        "spec": {
                            "version": 3, "widgetType": "bar",
                            "mark": {"layout": "group"},
                            "encodings": {
                                "x": {"fieldName": "plan_type", "scale": {"type": "categorical"}, "displayName": "Plan"},
                                "y": {"fieldName": "views", "scale": {"type": "quantitative"}, "displayName": "Views"},
                                "color": {"fieldName": "quality", "scale": {"type": "categorical"}, "displayName": "Quality"}
                            },
                            "frame": {"showTitle": True, "title": "Stream Quality by Plan (Metric View)"}
                        }
                    },
                    "position": {"x": 0, "y": 18, "width": 6, "height": 5}
                },
                # ── Row 23: Top content table ──
                {
                    "widget": {
                        "name": "section-content",
                        "multilineTextboxSpec": {"lines": ["### Top Content"]}
                    },
                    "position": {"x": 0, "y": 23, "width": 6, "height": 1}
                },
                {
                    "widget": {
                        "name": "content-table",
                        "queries": [{"name": "main_query", "query": {
                            "datasetName": "top_content",
                            "fields": [
                                {"name": "title", "expression": "`title`"},
                                {"name": "genre", "expression": "`genre`"},
                                {"name": "total_views", "expression": "`total_views`"},
                                {"name": "avg_watch_min", "expression": "`avg_watch_min`"},
                                {"name": "completion_pct", "expression": "`completion_pct`"}
                            ],
                            "disaggregated": True
                        }}],
                        "spec": {
                            "version": 2, "widgetType": "table",
                            "encodings": {
                                "columns": [
                                    {"fieldName": "title", "displayName": "Title"},
                                    {"fieldName": "genre", "displayName": "Genre"},
                                    {"fieldName": "total_views", "displayName": "Total Views"},
                                    {"fieldName": "avg_watch_min", "displayName": "Avg Watch (min)"},
                                    {"fieldName": "completion_pct", "displayName": "Completion %"}
                                ]
                            },
                            "frame": {"showTitle": True, "title": "Top 15 Content by Views"}
                        }
                    },
                    "position": {"x": 0, "y": 24, "width": 6, "height": 6}
                }
            ]
        },
        # ── Global filter page ──
        {
            "name": "filters",
            "displayName": "Filters",
            "pageType": "PAGE_TYPE_GLOBAL_FILTERS",
            "layout": [
                {
                    "widget": {
                        "name": "filter-genre",
                        "queries": [{"name": "dv_genre", "query": {
                            "datasetName": "genre_performance",
                            "fields": [{"name": "genre", "expression": "`genre`"}],
                            "disaggregated": False
                        }}],
                        "spec": {
                            "version": 2, "widgetType": "filter-multi-select",
                            "encodings": {"fields": [{"fieldName": "genre", "displayName": "Genre", "queryName": "dv_genre"}]},
                            "frame": {"showTitle": True, "title": "Genre"}
                        }
                    },
                    "position": {"x": 0, "y": 0, "width": 2, "height": 2}
                },
                {
                    "widget": {
                        "name": "filter-plan",
                        "queries": [{"name": "dv_plan", "query": {
                            "datasetName": "plan_engagement",
                            "fields": [{"name": "plan_type", "expression": "`plan_type`"}],
                            "disaggregated": False
                        }}],
                        "spec": {
                            "version": 2, "widgetType": "filter-multi-select",
                            "encodings": {"fields": [{"fieldName": "plan_type", "displayName": "Plan", "queryName": "dv_plan"}]},
                            "frame": {"showTitle": True, "title": "Plan Type"}
                        }
                    },
                    "position": {"x": 2, "y": 0, "width": 2, "height": 2}
                }
            ]
        }
    ]
}

# ══════════════════════════════════════════════════════════════
# Deploy
# ══════════════════════════════════════════════════════════════
print("Deploying dashboard...")

# Check for existing
dashboards = api_get("/api/2.0/lakeview/dashboards")
existing = [d for d in dashboards.get("dashboards", [])
            if d.get("display_name") == DASHBOARD_NAME and d.get("lifecycle_state") != "TRASHED"]

serialized = json.dumps(dashboard)

if existing:
    dash_id = existing[0]["dashboard_id"]
    result = api_patch(f"/api/2.0/lakeview/dashboards/{dash_id}", {
        "display_name": DASHBOARD_NAME,
        "serialized_dashboard": serialized,
        "warehouse_id": WH_ID,
    })
    print(f"  ✓ Updated: {dash_id}")
else:
    result = api_post("/api/2.0/lakeview/dashboards", {
        "display_name": DASHBOARD_NAME,
        "parent_path": f"/Users/{USER}",
        "serialized_dashboard": serialized,
        "warehouse_id": WH_ID,
    })
    dash_id = result.get("dashboard_id", "")
    print(f"  ✓ Created: {dash_id}")

# Publish
api_post(f"/api/2.0/lakeview/dashboards/{dash_id}/published", {
    "embed_credentials": True,
    "warehouse_id": WH_ID,
})
print(f"  ✓ Published")

host = "https://adb-7405619449104571.11.azuredatabricks.net"
print(f"\n✅ Dashboard: {host}/dashboardsv3/{dash_id}")
