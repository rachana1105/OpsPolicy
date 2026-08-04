-- Queries backing the OpsPolicy compliance dashboard.
SELECT total_requests, approved, rejected,
       ROUND(approved / total_requests, 3) AS approval_rate
FROM opspolicy.gold.compliance_summary;

SELECT requester_id, requests, high_risk, avg_score
FROM opspolicy.gold.department_risk_summary
ORDER BY high_risk DESC LIMIT 10;
