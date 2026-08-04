# Databricks notebook source
# MAGIC %md
# MAGIC # 00 — Setup catalog, schemas and Delta tables
# MAGIC Creates the OpsPolicy catalog and the bronze / silver / gold / simulation
# MAGIC schemas, plus the Bronze landing tables with lineage columns. Idempotent:
# MAGIC safe to re-run.

# COMMAND ----------

CATALOG = "opspolicy"
SCHEMAS = ["bronze", "silver", "gold", "simulation"]

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
for schema in SCHEMAS:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze tables
# MAGIC Preserve source records with lineage columns: `source_export_id`,
# MAGIC `source_updated_at`, `ingested_at`, `raw_payload`.

# COMMAND ----------

BRONZE_TABLES = [
    "requests",
    "policy_evaluations",
    "approval_events",
    "exceptions",
    "access_grants",
    "revocation_attempts",
    "audit_events",
]

for table in BRONZE_TABLES:
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {CATALOG}.bronze.{table} (
            source_export_id   STRING,
            source_updated_at  TIMESTAMP,
            ingested_at        TIMESTAMP,
            raw_payload        STRING
        ) USING DELTA
        """
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold summary tables (schema-on-write handled by build notebook)
# MAGIC Gold tables are (re)created by `02_build_compliance_metrics`. Simulation
# MAGIC results land in `simulation.results` via `03_run_policy_simulation`.

# COMMAND ----------

spark.sql(
    f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.simulation.results (
        simulation_id                     STRING,
        records_analysed                  BIGINT,
        requests_affected                 BIGINT,
        previously_approved_now_rejected  BIGINT,
        duration_reductions_required      BIGINT,
        recommendation                    STRING,
        generated_at                      TIMESTAMP,
        detail_json                       STRING
    ) USING DELTA
    """
)

print("Setup complete:", CATALOG, "→", ", ".join(SCHEMAS))
