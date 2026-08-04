import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { EvaluationPanel } from "../components/EvaluationPanel";
import type { EvaluationResult, Policy, Resource } from "../types";

export function PoliciesPage() {
  const { data: policies = [] } = useQuery({
    queryKey: ["policies"],
    queryFn: () => api.get<Policy[]>("/policies"),
  });
  const { data: resources = [] } = useQuery({
    queryKey: ["resources"],
    queryFn: () => api.get<Resource[]>("/resources"),
  });

  const [result, setResult] = useState<EvaluationResult | null>(null);

  async function tryScenario() {
    const restricted = resources.find((r) => r.sensitivity === "RESTRICTED");
    const res = await api.post<EvaluationResult>("/policies/evaluate-test", {
      request_type: "DATASET_ACCESS",
      resource_id: restricted?.id,
      payload: {
        requested_action: "EXPORT",
        destination_region: "US",
        duration_days: 30,
      },
    });
    setResult(res);
  }

  return (
    <div>
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="font-display text-3xl text-ink">Policy registry</h1>
          <p className="text-muted mt-1">
            Published policies evaluated by the deterministic engine, in priority
            order.
          </p>
        </div>
        <button className="btn-outline" onClick={tryScenario}>
          Test a restricted export
        </button>
      </div>

      {result && (
        <div className="card p-6 mb-6 border-primary/30">
          <div className="text-xs font-semibold uppercase tracking-wide text-primary-deep mb-4">
            Live evaluation · 30-day restricted export to US
          </div>
          <EvaluationPanel result={result} />
        </div>
      )}

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted border-b border-line">
              <th className="font-semibold px-5 py-3">Policy</th>
              <th className="font-semibold px-5 py-3">Type</th>
              <th className="font-semibold px-5 py-3">Priority</th>
              <th className="font-semibold px-5 py-3">Version</th>
              <th className="font-semibold px-5 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {[...policies]
              .sort((a, b) => a.priority - b.priority)
              .map((p) => (
                <tr
                  key={p.id}
                  className="border-b border-line last:border-0 hover:bg-canvas/60"
                >
                  <td className="px-5 py-3.5 text-ink">{p.name}</td>
                  <td className="px-5 py-3.5">
                    <span className="chip bg-primary-soft text-primary-deep">
                      {p.policy_type}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-muted">{p.priority}</td>
                  <td className="px-5 py-3.5 text-muted">v{p.version}</td>
                  <td className="px-5 py-3.5">
                    <span className="chip bg-success-soft text-success">
                      {p.status}
                    </span>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
