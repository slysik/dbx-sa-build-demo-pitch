-- Gold: Daily streaming metrics
CREATE OR REFRESH MATERIALIZED VIEW gold_daily_streaming
COMMENT 'Daily streaming KPIs — volume, watch time, completion rate'
AS
SELECT
    stream_date,
    COUNT(*)                                        AS total_streams,
    COUNT(DISTINCT subscriber_id)                   AS unique_viewers,
    ROUND(SUM(watch_min), 1)                        AS total_watch_min,
    ROUND(AVG(watch_min), 1)                        AS avg_watch_min,
    ROUND(SUM(CASE WHEN completed THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
                                                    AS completion_rate_pct
FROM interview.media.silver_stream_events
GROUP BY stream_date;

-- Gold: Content popularity (genre + content_type breakdown)
CREATE OR REFRESH MATERIALIZED VIEW gold_content_popularity
COMMENT 'Content engagement by genre and type'
AS
SELECT
    genre,
    content_type,
    COUNT(*)                                        AS total_streams,
    COUNT(DISTINCT subscriber_id)                   AS unique_viewers,
    ROUND(AVG(watch_min), 1)                        AS avg_watch_min,
    ROUND(SUM(CASE WHEN completed THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
                                                    AS completion_rate_pct
FROM interview.media.silver_stream_events
GROUP BY genre, content_type;

-- Gold: Plan engagement (subscriber plan behavior)
CREATE OR REFRESH MATERIALIZED VIEW gold_plan_engagement
COMMENT 'Streaming behavior by subscription plan and device'
AS
SELECT
    plan_type,
    device,
    country,
    COUNT(*)                                        AS total_streams,
    COUNT(DISTINCT subscriber_id)                   AS unique_viewers,
    ROUND(SUM(watch_min), 1)                        AS total_watch_min,
    ROUND(AVG(watch_min), 1)                        AS avg_watch_min,
    ROUND(SUM(CASE WHEN completed THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
                                                    AS completion_rate_pct
FROM interview.media.silver_stream_events
GROUP BY plan_type, device, country;
