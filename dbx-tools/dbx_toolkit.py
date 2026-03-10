"""
dbx_toolkit — Interview-ready DataFrame analysis toolkit.

Usage in a Databricks notebook:
    %run ./dbx_toolkit          # if uploaded to same workspace folder
    # — OR —
    # paste this file into a cell

Then call against any DataFrame or table name:

    profile(df)
    profile("catalog.schema.table")
    skew(df, keys=["store_id", "region"])
    nulls(df)
    keys(df, keys=["order_id", "customer_id"], top_n=10)
    compare(bronze_df, silver_df, keys=["order_id"])
    delta("catalog.schema.table")
    plan(df)
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from typing import List, Optional, Union

# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _spark() -> SparkSession:
    return SparkSession.builder.getOrCreate()

def _resolve(source: Union[str, DataFrame]) -> tuple:
    """Returns (DataFrame, label)."""
    if isinstance(source, str):
        return _spark().table(source), source
    return source, "DataFrame"

def _header(title: str) -> None:
    print("=" * 100)
    print(f"\033[38;2;255;106;0m{title}\033[0m")
    print("=" * 100)

def _show(df: DataFrame, n: int = 20, truncate: bool = False) -> None:
    df.show(n, truncate=truncate)

def _partition_stats(df: DataFrame) -> DataFrame:
    def count_partition(index, iterator):
        yield (index, sum(1 for _ in iterator))
    return df.rdd.mapPartitionsWithIndex(count_partition).toDF(["partition_id", "row_count"])

def _null_counts(df: DataFrame) -> DataFrame:
    exprs = [F.sum(F.when(F.col(c).isNull(), 1).otherwise(0)).alias(c) for c in df.columns]
    return df.agg(*exprs)

def _partition_summary(part_df: DataFrame) -> DataFrame:
    return part_df.agg(
        F.count("*").alias("partition_count"),
        F.sum("row_count").alias("total_rows"),
        F.min("row_count").alias("min_rows"),
        F.max("row_count").alias("max_rows"),
        F.avg("row_count").alias("avg_rows"),
        F.stddev("row_count").alias("stddev_rows"),
    ).withColumn("max_to_avg_ratio", F.col("max_rows") / F.col("avg_rows"))

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def profile(source: Union[str, DataFrame], keys: Optional[List[str]] = None, top_n: int = 20) -> None:
    """Full profile: schema, counts, partitions, nulls, optional key distribution."""
    df, label = _resolve(source)
    _header(f"PROFILE: {label}")

    print("[1] Schema")
    df.printSchema()

    print("\n[2] Counts")
    print("rows:", df.count())
    print("partitions:", df.rdd.getNumPartitions())

    print("\n[3] Partition stats")
    part_df = _partition_stats(df).orderBy("partition_id")
    _show(part_df, n=1000)
    _show(_partition_summary(part_df), 1)

    print("\n[4] Null profile")
    _show(_null_counts(df), 1, truncate=False)

    if keys:
        print("\n[5] Key profiles")
        for key in keys:
            print(f"--- {key} ---")
            _show(df.groupBy(key).count().orderBy(F.desc("count")), n=top_n, truncate=False)

    print("\n[6] Execution plan")
    df.explain(mode="formatted")


def skew(source: Union[str, DataFrame], keys: Optional[List[str]] = None, top_n: int = 20) -> None:
    """Partition skew + optional key skew analysis."""
    df, label = _resolve(source)
    _header(f"SKEW: {label}")

    print("[1] Partition row distribution")
    part_df = _partition_stats(df).orderBy(F.desc("row_count"))
    _show(part_df, n=1000)

    print("\n[2] Partition summary")
    _show(_partition_summary(part_df), 1)

    if keys:
        print("\n[3] Key skew")
        for key in keys:
            print(f"--- {key} ---")
            key_df = df.groupBy(key).count().orderBy(F.desc("count"))
            _show(key_df, n=top_n, truncate=False)
            _show(key_df.agg(
                F.count("*").alias("distinct_keys"),
                F.min("count").alias("min_key_count"),
                F.max("count").alias("max_key_count"),
                F.avg("count").alias("avg_key_count"),
                F.stddev("count").alias("stddev_key_count"),
            ).withColumn("max_to_avg_key_ratio", F.col("max_key_count") / F.col("avg_key_count")), 1)


def nulls(source: Union[str, DataFrame]) -> None:
    """Null counts per column."""
    df, label = _resolve(source)
    _header(f"NULLS: {label}")
    _show(_null_counts(df), 1, truncate=False)


def keys(source: Union[str, DataFrame], keys: List[str], top_n: int = 20) -> None:
    """Key distribution analysis — shows value counts and summary stats."""
    df, label = _resolve(source)
    _header(f"KEYS: {label}")
    for key in keys:
        print(f"--- {key} ---")
        prof = df.groupBy(key).count().orderBy(F.desc("count"))
        _show(prof, n=top_n, truncate=False)
        _show(prof.agg(
            F.count("*").alias("distinct_keys"),
            F.min("count").alias("min_key_count"),
            F.max("count").alias("max_key_count"),
            F.avg("count").alias("avg_key_count"),
        ), 1)


def compare(left: Union[str, DataFrame], right: Union[str, DataFrame],
            keys: Optional[List[str]] = None) -> None:
    """Compare two DataFrames/tables: row counts, columns, duplicate keys."""
    left_df, left_label = _resolve(left)
    right_df, right_label = _resolve(right)
    _header(f"COMPARE: {left_label} vs {right_label}")

    print("left_rows :", left_df.count())
    print("right_rows:", right_df.count())
    print("left_columns :", left_df.columns)
    print("right_columns:", right_df.columns)

    if keys:
        print("compare keys:", keys)
        ldup = left_df.groupBy(*keys).count().filter("count > 1").count()
        rdup = right_df.groupBy(*keys).count().filter("count > 1").count()
        print("left_duplicate_key_groups :", ldup)
        print("right_duplicate_key_groups:", rdup)


def delta(table: str) -> None:
    """DESCRIBE DETAIL + HISTORY for a Delta table (table name only)."""
    spark = _spark()
    _header(f"DELTA DETAIL: {table}")
    spark.sql(f"DESCRIBE DETAIL {table}").show(truncate=False)
    print("\nDELTA HISTORY")
    spark.sql(f"DESCRIBE HISTORY {table}").show(truncate=False)


def plan(source: Union[str, DataFrame]) -> None:
    """Show the formatted execution plan."""
    df, label = _resolve(source)
    _header(f"PLAN: {label}")
    df.explain(mode="formatted")
