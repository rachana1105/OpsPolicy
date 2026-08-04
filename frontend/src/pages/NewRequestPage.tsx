import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { EvaluationPanel } from "../components/EvaluationPanel";
import type {
  EvaluationResult,
  OpsRequest,
  RequestType,
  Resource,
} from "../types";

const REQUEST_TYPES: { value: RequestType; title: string; blurb: string }[] = [
  {
    value: "DATASET_ACCESS",
    title: "Dataset access",
    blurb: "Read or export access to a governed dataset.",
  },
  {
    value: "PRODUCTION_ACCESS",
    title: "Production access",
    blurb: "Temporary access to a production environment or service.",
  },
  {
    value: "PURCHASE_APPROVAL",
    title: "Purchase approval",
    blurb: "Approval for an enterprise software or vendor purchase.",
  },
];

const STEPS = ["Type", "Resource", "Details", "Review"];

export function NewRequestPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [requestType, setRequestType] = useState<RequestType | null>(null);
  const [resourceId, setResourceId] = useState<string | null>(null);
  const [payload, setPayload] = useState<Record<string, unknown>>({});
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const { data: resources = [] } = useQuery({
    queryKey: ["resources"],
    queryFn: () => api.get<Resource[]>("/resources"),
  });

  const needsResource = requestType !== "PURCHASE_APPROVAL";

  async function runEvaluation() {
    setEvaluating(true);
    try {
      const res = await api.post<EvaluationResult>("/policies/evaluate-test", {
        request_type: requestType,
        resource_id: resourceId,
        payload,
      });
      setResult(res);
      setStep(3);
    } finally {
      setEvaluating(false);
    }
  }

  function set(field: string, value: unknown) {
    setPayload((p) => ({ ...p, [field]: value }));
  }

  async function submitRequest() {
    setSubmitting(true);
    setSubmitError("");
    try {
      const title =
        (payload.business_justification as string)?.slice(0, 60) ||
        `${requestType?.replace(/_/g, " ")} request`;
      const created = await api.post<OpsRequest>("/requests", {
        request_type: requestType,
        title,
        resource_id: resourceId,
        business_justification: payload.business_justification ?? null,
        payload,
      });
      await api.post<OpsRequest>(`/requests/${created.id}/submit`);
      navigate(`/requests/${created.id}`);
    } catch (e) {
      setSubmitError(
        e instanceof ApiError ? e.message : "Could not submit the request."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="font-display text-3xl text-ink mb-1">New request</h1>
      <p className="text-muted mb-6">
        We evaluate your request against live policy before you submit — no
        surprises later.
      </p>

      {/* Stepper */}
      <div className="flex items-center gap-2 mb-8">
        {STEPS.map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            <div
              className={`h-7 w-7 rounded-full grid place-items-center text-xs font-semibold transition-colors ${
                i <= step
                  ? "bg-primary text-white"
                  : "bg-line text-muted"
              }`}
            >
              {i + 1}
            </div>
            <span
              className={`text-sm ${
                i === step ? "text-ink font-semibold" : "text-muted"
              }`}
            >
              {label}
            </span>
            {i < STEPS.length - 1 && (
              <div className="w-8 h-px bg-line mx-1" />
            )}
          </div>
        ))}
      </div>

      <div className="card p-6 max-w-3xl">
        {/* Step 1: Type */}
        {step === 0 && (
          <div className="space-y-3">
            {REQUEST_TYPES.map((t) => (
              <button
                key={t.value}
                onClick={() => {
                  setRequestType(t.value);
                  setResourceId(null);
                  setStep(t.value === "PURCHASE_APPROVAL" ? 2 : 1);
                }}
                className={`w-full text-left rounded-xl border p-4 transition-all ${
                  requestType === t.value
                    ? "border-primary bg-primary-soft/40"
                    : "border-line hover:border-primary/40"
                }`}
              >
                <div className="font-semibold text-ink">{t.title}</div>
                <div className="text-sm text-muted mt-0.5">{t.blurb}</div>
              </button>
            ))}
          </div>
        )}

        {/* Step 2: Resource */}
        {step === 1 && needsResource && (
          <div>
            <label className="label">Select a resource</label>
            <div className="grid sm:grid-cols-2 gap-2.5 mt-1">
              {resources.map((r) => (
                <button
                  key={r.id}
                  onClick={() => setResourceId(r.id)}
                  className={`text-left rounded-xl border p-3.5 transition-all ${
                    resourceId === r.id
                      ? "border-primary bg-primary-soft/40"
                      : "border-line hover:border-primary/40"
                  }`}
                >
                  <div className="font-mono text-sm text-ink">{r.name}</div>
                  <div className="flex gap-1.5 mt-2">
                    <span className="chip bg-line text-muted">
                      {r.sensitivity}
                    </span>
                    <span className="chip bg-line text-muted">
                      {r.resource_type.replace(/_/g, " ")}
                    </span>
                  </div>
                </button>
              ))}
            </div>
            <div className="flex justify-between mt-6">
              <button className="btn-ghost" onClick={() => setStep(0)}>
                Back
              </button>
              <button
                className="btn-primary"
                disabled={!resourceId}
                onClick={() => setStep(2)}
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Details */}
        {step === 2 && (
          <div className="space-y-4">
            {requestType === "DATASET_ACCESS" && (
              <>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Requested action</label>
                    <select
                      className="input"
                      onChange={(e) => set("requested_action", e.target.value)}
                      defaultValue=""
                    >
                      <option value="" disabled>
                        Choose…
                      </option>
                      <option value="READ">Read</option>
                      <option value="EXPORT">Export</option>
                    </select>
                  </div>
                  <div>
                    <label className="label">Destination region</label>
                    <select
                      className="input"
                      onChange={(e) => set("destination_region", e.target.value)}
                      defaultValue="IN"
                    >
                      <option value="IN">India (IN)</option>
                      <option value="SG">Singapore (SG)</option>
                      <option value="US">United States (US)</option>
                      <option value="EU">European Union (EU)</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="label">Duration (days)</label>
                  <input
                    type="number"
                    className="input"
                    placeholder="e.g. 30"
                    onChange={(e) => set("duration_days", Number(e.target.value))}
                  />
                </div>
              </>
            )}

            {requestType === "PRODUCTION_ACCESS" && (
              <>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Requested role</label>
                    <select
                      className="input"
                      onChange={(e) => set("requested_role", e.target.value)}
                      defaultValue=""
                    >
                      <option value="" disabled>
                        Choose…
                      </option>
                      <option value="READ">Read</option>
                      <option value="ADMIN">Admin</option>
                    </select>
                  </div>
                  <div>
                    <label className="label">Duration (days)</label>
                    <input
                      type="number"
                      className="input"
                      onChange={(e) => set("duration_days", Number(e.target.value))}
                    />
                  </div>
                </div>
                <label className="flex items-center gap-2 text-sm text-ink">
                  <input
                    type="checkbox"
                    onChange={(e) => set("emergency", e.target.checked)}
                  />
                  Emergency access (incident in progress)
                </label>
              </>
            )}

            {requestType === "PURCHASE_APPROVAL" && (
              <>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="label">Vendor</label>
                    <input
                      className="input"
                      onChange={(e) => set("vendor", e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="label">Amount (₹)</label>
                    <input
                      type="number"
                      className="input"
                      placeholder="e.g. 1200000"
                      onChange={(e) => set("amount", Number(e.target.value))}
                    />
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="label">Business justification</label>
              <textarea
                className="input min-h-[80px]"
                onChange={(e) => set("business_justification", e.target.value)}
              />
            </div>

            <div className="flex justify-between mt-2">
              <button
                className="btn-ghost"
                onClick={() => setStep(needsResource ? 1 : 0)}
              >
                Back
              </button>
              <button
                className="btn-primary"
                onClick={runEvaluation}
                disabled={evaluating}
              >
                {evaluating ? "Evaluating…" : "Review policy evaluation"}
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Review */}
        {step === 3 && result && (
          <div>
            <EvaluationPanel result={result} />
            <div className="flex justify-between mt-8 pt-6 border-t border-line">
              <button className="btn-ghost" onClick={() => setStep(2)}>
                Adjust details
              </button>
              <button
                className="btn-primary"
                disabled={result.decision === "REJECT" || submitting}
                onClick={submitRequest}
                title={
                  result.decision === "REJECT"
                    ? "This request is prohibited by policy"
                    : ""
                }
              >
                {submitting ? "Submitting…" : "Submit request"}
              </button>
            </div>
            {submitError && (
              <div className="rounded-xl bg-danger-soft text-danger text-sm px-3.5 py-2.5 mt-3">
                {submitError}
              </div>
            )}
            {result.decision === "REJECT" && (
              <p className="text-xs text-muted mt-3">
                This request is prohibited by policy and can't be submitted.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
