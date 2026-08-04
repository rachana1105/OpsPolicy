import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import {
  DecisionBadge,
  RiskBadge,
  StatusBadge,
} from "../components/Badges";
import {
  TimelineView,
  WorkflowView,
} from "../components/RequestDetailViews";
import type {
  AccessGrant,
  OpsRequest,
  PolicyException,
  RevocationAttempt,
  TimelineEvent,
  Workflow,
} from "../types";

const TABS = [
  "Summary",
  "Approval workflow",
  "Access lifecycle",
  "Audit timeline",
] as const;

export function RequestDetailPage() {
  const { requestId } = useParams();
  const [tab, setTab] = useState<(typeof TABS)[number]>("Summary");

  const { data: request } = useQuery({
    queryKey: ["request", requestId],
    queryFn: () => api.get<OpsRequest>(`/requests/${requestId}`),
    enabled: !!requestId,
  });
  const { data: workflow } = useQuery({
    queryKey: ["request-workflow", requestId],
    queryFn: () => api.get<Workflow | null>(`/requests/${requestId}/workflow`),
    enabled: !!requestId,
  });
  const { data: timeline = [] } = useQuery({
    queryKey: ["request-timeline", requestId],
    queryFn: () => api.get<TimelineEvent[]>(`/requests/${requestId}/timeline`),
    enabled: !!requestId,
  });
  const qc = useQueryClient();
  const [actionError, setActionError] = useState("");

  const { data: grants = [] } = useQuery({
    queryKey: ["request-grants", requestId],
    queryFn: () =>
      api.get<AccessGrant[]>(`/access-grants?mine=false`).then((all) =>
        all.filter((g) => g.request_id === requestId)
      ),
    enabled: !!requestId,
  });

  const provision = useMutation({
    mutationFn: () => api.post(`/requests/${requestId}/provision`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["request", requestId] });
      qc.invalidateQueries({ queryKey: ["request-grants", requestId] });
      qc.invalidateQueries({ queryKey: ["request-timeline", requestId] });
      setActionError("");
    },
    onError: (e) =>
      setActionError(e instanceof ApiError ? e.message : "Provisioning failed."),
  });

  const { data: exceptions = [] } = useQuery({
    queryKey: ["request-exceptions", requestId],
    queryFn: () =>
      api
        .get<PolicyException[]>("/exceptions")
        .then((all) => all.filter((e) => e.request_id === requestId)),
    enabled: !!requestId,
  });
  const [showExcForm, setShowExcForm] = useState(false);
  const [excJustification, setExcJustification] = useState("");
  const [excControls, setExcControls] = useState("");
  const [excDays, setExcDays] = useState(3);

  const requestException = useMutation({
    mutationFn: () => {
      const now = new Date();
      const expires = new Date(now.getTime() + excDays * 864e5);
      return api.post("/exceptions", {
        request_id: requestId,
        justification: excJustification,
        compensating_controls: excControls || null,
        start_at: now.toISOString(),
        expires_at: expires.toISOString(),
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["request-exceptions", requestId] });
      qc.invalidateQueries({ queryKey: ["request-timeline", requestId] });
      setShowExcForm(false);
      setExcJustification("");
      setExcControls("");
      setActionError("");
    },
    onError: (e) =>
      setActionError(e instanceof ApiError ? e.message : "Could not request exception."),
  });

  if (!request)
    return <div className="card p-10 text-center text-muted">Loading…</div>;

  const payload = request.request_payload;

  return (
    <div>
      <Link to="/requests" className="text-sm text-muted hover:text-primary-deep">
        ← My requests
      </Link>
      <div className="flex items-start justify-between mt-2 mb-6">
        <div>
          <h1 className="font-display text-3xl text-ink">{request.title}</h1>
          <div className="flex items-center gap-2 mt-2">
            <StatusBadge status={request.status} />
            {request.decision && <DecisionBadge decision={request.decision} />}
            {request.risk_level && <RiskBadge level={request.risk_level} />}
            <span className="text-sm text-muted">
              {request.request_type.replace(/_/g, " ").toLowerCase()}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-line mb-6">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t
                ? "border-primary text-primary-deep"
                : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Summary" && (
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="card p-6 lg:col-span-2">
            <h2 className="font-display text-lg text-ink mb-4">Details</h2>
            <dl className="space-y-3 text-sm">
              {request.business_justification && (
                <div>
                  <dt className="text-muted">Business justification</dt>
                  <dd className="text-ink mt-0.5">
                    {request.business_justification}
                  </dd>
                </div>
              )}
              {Object.entries(payload).map(([k, v]) => (
                <div key={k} className="flex justify-between border-b border-line pb-2">
                  <dt className="text-muted capitalize">
                    {k.replace(/_/g, " ")}
                  </dt>
                  <dd className="text-ink font-medium">{String(v)}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="card p-6">
            <h2 className="font-display text-lg text-ink mb-4">Risk</h2>
            <div className="font-display text-4xl text-primary-deep">
              {request.risk_score}
            </div>
            <div className="mt-1">
              {request.risk_level && <RiskBadge level={request.risk_level} />}
            </div>
          </div>

          <div className="card p-6 lg:col-span-3">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-display text-lg text-ink">Policy exceptions</h2>
              {["REJECTED", "CHANGES_REQUESTED", "UNDER_REVIEW", "ACTIVE"].includes(
                request.status
              ) && (
                <button
                  className="btn-outline text-xs py-1.5 px-3"
                  onClick={() => setShowExcForm((s) => !s)}
                >
                  {showExcForm ? "Cancel" : "Request exception"}
                </button>
              )}
            </div>

            {showExcForm && (
              <div className="rounded-xl border border-line p-4 mb-4 animate-fade-up">
                <label className="label">Justification</label>
                <textarea
                  className="input min-h-[60px] mb-3"
                  value={excJustification}
                  onChange={(e) => setExcJustification(e.target.value)}
                  placeholder="Why is this override needed?"
                />
                <label className="label">Compensating controls</label>
                <input
                  className="input mb-3"
                  value={excControls}
                  onChange={(e) => setExcControls(e.target.value)}
                  placeholder="e.g. read-only, MFA enforced, time-boxed"
                />
                <label className="label">Duration (days)</label>
                <input
                  type="number"
                  className="input mb-3 max-w-[120px]"
                  value={excDays}
                  onChange={(e) => setExcDays(Number(e.target.value))}
                />
                <div>
                  <button
                    className="btn-primary"
                    disabled={!excJustification || requestException.isPending}
                    onClick={() => requestException.mutate()}
                  >
                    {requestException.isPending ? "Submitting…" : "Submit exception request"}
                  </button>
                </div>
                {actionError && (
                  <div className="rounded-lg bg-danger-soft text-danger text-sm px-3 py-2 mt-3">
                    {actionError}
                  </div>
                )}
              </div>
            )}

            {exceptions.length === 0 ? (
              <p className="text-sm text-muted">
                No exceptions requested for this request.
              </p>
            ) : (
              <div className="space-y-2">
                {exceptions.map((exc) => (
                  <div
                    key={exc.id}
                    className="rounded-xl border border-line px-4 py-3"
                  >
                    <div className="flex items-center gap-2">
                      <span className="chip bg-primary-soft text-primary-deep">
                        {exc.status.replace(/_/g, " ")}
                      </span>
                      <span className="text-xs text-muted">
                        until {new Date(exc.expires_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-sm text-ink mt-1.5">{exc.justification}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === "Approval workflow" && (
        <div className="card p-6">
          {workflow ? (
            <WorkflowView workflow={workflow} />
          ) : (
            <p className="text-sm text-muted">
              No approval workflow — this request didn't require approvals.
            </p>
          )}
        </div>
      )}

      {tab === "Access lifecycle" && (
        <div className="card p-6">
          {request.status === "APPROVED" && grants.length === 0 && (
            <div className="rounded-xl bg-primary-soft/40 border border-primary/20 p-4 mb-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="font-semibold text-ink">Ready to provision</div>
                  <p className="text-sm text-muted mt-0.5">
                    This request is approved. Provision it to create a
                    time-bound access grant that expires automatically.
                  </p>
                </div>
                <button
                  className="btn-primary shrink-0"
                  disabled={provision.isPending}
                  onClick={() => provision.mutate()}
                >
                  {provision.isPending ? "Provisioning…" : "Provision access"}
                </button>
              </div>
              {actionError && (
                <div className="rounded-lg bg-danger-soft text-danger text-sm px-3 py-2 mt-3">
                  {actionError}
                </div>
              )}
            </div>
          )}

          {grants.length === 0 && request.status !== "APPROVED" ? (
            <p className="text-sm text-muted">
              No access grant yet. Grants appear once an approved request is
              provisioned.
            </p>
          ) : (
            grants.map((g) => <GrantLifecycle key={g.id} grant={g} />)
          )}
        </div>
      )}

      {tab === "Audit timeline" && (
        <div className="card p-6">
          <TimelineView events={timeline} />
        </div>
      )}
    </div>
  );
}

function GrantLifecycle({ grant }: { grant: AccessGrant }) {
  const { data: attempts = [] } = useQuery({
    queryKey: ["grant-attempts", grant.id],
    queryFn: () =>
      api.get<RevocationAttempt[]>(`/access-grants/${grant.id}/revocation-attempts`),
  });

  const stages = [
    { key: "PROVISIONED", label: "Provisioned", done: !!grant.granted_at },
    {
      key: "ACTIVE",
      label: "Active",
      done: grant.provisioning_status === "SUCCEEDED",
    },
    {
      key: "EXPIRING",
      label: "Expiring",
      done:
        grant.revocation_status === "IN_PROGRESS" ||
        grant.revocation_status === "SUCCEEDED" ||
        grant.revocation_status === "FAILED" ||
        grant.revocation_status === "ESCALATED",
    },
    {
      key: "REVOKED",
      label:
        grant.revocation_status === "ESCALATED" ? "Escalated" : "Revoked",
      done:
        grant.revocation_status === "SUCCEEDED" ||
        grant.revocation_status === "ESCALATED",
    },
  ];

  return (
    <div>
      <div className="flex items-center gap-1 mb-5">
        {stages.map((s, i) => (
          <div key={s.key} className="flex items-center gap-1 flex-1">
            <div className="flex flex-col items-center gap-1.5 flex-1">
              <div
                className={`h-8 w-8 rounded-full grid place-items-center text-xs font-semibold ${
                  s.done
                    ? "bg-primary text-white"
                    : "bg-line text-muted"
                }`}
              >
                {i + 1}
              </div>
              <span
                className={`text-xs ${s.done ? "text-ink font-medium" : "text-muted"}`}
              >
                {s.label}
              </span>
            </div>
            {i < stages.length - 1 && (
              <div
                className={`h-px flex-1 ${stages[i + 1].done ? "bg-primary" : "bg-line"}`}
              />
            )}
          </div>
        ))}
      </div>

      <dl className="grid sm:grid-cols-2 gap-3 text-sm mb-5">
        <div className="flex justify-between border-b border-line pb-2">
          <dt className="text-muted">Grant type</dt>
          <dd className="text-ink font-mono text-xs">{grant.grant_type}</dd>
        </div>
        <div className="flex justify-between border-b border-line pb-2">
          <dt className="text-muted">External reference</dt>
          <dd className="text-ink font-mono text-xs">
            {grant.external_reference ?? "—"}
          </dd>
        </div>
        <div className="flex justify-between border-b border-line pb-2">
          <dt className="text-muted">Granted at</dt>
          <dd className="text-ink">
            {grant.granted_at
              ? new Date(grant.granted_at).toLocaleString()
              : "—"}
          </dd>
        </div>
        <div className="flex justify-between border-b border-line pb-2">
          <dt className="text-muted">Expires at</dt>
          <dd className="text-ink">
            {grant.expires_at
              ? new Date(grant.expires_at).toLocaleString()
              : "—"}
          </dd>
        </div>
      </dl>

      {attempts.length > 0 && (
        <div>
          <div className="label">Revocation attempts</div>
          <div className="space-y-2">
            {attempts.map((a) => (
              <div
                key={a.id}
                className="flex items-center justify-between rounded-lg border border-line px-3 py-2 text-sm"
              >
                <span className="text-ink">Attempt {a.attempt_number}</span>
                <div className="flex items-center gap-2">
                  {a.error_message && (
                    <span className="text-xs text-muted">{a.error_message}</span>
                  )}
                  <span
                    className={`chip ${
                      a.status === "SUCCEEDED"
                        ? "bg-success-soft text-success"
                        : "bg-danger-soft text-danger"
                    }`}
                  >
                    {a.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
