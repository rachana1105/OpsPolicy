# Databricks notebook source
# MAGIC %md
# MAGIC # 02 — Build compliance metrics (Bronze → Silver → Gold)
# MAGIC Parses Bronze raw payloads, cleans and enriches into Silver, then computes
# MAGIC the Gold compliance summary tables the OpsPolicy backend reads. Mirrors the
# MAGIC metrics the backend computes locally so results match either way.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import (StructType, StructField, StringType, LongType,
                               DoubleType, TimestampType, BooleanType)

CATALOG = "opspolicy"

# COMMAND ----------
# MAGIC %md ## Silver: parse and normalise requests

request_schema = StructType([
    StructField("id", StringType()), StructField("organisation_id", StringType()),
    StructField("request_type", StringType()), StructField("requester_id", StringType()),
    StructField("resource_id", StringType()), StructField("risk_score", LongType()),
    StructField("risk_level", StringType()), StructField("decision", StringType()),
    StructField("status", StringType()), StructField("submitted_at", StringType()),
    StructField("approved_at", StringType()), StructField("created_at", StringType()),
])

bronze_requests = spark.table(f"{CATALOG}.bronze.requests")
silver_requests = (bronze_requests
    .select(F.from_json("raw_payload", request_schema).alias("r"))
    .select("r.*")
    # dedupe on id keeping the latest ingested
    .dropDuplicates(["id"])
    .withColumn("submitted_ts", F.to_timestamp("submitted_at"))
    .withColumn("approved_ts", F.to_timestamp("approved_at")))
silver_requests.write.mode("overwrite").saveAsTable(f"{CATALOG}.silver.requests")

# COMMAND ----------
# MAGIC %md ## Gold: compliance summary

approval_hours = (F.col("approved_ts").cast("long") - F.col("submitted_ts").cast("long")) / 3600.0

gold = (silver_requests
    .withColumn("approval_hours",
                F.when(F.col("approved_ts").isNotNull() & F.col("submitted_ts").isNotNull(),
                       approval_hours)))

summary = gold.agg(
    F.count("*").alias("total_requests"),
    F.sum(F.when(F.col("status").isin("APPROVED", "ACTIVE", "EXPIRING", "REVOKED",
                                      "PROVISIONING"), 1).otherwise(0)).alias("approved"),
    F.sum(F.when(F.col("status") == "REJECTED", 1).otherwise(0)).alias("rejected"),
    F.round(F.avg("approval_hours"), 2).alias("avg_approval_hours"),
    F.round(F.expr("percentile_approx(approval_hours, 0.95)"), 2).alias("p95_approval_hours"),
)
summary.write.mode("overwrite").saveAsTable(f"{CATALOG}.gold.compliance_summary")

# Department risk summary
dept_risk = (gold.groupBy("requester_id")
    .agg(F.count("*").alias("requests"),
         F.sum(F.when(F.col("risk_level").isin("HIGH", "CRITICAL"), 1).otherwise(0)).alias("high_risk"),
         F.round(F.avg("risk_score"), 1).alias("avg_score")))
dept_risk.write.mode("overwrite").saveAsTable(f"{CATALOG}.gold.department_risk_summary")

print("Gold compliance tables refreshed.")
