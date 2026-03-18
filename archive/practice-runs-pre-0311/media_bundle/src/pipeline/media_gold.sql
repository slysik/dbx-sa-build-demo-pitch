-- ============================================================================
-- GOLD LAYER — Media Streaming
-- Pre-aggregated, consumption-shaped. BI/dashboard-ready.
--
-- Liquid Clustering on every Gold table:
--   - Auto-optimizes file layout based on query patterns
--   - Multi-column data skipping via Hilbert curves
--   - Keys are MUTABLE: ALTER TABLE ... CLUSTER BY (new_col)
-- ============================================================================


-- Gold: Daily Streaming Metrics — the main dashboard time-series
-- "How is viewership trending by genre and country?"
CREATE OR REFRESH MATERIALIZED VIEW gold_daily_streaming
CLUSTER BY (event_date, genre)
COMMENT 'Daily streaming KPIs by genre and country — core dashboard table'
AS
SELECT
  e.event_date,
  c.genre,
  s.country,
  COUNT(*)                                                     AS view_count,
  COUNT(DISTINCT e.subscriber_id)                              AS unique_viewers,
  ROUND(AVG(e.stream_duration_sec / 60.0), 1)                 AS avg_watch_min,
  ROUND(SUM(CASE WHEN e.completed THEN 1 ELSE 0 END) * 100.0
        / COUNT(*), 1)                                         AS completion_pct,
  ROUND(AVG(e.buffering_events), 2)                            AS avg_buffering
FROM silver_stream_events e
INNER JOIN silver_content c ON e.content_id = c.content_id
INNER JOIN silver_subscribers s ON e.subscriber_id = s.subscriber_id
GROUP BY e.event_date, c.genre, s.country;


-- Gold: Content Popularity — "What are our top-performing titles?"
CREATE OR REFRESH MATERIALIZED VIEW gold_content_popularity
CLUSTER BY (genre)
COMMENT 'Content performance — total views, watch time, completion rate per title'
AS
SELECT
  c.content_id,
  c.title,
  c.genre,
  c.content_type,
  c.duration_min,
  COUNT(*)                                                     AS total_views,
  COUNT(DISTINCT e.subscriber_id)                              AS unique_viewers,
  ROUND(AVG(e.stream_duration_sec / 60.0), 1)                 AS avg_watch_min,
  ROUND(SUM(CASE WHEN e.completed THEN 1 ELSE 0 END) * 100.0
        / COUNT(*), 1)                                         AS completion_pct
FROM silver_stream_events e
INNER JOIN silver_content c ON e.content_id = c.content_id
GROUP BY c.content_id, c.title, c.genre, c.content_type, c.duration_min;


-- Gold: Plan Engagement — "How do subscription tiers compare?"
CREATE OR REFRESH MATERIALIZED VIEW gold_plan_engagement
CLUSTER BY (plan_type)
COMMENT 'Subscriber engagement by plan — views, quality mix, watch time'
AS
SELECT
  s.plan_type,
  e.quality,
  s.age_group,
  COUNT(*)                                                     AS view_count,
  COUNT(DISTINCT e.subscriber_id)                              AS unique_viewers,
  ROUND(AVG(e.stream_duration_sec / 60.0), 1)                 AS avg_watch_min,
  ROUND(SUM(CASE WHEN e.completed THEN 1 ELSE 0 END) * 100.0
        / COUNT(*), 1)                                         AS completion_pct,
  ROUND(AVG(e.buffering_events), 2)                            AS avg_buffering
FROM silver_stream_events e
INNER JOIN silver_subscribers s ON e.subscriber_id = s.subscriber_id
GROUP BY s.plan_type, e.quality, s.age_group;
