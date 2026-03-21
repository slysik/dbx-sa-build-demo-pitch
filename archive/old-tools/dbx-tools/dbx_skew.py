import argparse
from pyspark.sql import functions as F
from common import get_spark, get_df, parse_keys, print_header, partition_stats_df, show_df

parser = argparse.ArgumentParser()
parser.add_argument("--table", required=True)
parser.add_argument("--keys", default="")
parser.add_argument("--top-n", type=int, default=20)
args = parser.parse_args()

spark = get_spark("dbx_skew")
df = get_df(spark, args.table)
keys = parse_keys(args.keys)

print_header(f"SKEW: {args.table}")

print("[1] Partition row distribution")
part_df = partition_stats_df(df).orderBy(F.desc("row_count"))
show_df(part_df, n=1000)
print("\n[2] Partition summary")
show_df(part_df.agg(
    F.count("*").alias("partition_count"),
    F.sum("row_count").alias("total_rows"),
    F.min("row_count").alias("min_rows"),
    F.max("row_count").alias("max_rows"),
    F.avg("row_count").alias("avg_rows"),
    F.stddev("row_count").alias("stddev_rows"),
).withColumn("max_to_avg_ratio", F.col("max_rows") / F.col("avg_rows")), 1)

if keys:
    print("\n[3] Key skew")
    for key in keys:
        print(f"--- {key} ---")
        key_df = df.groupBy(key).count().orderBy(F.desc("count"))
        show_df(key_df, n=args.top_n, truncate=False)
        show_df(key_df.agg(
            F.count("*").alias("distinct_keys"),
            F.min("count").alias("min_key_count"),
            F.max("count").alias("max_key_count"),
            F.avg("count").alias("avg_key_count"),
            F.stddev("count").alias("stddev_key_count"),
        ).withColumn("max_to_avg_key_ratio", F.col("max_key_count") / F.col("avg_key_count")), 1)
