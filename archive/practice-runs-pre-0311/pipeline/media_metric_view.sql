CREATE OR REPLACE VIEW interview.media.streaming_metrics
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
comment: "Media streaming KPIs — governed metrics with star-schema joins"
source: interview.media.silver_stream_events
joins:
  - name: content
    source: interview.media.silver_content
    on: source.content_id = content.content_id
  - name: subscriber
    source: interview.media.silver_subscribers
    on: source.subscriber_id = subscriber.subscriber_id
dimensions:
  - name: Event Date
    expr: event_date
    comment: "Date of streaming event"
  - name: Event Month
    expr: "DATE_TRUNC('MONTH', event_date)"
    comment: "Month truncation for trend analysis"
  - name: Genre
    expr: content.genre
    comment: "Content genre from content dimension"
  - name: Content Type
    expr: content.content_type
  - name: Plan Type
    expr: subscriber.plan_type
    comment: "Subscription tier"
  - name: Country
    expr: subscriber.country
  - name: Quality
    expr: quality
    comment: "Stream quality SD/HD/4K/4K HDR"
measures:
  - name: View Count
    expr: "COUNT(1)"
    comment: "Total streaming sessions"
  - name: Unique Viewers
    expr: "COUNT(DISTINCT source.subscriber_id)"
    comment: "Distinct subscribers who streamed"
  - name: Avg Watch Minutes
    expr: "AVG(stream_duration_sec / 60.0)"
    comment: "Average watch time in minutes"
  - name: Completion Rate
    expr: "SUM(CASE WHEN completed THEN 1 ELSE 0 END) * 1.0 / COUNT(1)"
    comment: "Fraction of sessions completed (0 to 1)"
  - name: Avg Buffering
    expr: "AVG(buffering_events)"
    comment: "Average buffering events per session"
$$;
