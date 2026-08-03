import type { TimelineEvent, Workflow } from "../types";

const EVENT_LABELS: Record<string, string> = {
  REQUEST_CREATED: "Request created",
  REQUEST_SUBMITTED: "Submitted",
  POLICY_EVALUATED: "Policies evaluated",
  RISK_CALCULATED: "Risk scored",
  WORKFLOW_CREATED: "Approval workflow created",
  REQUEST_APPROVED: "Approved",
  REQUEST_REJECTED: "Rejected",
  REQUEST_CANCELLED: "Cancelled",
  APPROVAL_ASSIGNED: "Approval assigned",
  APPROVAL_GRANTED: "Approval granted",
};

const TASK_TONE: Record<string, string> = {
  PENDING: "bg-line text-muted",
  APPROVED: "bg-success-soft text-success",
  REJECTED: "bg-danger-soft text-danger",
  CHANGES_REQUESTED: "bg-warning-soft text-warning",
  DELEGATED: "bg-info-soft text-info",
};

export function WorkflowView({ workflow }: { workflow: Workflow }) {
  return (
    <div className="space-y-4">
      {workflow.stages.map((stage) => (
        <div
          key={stage.id}
          className={`rounded-xl border p-4 ${
            stage.status === "IN_PROGRESS"
              ? "border-primary/40 bg-primary-soft/30"
              : "border-line"
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-full bg-primary text-white grid place-items-center text-xs font-semibold">
                {stage.stage_number}
              </div>
              <span className="text-sm font-semibold text-ink">
                Stage {stage.stage_number}
              </span>
              <span className="chip bg-line text-muted">
                {stage.execution_mode.toLowerCase()}
              </span>
              <span className="text-xs text-muted">
                min {stage.minimum_approvals} approval
                {stage.minimum_approvals > 1 ? "s" : ""}
              </span>
            </div>
            <span className="chip bg-line text-muted">{stage.status}</span>
          </div>
          <div className="space-y-2">
            {stage.tasks.map((task) => (
              <div
                key={task.id}
                className="flex items-center justify-between rounded-lg bg-card border border-line px-3 py-2"
              >
                <span className="text-sm text-ink capitalize">
                  {task.approver_role?.replace(/_/g, " ").toLowerCase() ??
                    "Unassigned"}
                </span>
                <span
                  className={`chip ${TASK_TONE[task.status] ?? "bg-line text-muted"}`}
                >
                  {task.status.replace(/_/g, " ")}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function TimelineView({ events }: { events: TimelineEvent[] }) {
  return (
    <ol className="relative border-l border-line ml-3 space-y-5">
      {events.map((e) => (
        <li key={e.id} className="ml-5">
          <div className="absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full bg-primary border-2 border-card" />
          <div className="text-sm font-medium text-ink">
            {EVENT_LABELS[e.event_type] ?? e.event_type.replace(/_/g, " ")}
          </div>
          <div className="text-xs text-muted mt-0.5">
            {new Date(e.created_at).toLocaleString()}
          </div>
          {Object.keys(e.payload).length > 0 && (
            <pre className="mt-1.5 text-[11px] text-muted bg-canvas rounded-lg p-2 overflow-x-auto font-mono">
              {JSON.stringify(e.payload, null, 2)}
            </pre>
          )}
        </li>
      ))}
    </ol>
  );
}
