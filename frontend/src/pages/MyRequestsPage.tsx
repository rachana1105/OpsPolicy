import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { RiskBadge, StatusBadge } from "../components/Badges";
import type { OpsRequest } from "../types";

function fmt(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function MyRequestsPage() {
  const { data: requests = [], isLoading } = useQuery({
    queryKey: ["my-requests"],
    queryFn: () => api.get<OpsRequest[]>("/requests?mine=true"),
  });

  return (
    <div>
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="font-display text-3xl text-ink">My requests</h1>
          <p className="text-muted mt-1">
            Everything you've submitted, with its live decision and status.
          </p>
        </div>
        <Link to="/requests/new" className="btn-primary">
          New request
        </Link>
      </div>

      {isLoading ? (
        <div className="card p-10 text-center text-muted">Loading…</div>
      ) : requests.length === 0 ? (
        <div className="card p-10 grid place-items-center text-center">
          <div className="h-14 w-14 rounded-2xl bg-primary-soft grid place-items-center mb-4">
            <span className="font-display text-2xl text-primary-deep">+</span>
          </div>
          <div className="font-display text-xl text-ink mb-1">
            No requests yet
          </div>
          <p className="text-sm text-muted max-w-sm mb-4">
            Submit your first request and watch it move through policy evaluation
            and approval.
          </p>
          <Link to="/requests/new" className="btn-primary">
            New request
          </Link>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-line">
                <th className="font-semibold px-5 py-3">Request</th>
                <th className="font-semibold px-5 py-3">Type</th>
                <th className="font-semibold px-5 py-3">Status</th>
                <th className="font-semibold px-5 py-3">Risk</th>
                <th className="font-semibold px-5 py-3">Submitted</th>
                <th className="font-semibold px-5 py-3">Expires</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((r) => (
                <tr
                  key={r.id}
                  className="border-b border-line last:border-0 hover:bg-canvas/60"
                >
                  <td className="px-5 py-3.5">
                    <Link
                      to={`/requests/${r.id}`}
                      className="text-ink hover:text-primary-deep font-medium"
                    >
                      {r.title}
                    </Link>
                  </td>
                  <td className="px-5 py-3.5 text-muted">
                    {r.request_type.replace(/_/g, " ").toLowerCase()}
                  </td>
                  <td className="px-5 py-3.5">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="px-5 py-3.5">
                    {r.risk_level ? <RiskBadge level={r.risk_level} /> : "—"}
                  </td>
                  <td className="px-5 py-3.5 text-muted">{fmt(r.submitted_at)}</td>
                  <td className="px-5 py-3.5 text-muted">{fmt(r.expires_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
