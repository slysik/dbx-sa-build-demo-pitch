# AI Functions, http_request, remote_query, read_files

## Table of Contents

- [AI Functions Overview](#ai-functions-overview)
- [ai_query (General Purpose)](#ai_query)
- [Convenience AI Functions](#convenience-ai-functions)
- [ai_forecast and ai_embed](#ai_forecast-and-ai_embed)
- [http_request](#http_request)
- [remote_query (Lakehouse Federation)](#remote_query)
- [read_files](#read_files)
- [Cost and Performance Tips](#cost-and-performance)

---

## AI Functions Overview

**Requires:** Serverless or Pro SQL warehouse. All AI functions call Databricks Model Serving endpoints.

| Function | Purpose | Input | Output |
|----------|---------|-------|--------|
| `ai_query` | General-purpose LLM call | prompt + model | STRING or structured type |
| `ai_classify` | Classify text into categories | text + labels array | STRING |
| `ai_extract` | Extract entities from text | text + labels array | STRUCT |
| `ai_fix_grammar` | Fix grammar/spelling | text | STRING |
| `ai_gen` | Generate text from prompt | prompt | STRING |
| `ai_mask` | Mask PII in text | text + labels array | STRING |
| `ai_similarity` | Semantic similarity score | text1, text2 | DOUBLE (0-1) |
| `ai_summarize` | Summarize text | text | STRING |
| `ai_translate` | Translate text | text + target language | STRING |
| `ai_analyze_sentiment` | Sentiment analysis | text | STRING |
| `ai_forecast` | Time-series forecasting | group, order, value cols | TABLE |
| `ai_embed` | Generate embeddings | text + model | ARRAY\<FLOAT\> |

---

## ai_query

The most flexible AI function. Calls any Databricks Model Serving endpoint.

### Syntax

```sql
ai_query(
  model,                    -- STRING: endpoint name or foundation model
  prompt,                   -- STRING: the input text/prompt
  returnType => type,       -- Optional: return type (default STRING)
  modelParameters => params -- Optional: named_struct of model params
)
```

### Foundation Models (no endpoint setup needed)

```sql
-- Simple text generation
SELECT ai_query(
  'databricks-meta-llama-3-3-70b-instruct',
  'Explain Delta Lake in one sentence.'
) AS response;

-- With structured output
SELECT ai_query(
  'databricks-meta-llama-3-3-70b-instruct',
  concat('Classify this review as positive/negative/neutral. Review: ', review_text),
  returnType => 'STRUCT<sentiment STRING, confidence DOUBLE>'
) AS analysis
FROM catalog.schema.reviews
LIMIT 100;
```

### Available Foundation Models

| Model | Best For |
|-------|----------|
| `databricks-meta-llama-3-3-70b-instruct` | General text, classification, extraction |
| `databricks-meta-llama-3-1-405b-instruct` | Complex reasoning, long context |
| `databricks-claude-sonnet-4` | High-quality analysis, coding |
| `databricks-mixtral-8x7b-instruct` | Fast, cost-effective |
| `databricks-dbrx-instruct` | Databricks-optimized |
| `databricks-gte-large-en` | Embeddings |
| `databricks-bge-large-en` | Embeddings |

### Model Parameters

```sql
SELECT ai_query(
  'databricks-meta-llama-3-3-70b-instruct',
  prompt_text,
  modelParameters => named_struct(
    'temperature', CAST(0.0 AS DOUBLE),
    'max_tokens', CAST(500 AS INT),
    'top_p', CAST(0.9 AS DOUBLE)
  )
) AS response
FROM catalog.schema.prompts;
```

### Return Types

| returnType | Example |
|-----------|---------|
| `'STRING'` | Default, raw text response |
| `'STRUCT<k1 T1, k2 T2>'` | Parsed JSON into struct |
| `'ARRAY<STRING>'` | List of strings |
| `'STRUCT<label STRING, score DOUBLE>'` | Classification with confidence |
| `'STRUCT<topic STRING, sentiment STRING, action_items ARRAY<STRING>>'` | Complex nested |

### Custom Model Serving Endpoints

```sql
-- Call your own fine-tuned or external model
SELECT ai_query(
  'my-custom-endpoint',           -- endpoint name from Model Serving
  named_struct('text', review),   -- input matching endpoint schema
  returnType => 'STRUCT<label STRING, score DOUBLE>'
) FROM catalog.schema.reviews;
```

---

## Convenience AI Functions

These wrap `ai_query` with simpler interfaces for common tasks.

### ai_classify

```sql
SELECT
  ticket_id,
  description,
  ai_classify(description, ARRAY('billing', 'technical', 'account', 'feature_request')) AS category
FROM catalog.schema.support_tickets
LIMIT 100;
```

### ai_extract

```sql
-- Returns STRUCT with one field per label
SELECT
  doc_id,
  ai_extract(content, ARRAY('person_name', 'company', 'dollar_amount')) AS entities
FROM catalog.schema.contracts;
-- Access: entities.person_name, entities.company, entities.dollar_amount
```

### ai_analyze_sentiment

```sql
SELECT text, ai_analyze_sentiment(text) AS sentiment  -- returns 'positive'/'negative'/'neutral'/'mixed'
FROM catalog.schema.feedback;
```

### ai_summarize

```sql
SELECT doc_id, ai_summarize(long_text) AS summary  -- ~2-3 sentence summary
FROM catalog.schema.documents;
```

### ai_translate

```sql
SELECT text, ai_translate(text, 'fr') AS french_text  -- ISO 639-1 language codes
FROM catalog.schema.messages;
```

### ai_fix_grammar

```sql
SELECT ai_fix_grammar('their going too the store tommorow') AS fixed;
-- "They're going to the store tomorrow"
```

### ai_gen

```sql
SELECT ai_gen('Write a product description for a wireless mouse under $30') AS copy;
```

### ai_mask

```sql
-- Mask PII categories
SELECT ai_mask(text, ARRAY('phone', 'email', 'ssn', 'address')) AS masked_text
FROM catalog.schema.customer_notes;
```

### ai_similarity

```sql
-- Semantic similarity score (0 = unrelated, 1 = identical meaning)
SELECT ai_similarity('fast car', 'quick automobile') AS score;  -- ~0.85+
```

---

## ai_forecast and ai_embed

### ai_forecast

Time-series forecasting directly in SQL.

```sql
-- Forecast next 30 days of sales per store
SELECT * FROM ai_forecast(
  TABLE(catalog.schema.daily_sales),         -- input table
  horizon => 30,                              -- periods to forecast
  time_col => 'sale_date',                    -- timestamp/date column
  value_col => 'revenue',                     -- numeric column to forecast
  group_col => 'store_id',                    -- optional: forecast per group
  parameters => named_struct(
    'frequency', 'D',                         -- D=daily, W=weekly, M=monthly
    'prediction_interval_width', 0.95         -- confidence interval
  )
);
```

**Output columns:** `time_col`, `group_col`, `forecast`, `forecast_lower`, `forecast_upper`

### ai_embed

```sql
-- Generate embeddings for vector search
SELECT
  doc_id,
  ai_embed('databricks-gte-large-en', text_content) AS embedding  -- ARRAY<FLOAT>
FROM catalog.schema.documents;

-- Use with Vector Search index
INSERT INTO catalog.schema.doc_embeddings
SELECT doc_id, text_content, ai_embed('databricks-bge-large-en', text_content) AS embedding
FROM catalog.schema.documents;
```

---

## http_request

Call external HTTP APIs from SQL. **Requires:** Serverless or Pro warehouse + UC connection.

### Connection Setup (one-time)

```sql
-- Bearer token auth
CREATE CONNECTION my_api TYPE HTTP
OPTIONS (
  host 'https://api.example.com',
  bearer_token secret('my_scope', 'my_token')
);

-- Basic auth
CREATE CONNECTION my_api_basic TYPE HTTP
OPTIONS (
  host 'https://api.example.com',
  http_header ('Authorization' = concat('Basic ', base64('user:pass')))
);

-- API key in header
CREATE CONNECTION my_api_key TYPE HTTP
OPTIONS (
  host 'https://api.example.com',
  http_header ('X-API-Key' = secret('scope', 'key'))
);
```

### Usage

```sql
-- GET request
SELECT http_request(
  conn => 'my_api',
  method => 'GET',
  path => '/v1/users/123'
).text AS response_body;

-- POST with JSON body
SELECT
  order_id,
  http_request(
    conn => 'my_api',
    method => 'POST',
    path => '/v1/validate',
    json => to_json(named_struct('order_id', order_id, 'amount', amount))
  ):text AS validation_result
FROM catalog.schema.orders
WHERE needs_validation = true;
```

### Response Structure

`http_request()` returns a STRUCT:

| Field | Type | Description |
|-------|------|-------------|
| `status_code` | INT | HTTP status code (200, 404, etc.) |
| `text` | STRING | Response body as text |
| `headers` | MAP\<STRING,STRING\> | Response headers |

```sql
-- Parse JSON response
SELECT
  http_request(conn => 'my_api', method => 'GET', path => '/data'):text::STRUCT<name STRING, value DOUBLE>
AS parsed;

-- Error handling
SELECT
  CASE
    WHEN resp.status_code = 200 THEN from_json(resp.text, 'STRUCT<result STRING>')
    ELSE named_struct('result', concat('ERROR: ', resp.status_code))
  END AS result
FROM (
  SELECT http_request(conn => 'my_api', method => 'GET', path => '/check') AS resp
);
```

---

## remote_query

Query external databases via Lakehouse Federation. **Requires:** UC connection to external source.

### Connection Setup

```sql
-- PostgreSQL
CREATE CONNECTION my_postgres TYPE POSTGRESQL
OPTIONS (
  host 'pg-server.example.com',
  port '5432',
  user secret('scope', 'pg_user'),
  password secret('scope', 'pg_pass')
);

-- MySQL
CREATE CONNECTION my_mysql TYPE MYSQL
OPTIONS (host 'mysql.example.com', port '3306', user 'reader', password secret('s', 'k'));

-- SQL Server
CREATE CONNECTION my_sqlserver TYPE SQLSERVER
OPTIONS (host 'sqlserver.example.com', port '1433', user 'reader', password secret('s', 'k'));

-- Snowflake
CREATE CONNECTION my_snowflake TYPE SNOWFLAKE
OPTIONS (sfUrl 'https://acct.snowflakecomputing.com', user 'reader', password secret('s', 'k'));
```

**Supported sources:** PostgreSQL, MySQL, SQL Server, Snowflake, Oracle, Google BigQuery, Amazon Redshift, Teradata, Salesforce, Workday, ServiceNow, SAP HANA.

### Usage

```sql
-- Direct query (pushdown to remote)
SELECT * FROM remote_query(
  'my_postgres',
  database => 'my_db',
  query => 'SELECT customer_id, email FROM customers WHERE active = true'
);

-- Join remote data with local Delta tables
SELECT o.order_id, o.amount, c.email
FROM catalog.schema.orders o
JOIN remote_query(
  'my_postgres',
  database => 'my_db',
  query => 'SELECT customer_id, email FROM customers'
) c ON o.customer_id = c.customer_id;
```

### Foreign Catalog (alternative to remote_query)

```sql
-- Register external database as UC catalog
CREATE FOREIGN CATALOG pg_catalog USING CONNECTION my_postgres
OPTIONS (database 'my_db');

-- Query like any UC table
SELECT * FROM pg_catalog.public.customers WHERE active = true;
```

---

## read_files

Read raw files from Volumes, cloud storage, or external locations.

### Syntax

```sql
SELECT * FROM read_files(
  path,                                -- STRING: file/directory path
  format => 'json',                    -- file format
  [option => value, ...]               -- format-specific options
);
```

### Supported Formats

| Format | Key Options |
|--------|------------|
| `json` | `multiLine`, `schemaHints`, `allowComments` |
| `csv` | `header`, `delimiter`, `quote`, `escape`, `dateFormat`, `timestampFormat` |
| `parquet` | `mergeSchema` |
| `avro` | (standard options) |
| `text` | `wholetext` (read entire file as one row) |
| `binaryFile` | Returns `path`, `length`, `modificationTime`, `content` (BINARY) |
| `xml` | `rowTag` |
| `orc` | (standard options) |

### Common Options (all formats)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `format` | STRING | auto-detect | File format |
| `schema` | STRING | inferred | Explicit schema (`'col1 INT, col2 STRING'`) |
| `schemaHints` | STRING | none | Partial schema hints (merged with inference) |
| `pathGlobFilter` | STRING | none | Glob pattern (`'*.json'`, `'2024-*.csv'`) |
| `recursiveFileLookup` | BOOLEAN | false | Search subdirectories |
| `modifiedBefore` | TIMESTAMP | none | Only files modified before |
| `modifiedAfter` | TIMESTAMP | none | Only files modified after |
| `maxFilesPerTrigger` | INT | none | Limit files (streaming) |

### Examples

```sql
-- JSON from Volume
SELECT * FROM read_files(
  '/Volumes/catalog/schema/raw/events/',
  format => 'json',
  schemaHints => 'event_id STRING, ts TIMESTAMP, payload MAP<STRING, STRING>',
  pathGlobFilter => '*.json',
  recursiveFileLookup => true
);

-- CSV with custom delimiter and schema
SELECT * FROM read_files(
  '/Volumes/catalog/schema/raw/sales/',
  format => 'csv',
  header => true,
  delimiter => '|',
  dateFormat => 'yyyy-MM-dd',
  schema => 'sale_id INT, sale_date DATE, amount DECIMAL(10,2), store STRING'
);

-- Parquet with schema merge
SELECT * FROM read_files(
  '/Volumes/catalog/schema/raw/logs/',
  format => 'parquet',
  mergeSchema => true
);

-- Binary files (images, PDFs)
SELECT path, length, modificationTime
FROM read_files(
  '/Volumes/catalog/schema/raw/images/',
  format => 'binaryFile',
  pathGlobFilter => '*.png'
);

-- Text files (each file = one row)
SELECT path, value AS content
FROM read_files(
  '/Volumes/catalog/schema/raw/docs/',
  format => 'text',
  wholetext => true,
  pathGlobFilter => '*.md'
);

-- CTAS pattern: ingest into Delta
CREATE TABLE catalog.schema.events AS
SELECT * FROM read_files(
  '/Volumes/catalog/schema/raw/events/',
  format => 'json',
  schemaHints => 'event_id STRING, ts TIMESTAMP'
);
```

### Auto Loader (Streaming Alternative)

For production ingestion, use Auto Loader instead of `read_files`:
```sql
CREATE OR REFRESH STREAMING TABLE catalog.schema.events
AS SELECT * FROM STREAM read_files('/Volumes/catalog/schema/raw/events/', format => 'json');
```

---

## Cost and Performance

| Tip | Detail |
|-----|--------|
| **Always use LIMIT during dev** | AI functions cost per row; `LIMIT 10` while testing |
| **Batch with MVs** | Create MV with AI function + schedule for batch processing |
| **Cache with tables** | `INSERT INTO enriched SELECT ai_query(...) FROM raw` -- process once |
| **returnType struct** | Parse once in ai_query vs post-processing JSON strings |
| **http_request rate limits** | External APIs may throttle; test with small batches first |
| **read_files schema** | Always provide `schema` or `schemaHints` for predictable types |
| **remote_query pushdown** | Keep filters in the remote query string for performance |
| **Foundation models** | No provisioned endpoint needed; pay-per-token on serverless |
