-- ============================================================================
-- SILVER LAYER — Media Streaming
-- Cleaned, typed, deduped. Materialized views reading from Bronze Delta.
--
-- Pattern: ROW_NUMBER dedup → CAST every column → expectations → CLUSTER BY
-- Bronze was written by spark.range() notebook — regular Delta tables.
-- ============================================================================


-- Silver: Content — normalize genre casing, filter future years, dedup
CREATE OR REFRESH MATERIALIZED VIEW silver_content(
  CONSTRAINT valid_content_id  EXPECT (content_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_release     EXPECT (release_year <= 2025)   ON VIOLATION DROP ROW
)
CLUSTER BY (genre)
COMMENT 'Cleaned content dimension — genre normalized, future years dropped'
AS
SELECT
  CAST(content_id AS STRING)      AS content_id,
  CAST(title AS STRING)           AS title,
  INITCAP(CAST(genre AS STRING))  AS genre,        -- normalize "drama" → "Drama"
  CAST(content_type AS STRING)    AS content_type,
  CAST(duration_min AS INT)       AS duration_min,
  CAST(release_year AS INT)       AS release_year
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY content_id ORDER BY content_id) AS _rn
  FROM interview.media.bronze_content
)
WHERE _rn = 1;


-- Silver: Subscribers — trim country, dedup on subscriber_id
CREATE OR REFRESH MATERIALIZED VIEW silver_subscribers(
  CONSTRAINT valid_subscriber_id EXPECT (subscriber_id IS NOT NULL) ON VIOLATION DROP ROW
)
CLUSTER BY (plan_type)
COMMENT 'Cleaned subscriber dimension — deduped, country trimmed'
AS
SELECT
  CAST(subscriber_id AS STRING)      AS subscriber_id,
  CAST(plan_type AS STRING)          AS plan_type,
  TRIM(CAST(country AS STRING))      AS country,     -- remove whitespace
  CAST(age_group AS STRING)          AS age_group,
  CAST(signup_date AS DATE)          AS signup_date,
  CAST(preferred_device AS STRING)   AS preferred_device
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY subscriber_id ORDER BY signup_date DESC) AS _rn
  FROM interview.media.bronze_subscribers
)
WHERE _rn = 1;


-- Silver: Stream Events — filter negative durations, dedup on event_id
-- Only select fact-native columns — dim attributes joined in Gold
CREATE OR REFRESH MATERIALIZED VIEW silver_stream_events(
  CONSTRAINT valid_event_id    EXPECT (event_id IS NOT NULL)       ON VIOLATION DROP ROW,
  CONSTRAINT valid_content     EXPECT (content_id IS NOT NULL)     ON VIOLATION DROP ROW,
  CONSTRAINT positive_duration EXPECT (stream_duration_sec > 0)    ON VIOLATION DROP ROW
)
CLUSTER BY (event_date)
COMMENT 'Cleaned stream events — negative durations dropped, deduped, typed'
AS
SELECT
  CAST(event_id AS STRING)            AS event_id,
  CAST(subscriber_id AS STRING)       AS subscriber_id,
  CAST(content_id AS STRING)          AS content_id,
  CAST(event_date AS DATE)            AS event_date,
  CAST(event_ts AS TIMESTAMP)         AS event_ts,
  CAST(stream_duration_sec AS INT)    AS stream_duration_sec,
  CAST(quality AS STRING)             AS quality,
  CAST(buffering_events AS INT)       AS buffering_events,
  CAST(completed AS BOOLEAN)          AS completed
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY event_id) AS _rn
  FROM interview.media.bronze_stream_events
)
WHERE _rn = 1;
