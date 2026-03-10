import argparse
from common import get_spark, get_df, parse_keys, print_header

parser = argparse.ArgumentParser()
parser.add_argument("--left", required=True)
parser.add_argument("--right", required=True)
parser.add_argument("--keys", default="")
args = parser.parse_args()

spark = get_spark("dbx_compare")
left = get_df(spark, args.left)
right = get_df(spark, args.right)
keys = parse_keys(args.keys)

print_header(f"COMPARE: {args.left} vs {args.right}")
print("left_rows :", left.count())
print("right_rows:", right.count())
print("left_columns :", left.columns)
print("right_columns:", right.columns)

if keys:
    print("compare keys:", keys)
    ldup = left.groupBy(*keys).count().filter("count > 1").count()
    rdup = right.groupBy(*keys).count().filter("count > 1").count()
    print("left_duplicate_key_groups :", ldup)
    print("right_duplicate_key_groups:", rdup)
