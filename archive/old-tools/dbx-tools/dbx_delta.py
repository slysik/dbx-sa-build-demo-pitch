import argparse
from common import get_spark, print_header

parser = argparse.ArgumentParser()
parser.add_argument("--table", required=True)
args = parser.parse_args()

spark = get_spark("dbx_delta")
print_header(f"DELTA DETAIL: {args.table}")
spark.sql(f"DESCRIBE DETAIL {args.table}").show(truncate=False)
print("\nDELTA HISTORY")
spark.sql(f"DESCRIBE HISTORY {args.table}").show(truncate=False)
