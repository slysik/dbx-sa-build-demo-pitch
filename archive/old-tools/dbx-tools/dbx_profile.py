import argparse
from pyspark.sql import functions as F
from common import get_spark, get_df, parse_keys, print_header, partition_stats_df, null_profile_df, show_df

parser = argparse.ArgumentParser()
parser.add_argument("--table", required=True)
parser.add_argument("--keys", default="")
parser.add_argument("--top-n", type=int, default=20)
args = parser.parse_args()

spark = get_spark("dbx_profile")
df = get_df(spark, args.table)
keys = parse_keys(args.keys)

print_header(f"PROFILE: {args.table}")
print("[1] Schema")
df.printSchema()

print("\n[2] Counts")
print("rows:", df.count())
print("partitions:", df.rdd.getNumPartitions())

print("\n[3] Partition stats")
part_df = partition_stats_df(df).orderBy("partition_id")
show_df(part_df, n=1000)
show_df(part_df.agg(
    F.count("*").alias("partition_count"),
    F.min("row_count").alias("min_rows"),
    F.max("row_count").alias("max_rows"),
    F.avg("row_count").alias("avg_rows"),
    F.stddev("row_count").alias("stddev_rows"),
).withColumn("max_to_avg_ratio", F.col("max_rows") / F.col("avg_rows")), 1)

print("\n[4] Null profile")
show_df(null_profile_df(df), 1, truncate=False)

if keys:
    print("\n[5] Key profiles")
    for key in keys:
        print(f"--- {key} ---")
        show_df(df.groupBy(key).count().orderBy(F.desc("count")), n=args.top_n, truncate=False)

print("\n[6] Execution plan")
df.explain(mode="formatted")
