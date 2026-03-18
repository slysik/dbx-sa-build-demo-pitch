orders_1m_df = (
    orders_df
    .crossJoin(spark.range(10).withColumnRenamed("id", "_multiplier"))
    .withColumn("order_id", F.concat(F.col("order_id"), F.lit("-"), F.col("_multiplier")))
    .withColumn("order_timestamp", F.col("order_timestamp") + F.expr("make_interval(0,0,0,0,_multiplier,0,0)"))
    .drop("_multiplier")
)

orders_1m_df.cache()
print(f"rows: {orders_1m_df.count():,}")
print(f"partitions: {orders_1m_df.rdd.getNumPartitions()}")
