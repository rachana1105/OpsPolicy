import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import type { Policy, Resource } from "../types";

function StatCard({
  label,
  value,
  tone = "primary",
}: {
  label: string;
  value: string | number;
  tone?: "primary" | "secondary" | "warning" | "danger";
}) {
  const tones = {
    primary: "text-primary-deep",
    secondary: "text-secondary",
    warning: "text-warning",
    danger: "text-danger",
  };
  return (
    <div className="card p-5">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted">
        {label}
      </div>
      <div className={`font-display text-3xl mt-2 ${tones[tone]}`}>{value}</div>
    </div>
  );
}

export function OverviewPage() {
  const { user } = useAuth();
  const { data: policies = [] } = useQuery({
    queryKey: ["policies"],
    queryFn: () => api.get<Policy[]>("/policies"),
  });
  const { data: resources = [] } = useQuery({
    queryKey: ["resources"],
    queryFn: () => api.get<Resource[]>("/resources"),
  });

  const restricted = resources.filter((r) => r.sensitivity === "RESTRICTED");

  return (
    <div>
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="font-display text-3xl text-ink">
            Good to see you, {user?.name.split(" ")[0]}.
          </h1>
          <p className="text-muted mt-1">
            Here's the state of governance across Northstar today.
          </p>
        </div>
        <Link to="/requests/new" className="btn-primary">
          New request
        </Link>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Published policies" value={policies.length} />
        <StatCard
          label="Governed resources"
          value={resources.length}
          tone="secondary"
        />
        <StatCard
          label="Restricted datasets"
          value={restricted.length}
          tone="warning"
        />
        <StatCard label="Pending approvals" value="—" tone="primary" />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h2 className="font-display text-xl text-ink mb-4">
            Governed resources
          </h2>
          <div className="space-y-2">
            {resources.slice(0, 6).map((r) => (
              <div
                key={r.id}
                className="flex items-center justify-between rounded-xl border border-line px-3.5 py-2.5"
              >
                <span className="font-mono text-sm text-ink">{r.name}</span>
                <span
                  className={`chip ${
                    r.sensitivity === "RESTRICTED"
                      ? "bg-danger-soft text-danger"
                      : "bg-line text-muted"
                  }`}
                >
                  {r.sensitivity}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="card p-6">
          <h2 className="font-display text-xl text-ink mb-4">Active policies</h2>
          <div className="space-y-2">
            {policies.slice(0, 6).map((p) => (
              <div
                key={p.id}
                className="rounded-xl border border-line px-3.5 py-2.5"
              >
                <div className="text-sm text-ink">{p.name}</div>
                <div className="flex gap-1.5 mt-1.5">
                  <span className="chip bg-primary-soft text-primary-deep">
                    {p.policy_type}
                  </span>
                  <span className="chip bg-line text-muted">
                    priority {p.priority}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
