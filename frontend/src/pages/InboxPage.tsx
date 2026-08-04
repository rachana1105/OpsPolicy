import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { RiskBadge } from "../components/Badges";
import type { InboxItem } from "../types";

function opId() {
  return `op-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function dueLabel(due: string | null): { text: string; overdue: boolean } {
  if (!due) return { text: "No deadline", overdue: false };
  const d = new Date(due).getTime();
  const now = Date.now();
  const overdue = d < now;
  const hours = Math.abs(d - now) / 36e5;
  const rel =
    hours < 1
      ? `${Math.round(hours * 60)}m`
      : hours < 48
        ? `${Math.round(hours)}h`
        : `${Math.round(hours / 24)}d`;
  return { text: overdue ? `${rel} overdue` : `Due in ${rel}`, overdue };
}

export function InboxPage() {
  const qc = useQueryClient();
  const [activeTask, setActiveTask] = useState<InboxItem | null>(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");

  const { data: items = [], isLoading } = useQuery({
    queryKey: ["inbox"],
    queryFn: () => api.get<InboxItem[]>("/approvals/inbox"),
  });

  const decide = useMutation({
    mutationFn: (vars: { taskId: string; decision: string; version: number }) =>
      api.post(`/approvals/${vars.taskId}/decision`, {
        operation_id: opId(),
        decision: vars.decision,
        comment: comment || null,
        expected_version: vars.version,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["inbox"] });
      setActiveTask(null);
      setComment("");
      setError("");
    },
    onError: (e) =>
      setError(e instanceof ApiError ? e.message : "Decision failed."),
  });

  return (
    <div>
      <h1 className="font-display text-3xl text-ink mb-1">Approval inbox</h1>
      <p className="text-muted mb-6">
        Requests waiting on your decision, most urgent first.
      </p>

      {isLoading ? (
        <div className="card p-10 text-center text-muted">Loading…</div>
      ) : items.length === 0 ? (
        <div className="card p-10 grid place-items-center text-center">
          <div className="h-14 w-14 rounded-2xl bg-secondary-soft grid place-items-center mb-4">
            <span className="font-display text-2xl text-secondary">✓</span>
          </div>
          <div className="font-display text-xl text-ink mb-1">
            Inbox zero
          </div>
          <p className="text-sm text-muted max-w-sm">
            Nothing needs your approval right now.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const due = dueLabel(item.due_at);
            const isActive = activeTask?.task_id === item.task_id;
            return (
              <div key={item.task_id} className="card p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <Link
                      to={`/requests/${item.request_id}`}
                      className="font-semibold text-ink hover:text-primary-deep"
                    >
                      {item.request_title}
                    </Link>
                    <div className="flex flex-wrap items-center gap-2 mt-2">
                      <span className="chip bg-primary-soft text-primary-deep">
                        {item.approver_role?.replace(/_/g, " ").toLowerCase()}
                      </span>
                      <span className="chip bg-line text-muted">
                        stage {item.stage_number}
                      </span>
                      {item.risk_level && <RiskBadge level={item.risk_level} />}
                      <span
                        className={`chip ${
                          due.overdue
                            ? "bg-danger-soft text-danger"
                            : "bg-line text-muted"
                        }`}
                      >
                        {due.text}
                      </span>
                    </div>
                  </div>
                  <button
                    className="btn-outline shrink-0"
                    onClick={() =>
                      setActiveTask(isActive ? null : item)
                    }
                  >
                    {isActive ? "Close" : "Review"}
                  </button>
                </div>

                {isActive && (
                  <div className="mt-4 pt-4 border-t border-line animate-fade-up">
                    <label className="label">Comment (optional)</label>
                    <textarea
                      className="input min-h-[70px] mb-3"
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      placeholder="Add context for your decision…"
                    />
                    {error && (
                      <div className="rounded-xl bg-danger-soft text-danger text-sm px-3.5 py-2.5 mb-3">
                        {error}
                      </div>
                    )}
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="btn-primary bg-success hover:bg-success"
                        disabled={decide.isPending}
                        onClick={() =>
                          decide.mutate({
                            taskId: item.task_id,
                            decision: "APPROVE",
                            version: item.lock_version,
                          })
                        }
                      >
                        Approve
                      </button>
                      <button
                        className="btn-outline text-danger border-danger/30 hover:border-danger"
                        disabled={decide.isPending}
                        onClick={() =>
                          decide.mutate({
                            taskId: item.task_id,
                            decision: "REJECT",
                            version: item.lock_version,
                          })
                        }
                      >
                        Reject
                      </button>
                      <button
                        className="btn-ghost"
                        disabled={decide.isPending}
                        onClick={() =>
                          decide.mutate({
                            taskId: item.task_id,
                            decision: "REQUEST_CHANGES",
                            version: item.lock_version,
                          })
                        }
                      >
                        Request changes
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
