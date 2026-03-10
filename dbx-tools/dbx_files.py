import argparse
from common import get_spark, print_header

parser = argparse.ArgumentParser()
parser.add_argument("--table", required=True)
args = parser.parse_args()

spark = get_spark("dbx_files")
print_header(f"FILES: {args.table}")
detail = spark.sql(f"DESCRIBE DETAIL {args.table}")
detail.show(truncate=False)
cols = [c for c in detail.columns if c in ("location", "numFiles", "sizeInBytes", "partitionColumns")]
if cols:
    detail.select(*cols).show(truncate=False)
