import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { AuditEvent, User } from "../types";

const EVENT_TONE: Record<string, string> = {
  REQUEST_APPROVED: "bg-success-soft text-success",
  REQUEST_REJECTED: "bg-danger-soft text-danger",
  ACCESS_REVOKED: "bg-line text-muted",
  ACCESS_PROVISIONED: "bg-secondary-soft text-secondary",
  REVOCATION_FAILED: "bg-danger-soft text-danger",
  SLA_ESCALATED: "bg-warning-soft text-warning",
  POLICY_EVALUATED: "bg-primary-soft text-primary-deep",
  RISK_CALCULATED: "bg-primary-soft text-primary-deep",
};

export function AuditExplorerPage() {
  const [eventType, setEventType] = useState("");
  const [actorId, setActorId] = useState("");
  const [requestId, setRequestId] = useState("");

  const { data: eventTypes = [] } = useQuery({
    queryKey: ["audit-event-types"],
    queryFn: () => api.get<string[]>("/audit/event-types"),
  });
  const { data: users = [] } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.get<User[]>("/users"),
  });

  const params = new URLSearchParams();
  if (eventType) params.set("event_type", eventType);
  if (actorId) params.set("actor_id", actorId);
  if (requestId) params.set("request_id", requestId.trim());

  const { data: events = [], isLoading } = useQuery({
    queryKey: ["audit", eventType, actorId, requestId],
    queryFn: () => api.get<AuditEvent[]>(`/audit/events?${params.toString()}`),
  });

  const userName = (id: string | null) =>
    users.find((u) => u.id === id)?.name ?? (id ? id.slice(0, 8) : "system");

  return (
    <div>
      <h1 className="font-display text-3xl text-ink mb-1">Audit explorer</h1>
      <p className="text-muted mb-6">
        The immutable, ordered record of every decision. Append-only — nothing
        here is ever edited or deleted.
      </p>

      <div className="card p-4 mb-5">
        <div className="grid sm:grid-cols-3 gap-3">
          <div>
            <label className="label">Event type</label>
            <select
              className="input"
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
            >
              <option value="">All events</option>
              {eventTypes.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Actor</label>
            <select
              className="input"
              value={actorId}
              onChange={(e) => setActorId(e.target.value)}
            >
              <option value="">Anyone</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Request ID</label>
            <input
              className="input"
              value={requestId}
              onChange={(e) => setRequestId(e.target.value)}
              placeholder="Paste a request id…"
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="card p-10 text-center text-muted">Loading…</div>
      ) : events.length === 0 ? (
        <div className="card p-10 text-center text-muted">
          No events match these filters.
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-line">
                <th className="font-semibold px-5 py-3">Event</th>
                <th className="font-semibold px-5 py-3">Actor</th>
                <th className="font-semibold px-5 py-3">Entity</th>
                <th className="font-semibold px-5 py-3">Request</th>
                <th className="font-semibold px-5 py-3">When</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr
                  key={e.id}
                  className="border-b border-line last:border-0 hover:bg-canvas/60"
                >
                  <td className="px-5 py-3">
                    <span
                      className={`chip ${EVENT_TONE[e.event_type] ?? "bg-line text-muted"}`}
                    >
                      {e.event_type.replace(/_/g, " ")}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-ink">{userName(e.actor_id)}</td>
                  <td className="px-5 py-3 text-muted">{e.entity_type}</td>
                  <td className="px-5 py-3">
                    {e.request_id ? (
                      <Link
                        to={`/requests/${e.request_id}`}
                        className="font-mono text-xs text-primary-deep hover:underline"
                      >
                        {e.request_id.slice(0, 8)}
                      </Link>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-5 py-3 text-muted whitespace-nowrap">
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
