-- Gold 1: Daily streaming summary
CREATE OR REFRESH MATERIALIZED VIEW gold_daily_streaming
CLUSTER BY (stream_date)
AS
SELECT
    CAST(event_ts AS DATE) AS stream_date,
    COUNT(*) AS total_streams,
    ROUND(SUM(watch_minutes), 1) AS total_watch_minutes,
    COUNT(DISTINCT subscriber_id) AS unique_viewers
FROM interview.media.silver_stream_events
GROUP BY CAST(event_ts AS DATE);

-- Gold 2: Content popularity (joined with content dim)
CREATE OR REFRESH MATERIALIZED VIEW gold_content_popularity
AS
SELECT
    c.content_id,
    c.title,
    c.genre,
    COUNT(*) AS total_streams,
    ROUND(SUM(s.watch_minutes), 1) AS total_watch_minutes,
    ROUND(AVG(s.watch_minutes), 1) AS avg_session_minutes
FROM interview.media.silver_stream_events s
JOIN interview.media.bronze_content c ON s.content_id = c.content_id
GROUP BY c.content_id, c.title, c.genre;

-- Gold 3: Subscriber engagement (joined with subscriber dim)
CREATE OR REFRESH MATERIALIZED VIEW gold_subscriber_engagement
AS
SELECT
    sub.plan_type,
    sub.region,
    COUNT(DISTINCT s.subscriber_id) AS active_subscribers,
    ROUND(SUM(s.watch_minutes), 1) AS total_watch_minutes,
    ROUND(AVG(s.watch_minutes), 1) AS avg_watch_minutes
FROM interview.media.silver_stream_events s
JOIN interview.media.bronze_subscribers sub ON s.subscriber_id = sub.subscriber_id
GROUP BY sub.plan_type, sub.region;
