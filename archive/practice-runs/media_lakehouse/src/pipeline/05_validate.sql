-- Validation: Row counts across layers
SELECT 'bronze_content' AS table_name, COUNT(*) AS rows FROM interview.media.bronze_content
UNION ALL SELECT 'bronze_subscribers', COUNT(*) FROM interview.media.bronze_subscribers
UNION ALL SELECT 'bronze_stream_events', COUNT(*) FROM interview.media.bronze_stream_events
UNION ALL SELECT 'silver_stream_events', COUNT(*) FROM interview.media.silver_stream_events
UNION ALL SELECT 'gold_daily_streaming', COUNT(*) FROM interview.media.gold_daily_streaming
UNION ALL SELECT 'gold_content_popularity', COUNT(*) FROM interview.media.gold_content_popularity
UNION ALL SELECT 'gold_subscriber_engagement', COUNT(*) FROM interview.media.gold_subscriber_engagement;

-- CDC verification: Silver should have 99K rows (100K - 1K deletes)
-- Duplicate check on Silver
SELECT event_id, COUNT(*) cnt
FROM interview.media.silver_stream_events
GROUP BY event_id HAVING cnt > 1;

-- Null audit
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN event_id IS NULL THEN 1 ELSE 0 END) AS null_event_ids,
    SUM(CASE WHEN subscriber_id IS NULL THEN 1 ELSE 0 END) AS null_subscriber_ids,
    SUM(CASE WHEN watch_minutes IS NULL THEN 1 ELSE 0 END) AS null_watch_minutes
FROM interview.media.silver_stream_events;
