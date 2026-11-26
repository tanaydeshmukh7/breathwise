"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Info, PlusCircle, TrendingUp } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AppShell } from "@/components/layout/AppShell";
import {
  AuthPromptCard,
  LoadingCard,
  UnavailableBanner,
} from "@/components/ui/Primitives";
import { useBreatheWise } from "@/hooks/useBreatheWise";
import { api } from "@/lib/api";
import { ImpactSummary } from "@/types";

interface CatalogItem {
  action_type: string;
  category: string;
  default_label: string;
  unit: string;
  kg_co2e_per_unit: number | null;
  basis: string;
}

export default function ImpactPage() {
  const { token } = useBreatheWise();
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [methodologyNote, setMethodologyNote] = useState("");
  const [summary, setSummary] = useState<ImpactSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedType, setSelectedType] = useState("walk_cycle_km");
  const [actionName, setActionName] = useState(
    "Walked or cycled instead of driving a car"
  );
  const [quantity, setQuantity] = useState("4");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api
      .getImpactCatalog()
      .then((res) => {
        setCatalog(res.actions);
        setMethodologyNote(res.methodology_note);
      })
      .catch(() => {});
  }, []);

  const loadSummary = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.getImpactSummary(token);
      setSummary(res);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load impact summary."
      );
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const handleSelectType = (actionType: string) => {
    setSelectedType(actionType);
    const found = catalog.find((c) => c.action_type === actionType);
    if (found) setActionName(found.default_label);
  };

  const handleLog = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    const found = catalog.find((c) => c.action_type === selectedType);
    setSubmitting(true);
    try {
      await api.logImpactAction(
        {
          category: found?.category || "transportation",
          action_type: selectedType,
          action_name: actionName,
          quantity: Math.max(0.1, Number(quantity) || 1),
        },
        token
      );
      await loadSummary();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to log action.");
    } finally {
      setSubmitting(false);
    }
  };

  const activeFactor = catalog.find((c) => c.action_type === selectedType);

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-2.5">
            <TrendingUp className="h-6 w-6 text-bw-accent" />
            Personal Impact Tracker
          </h1>
          <p className="text-sm text-bw-muted mt-1">
            Track sustainable daily decisions and factor-based CO2e avoidance estimates
          </p>
        </div>

        {!token ? (
          <AuthPromptCard
            title="Sign in to persist your Personal Impact Tracker"
            description="Your logged metro commutes, cycling distance, and household energy actions are saved per account in MongoDB Atlas."
          />
        ) : (
          <>
            {error && (
              <UnavailableBanner
                title="Impact Tracker Error"
                message={error}
                onRetry={loadSummary}
              />
            )}

            {loading && !summary ? (
              <LoadingCard lines={5} />
            ) : (
              summary && (
                <>
                  <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                    {[
                      {
                        label: "Actions Completed",
                        value: summary.total_actions,
                        unit: "logged",
                      },
                      {
                        label: "Est. Emissions Avoided",
                        value: summary.total_estimated_co2e_avoided_kg,
                        unit: "kg CO2e (est.)",
                      },
                      {
                        label: "Public Transport",
                        value: summary.public_transport_km,
                        unit: "km",
                      },
                      {
                        label: "Walking & Cycling",
                        value: summary.walk_cycle_km,
                        unit: "km",
                      },
                      {
                        label: "Energy Saved",
                        value: summary.energy_saved_kwh,
                        unit: "kWh",
                      },
                    ].map((stat) => (
                      <div
                        key={stat.label}
                        className="bw-surface rounded-2xl p-4 space-y-1"
                      >
                        <span className="text-xs text-bw-muted block">
                          {stat.label}
                        </span>
                        <span className="font-mono text-2xl font-semibold text-bw-text block">
                          {stat.value}
                        </span>
                        <span className="text-[11px] text-bw-teal">
                          {stat.unit}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="grid lg:grid-cols-12 gap-6">
                    {/* Log Action Form */}
                    <form
                      onSubmit={handleLog}
                      className="lg:col-span-5 bw-surface rounded-2xl p-6 space-y-4"
                    >
                      <h2 className="text-base font-semibold flex items-center gap-2">
                        <PlusCircle className="h-4 w-4 text-bw-accent" />
                        Log Sustainable Action
                      </h2>

                      <div className="space-y-1.5">
                        <label
                          htmlFor="impact-action-type"
                          className="text-xs text-bw-muted block"
                        >
                          Action Type
                        </label>
                        <select
                          id="impact-action-type"
                          value={selectedType}
                          onChange={(e) => handleSelectType(e.target.value)}
                          className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-xs text-bw-text"
                        >
                          {catalog.map((c) => (
                            <option key={c.action_type} value={c.action_type}>
                              [{c.category}] {c.default_label}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="space-y-1.5">
                        <label
                          htmlFor="impact-action-name"
                          className="text-xs text-bw-muted block"
                        >
                          Description
                        </label>
                        <input
                          id="impact-action-name"
                          type="text"
                          value={actionName}
                          onChange={(e) => setActionName(e.target.value)}
                          required
                          className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-xs text-bw-text"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <label
                          htmlFor="impact-quantity"
                          className="text-xs text-bw-muted block"
                        >
                          Quantity ({activeFactor?.unit || "units"})
                        </label>
                        <input
                          id="impact-quantity"
                          type="number"
                          step="0.1"
                          min="0.1"
                          value={quantity}
                          onChange={(e) => setQuantity(e.target.value)}
                          required
                          className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-xs font-mono text-bw-text"
                        />
                      </div>

                      {activeFactor && (
                        <p className="text-[11px] text-bw-muted bg-bw-secondary border border-white/[0.06] rounded-lg p-3">
                          {activeFactor.basis}
                        </p>
                      )}

                      <button
                        type="submit"
                        disabled={submitting}
                        className="w-full py-2.5 rounded-xl bg-bw-accent text-bw-bg text-sm font-semibold hover:opacity-90 disabled:opacity-50"
                      >
                        {submitting ? "Logging..." : "Log Action"}
                      </button>
                    </form>

                    {/* Weekly Progress Chart */}
                    <div className="lg:col-span-7 bw-surface rounded-2xl p-6 space-y-4">
                      <div>
                        <h2 className="text-base font-semibold">
                          7-Day Action & CO2e Estimate Trend
                        </h2>
                        <p className="text-xs text-bw-muted">
                          {summary.disclaimer}
                        </p>
                      </div>

                      <div className="h-64 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={summary.weekly_progress}>
                            <CartesianGrid
                              stroke="rgba(244,247,243,0.06)"
                              strokeDasharray="3 3"
                              vertical={false}
                            />
                            <XAxis
                              dataKey="date"
                              stroke="#8F9B91"
                              tick={{ fontSize: 11 }}
                            />
                            <YAxis stroke="#8F9B91" tick={{ fontSize: 11 }} />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: "#111915",
                                border: "1px solid rgba(244,247,243,0.12)",
                                borderRadius: "10px",
                                fontSize: "12px",
                              }}
                            />
                            <Bar
                              dataKey="estimated_co2e_kg"
                              name="Est. kg CO2e avoided"
                              fill="#B7F36B"
                              radius={[6, 6, 0, 0]}
                            />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>

                  {/* Recent Actions Table */}
                  <div className="bw-surface rounded-2xl p-6 space-y-4">
                    <h2 className="text-base font-semibold">
                      Recent Logged Actions
                    </h2>
                    {summary.actions.length === 0 ? (
                      <p className="text-xs text-bw-muted">
                        No actions logged yet. Add your first sustainable action
                        on the left.
                      </p>
                    ) : (
                      <div className="space-y-2.5">
                        {summary.actions.map((act) => (
                          <div
                            key={act.id}
                            className="rounded-xl bg-bw-secondary border border-white/[0.06] p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                          >
                            <div>
                              <span className="text-[10px] uppercase tracking-wider text-bw-teal font-semibold">
                                {act.category}
                              </span>
                              <p className="text-sm font-medium text-bw-text">
                                {act.action_name}
                              </p>
                              <p className="text-[11px] text-bw-muted">
                                {act.calculation_basis}
                              </p>
                            </div>
                            <div className="text-right font-mono text-xs shrink-0">
                              <span className="text-bw-text block">
                                {act.quantity} {act.unit}
                              </span>
                              <span className="text-bw-accent">
                                {act.estimated_co2e_avoided_kg !== null
                                  ? `~${act.estimated_co2e_avoided_kg} kg CO2e (est.)`
                                  : "Qualitative impact"}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )
            )}
          </>
        )}

        {methodologyNote && (
          <p className="text-xs text-bw-muted flex items-center gap-1.5">
            <Info className="h-3.5 w-3.5 text-bw-teal shrink-0" />
            {methodologyNote}
          </p>
        )}
      </div>
    </AppShell>
  );
}
