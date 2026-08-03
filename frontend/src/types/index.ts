export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  employee_type: string;
  status: string;
  organisation_id: string;
  team_id: string | null;
  manager_id: string | null;
}

export interface Resource {
  id: string;
  name: string;
  resource_type: string;
  owner_user_id: string | null;
  criticality: string;
  sensitivity: string;
  region: string | null;
  is_active: boolean;
}

export interface Policy {
  id: string;
  name: string;
  description: string | null;
  policy_type: string;
  priority: number;
  status: string;
  version: number;
  owner_user_id: string | null;
}

export interface RequiredApproval {
  role: string;
  stage: number;
}

export interface RiskFactor {
  name: string;
  points: number;
}

export interface EvaluationResult {
  decision: string;
  matched_policies: string[];
  violations: string[];
  required_approvals: RequiredApproval[];
  maximum_allowed_duration_days: number | null;
  explanation: string[];
  conflicts: string[];
  risk_score: number;
  risk_level: string;
  risk_factors: RiskFactor[];
}

export type RequestType =
  | "DATASET_ACCESS"
  | "PRODUCTION_ACCESS"
  | "PURCHASE_APPROVAL";

export interface OpsRequest {
  id: string;
  request_type: string;
  requester_id: string;
  resource_id: string | null;
  title: string;
  business_justification: string | null;
  request_payload: Record<string, unknown>;
  risk_score: number;
  risk_level: string | null;
  decision: string | null;
  status: string;
  submitted_at: string | null;
  approved_at: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface TimelineEvent {
  id: string;
  event_type: string;
  entity_type: string;
  actor_id: string | null;
  previous_state: string | null;
  new_state: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface ApprovalTask {
  id: string;
  approver_user_id: string | null;
  approver_role: string | null;
  status: string;
  decision: string | null;
  comment: string | null;
  due_at: string | null;
  acted_at: string | null;
}

export interface ApprovalStage {
  id: string;
  stage_number: number;
  execution_mode: string;
  minimum_approvals: number;
  status: string;
  deadline_at: string | null;
  tasks: ApprovalTask[];
}

export interface PolicyException {
  id: string;
  request_id: string;
  policy_id: string | null;
  requested_by: string;
  justification: string;
  risk_description: string | null;
  compensating_controls: string | null;
  start_at: string;
  expires_at: string;
  status: string;
  approved_at: string | null;
  approved_by: string | null;
  revoked_at: string | null;
}

export interface ComplianceSummary {
  available: boolean;
  message?: string;
  data_freshness?: string | null;
  compliance_summary?: {
    total_requests: number;
    approved: number;
    rejected: number;
    approval_rate: number;
    rejection_rate: number;
    avg_approval_hours: number;
    p95_approval_hours: number;
    risk_distribution: Record<string, number>;
    requests_by_type: Record<string, number>;
  };
  approval_sla?: {
    total_tasks: number;
    breached: number;
    sla_compliance: number;
    avg_hours_by_role: Record<string, number>;
  };
  department_risk?: { by_team: Record<string, Record<string, number>> };
  revocation_failures?: {
    failed_revocations: number;
    escalated: number;
    total_attempts: number;
  };
  exception_trends?: { total: number; by_status: Record<string, number> };
}

export interface SimulationResult {
  simulation_id: string;
  records_analysed: number;
  requests_affected: number;
  previously_approved_now_rejected: number;
  duration_reductions_required: number;
  most_affected_departments: { team: string; affected_requests: number }[];
  risk_distribution: Record<string, number>;
  recommendation: string;
  generated_at: string;
}

export interface SimulationJob {
  id: string;
  status: string;
  job_type: string;
  input_reference: string | null;
  created_at: string | null;
  completed_at: string | null;
  result: SimulationResult | null;
}

export interface AuditEvent {
  id: string;
  request_id: string | null;
  actor_id: string | null;
  event_type: string;
  entity_type: string;
  entity_id: string | null;
  previous_state: string | null;
  new_state: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface Notification {
  id: string;
  notification_type: string;
  subject: string;
  body: string | null;
  status: string;
  attempts: number;
  created_at: string;
}

export interface AccessGrant {
  id: string;
  request_id: string;
  resource_id: string | null;
  user_id: string;
  grant_type: string;
  provisioning_status: string;
  revocation_status: string | null;
  granted_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  external_reference: string | null;
}

export interface RevocationAttempt {
  id: string;
  attempt_number: number;
  status: string;
  error_code: string | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  next_retry_at: string | null;
}

export interface InboxItem {
  task_id: string;
  request_id: string;
  request_title: string;
  request_type: string;
  risk_level: string | null;
  risk_score: number;
  approver_role: string | null;
  task_status: string;
  stage_number: number;
  due_at: string | null;
  requester_id: string;
  lock_version: number;
}

export interface Workflow {
  id: string;
  status: string;
  current_stage: number;
  stages: ApprovalStage[];
}
