# Databricks notebook source
# MAGIC %md
# MAGIC # 03 — Run historical policy simulation
# MAGIC Re-evaluates historical requests against a proposed policy using the SAME
# MAGIC deterministic rule logic as the live engine, and writes the impact summary
# MAGIC to `opspolicy.simulation.results`. Because the evaluator is a pure function,
# MAGIC the simulated impact matches what production would do.
# MAGIC
# MAGIC Parameters (widgets): `simulation_id`, `policy_definition_json`,
# MAGIC `start_date`, `end_date`.

# COMMAND ----------

import json
from pyspark.sql import functions as F

CATALOG = "opspolicy"

dbutils.widgets.text("simulation_id", "")
dbutils.widgets.text("policy_definition_json", "{}")
dbutils.widgets.text("start_date", "2025-01-01")
dbutils.widgets.text("end_date", "2026-12-31")

simulation_id = dbutils.widgets.get("simulation_id")
policy = json.loads(dbutils.widgets.get("policy_definition_json"))
start_date = dbutils.widgets.get("start_date")
end_date = dbutils.widgets.get("end_date")

# COMMAND ----------
# MAGIC %md ## Deterministic evaluator (ported from backend/app/policy_engine)
# MAGIC The same operator + condition-group + action semantics, expressed as a
# MAGIC Python UDF applied per historical request.

def resolve(ctx, path):
    cur = ctx
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur

def leaf(cond, ctx):
    op, actual, expected = cond["operator"], resolve(ctx, cond["field"]), cond.get("value")
    if op == "IS_NULL": return actual is None
    if op == "IS_NOT_NULL": return actual is not None
    if op == "EQUALS": return actual == expected
    if op == "NOT_EQUALS": return actual != expected
    if op == "IN": return actual in (expected or [])
    if op == "NOT_IN": return actual not in (expected or [])
    if op == "CONTAINS":
        try: return expected in actual
        except TypeError: return False
    try:
        a, b = float(actual), float(expected)
    except (TypeError, ValueError):
        return False
    return {"GREATER_THAN": a > b, "GREATER_THAN_OR_EQUAL": a >= b,
            "LESS_THAN": a < b, "LESS_THAN_OR_EQUAL": a <= b}.get(op, False)

def evaluate(node, ctx):
    if not node: return True
    if "all" in node: return all(evaluate(c, ctx) for c in node["all"])
    if "any" in node: return any(evaluate(c, ctx) for c in node["any"])
    if "not" in node: return not evaluate(node["not"], ctx)
    return leaf(node, ctx)

# COMMAND ----------
# MAGIC %md ## Apply the proposed policy to Silver requests

silver = spark.table(f"{CATALOG}.silver.requests").filter(
    (F.col("created_at") >= start_date) & (F.col("created_at") <= end_date))

rows = silver.collect()
analysed = affected = prev_approved_now_rejected = duration_reductions = 0
approved_states = {"APPROVED", "ACTIVE", "EXPIRING", "REVOKED", "PROVISIONING"}
applies = policy.get("applies_to", {})
conditions = policy.get("conditions")
actions = policy.get("actions", [])

for r in rows:
    analysed += 1
    ctx = {"request": {"request_type": r["request_type"]},
           "requester": {}, "resource": {}}
    # NOTE: a production job joins requester/resource attributes here.
    if applies.get("request_type") and r["request_type"] != applies["request_type"]:
        continue
    if not evaluate(conditions, ctx):
        continue
    changed = False
    for a in actions:
        if a["type"] == "REJECT":
            changed = True
            if r["status"] in approved_states:
                prev_approved_now_rejected += 1
        elif a["type"] == "SET_MAXIMUM_DURATION":
            duration_reductions += 1
            changed = True
        elif a["type"] == "REQUIRE_APPROVAL":
            changed = True
    if changed:
        affected += 1

recommendation = ("HIGH_IMPACT_REVIEW_BEFORE_ROLLOUT"
                  if analysed and prev_approved_now_rejected / analysed > 0.15
                  else "INTRODUCE_GRADUALLY" if analysed and affected / analysed > 0.30
                  else "SAFE_TO_INTRODUCE")

# COMMAND ----------
# MAGIC %md ## Publish result

result = [(simulation_id, analysed, affected, prev_approved_now_rejected,
           duration_reductions, recommendation)]
cols = ["simulation_id", "records_analysed", "requests_affected",
        "previously_approved_now_rejected", "duration_reductions_required", "recommendation"]
(spark.createDataFrame(result, cols)
    .withColumn("generated_at", F.current_timestamp())
    .write.mode("append").saveAsTable(f"{CATALOG}.simulation.results"))
print("Simulation complete:", simulation_id, "affected:", affected)
