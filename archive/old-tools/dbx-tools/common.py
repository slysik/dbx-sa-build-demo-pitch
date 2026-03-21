from typing import List, Optional
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

def get_spark(app_name: str = "dbx_tools") -> SparkSession:
    return SparkSession.builder.appName(app_name).getOrCreate()

def get_df(spark: SparkSession, table: str) -> DataFrame:
    return spark.table(table)

def parse_keys(keys: str) -> Optional[List[str]]:
    vals = [k.strip() for k in (keys or "").split(",") if k.strip()]
    return vals or None

def show_df(df: DataFrame, n: int = 20, truncate: bool = False) -> None:
    df.show(n, truncate=truncate)

def print_header(title: str) -> None:
    print("=" * 100)
    print(title)
    print("=" * 100)

def partition_stats_df(df: DataFrame) -> DataFrame:
    def count_partition(index, iterator):
        yield (index, sum(1 for _ in iterator))
    return df.rdd.mapPartitionsWithIndex(count_partition).toDF(["partition_id", "row_count"])

def null_profile_df(df: DataFrame) -> DataFrame:
    exprs = [F.sum(F.when(F.col(c).isNull(), 1).otherwise(0)).alias(c) for c in df.columns]
    return df.agg(*exprs)
