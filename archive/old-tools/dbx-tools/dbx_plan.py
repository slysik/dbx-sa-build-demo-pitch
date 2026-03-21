import argparse
from common import get_spark, get_df, print_header

parser = argparse.ArgumentParser()
parser.add_argument("--table", required=True)
args = parser.parse_args()

spark = get_spark("dbx_plan")
df = get_df(spark, args.table)
print_header(f"PLAN: {args.table}")
df.explain(mode="formatted")
