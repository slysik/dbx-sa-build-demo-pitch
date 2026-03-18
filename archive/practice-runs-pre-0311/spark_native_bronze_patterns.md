# Spark-Native Bronze Data Generation Patterns

## Purpose

This guide defines the recommended Databricks architecture and coding patterns for generating a small synthetic dataset (for example, **100 rows**) and scaling the exact same pattern cleanly to **1M+ rows** using **PySpark**, then writing the result **directly to Bronze Delta tables**.

It is written for coding agents and engineers who need a clear, implementation-oriented standard that works across domains such as **retail, media, subscriptions, commerce, clickstream, IoT, or other fact-heavy datasets**.

---

## Core Architectural Principle

When the dataset is **born inside Spark** as synthetic or notebook-generated data, the optimal pattern is:

1. Generate all synthetic data **natively in PySpark DataFrames**
2. Keep all large-row generation **distributed**
3. Scale from small test volumes to 1M+ rows by changing parameters only
4. Write **directly to Bronze Delta**
5. After Bronze is established, implement **SDP / medallion transformations in SQL** for Silver and Gold
6. Apply **Databricks best practices** in Silver and Gold, including data quality controls, incremental patterns, and **Liquid Clustering** where justified

### Preferred flow

```text
PySpark DataFrame synthetic generation
    -> Bronze Delta tables in catalog.schema.bronze_*
    -> SQL-based Silver transformations in SDP / medallion layer
    -> SQL-based Gold aggregations / marts
```

### Avoid this anti-pattern

```text
Python loops / Faker / Pandas
    -> local list
    -> Pandas DataFrame
    -> Spark DataFrame
    -> parquet files / Volumes
    -> read back into Spark
    -> Delta Bronze
```

That anti-pattern may work for demos, but it does not scale cleanly and weakens the Databricks architecture story.

---

## What “optimal” means here

The target solution should:

- scale from **100 rows to 1M rows** by changing only parameters
- perform all synthetic dataset creation and scale-out using **PySpark DataFrames**
- avoid driver memory bottlenecks
- avoid Pandas for large fact generation
- avoid Python row-by-row loops for large datasets
- avoid unnecessary file landing layers when data is synthetic
- preserve a valid medallion pattern
- use **Bronze as Delta landing tables** generated from PySpark
- use **SQL for Silver and Gold** implementation in the SDP / medallion layers
- apply Databricks best practices for **Silver and Gold**, including Liquid Clustering where it improves layout and query performance
- be domain-agnostic enough for retail, media, telemetry, orders, subscriptions, or events
- produce Bronze tables that are immediately usable by downstream pipelines

---

## Design Rules

## Rule 1: Generate large datasets with `spark.range()`

Use `spark.range(n)` as the canonical distributed row generator.

Why:
- distributed row creation
- stable scaling shape
- simple parameterization
- no Python object explosion on the driver

### Good

```python
fact_df = spark.range(100)
```

```python
fact_df = spark.range(1_000_000)
```

### Bad

```python
rows = []
for i in range(1_000_000):
    rows.append({...})
```

---

## Rule 2: Keep fact generation in Spark, not Pandas

Large fact tables must be derived with Spark column expressions.

Use:
- `withColumn`
- `expr`
- `when`
- `rand`
- `sha2`
- `concat_ws`
- `date_add`
- `timestampadd`-style logic via expressions
- broadcast joins to tiny dimensions

Avoid:
- `pd.DataFrame(...)` for large facts
- `spark.createDataFrame(pandas_df)` for large facts
- row-by-row Python loops

---

## Rule 3: Write directly to Bronze Delta

If the source data is synthetic and generated in PySpark DataFrames, Bronze should be the **first durable storage layer**.

### Good

```python
fact_df.write.format("delta").mode("overwrite").saveAsTable("catalog.schema.bronze_orders")
```

### Bad

```python
fact_df.write.parquet(volume_path)
raw_df = spark.read.parquet(volume_path)
raw_df.write.format("delta").saveAsTable(...)
```

Only use a file landing layer if you explicitly need:
- raw file arrival simulation
- Auto Loader / `read_files()` demo
- file-level replay semantics
- file provenance testing

After Bronze is written, Silver and Gold should preferably be implemented in SQL using SDP / medallion patterns and Databricks-native table optimization features.

---

## Rule 4: Bronze should be source-shaped, not heavily transformed

Bronze tables should stay close to source shape.

For synthetic data, this means:
- realistic column names
- realistic types
- realistic event grain
- minimal derivation needed to make the data usable
- ingestion metadata added at write time

Do not over-model Bronze.

---

## Rule 5: Add ingestion metadata consistently

Each Bronze table should include a minimal standard set of metadata columns.

Recommended:
- `ingest_ts`
- `bronze_load_date`
- `source_system`
- `source_type`
- `batch_id`
- optional `generator_version`

Example:

```python
.withColumn("ingest_ts", F.current_timestamp()) \
.withColumn("bronze_load_date", F.current_date()) \
.withColumn("source_system", F.lit("synthetic_generator")) \
.withColumn("source_type", F.lit("spark_native")) \
.withColumn("batch_id", F.lit(batch_id))
```

---

## Rule 6: Use small dimensions and broadcast them

A common pattern is:
- generate a large fact table with `spark.range()`
- generate or load tiny dimensions
- broadcast join tiny dimensions onto the fact table

This works well for:
- product dimension
- customer segment
- plan type
- country / region
- content category
- device type
- store dimension

### Good

```python
fact_df.join(F.broadcast(dim_df), "product_id", "left")
```

---

## Rule 7: Parameterize row count and keep logic identical

The same code should support both small and large datasets.

Use a variable like:

```python
ROW_COUNT = 100
```

or

```python
ROW_COUNT = 1_000_000
```

All downstream logic should remain unchanged.

This is a core sign of a good synthetic data design.

---

## Rule 8: Minimize actions during generation

Avoid repeated full-table actions such as:
- multiple `count()` calls
- duplicate checks after every step
- repeated full scans for validation

Prefer:
- one validation count after final write
- `display(df.limit(10))` for inspection
- a small number of targeted aggregate checks

---

## Rule 9: Control write partitioning intentionally

At 1M rows, partitioning may still matter for write efficiency and file sizing.

General guidance:
- keep small datasets simple
- for larger facts, consider `repartition()` before write
- do not randomly repartition tiny dimension tables

Example:

```python
fact_df = fact_df.repartition(8)
```

The exact number should reflect:
- cluster size
- row width
- downstream workload
- desired file count

---

## Rule 10: Use deterministic generation where possible

Avoid excessive dependence on Faker for large-scale facts.

Prefer deterministic synthetic values using Spark functions:
- IDs from row number
- categories from modulo logic
- timestamps from row offsets
- emails from concatenation / hashing
- revenue / amount fields from bounded random values

Why:
- faster
- scalable
- reproducible
- easier to debug

---

## Domain-Neutral Data Model Pattern

The architecture should support multiple business domains by separating the model into:

1. **Small dimensions**
2. **Large fact table**
3. **Bronze Delta persistence**

### Examples by domain

#### Retail
- Dimensions: customer, product, store, channel
- Fact: order lines, transactions, cart events

#### Media / streaming
- Dimensions: subscriber, content, device, region
- Fact: stream events, watch sessions, ad impressions

#### SaaS / product analytics
- Dimensions: account, user, feature, plan
- Fact: product events, page views, API calls

#### IoT / telemetry
- Dimensions: device, site, sensor type
- Fact: readings, alerts, status events

The coding pattern stays the same.

---

## Reference Implementation Pattern

The implementation standard is:

- **Synthetic dataset creation:** PySpark DataFrame code only
- **Scaling from 100 to 1M+:** PySpark parameterization only
- **Bronze persistence:** direct Delta writes
- **Silver and Gold logic:** SQL in SDP / medallion layers
- **Optimization at Silver and Gold:** Databricks best practices including Liquid Clustering where justified

## 1. Parameters

```python
from pyspark.sql import functions as F

CATALOG = "main"
SCHEMA = "demo"
ROW_COUNT = 100  # change to 1_000_000 to scale
BATCH_ID = "run_001"
TARGET_TABLE = f"{CATALOG}.{SCHEMA}.bronze_fact_events"
```

---

## 2. Small dimensions

Small dimensions can be built with simple Spark-native logic.

### Example product/content dimension

```python
product_dim = (
    spark.range(10)
    .select(
        F.col("id").cast("int").alias("product_id"),
        F.concat(F.lit("P"), F.lpad(F.col("id").cast("string"), 3, "0")).alias("product_code"),
        F.when((F.col("id") % 4) == 0, "Premium")
         .when((F.col("id") % 4) == 1, "Standard")
         .when((F.col("id") % 4) == 2, "Basic")
         .otherwise("Trial").alias("product_tier"),
        F.when((F.col("id") % 3) == 0, "North")
         .when((F.col("id") % 3) == 1, "South")
         .otherwise("West").alias("region")
    )
)
```

### Example customer/subscriber dimension

```python
customer_dim = (
    spark.range(1_000)
    .select(
        F.col("id").cast("int").alias("customer_id"),
        F.concat(F.lit("C"), F.lpad(F.col("id").cast("string"), 6, "0")).alias("customer_code"),
        F.when((F.col("id") % 4) == 0, "Free")
         .when((F.col("id") % 4) == 1, "Basic")
         .when((F.col("id") % 4) == 2, "Standard")
         .otherwise("Premium").alias("plan_type")
    )
)
```

These dimensions are small enough to broadcast.

---

## 3. Large fact generation

The fact table should be generated from `spark.range(ROW_COUNT)` and then enriched with Spark-native columns.

### Generic fact pattern

```python
fact_df = (
    spark.range(ROW_COUNT)
    .withColumnRenamed("id", "event_seq")
    .withColumn("event_id", F.concat(F.lit("E"), F.lpad(F.col("event_seq").cast("string"), 12, "0")))
    .withColumn("customer_id", (F.col("event_seq") % F.lit(1000)).cast("int"))
    .withColumn("product_id", (F.col("event_seq") % F.lit(10)).cast("int"))
    .withColumn("quantity", (F.col("event_seq") % 5 + 1).cast("int"))
    .withColumn("unit_price", (F.round(F.rand(42) * 90 + 10, 2)))
    .withColumn("gross_amount", F.round(F.col("quantity") * F.col("unit_price"), 2))
    .withColumn(
        "event_type",
        F.when((F.col("event_seq") % 5) == 0, "purchase")
         .when((F.col("event_seq") % 5) == 1, "view")
         .when((F.col("event_seq") % 5) == 2, "add_to_cart")
         .when((F.col("event_seq") % 5) == 3, "refund")
         .otherwise("click")
    )
    .withColumn("event_date", F.expr("date_add(date'2025-01-01', cast(event_seq % 90 as int))"))
    .withColumn("event_ts", F.expr("timestampadd(SECOND, cast(event_seq * 17 as int), timestamp('2025-01-01 00:00:00'))"))
)
```

If `timestampadd` is not supported in your runtime, use epoch arithmetic:

```python
fact_df = fact_df.withColumn(
    "event_ts",
    (F.lit("2025-01-01 00:00:00").cast("timestamp").cast("long") + F.col("event_seq") * 17).cast("timestamp")
)
```

---

## 4. Broadcast joins to dimensions

```python
fact_enriched_df = (
    fact_df
    .join(F.broadcast(customer_dim), "customer_id", "left")
    .join(F.broadcast(product_dim), "product_id", "left")
)
```

This pattern works across retail, media, or telemetry facts.

---

## 5. Bronze metadata

```python
bronze_df = (
    fact_enriched_df
    .withColumn("source_system", F.lit("synthetic_generator"))
    .withColumn("source_type", F.lit("spark_native"))
    .withColumn("batch_id", F.lit(BATCH_ID))
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("bronze_load_date", F.current_date())
)
```

---

## 6. Direct write to Bronze Delta

```python
(
    bronze_df
    .repartition(8)
    .write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TARGET_TABLE)
)
```

---

## 7. Minimal validation

```python
written_df = spark.table(TARGET_TABLE)

print(f"rows: {written_df.count():,}")
display(written_df.limit(10))
```

Optional lightweight checks:

```python
written_df.groupBy("event_type").count().orderBy("event_type").show()
written_df.groupBy("event_date").count().orderBy("event_date").show(10)
```

---

## Small-to-Large Scaling Example

## Start with 100 rows

```python
ROW_COUNT = 100
```

Use this for:
- notebook development
- schema validation
- quick debugging
- visual inspection

## Scale to 1M rows

```python
ROW_COUNT = 1_000_000
```

No logic changes should be required.

This is a key quality bar. If the code requires an entirely different generation path for 1M rows, the original design is weak.

---

## Recommended Table Strategy

For a complete synthetic Bronze layer, write separate tables for dimensions and fact.

Examples:
- `catalog.schema.bronze_customers`
- `catalog.schema.bronze_products`
- `catalog.schema.bronze_fact_events`

### Dimensions

```python
customer_dim.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_customers")
product_dim.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_products")
```

### Fact

```python
bronze_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(TARGET_TABLE)
```

After Bronze tables are written, Silver and Gold should be created in SQL. This keeps responsibilities clear:

- **PySpark / DataFrame layer:** synthetic data generation and Bronze creation
- **SQL / SDP layer:** Silver cleansing, conformance, joins, and business logic
- **SQL / SDP layer:** Gold marts, aggregates, KPIs, and consumption-ready tables

This keeps the medallion model honest and easy to explain.

---

## Patterns That Do Not Scale Well

Avoid the following for large fact generation:

### 1. Python list accumulation

```python
rows = []
for i in range(1_000_000):
    rows.append(...)
```

Why it is bad:
- driver memory pressure
- slow Python loops
- no distributed generation

### 2. Pandas as intermediate for fact generation

```python
pdf = pd.DataFrame(rows)
df = spark.createDataFrame(pdf)
```

Why it is bad:
- materializes large data on the driver
- serialization overhead
- not Spark-native

### 3. Excessive Faker use for large datasets

Why it is bad:
- row-by-row generation
- slow throughput
- CPU-bound on driver

Use Faker only for tiny, optional dimension decoration.

### 4. Write parquet, then read, then write Delta

Why it is bad:
- double I/O
- unnecessary latency
- unnecessary storage lifecycle complexity

### 5. Repeated `count()` after every step

Why it is bad:
- multiple full scans
- slows development and scaling tests

### 6. Heavy duplicate checks on every load step

Why it is bad:
- expensive groupBy/shuffle
- weak default pattern for large notebooks

---

## Bronze Naming and Architecture Guidance

Be precise about what Bronze means.

If the data is synthetic, name it clearly if needed:
- `bronze_orders_synthetic`
- `bronze_stream_events_seed`
- `bronze_retail_transactions_simulated`

This is often more architecturally honest than pretending the data is raw external ingestion.

Still, the table should behave like Bronze by being:
- source-shaped
- minimally transformed
- metadata-enriched
- durable
- queryable

---

## Performance Guidance for 1M Rows

At roughly 1M rows, the following approach is generally strong:

- generate the fact with `spark.range(1_000_000)`
- broadcast dimensions under a few MBs
- write directly to Delta
- add a modest repartition before write if needed
- keep validations lightweight

For larger scale beyond 1M, consider:
- partition-aware write tuning
- file-size tuning
- clustering / layout optimization where justified
- more realistic skew simulation only if the use case requires it

Do not prematurely optimize the 100-row version with heavy layout logic.

---

## Implementation Checklist

A coding agent should satisfy all of the following:

- use `spark.range()` for the large fact row generator
- avoid Pandas for large facts
- avoid driver-side Python row loops for large facts
- generate dimensions as tiny Spark DataFrames
- broadcast join dimensions into the fact table
- add Bronze ingestion metadata
- write directly to `catalog.schema.bronze_*` as Delta
- parameterize row count so 100 and 1M use the same logic
- keep Bronze source-shaped and minimally transformed
- minimize full-table actions
- avoid redundant parquet / Volume landing steps unless specifically required

---

## Final Standard

For Databricks, the preferred synthetic Bronze generation pattern is:

```text
PySpark DataFrame generation
    -> Spark-native derived columns
    -> broadcast joins to tiny dimensions
    -> add Bronze metadata
    -> write directly to Delta Bronze tables
    -> SQL-based Silver transformations
    -> SQL-based Gold aggregates / marts
```

This is the most defensible pattern for an SA/architect review because it is:
- scalable
- simple
- Delta-native
- medallion-consistent
- domain-neutral
- easy for coding agents to implement correctly
- aligned to a clean separation of responsibilities between PySpark Bronze generation and SQL-based Silver/Gold implementation

---

## Canonical End-to-End Example

```python
from pyspark.sql import functions as F

CATALOG = "main"
SCHEMA = "demo"
ROW_COUNT = 1_000_000
BATCH_ID = "run_001"
TARGET_TABLE = f"{CATALOG}.{SCHEMA}.bronze_fact_events"

customer_dim = (
    spark.range(1_000)
    .select(
        F.col("id").cast("int").alias("customer_id"),
        F.concat(F.lit("C"), F.lpad(F.col("id").cast("string"), 6, "0")).alias("customer_code"),
        F.when((F.col("id") % 4) == 0, "Free")
         .when((F.col("id") % 4) == 1, "Basic")
         .when((F.col("id") % 4) == 2, "Standard")
         .otherwise("Premium").alias("plan_type")
    )
)

product_dim = (
    spark.range(10)
    .select(
        F.col("id").cast("int").alias("product_id"),
        F.concat(F.lit("P"), F.lpad(F.col("id").cast("string"), 3, "0")).alias("product_code"),
        F.when((F.col("id") % 4) == 0, "Premium")
         .when((F.col("id") % 4) == 1, "Standard")
         .when((F.col("id") % 4) == 2, "Basic")
         .otherwise("Trial").alias("product_tier"),
        F.when((F.col("id") % 3) == 0, "North")
         .when((F.col("id") % 3) == 1, "South")
         .otherwise("West").alias("region")
    )
)

fact_df = (
    spark.range(ROW_COUNT)
    .withColumnRenamed("id", "event_seq")
    .withColumn("event_id", F.concat(F.lit("E"), F.lpad(F.col("event_seq").cast("string"), 12, "0")))
    .withColumn("customer_id", (F.col("event_seq") % 1000).cast("int"))
    .withColumn("product_id", (F.col("event_seq") % 10).cast("int"))
    .withColumn("quantity", (F.col("event_seq") % 5 + 1).cast("int"))
    .withColumn("unit_price", F.round(F.rand(42) * 90 + 10, 2))
    .withColumn("gross_amount", F.round(F.col("quantity") * F.col("unit_price"), 2))
    .withColumn(
        "event_type",
        F.when((F.col("event_seq") % 5) == 0, "purchase")
         .when((F.col("event_seq") % 5) == 1, "view")
         .when((F.col("event_seq") % 5) == 2, "add_to_cart")
         .when((F.col("event_seq") % 5) == 3, "refund")
         .otherwise("click")
    )
    .withColumn("event_date", F.expr("date_add(date'2025-01-01', cast(event_seq % 90 as int))"))
    .withColumn("event_ts", (F.lit("2025-01-01 00:00:00").cast("timestamp").cast("long") + F.col("event_seq") * 17).cast("timestamp"))
)

bronze_df = (
    fact_df
    .join(F.broadcast(customer_dim), "customer_id", "left")
    .join(F.broadcast(product_dim), "product_id", "left")
    .withColumn("source_system", F.lit("synthetic_generator"))
    .withColumn("source_type", F.lit("spark_native"))
    .withColumn("batch_id", F.lit(BATCH_ID))
    .withColumn("ingest_ts", F.current_timestamp())
    .withColumn("bronze_load_date", F.current_date())
)

customer_dim.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_customers")
product_dim.write.format("delta").mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.bronze_products")

(
    bronze_df
    .repartition(8)
    .write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(TARGET_TABLE)
)

print(f"rows: {spark.table(TARGET_TABLE).count():,}")
```

This is the canonical Bronze implementation to prefer unless there is a specific requirement for raw file landing simulation.

## Silver and Gold Implementation Standard

After Bronze is created in PySpark, Silver and Gold should be implemented in SQL using SDP / medallion best practices.

### Silver goals
- enforce data quality rules
- standardize types and null handling
- deduplicate where required
- join and conform dimensions
- preserve business keys and auditability
- prepare clean, trusted analytical tables

### Gold goals
- create business-ready aggregates and marts
- optimize for BI, dashboards, and KPI consumption
- keep schemas intuitive for analysts and downstream tools

### Databricks best practices for Silver and Gold
- use SQL for transformation readability and maintainability
- apply incremental patterns where appropriate
- use expectations / quality controls where available in SDP
- cluster selectively based on real query patterns
- use **Liquid Clustering** for larger Silver and Gold tables where it improves pruning, maintenance, and layout flexibility
- avoid over-optimizing tiny dimensions or tiny Gold tables
- design Silver as the trusted conformed layer and Gold as the consumption layer

### Recommended architecture split

```text
PySpark DataFrames:
    synthetic generation
    Bronze Delta writes

SQL / SDP:
    Silver transformations
    Gold transformations
    Liquid Clustering and SQL-native optimization
```

That separation is the preferred architecture for synthetic enterprise demos because it gives the clearest and most scalable implementation model.

