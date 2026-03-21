import argparse
from common import get_spark, get_df, print_header, null_profile_df, show_df

parser = argparse.ArgumentParser()
parser.add_argument("--table", required=True)
args = parser.parse_args()

spark = get_spark("dbx_nulls")
df = get_df(spark, args.table)
print_header(f"NULLS: {args.table}")
show_df(null_profile_df(df), 1, truncate=False)
