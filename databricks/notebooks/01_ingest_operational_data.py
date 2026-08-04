# Databricks notebook source
# MAGIC %md
# MAGIC # 01 — Ingest operational data into Bronze
# MAGIC Reads the newline-delimited JSON exports (written by the backend
# MAGIC ExportService into a Unity Catalog Volume) and appends them to the Bronze
# MAGIC Delta tables with lineage columns. Idempotent per export_id.

# COMMAND ----------

from pyspark.sql import functions as F

CATALOG = "opspolicy"
# Volume path where the backend export lands. Adjust to your Volume.
EXPORT_VOLUME = "/Volumes/opspolicy/bronze/exports"

# COMMAND ----------

import json

# Discover the latest export via its manifest.
manifests = dbutils.fs.ls(EXPORT_VOLUME)
latest = sorted([m.path for m in manifests if m.name.rstrip("/")], reverse=True)[0]
manifest = json.loads(dbutils.fs.head(f"{latest}manifest.json"))
export_id = manifest["export_id"]
print("Ingesting export:", export_id)

# COMMAND ----------

TABLES = ["requests", "policy_evaluations", "approval_events", "exceptions",
          "access_grants", "revocation_attempts", "audit_events"]

for table in TABLES:
    info = manifest["tables"].get(table)
    if not info or info["row_count"] == 0:
        continue
    path = f"{latest}{info['file']}"
    raw = spark.read.text(path)  # each line is a JSON object
    enriched = (raw
                .withColumn("source_export_id", F.lit(export_id))
                .withColumn("source_updated_at", F.current_timestamp())
                .withColumn("ingested_at", F.current_timestamp())
                .withColumnRenamed("value", "raw_payload"))
    (enriched.select("source_export_id", "source_updated_at", "ingested_at", "raw_payload")
        .write.mode("append").saveAsTable(f"{CATALOG}.bronze.{table}"))
    print(f"  {table}: appended {info['row_count']} rows")

print("Bronze ingestion complete for", export_id)
