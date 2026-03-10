import argparse
from pyspark.sql import functions as F
from common import get_spark, get_df, parse_keys, print_header, show_df

parser = argparse.ArgumentParser()
parser.add_argument("--table", required=True)
parser.add_argument("--keys", required=True)
parser.add_argument("--top-n", type=int, default=20)
args = parser.parse_args()

spark = get_spark("dbx_keys")
df = get_df(spark, args.table)
keys = parse_keys(args.keys) or []

print_header(f"KEYS: {args.table}")
for key in keys:
    print(f"--- {key} ---")
    prof = df.groupBy(key).count().orderBy(F.desc("count"))
    show_df(prof, n=args.top_n, truncate=False)
    show_df(prof.agg(
        F.count("*").alias("distinct_keys"),
        F.min("count").alias("min_key_count"),
        F.max("count").alias("max_key_count"),
        F.avg("count").alias("avg_key_count"),
    ), 1)
