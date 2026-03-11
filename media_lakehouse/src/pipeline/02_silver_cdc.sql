-- Silver: Materialize latest state from Bronze CDC feed
-- APPLY CHANGES resolves INSERT/UPDATE/DELETE by event_id,
-- sequenced by _commit_timestamp (SCD Type 1 — latest state only)

CREATE OR REFRESH STREAMING TABLE silver_stream_events
CLUSTER BY (event_ts);

CREATE FLOW silver_cdc_flow AS
AUTO CDC INTO silver_stream_events
FROM stream(interview.media.bronze_stream_events)
KEYS (event_id)
APPLY AS DELETE WHEN _change_type = 'DELETE'
SEQUENCE BY _commit_timestamp
COLUMNS * EXCEPT (_change_type, _commit_timestamp, ingest_ts, source_system, batch_id)
STORED AS SCD TYPE 1;
