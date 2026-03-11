-- Silver: Clean, type, dedup stream events
CREATE OR REFRESH MATERIALIZED VIEW silver_stream_events
COMMENT 'Cleaned stream events — deduped, typed, null-handled'
AS
SELECT
    event_id,
    content_id,
    subscriber_id,
    genre,
    content_type,
    duration_min,
    plan_type,
    country,
    age_group,
    CAST(stream_date AS DATE)           AS stream_date,
    CAST(stream_ts AS TIMESTAMP)        AS stream_ts,
    ROUND(CAST(watch_min AS DOUBLE), 1) AS watch_min,
    device,
    COALESCE(completed, FALSE)          AS completed,
    CAST(ingest_ts AS TIMESTAMP)        AS ingest_ts,
    source_system,
    batch_id
FROM interview.media.bronze_stream_events
QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY ingest_ts DESC) = 1;

-- Silver: Clean content dimension
CREATE OR REFRESH MATERIALIZED VIEW silver_content
COMMENT 'Cleaned content library'
AS
SELECT
    content_id,
    genre,
    content_type,
    CAST(duration_min AS INT)   AS duration_min,
    CAST(release_year AS INT)   AS release_year
FROM interview.media.bronze_content;

-- Silver: Clean subscribers dimension
CREATE OR REFRESH MATERIALIZED VIEW silver_subscribers
COMMENT 'Cleaned subscriber profiles'
AS
SELECT
    subscriber_id,
    plan_type,
    country,
    age_group,
    CAST(signup_date AS DATE) AS signup_date
FROM interview.media.bronze_subscribers;
