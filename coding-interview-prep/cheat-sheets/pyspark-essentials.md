# PySpark Essentials Cheat Sheet

> You prefer SQL — and that's fine! Most transforms should be SQL.
> PySpark is mainly needed for: (1) creating DataFrames from Python data, (2) reading/writing files, (3) UDFs if needed.

## Creating DataFrames

### From Python list of dicts (most common in interview)
```python
# After generating data with Faker, convert to Spark DataFrame
data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
df = spark.createDataFrame(data)
# Spark infers schema from the dict keys and value types
```

### With explicit schema (more robust)
```python
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType, BooleanType, DateType

schema = StructType([
    StructField("transaction_id", StringType(), False),    # False = not nullable
    StructField("customer_id", StringType(), False),
    StructField("amount", DoubleType(), True),
    StructField("is_fraud", BooleanType(), True),
])

df = spark.createDataFrame(data, schema=schema)
```

## Writing to Delta Tables
```python
# Save as managed Delta table (most common in interview)
df.write.format("delta").mode("overwrite").saveAsTable("my_catalog.my_schema.my_table")

# Mode options:
#   "overwrite"  — replace entire table
#   "append"     — add rows to existing table
#   "ignore"     — skip if table exists
#   "error"      — fail if table exists (default)
```

## Reading Delta Tables
```python
# Read a Delta table into DataFrame
df = spark.table("my_catalog.my_schema.my_table")

# Or with SQL (you'll prefer this!)
df = spark.sql("SELECT * FROM my_catalog.my_schema.my_table")
```

## Quick DataFrame Operations (when SQL isn't available)
```python
# Show data
df.show(10)                          # First 10 rows
df.display()                         # Databricks rich display (use this!)
df.printSchema()                     # Show column names and types
df.count()                           # Row count

# Basic transforms (but prefer SQL!)
df.select("col1", "col2")           # Select columns
df.filter(df.amount > 100)          # Filter rows
df.groupBy("category").count()      # Group and count
df.orderBy("amount", ascending=False)  # Sort
```

## Register DataFrame as Temp View → Use SQL
```python
# THIS IS YOUR BEST FRIEND — create DataFrame in Python, transform in SQL
df.createOrReplaceTempView("raw_transactions")

# Now use SQL for everything else!
result = spark.sql("""
    SELECT 
        customer_id,
        COUNT(*) as txn_count,
        SUM(amount) as total_spend,
        AVG(amount) as avg_spend
    FROM raw_transactions
    GROUP BY customer_id
    ORDER BY total_spend DESC
""")
result.display()
```

## Common Schema Types Reference
```
StringType()      → strings, varchar
IntegerType()     → int (32-bit)
LongType()        → bigint (64-bit)
DoubleType()      → float/decimal
BooleanType()     → true/false
DateType()        → date only
TimestampType()   → date + time
DecimalType(p,s)  → precise decimal (use for money!)
ArrayType(T)      → array of type T
MapType(K,V)      → key-value map
```

## File I/O (if needed)
```python
# Read CSV
df = spark.read.csv("/path/to/file.csv", header=True, inferSchema=True)

# Read JSON
df = spark.read.json("/path/to/file.json")

# Read Parquet
df = spark.read.parquet("/path/to/file.parquet")

# Write to Volume (Databricks storage)
df.write.format("csv").save("/Volumes/catalog/schema/volume/output/")
```

## The Pattern You'll Use Most in the Interview

```python
# STEP 1: Generate data in Python (Faker)
data = generate_my_data(1000)

# STEP 2: Create Spark DataFrame
df = spark.createDataFrame(data)

# STEP 3: Save as Delta table
df.write.format("delta").mode("overwrite").saveAsTable("transactions_raw")

# STEP 4: Switch to SQL for ALL transforms!
# (Use %sql magic in notebook cells or spark.sql())
```
