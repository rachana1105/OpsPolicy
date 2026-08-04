# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — Publish results
# MAGIC Exposes the Gold compliance tables and simulation results for the OpsPolicy
# MAGIC backend to read (via Databricks SQL / the results API). This notebook is the
# MAGIC final task in both the compliance-refresh and policy-simulation jobs.

# COMMAND ----------

CATALOG = "opspolicy"

# Compliance summary snapshot the backend polls.
spark.sql(f"""
    CREATE OR REPLACE VIEW {CATALOG}.gold.compliance_dashboard AS
    SELECT * FROM {CATALOG}.gold.compliance_summary
""")

# Latest simulation results, most recent first.
spark.sql(f"""
    CREATE OR REPLACE VIEW {CATALOG}.simulation.latest_results AS
    SELECT * FROM {CATALOG}.simulation.results
    ORDER BY generated_at DESC
""")

print("Published gold.compliance_dashboard and simulation.latest_results.")
print("The OpsPolicy backend reads these through its DatabricksAnalyticsProvider.")
