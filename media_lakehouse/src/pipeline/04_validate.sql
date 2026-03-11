-- Validation: Row counts across all layers
SELECT 'bronze_content' AS table_name, COUNT(*) AS rows FROM interview.media.bronze_content
UNION ALL SELECT 'bronze_subscribers', COUNT(*) FROM interview.media.bronze_subscribers
UNION ALL SELECT 'bronze_stream_events', COUNT(*) FROM interview.media.bronze_stream_events
UNION ALL SELECT 'silver_content', COUNT(*) FROM interview.media.silver_content
UNION ALL SELECT 'silver_subscribers', COUNT(*) FROM interview.media.silver_subscribers
UNION ALL SELECT 'silver_stream_events', COUNT(*) FROM interview.media.silver_stream_events
UNION ALL SELECT 'gold_daily_streaming', COUNT(*) FROM interview.media.gold_daily_streaming
UNION ALL SELECT 'gold_content_popularity', COUNT(*) FROM interview.media.gold_content_popularity
UNION ALL SELECT 'gold_plan_engagement', COUNT(*) FROM interview.media.gold_plan_engagement;
