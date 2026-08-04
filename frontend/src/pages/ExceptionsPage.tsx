import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import type { PolicyException, User } from "../types";
import { useAuth } from "../hooks/useAuth";

const STATUS_TONE: Record<string, string> = {
  REQUESTED: "bg-info-soft text-info",
  UNDER_REVIEW: "bg-info-soft text-info",
  APPROVED: "bg-secondary-soft text-secondary",
  ACTIVE: "bg-success-soft text-success",
  REJECTED: "bg-danger-soft text-danger",
  EXPIRED: "bg-line text-muted",
  REVOKED: "bg-line text-muted",
};

function expiryLabel(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now();
  if (ms <= 0) return "Expired";
  const h = ms / 36e5;
  return h < 24 ? `${Math.round(h)}h left` : `${Math.round(h / 24)}d left`;
}

export function ExceptionsPage() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const [error, setError] = useState("");

  const { data: exceptions = [], isLoading } = useQuery({
    queryKey: ["exceptions"],
    queryFn: () => api.get<PolicyException[]>("/exceptions"),
  });
  const { data: users = [] } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.get<User[]>("/users"),
  });

  const act = useMutation({
    mutationFn: (v: { id: string; action: string }) =>
      api.post(`/exceptions/${v.id}/${v.action}`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["exceptions"] });
      setError("");
    },
    onError: (e) =>
      setError(e instanceof ApiError ? e.message : "Action failed."),
  });

  const canReview = user && user.role !== "EMPLOYEE";
  const userName = (id: string) =>
    users.find((u) => u.id === id)?.name ?? id.slice(0, 8);

  return (
    <div>
      <h1 className="font-display text-3xl text-ink mb-1">Exceptions</h1>
      <p className="text-muted mb-6">
        Temporary, justified overrides with compensating controls. Every
        exception has a hard expiry — nothing here is permanent.
      </p>

      {error && (
        <div className="rounded-xl bg-danger-soft text-danger text-sm px-3.5 py-2.5 mb-4">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="card p-10 text-center text-muted">Loading…</div>
      ) : exceptions.length === 0 ? (
        <div className="card p-10 grid place-items-center text-center">
          <div className="h-14 w-14 rounded-2xl bg-primary-soft grid place-items-center mb-4">
            <span className="font-display text-2xl text-primary-deep">§</span>
          </div>
          <div className="font-display text-xl text-ink mb-1">
            No exceptions
          </div>
          <p className="text-sm text-muted max-w-sm">
            Exceptions are requested from a specific request when policy would
            otherwise block it. They appear here for review.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {exceptions.map((exc) => (
            <div key={exc.id} className="card p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`chip ${STATUS_TONE[exc.status] ?? "bg-line text-muted"}`}>
                      {exc.status.replace(/_/g, " ")}
                    </span>
                    <span className="text-xs text-muted">
                      requested by {userName(exc.requested_by)}
                    </span>
                    {["ACTIVE", "APPROVED"].includes(exc.status) && (
                      <span className="chip bg-warning-soft text-warning">
                        {expiryLabel(exc.expires_at)}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-ink mt-2">{exc.justification}</p>
                  {exc.compensating_controls && (
                    <p className="text-xs text-muted mt-1">
                      <span className="font-semibold">Controls:</span>{" "}
                      {exc.compensating_controls}
                    </p>
                  )}
                  <Link
                    to={`/requests/${exc.request_id}`}
                    className="text-xs text-primary-deep hover:underline mt-1 inline-block"
                  >
                    View request →
                  </Link>
                </div>

                {canReview &&
                  ["REQUESTED", "UNDER_REVIEW"].includes(exc.status) && (
                    <div className="flex flex-col gap-2 shrink-0">
                      <button
                        className="btn-primary bg-success hover:bg-success py-1.5 px-3 text-xs"
                        disabled={act.isPending}
                        onClick={() =>
                          act.mutate({ id: exc.id, action: "approve" })
                        }
                      >
                        Approve
                      </button>
                      <button
                        className="btn-outline text-danger border-danger/30 py-1.5 px-3 text-xs"
                        disabled={act.isPending}
                        onClick={() =>
                          act.mutate({ id: exc.id, action: "reject" })
                        }
                      >
                        Reject
                      </button>
                    </div>
                  )}
                {canReview && ["ACTIVE", "APPROVED"].includes(exc.status) && (
                  <button
                    className="btn-ghost text-xs shrink-0"
                    disabled={act.isPending}
                    onClick={() => act.mutate({ id: exc.id, action: "revoke" })}
                  >
                    Revoke
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
