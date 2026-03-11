-- Metric View: Governed media streaming KPIs
-- Star-schema joins in YAML — Silver fact + Bronze dims
-- Query with: SELECT `Genre`, MEASURE(`Total Watch Minutes`) FROM ... GROUP BY ALL

CREATE OR REPLACE VIEW interview.media.media_streaming_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
comment: "Media platform streaming KPIs — governed metrics for consistent reporting"
source: interview.media.silver_stream_events

joins:
  - name: content
    source: interview.media.bronze_content
    on: source.content_id = content.content_id
  - name: subscribers
    source: interview.media.bronze_subscribers
    on: source.subscriber_id = subscribers.subscriber_id

dimensions:
  - name: Genre
    expr: content.genre
    comment: "Content genre category"
  - name: Plan Type
    expr: subscribers.plan_type
    comment: "Subscriber plan tier"
  - name: Region
    expr: subscribers.region
    comment: "Subscriber geographic region"
  - name: Stream Month
    expr: "DATE_TRUNC('MONTH', source.event_ts)"
    comment: "Month of stream event"

measures:
  - name: Total Watch Minutes
    expr: SUM(source.watch_minutes)
    comment: "Total minutes watched across all streams"
  - name: Total Streams
    expr: COUNT(1)
    comment: "Number of streaming events"
  - name: Avg Session Minutes
    expr: AVG(source.watch_minutes)
    comment: "Average watch time per streaming session"
$$;
