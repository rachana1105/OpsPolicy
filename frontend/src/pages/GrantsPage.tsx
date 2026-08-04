import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { AccessGrant } from "../types";

function fmt(d: string | null) {
  if (!d) return "—";
  return new Date(d).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function grantState(g: AccessGrant): { label: string; tone: string } {
  if (g.revocation_status === "SUCCEEDED")
    return { label: "Revoked", tone: "bg-line text-muted" };
  if (g.revocation_status === "ESCALATED")
    return { label: "Escalated", tone: "bg-danger text-white" };
  if (g.revocation_status === "FAILED")
    return { label: "Revocation failed", tone: "bg-danger-soft text-danger" };
  if (g.revocation_status === "IN_PROGRESS")
    return { label: "Expiring", tone: "bg-warning-soft text-warning" };
  if (g.provisioning_status === "SUCCEEDED")
    return { label: "Active", tone: "bg-secondary-soft text-secondary" };
  if (g.provisioning_status === "FAILED")
    return { label: "Provisioning failed", tone: "bg-danger-soft text-danger" };
  return { label: g.provisioning_status, tone: "bg-line text-muted" };
}

function expiryLabel(g: AccessGrant): string {
  if (!g.expires_at || g.revocation_status === "SUCCEEDED") return "—";
  const ms = new Date(g.expires_at).getTime() - Date.now();
  if (ms <= 0) return "Expired";
  const hours = ms / 36e5;
  if (hours < 24) return `${Math.round(hours)}h left`;
  return `${Math.round(hours / 24)}d left`;
}

export function GrantsPage() {
  const { data: grants = [], isLoading } = useQuery({
    queryKey: ["grants"],
    queryFn: () => api.get<AccessGrant[]>("/access-grants"),
  });

  return (
    <div>
      <h1 className="font-display text-3xl text-ink mb-1">Access grants</h1>
      <p className="text-muted mb-6">
        Provisioned access, its expiry, and revocation status.
      </p>

      {isLoading ? (
        <div className="card p-10 text-center text-muted">Loading…</div>
      ) : grants.length === 0 ? (
        <div className="card p-10 grid place-items-center text-center">
          <div className="h-14 w-14 rounded-2xl bg-primary-soft grid place-items-center mb-4">
            <span className="font-display text-2xl text-primary-deep">⚿</span>
          </div>
          <div className="font-display text-xl text-ink mb-1">
            No grants yet
          </div>
          <p className="text-sm text-muted max-w-sm">
            Approved requests appear here once provisioned, with a live countdown
            to automatic expiry.
          </p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-line">
                <th className="font-semibold px-5 py-3">Grant</th>
                <th className="font-semibold px-5 py-3">State</th>
                <th className="font-semibold px-5 py-3">Granted</th>
                <th className="font-semibold px-5 py-3">Expires</th>
                <th className="font-semibold px-5 py-3">Countdown</th>
              </tr>
            </thead>
            <tbody>
              {grants.map((g) => {
                const st = grantState(g);
                return (
                  <tr
                    key={g.id}
                    className="border-b border-line last:border-0 hover:bg-canvas/60"
                  >
                    <td className="px-5 py-3.5">
                      <Link
                        to={`/requests/${g.request_id}`}
                        className="font-mono text-xs text-ink hover:text-primary-deep"
                      >
                        {g.grant_type.replace(/GRANT_/g, "").replace(/_/g, " ").toLowerCase()}
                      </Link>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`chip ${st.tone}`}>{st.label}</span>
                    </td>
                    <td className="px-5 py-3.5 text-muted">{fmt(g.granted_at)}</td>
                    <td className="px-5 py-3.5 text-muted">{fmt(g.expires_at)}</td>
                    <td className="px-5 py-3.5 text-ink font-medium">
                      {expiryLabel(g)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
