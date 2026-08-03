import type { EvaluationResult } from "../types";
import { DecisionBadge, RiskBadge } from "./Badges";

export function EvaluationPanel({ result }: { result: EvaluationResult }) {
  const maxFactor = Math.max(1, ...result.risk_factors.map((f) => f.points));

  return (
    <div className="space-y-5">
      {/* Decision + risk headline */}
      <div className="flex flex-wrap items-center gap-3">
        <DecisionBadge decision={result.decision} />
        <RiskBadge level={result.risk_level} />
        <span className="text-sm text-muted">
          Risk score{" "}
          <span className="font-semibold text-ink">{result.risk_score}</span>
        </span>
        {result.maximum_allowed_duration_days != null && (
          <span className="text-sm text-muted">
            · Max duration{" "}
            <span className="font-semibold text-ink">
              {result.maximum_allowed_duration_days} days
            </span>
          </span>
        )}
      </div>

      {/* Violations */}
      {result.violations.length > 0 && (
        <div className="rounded-xl bg-warning-soft border border-warning/20 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-warning mb-2">
            Violations to resolve
          </div>
          <ul className="space-y-1.5">
            {result.violations.map((v, i) => (
              <li key={i} className="text-sm text-ink flex gap-2">
                <span className="text-warning mt-0.5">•</span>
                {v}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-5">
        {/* Matched policies */}
        <div>
          <div className="label">Matched policies</div>
          {result.matched_policies.length === 0 ? (
            <p className="text-sm text-muted">
              No policies matched — this request auto-approves.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {result.matched_policies.map((p, i) => (
                <li
                  key={i}
                  className="text-sm text-ink rounded-lg bg-primary-soft/50 px-3 py-2"
                >
                  {p}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Required approvals */}
        <div>
          <div className="label">Required approvals</div>
          {result.required_approvals.length === 0 ? (
            <p className="text-sm text-muted">None required.</p>
          ) : (
            <ul className="space-y-1.5">
              {result.required_approvals.map((a, i) => (
                <li
                  key={i}
                  className="text-sm flex items-center justify-between rounded-lg border border-line px-3 py-2"
                >
                  <span className="text-ink capitalize">
                    {a.role.replace(/_/g, " ").toLowerCase()}
                  </span>
                  <span className="chip bg-secondary-soft text-secondary">
                    Stage {a.stage}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Risk breakdown */}
      {result.risk_factors.length > 0 && (
        <div>
          <div className="label">Risk breakdown</div>
          <div className="space-y-2">
            {result.risk_factors.map((f, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-40 shrink-0 text-sm text-muted capitalize">
                  {f.name.replace(/_/g, " ")}
                </div>
                <div className="flex-1 h-2 rounded-full bg-line overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${(f.points / maxFactor) * 100}%` }}
                  />
                </div>
                <div className="w-8 text-right text-sm font-semibold text-ink">
                  +{f.points}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Conflicts */}
      {result.conflicts.length > 0 && (
        <div className="rounded-xl bg-danger-soft border border-danger/20 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-danger mb-2">
            Policy conflicts
          </div>
          {result.conflicts.map((c, i) => (
            <p key={i} className="text-sm text-ink">
              {c}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
