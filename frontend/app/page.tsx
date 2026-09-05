"use client";

import { useCallback, useEffect, useState } from "react";
import type { ApiState, Catalog } from "./types";

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
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [selectedSku, setSelectedSku] = useState<string>("");
  const [quantity, setQuantity] = useState<number>(1);
  const [error, setError] = useState<string | null>(null);
  const [revoking, setRevoking] = useState<boolean>(false);
  const [resetting, setResetting] = useState<boolean>(false);
  const [purchasing, setPurchasing] = useState<boolean>(false);
  const [lastResult, setLastResult] = useState<{
    ok: boolean;
    message: string;
    code?: string;
  } | null>(null);

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

  // Fetch product catalog once on load (FR-CAT-1)
  useEffect(() => {
    fetch(`${API_URL}/api/catalog`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data: Catalog | null) => {
        if (data && data.products.length > 0) {
          setCatalog(data);
          setSelectedSku(data.products[0].sku);
        }
      })
      .catch((err) => console.error("Failed to load catalog:", err));
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

  const resetState = async () => {
    setResetting(true);
    try {
      await fetch(`${API_URL}/api/reset`, { method: "POST" });
      setLastResult(null);
      await loadState();
    } catch (e) {
      console.error("Failed to reset:", e);
    } finally {
      setResetting(false);
    }
  };

  const executePurchase = async (
    skuQtyPairs: [string, number][],
    merchantId?: string
  ) => {
    setPurchasing(true);
    setLastResult(null);
    try {
      const targetMerchant =
        merchantId ?? catalog?.merchant_id ?? "amart-grocers-001";
      const res = await fetch(`${API_URL}/api/purchase`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sku_qty_pairs: skuQtyPairs,
          merchant_id: targetMerchant,
        }),
      });
      const data = await res.json();
      setLastResult({
        ok: data.ok,
        message: data.message,
        code: data.code,
      });
      await loadState();
    } catch (e) {
      setLastResult({
        ok: false,
        message:
          e instanceof Error ? e.message : "Failed to execute purchase",
      });
    } finally {
      setPurchasing(false);
    }
  };

  const handleManualPurchase = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSku || quantity < 1) return;
    executePurchase([[selectedSku, quantity]]);
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
      ? Math.min(
          100,
          (stats.total_spend_inr / stats.cumulative_limit_inr) * 100
        )
      : 0;

  const currentProduct = catalog?.products.find((p) => p.sku === selectedSku);
  const currentTotal = (currentProduct?.price_inr ?? 0) * quantity;

  const DEMO_PRESETS = [
    {
      title: "1. Normal grocery order",
      badge: "In-Mandate",
      desc: "Basmati Rice 1kg × 2 (₹360)",
      expected: "Expected: Approved",
      expectedColor: "text-approved border-approved/40 bg-approved/10",
      action: () => executePurchase([["RICE-BASMATI-1KG", 2]]),
    },
    {
      title: "2. Try to buy a gift card",
      badge: "Prompt Injection",
      desc: "Amazon Gift Card ₹500 × 1 (₹500)",
      expected: "Expected: Blocked [SCOPE_CATEGORY]",
      expectedColor: "text-blocked border-blocked/40 bg-blocked/10",
      action: () => executePurchase([["GC-AMAZON-500", 1]]),
    },
    {
      title: "3. Exceed the limit",
      badge: "Cap Overrun",
      desc: "Shimla Apples 1kg × 6 (₹1,260 > ₹1,000 cap)",
      expected: "Expected: Blocked [Z8]",
      expectedColor: "text-amber border-amber/40 bg-amber/10",
      action: () => executePurchase([["APPLE-SHIMLA-1KG", 6]]),
    },
    {
      title: "4. Unrecognized SKU injection",
      badge: "Tamper Defense",
      desc: "Unknown SKU (HACK-PAYLOAD-99) × 1",
      expected: "Expected: Blocked [UNKNOWN_SKU]",
      expectedColor: "text-purple-400 border-purple-400/40 bg-purple-400/10",
      action: () => executePurchase([["HACK-PAYLOAD-99", 1]]),
    },
  ];

  return (
    <main className="min-h-screen bg-ink px-6 py-8 font-sans text-white">
      <div className="mx-auto max-w-5xl space-y-6">
        {/* Header */}
        <header className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Agentic Guard</h1>
            <p className="text-sm text-white/50">
              Mandate-Bounded Risk Interceptor
            </p>
          </div>
          {/* Action buttons: Reset state & Revoke Access */}
          <div className="flex items-center gap-3">
            <button
              onClick={resetState}
              disabled={resetting}
              className="border border-white/20 px-3 py-2 text-xs font-mono text-white/70 hover:text-white hover:border-white/40 transition rounded"
              title="Reset mandate status to Active and clear session stats"
            >
              {resetting ? "Resetting…" : "↺ Reset State"}
            </button>
            <button
              onClick={revoke}
              disabled={!isActive || revoking}
              className={`border px-4 py-2 font-medium transition rounded ${
                isActive
                  ? "border-amber text-amber hover:bg-amber/10"
                  : "border-white/20 text-white/40 cursor-not-allowed"
              }`}
            >
              {isActive ? "Revoke Access" : "Access Revoked"}
            </button>
          </div>
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
              <span className="font-mono">
                {fmtINR(mandate.limits.max_per_transaction)}
              </span>
            </Field>
            <Field label="Cumulative Limit">
              <span className="font-mono">
                {fmtINR(mandate.limits.max_cumulative)}
              </span>
            </Field>
            <Field label="Cumulative Window">
              <span className="font-mono">
                {mandate.limits.cumulative_window_hours}h
              </span>
            </Field>
            <Field label="Velocity Limit">
              <span className="font-mono">
                {mandate.limits.max_attempts_per_minute}/min
              </span>
            </Field>
            <Field label="Allowed MCC">
              <span className="font-mono">
                {mandate.scope.allowed_mcc.join(", ")}
              </span>
            </Field>
            <Field label="Allowed Merchants">
              <span className="font-mono">
                {mandate.scope.allowed_merchants.join(", ")}
              </span>
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
                {fmtINR(stats.total_spend_inr)} of{" "}
                {fmtINR(stats.cumulative_limit_inr)}
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

        {/* Purchase Trigger & Pitch Demo Presets Panel */}
        <section className="rounded-lg border border-white/10 bg-panel p-5 space-y-5">
          <div>
            <h2 className="text-sm uppercase tracking-widest text-white/50">
              Simulate Purchase Intent
            </h2>
            <p className="text-xs text-white/40 mt-0.5">
              Trigger agent tool calls against the deterministic Risk Manager
              interceptor.
            </p>
          </div>

          {/* Form & Presets Grid */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            {/* Manual Form */}
            <form
              onSubmit={handleManualPurchase}
              className="md:col-span-6 flex flex-col justify-between space-y-4 border border-white/10 bg-white/[0.02] p-4 rounded-md"
            >
              <div className="space-y-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-white/70">
                  Custom Purchase
                </div>
                <div>
                  <label className="block text-xs uppercase tracking-widest text-white/40 mb-1">
                    Select Product
                  </label>
                  <select
                    value={selectedSku}
                    onChange={(e) => setSelectedSku(e.target.value)}
                    disabled={!isActive || purchasing}
                    className="w-full rounded border border-white/20 bg-ink px-3 py-2 text-sm text-white font-mono focus:border-amber focus:outline-none disabled:opacity-50"
                  >
                    {catalog?.products.map((p) => (
                      <option key={p.sku} value={p.sku}>
                        {p.name} — {fmtINR(p.price_inr)} ({p.category})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3 items-end">
                  <div>
                    <label className="block text-xs uppercase tracking-widest text-white/40 mb-1">
                      Quantity
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={99}
                      value={quantity}
                      onChange={(e) =>
                        setQuantity(Math.max(1, parseInt(e.target.value) || 1))
                      }
                      disabled={!isActive || purchasing}
                      className="w-full rounded border border-white/20 bg-ink px-3 py-2 text-sm text-white font-mono focus:border-amber focus:outline-none disabled:opacity-50"
                    />
                  </div>
                  <div className="pb-2 text-sm font-mono text-white/70">
                    Total:{" "}
                    <span className="text-white font-semibold">
                      {fmtINR(currentTotal)}
                    </span>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={!isActive || purchasing || !selectedSku}
                className={`w-full rounded border py-2.5 font-medium transition ${
                  isActive && !purchasing
                    ? "border-approved text-approved hover:bg-approved/10"
                    : "border-white/20 text-white/40 cursor-not-allowed"
                }`}
              >
                {purchasing ? "Evaluating..." : "Purchase"}
              </button>
            </form>

            {/* Pitch Demo Presets */}
            <div className="md:col-span-6 flex flex-col justify-between space-y-3">
              <div className="text-xs font-semibold uppercase tracking-wider text-white/70">
                Preset Demo Scenarios
              </div>
              <div className="space-y-2.5">
                {DEMO_PRESETS.map((preset, i) => (
                  <button
                    key={i}
                    onClick={preset.action}
                    disabled={!isActive || purchasing}
                    className="w-full text-left rounded border border-white/10 bg-white/[0.02] hover:bg-white/[0.06] p-3 transition disabled:opacity-40 disabled:cursor-not-allowed group"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-white group-hover:text-amber transition">
                        {preset.title}
                      </span>
                      <span
                        className={`text-[10px] uppercase font-mono px-1.5 py-0.5 border rounded ${preset.expectedColor}`}
                      >
                        {preset.badge}
                      </span>
                    </div>
                    <div className="flex items-center justify-between font-mono text-xs text-white/50">
                      <span>{preset.desc}</span>
                      <span className="text-[11px] text-white/40">
                        {preset.expected}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Inline Purchase Result Banner */}
          {lastResult && (
            <div
              className={`rounded border p-3 font-mono text-xs flex items-start justify-between gap-3 ${
                lastResult.ok
                  ? "border-approved/40 bg-approved/10 text-approved"
                  : "border-blocked/40 bg-blocked/10 text-blocked"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="font-semibold uppercase">
                  {lastResult.ok ? "[APPROVED]" : "[BLOCKED]"}
                </span>
                <span>{lastResult.message}</span>
              </div>
              <button
                onClick={() => setLastResult(null)}
                className="text-white/40 hover:text-white transition text-xs"
              >
                ✕
              </button>
            </div>
          )}
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

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="text-xs uppercase tracking-widest text-white/40">
        {label}
      </div>
      <div className="text-sm">{children}</div>
    </div>
  );
}