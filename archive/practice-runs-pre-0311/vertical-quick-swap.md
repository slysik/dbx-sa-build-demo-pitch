# Vertical Quick-Swap Guide

> Swap entity names, measures, and domain terms in <30 seconds. Pick a vertical, paste the entity map into your pipeline.

---

## Retail

### Entity Map
| Role | Entity | Business Key | Common Columns |
|------|--------|-------------|----------------|
| Master | `customers` | `customer_id` | name, email, loyalty_tier, signup_date, region |
| Transaction | `orders` | `order_id` | customer_id, order_ts, store_id, total_amount, currency, status |
| Line Item | `order_lines` | `line_id` | order_id, product_id, quantity, unit_price, discount_pct |
| Reference | `products` | `product_id` | sku, upc, product_name, category, subcategory, brand |
| Event | `returns` | `return_id` | order_id, line_id, return_ts, reason_code, refund_amount |
| Reference | `stores` | `store_id` | store_name, city, state, region, format (big-box/express) |

### Measures
| Measure | Expression | Gold Column Type |
|---------|-----------|-----------------|
| Revenue | `SUM(total_amount)` | DECIMAL(38,2) |
| Units Sold | `SUM(quantity)` | BIGINT |
| Basket Size | `AVG(total_amount)` | DECIMAL(18,2) |
| Return Rate | `COUNT(returns) / COUNT(orders)` | DECIMAL(10,4) |
| Avg Discount | `AVG(discount_pct)` | DECIMAL(10,4) |

### Domain Terms
- SKU, UPC, loyalty_tier (Gold/Silver/Bronze/Basic), basket, POS, markdown, shrinkage

### PySpark Data Gen Snippet
```python
# TALK: Generating 100k retail orders with realistic distribution
# SCALING: spark.range() distributes row generation across executors
from pyspark.sql import functions as F
from pyspark.sql.types import StringType
import hashlib

N = 100_000
N_CUSTOMERS = 10_000
N_PRODUCTS = 5_000
N_STORES = 200

df = (spark.range(N)
    .withColumn("order_id", F.concat(F.lit("ORD-"), F.lpad(F.col("id").cast("string"), 10, "0")))
    .withColumn("customer_id", F.concat(F.lit("C"), F.lpad((F.abs(F.hash(F.col("id"), F.lit("cust"))) % N_CUSTOMERS).cast("string"), 6, "0")))
    .withColumn("store_id", F.concat(F.lit("S"), F.lpad((F.abs(F.hash(F.col("id"), F.lit("store"))) % N_STORES).cast("string"), 4, "0")))
    .withColumn("product_id", F.concat(F.lit("P"), F.lpad((F.abs(F.hash(F.col("id"), F.lit("prod"))) % N_PRODUCTS).cast("string"), 5, "0")))
    # DW-BRIDGE: hash-based assignment = deterministic like Netezza distribution keys
    .withColumn("order_ts", F.timestampadd("SECOND", -(F.abs(F.hash(F.col("id"), F.lit("ts"))) % (14 * 86400)).cast("int"), F.current_timestamp()))
    .withColumn("quantity", (F.abs(F.hash(F.col("id"), F.lit("qty"))) % 10 + 1).cast("int"))
    .withColumn("unit_price", F.round(F.abs(F.hash(F.col("id"), F.lit("price"))) % 50000 / 100.0 + 0.99, 2))
    .withColumn("total_amount", F.round(F.col("quantity") * F.col("unit_price"), 2).cast("decimal(18,2)"))
    .withColumn("currency", F.lit("USD"))
    .withColumn("status", F.element_at(F.array(F.lit("COMPLETED"), F.lit("PENDING"), F.lit("RETURNED")), (F.abs(F.hash(F.col("id"), F.lit("st"))) % 100).cast("int") + 1))
    # Fix status distribution: 85% completed, 10% pending, 5% returned
    .withColumn("status", F.when(F.abs(F.hash(F.col("id"), F.lit("st"))) % 100 < 85, "COMPLETED")
                           .when(F.abs(F.hash(F.col("id"), F.lit("st"))) % 100 < 95, "PENDING")
                           .otherwise("RETURNED"))
    .withColumn("loyalty_tier", F.when(F.abs(F.hash(F.col("id"), F.lit("tier"))) % 100 < 10, "Gold")
                                 .when(F.abs(F.hash(F.col("id"), F.lit("tier"))) % 100 < 35, "Silver")
                                 .when(F.abs(F.hash(F.col("id"), F.lit("tier"))) % 100 < 70, "Bronze")
                                 .otherwise("Basic"))
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("source_system", F.lit("synthetic_demo"))
    .drop("id")
)
# SCALING: At 1M rows, this completes in <30s — spark.range is embarrassingly parallel
```

### Gold Aggregation
```sql
-- Daily revenue by store and loyalty tier
SELECT
  CAST(order_ts AS DATE) AS order_date,
  store_id,
  loyalty_tier,
  COUNT(*) AS order_count,
  CAST(SUM(total_amount) AS DECIMAL(38,2)) AS total_revenue,
  CAST(AVG(total_amount) AS DECIMAL(18,2)) AS avg_basket
FROM {catalog}.silver.orders_current
WHERE CAST(order_ts AS DATE) >= date_sub(current_date(), 14)
GROUP BY CAST(order_ts AS DATE), store_id, loyalty_tier;
```

### Discovery Questions
1. "What's the business key for dedup -- order_id, or composite (order_id + line_id)?"
2. "Do returns arrive as separate events or updates to the original order?"
3. "What loyalty tiers exist and do they affect pricing or priority?"

---

## Media / Streaming

### Entity Map
| Role | Entity | Business Key | Common Columns |
|------|--------|-------------|----------------|
| Master | `users` | `user_id` | username, email, subscription_tier, signup_date, country |
| Event | `streams` | `stream_id` | user_id, content_id, start_ts, end_ts, device_type, quality |
| Reference | `content` | `content_id` | title, content_type (movie/series/live), genre, release_date, duration_min |
| Transaction | `subscriptions` | `subscription_id` | user_id, plan_id, start_date, end_date, mrr, status |

### Measures
| Measure | Expression | Gold Column Type |
|---------|-----------|-----------------|
| Watch Time (min) | `SUM(TIMESTAMPDIFF(MINUTE, start_ts, end_ts))` | BIGINT |
| Engagement Score | `AVG(watch_pct)` | DECIMAL(10,4) |
| Churn Flag | `CASE WHEN end_date < current_date() THEN 1 ELSE 0 END` | INT |
| MRR | `SUM(mrr)` | DECIMAL(38,2) |
| Completion Rate | `AVG(CASE WHEN watch_pct >= 0.9 THEN 1 ELSE 0 END)` | DECIMAL(10,4) |

### Domain Terms
- content_type (movie/series/live), genre, subscription_tier (Free/Basic/Premium), device_type, bitrate, buffering_events, watch_pct, churn

### PySpark Data Gen Snippet
```python
# TALK: Generating 100k streaming events with realistic watch patterns
# SCALING: spark.range() distributes — each executor handles a partition of IDs
from pyspark.sql import functions as F

N = 100_000
N_USERS = 15_000
N_CONTENT = 3_000

df = (spark.range(N)
    .withColumn("stream_id", F.concat(F.lit("STR-"), F.lpad(F.col("id").cast("string"), 10, "0")))
    .withColumn("user_id", F.concat(F.lit("U"), F.lpad((F.abs(F.hash(F.col("id"), F.lit("user"))) % N_USERS).cast("string"), 6, "0")))
    .withColumn("content_id", F.concat(F.lit("C"), F.lpad((F.abs(F.hash(F.col("id"), F.lit("content"))) % N_CONTENT).cast("string"), 5, "0")))
    .withColumn("start_ts", F.timestampadd("SECOND", -(F.abs(F.hash(F.col("id"), F.lit("ts"))) % (14 * 86400)).cast("int"), F.current_timestamp()))
    .withColumn("duration_min", (F.abs(F.hash(F.col("id"), F.lit("dur"))) % 180 + 5).cast("int"))
    .withColumn("watch_pct", F.round(F.abs(F.hash(F.col("id"), F.lit("wp"))) % 100 / 100.0, 2))
    .withColumn("end_ts", F.timestampadd("MINUTE", F.col("duration_min").cast("int"), F.col("start_ts")))
    .withColumn("device_type", F.when(F.abs(F.hash(F.col("id"), F.lit("dev"))) % 100 < 45, "mobile")
                                .when(F.abs(F.hash(F.col("id"), F.lit("dev"))) % 100 < 75, "smart_tv")
                                .when(F.abs(F.hash(F.col("id"), F.lit("dev"))) % 100 < 90, "desktop")
                                .otherwise("tablet"))
    .withColumn("content_type", F.when(F.abs(F.hash(F.col("id"), F.lit("ct"))) % 100 < 50, "series")
                                 .when(F.abs(F.hash(F.col("id"), F.lit("ct"))) % 100 < 85, "movie")
                                 .otherwise("live"))
    .withColumn("genre", F.element_at(
        F.array(*[F.lit(g) for g in ["drama","comedy","action","documentary","sci-fi","thriller"]]),
        (F.abs(F.hash(F.col("id"), F.lit("genre"))) % 6 + 1).cast("int")))
    .withColumn("subscription_tier", F.when(F.abs(F.hash(F.col("id"), F.lit("tier"))) % 100 < 20, "Free")
                                      .when(F.abs(F.hash(F.col("id"), F.lit("tier"))) % 100 < 60, "Basic")
                                      .otherwise("Premium"))
    .withColumn("quality", F.when(F.col("subscription_tier") == "Premium", "4K")
                            .when(F.col("subscription_tier") == "Basic", "HD")
                            .otherwise("SD"))
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("source_system", F.lit("synthetic_demo"))
    .drop("id")
)
# DW-BRIDGE: In Netezza, we'd distribute on user_id for co-located joins. Here CLUSTER BY does the same.
```

### Gold Aggregation
```sql
-- Daily engagement by content type and subscription tier
SELECT
  CAST(start_ts AS DATE) AS stream_date,
  content_type,
  subscription_tier,
  COUNT(*) AS stream_count,
  CAST(SUM(duration_min) AS BIGINT) AS total_watch_min,
  CAST(AVG(watch_pct) AS DECIMAL(10,4)) AS avg_engagement
FROM {catalog}.silver.streams_current
WHERE CAST(start_ts AS DATE) >= date_sub(current_date(), 14)
GROUP BY CAST(start_ts AS DATE), content_type, subscription_tier;
```

### Discovery Questions
1. "What's the business key -- stream_id, or composite (user_id + content_id + start_ts)?"
2. "Are we tracking engagement (watch_pct) or just view counts?"
3. "Churn definition -- no activity in 30 days, or subscription lapsed?"

---

## Generic (Fallback)

Use this when the vertical is unknown or doesn't match retail/media.

### Entity Map
| Role | Entity | Business Key | Common Columns |
|------|--------|-------------|----------------|
| Master | `entities` | `entity_id` | name, category, tier, region, created_date |
| Event | `events` | `event_id` | entity_id, event_ts, event_type, value, status |
| Reference | `attributes` | `attribute_id` | entity_id, attr_key, attr_value, effective_date |

### Measures
| Measure | Expression | Gold Column Type |
|---------|-----------|-----------------|
| Event Count | `COUNT(*)` | BIGINT |
| Total Value | `SUM(value)` | DECIMAL(38,2) |
| Avg Duration | `AVG(duration_sec)` | DECIMAL(18,2) |

### Domain Terms
- entity, event, attribute, tier, category, status (ACTIVE/PENDING/CLOSED)

### PySpark Data Gen Snippet
```python
# TALK: Generating 100k generic events — vertical-agnostic scaffold
# SCALING: spark.range is the distributed backbone — scales linearly with executors
from pyspark.sql import functions as F

N = 100_000
N_ENTITIES = 10_000

df = (spark.range(N)
    .withColumn("event_id", F.concat(F.lit("EVT-"), F.lpad(F.col("id").cast("string"), 10, "0")))
    .withColumn("entity_id", F.concat(F.lit("E"), F.lpad((F.abs(F.hash(F.col("id"), F.lit("ent"))) % N_ENTITIES).cast("string"), 6, "0")))
    .withColumn("event_ts", F.timestampadd("SECOND", -(F.abs(F.hash(F.col("id"), F.lit("ts"))) % (14 * 86400)).cast("int"), F.current_timestamp()))
    .withColumn("event_type", F.when(F.abs(F.hash(F.col("id"), F.lit("type"))) % 100 < 40, "CREATE")
                               .when(F.abs(F.hash(F.col("id"), F.lit("type"))) % 100 < 70, "UPDATE")
                               .when(F.abs(F.hash(F.col("id"), F.lit("type"))) % 100 < 90, "READ")
                               .otherwise("DELETE"))
    .withColumn("value", F.round(F.abs(F.hash(F.col("id"), F.lit("val"))) % 100000 / 100.0, 2).cast("decimal(18,2)"))
    .withColumn("status", F.when(F.abs(F.hash(F.col("id"), F.lit("st"))) % 100 < 70, "ACTIVE")
                           .when(F.abs(F.hash(F.col("id"), F.lit("st"))) % 100 < 90, "PENDING")
                           .otherwise("CLOSED"))
    .withColumn("category", F.element_at(
        F.array(*[F.lit(c) for c in ["A","B","C","D"]]),
        (F.abs(F.hash(F.col("id"), F.lit("cat"))) % 4 + 1).cast("int")))
    .withColumn("tier", F.when(F.abs(F.hash(F.col("id"), F.lit("tier"))) % 100 < 15, "Premium")
                         .when(F.abs(F.hash(F.col("id"), F.lit("tier"))) % 100 < 50, "Standard")
                         .otherwise("Basic"))
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("source_system", F.lit("synthetic_demo"))
    .drop("id")
)
```

### Gold Aggregation
```sql
-- Daily summary by category and status
SELECT
  CAST(event_ts AS DATE) AS event_date,
  category,
  status,
  COUNT(*) AS event_count,
  CAST(SUM(value) AS DECIMAL(38,2)) AS total_value,
  CAST(AVG(value) AS DECIMAL(18,2)) AS avg_value
FROM {catalog}.silver.events_current
WHERE CAST(event_ts AS DATE) >= date_sub(current_date(), 14)
GROUP BY CAST(event_ts AS DATE), category, status;
```

### Discovery Questions
1. "What's the natural business key for dedup?"
2. "What does 'correct' mean — latest-wins, or do we need history (SCD2)?"
3. "What are the main query patterns — date range? entity lookup? category drill-down?"

---

## How to Use This Guide

1. **Interviewer gives prompt** → identify which vertical it maps to
2. **Copy the entity map** → replace `{entity}` placeholders in your templates
3. **Copy the PySpark data gen snippet** → paste as your first code cell
4. **Copy the Gold aggregation** → paste into your Gold stage
5. **Use the discovery questions** → ask 2-3 before coding

If the prompt doesn't cleanly map to retail or media, use the **Generic** template and adapt entity names to match the scenario described.
