import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import type { SimulationJob } from "../types";

const PRESETS = [
  {
    label: "Contractors: production access max 7 days",
    definition: {
      name: "Contractor production access max 7 days",
      applies_to: { request_type: "PRODUCTION_ACCESS" },
      conditions: {
        all: [
          {
            field: "requester.employee_type",
            operator: "EQUALS",
            value: "CONTRACTOR",
          },
        ],
      },
      actions: [{ type: "SET_MAXIMUM_DURATION", days: 7 }],
    },
  },
  {
    label: "Contractors: production access max 3 days",
    definition: {
      name: "Contractor production access max 3 days",
      applies_to: { request_type: "PRODUCTION_ACCESS" },
      conditions: {
        all: [
          {
            field: "requester.employee_type",
            operator: "EQUALS",
            value: "CONTRACTOR",
          },
        ],
      },
      actions: [{ type: "SET_MAXIMUM_DURATION", days: 3 }],
    },
  },
  {
    label: "Restricted datasets: always require compliance approval",
    definition: {
      name: "Restricted always needs compliance",
      applies_to: { request_type: "DATASET_ACCESS" },
      conditions: {
        all: [
          {
            field: "resource.sensitivity",
            operator: "EQUALS",
            value: "RESTRICTED",
          },
        ],
      },
      actions: [
        { type: "REQUIRE_APPROVAL", role: "COMPLIANCE_OFFICER", stage: 1 },
      ],
    },
  },
];

const RISK_COLORS: Record<string, string> = {
  LOW: "#10B981",
  MEDIUM: "#F59E0B",
  HIGH: "#EF4444",
  CRITICAL: "#B91C1C",
};

const RECOMMENDATION_TONE: Record<string, string> = {
  SAFE_TO_INTRODUCE: "bg-success-soft text-success",
  INTRODUCE_GRADUALLY: "bg-warning-soft text-warning",
  HIGH_IMPACT_REVIEW_BEFORE_ROLLOUT: "bg-danger-soft text-danger",
  NO_HISTORICAL_DATA: "bg-line text-muted",
};

export function SimulationPage() {
  const qc = useQueryClient();
  const [preset, setPreset] = useState(0);
  const [activeJob, setActiveJob] = useState<SimulationJob | null>(null);

  const { data: history = [] } = useQuery({
    queryKey: ["simulations"],
    queryFn: () => api.get<SimulationJob[]>("/policy-simulations"),
  });

  const run = useMutation({
    mutationFn: () =>
      api.post<SimulationJob>("/policy-simulations", {
        policy_definition: PRESETS[preset].definition,
      }),
    onSuccess: (job) => {
      setActiveJob(job);
      qc.invalidateQueries({ queryKey: ["simulations"] });
    },
  });

  const result = activeJob?.result;
  const riskData = result
    ? Object.entries(result.risk_distribution).map(([name, value]) => ({
        name,
        value,
      }))
    : [];

  return (
    <div>
      <h1 className="font-display text-3xl text-ink mb-1">Policy simulation</h1>
      <p className="text-muted mb-6">
        Run a proposed policy against your historical requests before you publish
        it — the same deterministic engine, applied to the past.
      </p>

      <div className="card p-6 mb-6">
        <label className="label">Proposed policy</label>
        <select
          className="input mb-4"
          value={preset}
          onChange={(e) => setPreset(Number(e.target.value))}
        >
          {PRESETS.map((p, i) => (
            <option key={i} value={i}>
              {p.label}
            </option>
          ))}
        </select>
        <button
          className="btn-primary"
          onClick={() => run.mutate()}
          disabled={run.isPending}
        >
          {run.isPending ? "Running simulation…" : "Run simulation"}
        </button>
      </div>

      {result && (
        <div className="card p-6 mb-6 animate-fade-up">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-display text-xl text-ink">Impact report</h2>
            <span
              className={`chip ${
                RECOMMENDATION_TONE[result.recommendation] ?? "bg-line text-muted"
              }`}
            >
              {result.recommendation.replace(/_/g, " ")}
            </span>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="rounded-xl border border-line p-4">
              <div className="text-xs text-muted">Requests analysed</div>
              <div className="font-display text-2xl text-ink mt-1">
                {result.records_analysed.toLocaleString()}
              </div>
            </div>
            <div className="rounded-xl border border-line p-4">
              <div className="text-xs text-muted">Requests affected</div>
              <div className="font-display text-2xl text-primary-deep mt-1">
                {result.requests_affected.toLocaleString()}
              </div>
            </div>
            <div className="rounded-xl border border-line p-4">
              <div className="text-xs text-muted">Now rejected</div>
              <div className="font-display text-2xl text-danger mt-1">
                {result.previously_approved_now_rejected.toLocaleString()}
              </div>
            </div>
            <div className="rounded-xl border border-line p-4">
              <div className="text-xs text-muted">Duration reductions</div>
              <div className="font-display text-2xl text-warning mt-1">
                {result.duration_reductions_required.toLocaleString()}
              </div>
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            <div>
              <div className="label">Most affected teams</div>
              {result.most_affected_departments.length === 0 ? (
                <p className="text-sm text-muted">No teams affected.</p>
              ) : (
                <div className="space-y-2">
                  {result.most_affected_departments.map((d) => (
                    <div
                      key={d.team}
                      className="flex items-center justify-between rounded-lg border border-line px-3 py-2 text-sm"
                    >
                      <span className="text-ink font-mono text-xs">
                        {d.team.slice(0, 12)}
                      </span>
                      <span className="chip bg-primary-soft text-primary-deep">
                        {d.affected_requests} affected
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div>
              <div className="label">Risk distribution (historical)</div>
              {riskData.length === 0 ? (
                <p className="text-sm text-muted">No scored requests.</p>
              ) : (
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={riskData}>
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 11, fill: "#6B6577" }}
                    />
                    <YAxis tick={{ fontSize: 11, fill: "#6B6577" }} />
                    <Tooltip />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                      {riskData.map((d) => (
                        <Cell
                          key={d.name}
                          fill={RISK_COLORS[d.name] ?? "#6D5DFB"}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>
      )}

      {history.length > 0 && (
        <div className="card p-6">
          <h2 className="font-display text-lg text-ink mb-4">
            Recent simulations
          </h2>
          <div className="space-y-2">
            {history.slice(0, 8).map((job) => (
              <button
                key={job.id}
                onClick={() => job.result && setActiveJob(job)}
                className="w-full flex items-center justify-between rounded-xl border border-line px-4 py-3 text-left hover:border-primary/40"
              >
                <div>
                  <div className="text-sm text-ink">{job.input_reference}</div>
                  <div className="text-xs text-muted mt-0.5">
                    {job.completed_at
                      ? new Date(job.completed_at).toLocaleString()
                      : "—"}
                  </div>
                </div>
                {job.result && (
                  <span className="chip bg-primary-soft text-primary-deep">
                    {job.result.requests_affected} affected
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
