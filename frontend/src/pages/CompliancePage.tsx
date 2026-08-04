import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import type { ComplianceSummary } from "../types";

const RISK_COLORS: Record<string, string> = {
  LOW: "#10B981",
  MEDIUM: "#F59E0B",
  HIGH: "#EF4444",
  CRITICAL: "#B91C1C",
};

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="card p-5">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted">
        {label}
      </div>
      <div className="font-display text-3xl mt-2 text-ink">{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  );
}

export function CompliancePage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["compliance"],
    queryFn: () => api.get<ComplianceSummary>("/analytics/compliance-summary"),
  });

  const refresh = useMutation({
    mutationFn: () => api.post("/analytics/refresh"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["compliance"] }),
  });

  const freshness = data?.data_freshness
    ? new Date(data.data_freshness).toLocaleString()
    : null;

  const cs = data?.compliance_summary;
  const riskData = cs
    ? Object.entries(cs.risk_distribution).map(([name, value]) => ({ name, value }))
    : [];
  const typeData = cs
    ? Object.entries(cs.requests_by_type).map(([name, value]) => ({
        name: name.replace(/_/g, " ").toLowerCase(),
        value,
      }))
    : [];

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="font-display text-3xl text-ink">Compliance</h1>
          <p className="text-muted mt-1">
            Organisation-wide metrics, computed behind the platform.
          </p>
        </div>
        <div className="text-right">
          <button
            className="btn-primary"
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending}
          >
            {refresh.isPending ? "Refreshing…" : "Refresh metrics"}
          </button>
          <div className="text-xs text-muted mt-2">
            {freshness ? `Data as of ${freshness}` : "Never refreshed"}
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="card p-10 text-center text-muted">Loading…</div>
      ) : !data?.available ? (
        <div className="card p-10 grid place-items-center text-center">
          <div className="h-14 w-14 rounded-2xl bg-warning-soft grid place-items-center mb-4">
            <span className="font-display text-2xl text-warning">◷</span>
          </div>
          <div className="font-display text-xl text-ink mb-1">
            No analytics yet
          </div>
          <p className="text-sm text-muted max-w-sm mb-4">
            Compliance metrics are computed by a background job. Run a refresh to
            populate the dashboard.
          </p>
          <button className="btn-primary" onClick={() => refresh.mutate()}>
            Run first refresh
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Stat
              label="Total requests"
              value={String(cs?.total_requests ?? 0)}
            />
            <Stat
              label="Approval rate"
              value={`${Math.round((cs?.approval_rate ?? 0) * 100)}%`}
              sub={`${cs?.approved ?? 0} approved · ${cs?.rejected ?? 0} rejected`}
            />
            <Stat
              label="SLA compliance"
              value={`${Math.round((data.approval_sla?.sla_compliance ?? 1) * 100)}%`}
              sub={`${data.approval_sla?.breached ?? 0} breached`}
            />
            <Stat
              label="Failed revocations"
              value={String(data.revocation_failures?.failed_revocations ?? 0)}
              sub={`${data.revocation_failures?.escalated ?? 0} escalated`}
            />
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            <div className="card p-6">
              <h2 className="font-display text-lg text-ink mb-4">
                Risk distribution
              </h2>
              {riskData.length === 0 ? (
                <p className="text-sm text-muted">No scored requests yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={riskData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={50}
                      outerRadius={90}
                    >
                      {riskData.map((d) => (
                        <Cell
                          key={d.name}
                          fill={RISK_COLORS[d.name] ?? "#6D5DFB"}
                        />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              )}
              <div className="flex flex-wrap gap-3 justify-center mt-2">
                {riskData.map((d) => (
                  <div key={d.name} className="flex items-center gap-1.5 text-xs">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ background: RISK_COLORS[d.name] ?? "#6D5DFB" }}
                    />
                    <span className="text-muted">
                      {d.name} ({d.value})
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="card p-6">
              <h2 className="font-display text-lg text-ink mb-4">
                Requests by type
              </h2>
              {typeData.length === 0 ? (
                <p className="text-sm text-muted">No requests yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={typeData}>
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 11, fill: "#6B6577" }}
                    />
                    <YAxis tick={{ fontSize: 11, fill: "#6B6577" }} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#6D5DFB" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          <div className="card p-6">
            <h2 className="font-display text-lg text-ink mb-4">
              Approval time by role
            </h2>
            <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries(data.approval_sla?.avg_hours_by_role ?? {}).map(
                ([role, hours]) => (
                  <div
                    key={role}
                    className="rounded-xl border border-line px-4 py-3"
                  >
                    <div className="text-xs text-muted capitalize">
                      {role.replace(/_/g, " ").toLowerCase()}
                    </div>
                    <div className="font-display text-xl text-ink mt-1">
                      {hours}h
                    </div>
                  </div>
                )
              )}
              {Object.keys(data.approval_sla?.avg_hours_by_role ?? {}).length ===
                0 && (
                <p className="text-sm text-muted">
                  No completed approvals to measure yet.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
