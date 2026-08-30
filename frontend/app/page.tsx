"use client";

import { useCallback, useEffect, useState } from "react";
import type { ApiState } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const POLL_MS = 2000;

function fmtINR(n: number): string {
  return `₹${n.toLocaleString("en-IN")}`;
}

function AuditStamp({ approved }: { approved: boolean }) {
  return (
    <span
      className={`inline-block border-2 px-2 py-0.5 font-mono text-sm font-semibold uppercase tracking-widest ${
        approved
          ? "border-approved text-approved"
          : "border-blocked text-blocked"
      }`}
      style={{ transform: "rotate(-6deg)" }}
    >
      {approved ? "Approved" : "Blocked"}
    </span>
  );
}

export default function Dashboard() {
  const [state, setState] = useState<ApiState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revoking, setRevoking] = useState(false);

  const loadState = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/state`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: ApiState = await res.json();
      setState(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch state");
    }
  }, []);

  // Periodic polling for real-time state refresh (FR-DSH-4)
  useEffect(() => {
    loadState();
    const id = setInterval(loadState, POLL_MS);
    return () => clearInterval(id);
  }, [loadState]);

  const revoke = async () => {
    setRevoking(true);
    try {
      await fetch(`${API_URL}/api/revoke`, { method: "POST" });
      await loadState();
    } finally {
      setRevoking(false);
    }
  };

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ink text-blocked font-mono">
        {error}
      </div>
    );
  }

  if (!state) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ink text-amber font-mono">
        loading…
      </div>
    );
  }

  const { mandate, stats, audit_log } = state;
  const isActive = mandate.status === "active";
  const pct =
    stats.cumulative_limit_inr > 0
      ? Math.min(100, (stats.total_spend_inr / stats.cumulative_limit_inr) * 100)
      : 0;

  return (
    <main className="min-h-screen bg-ink px-6 py-8 font-sans">
      <div className="mx-auto max-w-5xl space-y-6">
        {/* Header */}
        <header className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Agentic Guard</h1>
            <p className="text-sm text-white/50">Mandate-Bounded Risk Interceptor</p>
          </div>
          {/* Revoke button (FR-DSH-5) & disabled state upon revocation (FR-DSH-6) */}
          <button
            onClick={revoke}
            disabled={!isActive || revoking}
            className={`border px-4 py-2 font-medium transition ${
              isActive
                ? "border-amber text-amber hover:bg-amber/10"
                : "border-white/20 text-white/40 cursor-not-allowed"
            }`}
          >
            {isActive ? "Revoke Access" : "Access Revoked"}
          </button>
        </header>

        {/* Mandate panel — FR-DSH-1 */}
        <section className="rounded-lg border border-white/10 bg-panel p-5">
          <h2 className="mb-3 text-sm uppercase tracking-widest text-white/50">
            Mandate
          </h2>
          <div className="grid grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-3">
            <Field label="Status">
              <span
                className={`font-mono font-semibold ${
                  isActive ? "text-approved" : "text-blocked"
                }`}
              >
                {mandate.status.toUpperCase()}
              </span>
            </Field>
            <Field label="Mandate ID">
              <span className="font-mono">{mandate.mandate_id}</span>
            </Field>
            <Field label="User ID">
              <span className="font-mono">{mandate.user_id}</span>
            </Field>
            <Field label="Max / Transaction">
              <span className="font-mono">{fmtINR(mandate.limits.max_per_transaction)}</span>
            </Field>
            <Field label="Cumulative Limit">
              <span className="font-mono">{fmtINR(mandate.limits.max_cumulative)}</span>
            </Field>
            <Field label="Cumulative Window">
              <span className="font-mono">{mandate.limits.cumulative_window_hours}h</span>
            </Field>
            <Field label="Velocity Limit">
              <span className="font-mono">{mandate.limits.max_attempts_per_minute}/min</span>
            </Field>
            <Field label="Allowed MCC">
              <span className="font-mono">{mandate.scope.allowed_mcc.join(", ")}</span>
            </Field>
            <Field label="Allowed Merchants">
              <span className="font-mono">{mandate.scope.allowed_merchants.join(", ")}</span>
            </Field>
          </div>
          <div className="mt-4">
            <Field label="Blocked Categories">
              <span className="font-mono text-blocked">
                {mandate.scope.blocked_categories.join(", ")}
              </span>
            </Field>
          </div>
        </section>

        {/* Stats panel — FR-DSH-2 */}
        <section className="rounded-lg border border-white/10 bg-panel p-5">
          <h2 className="mb-3 text-sm uppercase tracking-widest text-white/50">
            Session Statistics
          </h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded border border-approved/30 p-3 text-center">
              <div className="font-mono text-3xl font-semibold text-approved">
                {stats.approved_count}
              </div>
              <div className="text-xs uppercase tracking-widest text-white/50">
                Approved
              </div>
            </div>
            <div className="rounded border border-blocked/30 p-3 text-center">
              <div className="font-mono text-3xl font-semibold text-blocked">
                {stats.blocked_count}
              </div>
              <div className="text-xs uppercase tracking-widest text-white/50">
                Blocked
              </div>
            </div>
            <div className="rounded border border-white/10 p-3 text-center">
              <div className="font-mono text-3xl font-semibold">
                {fmtINR(stats.total_spend_inr)}
              </div>
              <div className="text-xs uppercase tracking-widest text-white/50">
                Spend
              </div>
            </div>
          </div>

          <div className="mt-5">
            <div className="mb-1 flex justify-between font-mono text-sm">
              <span>
                {fmtINR(stats.total_spend_inr)} of {fmtINR(stats.cumulative_limit_inr)}
              </span>
              <span>{pct.toFixed(0)}%</span>
            </div>
            <div className="h-3 w-full overflow-hidden rounded bg-white/10">
              <div
                className={`h-full transition-all duration-500 ${
                  pct >= 100 ? "bg-blocked" : "bg-approved"
                }`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        </section>

        {/* Audit ledger — FR-DSH-3 */}
        <section className="rounded-lg border border-white/10 bg-panel p-5">
          <h2 className="mb-3 text-sm uppercase tracking-widest text-white/50">
            Audit Ledger
          </h2>
          {audit_log.length === 0 ? (
            <p className="font-mono text-white/40">No transactions yet.</p>
          ) : (
            <ul className="space-y-2">
              {audit_log.map((entry, i) => (
                <li
                  key={`${entry.timestamp}-${i}`}
                  className="flex items-center gap-4 rounded border border-white/5 bg-white/[0.02] p-3"
                >
                  <AuditStamp approved={entry.decision.approved} />
                  <div className="flex-1">
                    <div className="font-mono text-sm">
                      {entry.tool_call.args.items
                        .map((it) => `${it.name} ×${it.qty}`)
                        .join(", ")}
                    </div>
                    <div className="font-mono text-xs text-white/50">
                      [{entry.decision.code}] {entry.decision.reason}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-sm">
                      {fmtINR(entry.tool_call.args.amount_inr)}
                    </div>
                    <div className="font-mono text-xs text-white/40">
                      {new Date(entry.timestamp).toLocaleTimeString("en-IN")}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-widest text-white/40">{label}</div>
      <div className="text-sm">{children}</div>
    </div>
  );
}