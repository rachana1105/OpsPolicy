-- Compliance views over the OpsPolicy gold tables.

CREATE OR REPLACE VIEW opspolicy.gold.approval_sla_summary AS
SELECT approver_role, COUNT(*) AS tasks,
       ROUND(AVG(approval_hours), 2) AS avg_hours,
       SUM(CASE WHEN breached THEN 1 ELSE 0 END) AS breached
FROM opspolicy.silver.approval_events
GROUP BY approver_role;

CREATE OR REPLACE VIEW opspolicy.gold.revocation_failure_summary AS
SELECT DATE(started_at) AS day, COUNT(*) AS attempts,
       SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failures
FROM opspolicy.silver.revocation_results
GROUP BY DATE(started_at);
