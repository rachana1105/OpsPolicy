import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../hooks/useAuth";

const DEMO_USERS = [
  { email: "lena@northstar.io", label: "Lena — Analyst (requester)" },
  { email: "kabir.owner@northstar.io", label: "Kabir — Data Owner" },
  { email: "ishaan.comp@northstar.io", label: "Ishaan — Compliance Officer" },
  { email: "arjun.mgr@northstar.io", label: "Arjun — Manager" },
  { email: "admin@northstar.io", label: "Aisha — Platform Admin" },
];

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("lena@northstar.io");
  const [password, setPassword] = useState("opspolicy123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left: brand panel */}
      <div className="hidden lg:flex flex-col justify-between bg-sidebar text-white p-12 relative overflow-hidden">
        <div
          className="absolute -right-20 -top-20 h-80 w-80 rounded-full opacity-30 blur-3xl"
          style={{ background: "radial-gradient(circle,#6D5DFB,transparent)" }}
        />
        <div
          className="absolute -left-16 bottom-0 h-72 w-72 rounded-full opacity-20 blur-3xl"
          style={{ background: "radial-gradient(circle,#14B8A6,transparent)" }}
        />
        <div className="relative flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-primary grid place-items-center">
            <span className="font-display text-white text-xl">O</span>
          </div>
          <span className="font-display text-2xl">OpsPolicy</span>
        </div>
        <div className="relative">
          <h1 className="font-display text-4xl leading-tight mb-4">
            Every access request,
            <br />
            governed and accounted for.
          </h1>
          <p className="text-white/60 max-w-md">
            One place to define policy, evaluate requests deterministically, route
            approvals, and let temporary access expire on its own — with an
            immutable trail behind every decision.
          </p>
        </div>
        <div className="relative text-white/40 text-sm">
          Northstar Enterprises · internal platform
        </div>
      </div>

      {/* Right: form */}
      <div className="flex items-center justify-center p-8 bg-canvas">
        <div className="w-full max-w-sm">
          <h2 className="font-display text-3xl text-ink mb-1">Welcome back</h2>
          <p className="text-muted mb-8">Sign in to continue to your workspace.</p>

          <div className="space-y-4">
            <div>
              <label className="label">Email</label>
              <input
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submit()}
              />
            </div>
            <div>
              <label className="label">Password</label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submit()}
              />
            </div>

            {error && (
              <div className="rounded-xl bg-danger-soft text-danger text-sm px-3.5 py-2.5">
                {error}
              </div>
            )}

            <button className="btn-primary w-full" onClick={submit} disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </div>

          <div className="mt-8">
            <div className="label">Demo accounts · password opspolicy123</div>
            <div className="space-y-1.5 mt-2">
              {DEMO_USERS.map((u) => (
                <button
                  key={u.email}
                  onClick={() => setEmail(u.email)}
                  className="w-full text-left rounded-xl border border-line bg-card px-3.5 py-2 text-sm text-muted hover:border-primary/40 hover:text-primary-deep transition-colors"
                >
                  {u.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
