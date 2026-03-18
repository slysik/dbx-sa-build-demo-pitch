-- =============================================================================
-- BRONZE: Real-time Market Data Feed
-- Source : Azure Event Hub (Bloomberg B-PIPE / EMSX integration)
-- Pattern: Streaming table from Event Hub — near-real-time
-- =============================================================================

CREATE OR REFRESH STREAMING TABLE bronze_market_data
  COMMENT "Real-time market data from Bloomberg via Azure Event Hub. Used for Basel IV risk exposure calculations."
  TBLPROPERTIES (
    'quality'       = 'bronze',
    'source_system' = 'bloomberg',
    'delta.enableChangeDataFeed' = 'true'
  )
  CLUSTER BY (event_date, asset_class)
AS
SELECT
  -- Parse JSON payload from Event Hub message body
  get_json_object(CAST(body AS STRING), '$.instrument_id')  AS instrument_id,
  get_json_object(CAST(body AS STRING), '$.isin')           AS isin,
  get_json_object(CAST(body AS STRING), '$.asset_class')    AS asset_class,
  get_json_object(CAST(body AS STRING), '$.price')          AS price_raw,
  get_json_object(CAST(body AS STRING), '$.bid')            AS bid_raw,
  get_json_object(CAST(body AS STRING), '$.ask')            AS ask_raw,
  get_json_object(CAST(body AS STRING), '$.volume')         AS volume_raw,
  get_json_object(CAST(body AS STRING), '$.currency')       AS currency,
  get_json_object(CAST(body AS STRING), '$.market_ts')      AS market_ts_raw,
  -- Event Hub metadata
  enqueuedTime                                               AS enqueued_ts,
  offset                                                     AS eventhub_offset,
  sequenceNumber                                             AS eventhub_seq,
  -- Pipeline metadata
  current_timestamp()                                        AS _ingested_at,
  current_date()                                             AS event_date,
  'bloomberg'                                                AS source_system
FROM read_stream(
  format                        => 'eventhubs',
  eventhubs.connectionString    => '${eventhub_conn_str}',
  eventhubs.consumerGroup       => '${eventhub_consumer_group}',
  startingPosition              => 'latest'
);
