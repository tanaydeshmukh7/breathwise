"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Leaf, RefreshCw } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import {
  AiSourceBadge,
  LoadingCard,
  UnavailableBanner,
} from "@/components/ui/Primitives";
import { useBreatheWise } from "@/hooks/useBreatheWise";
import { api } from "@/lib/api";
import { AIResponseEnvelope, StructuredSustainableOutput } from "@/types";

const CATEGORIES = [
  { key: "all", label: "All Categories" },
  { key: "transportation", label: "Transportation" },
  { key: "energy", label: "Energy" },
  { key: "household", label: "Household" },
  { key: "shopping", label: "Shopping" },
  { key: "waste", label: "Waste" },
  { key: "community", label: "Community" },
];

export default function SustainablePage() {
  const { token, location, householdContext, selectedModel, modelsLoaded, airQuality } =
    useBreatheWise();
  const [category, setCategory] = useState("all");
  const [data, setData] =
    useState<AIResponseEnvelope<StructuredSustainableOutput> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAlternatives = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.generateSustainableAlternatives(
        {
          location_name: airQuality?.location.name || location.name,
          latitude: airQuality?.location.latitude || location.latitude,
          longitude: airQuality?.location.longitude || location.longitude,
          household_context: householdContext,
          focus_category: category,
          model_id: selectedModel || undefined,
        },
        token
      );
      setData(res);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load sustainable alternatives."
      );
    } finally {
      setLoading(false);
    }
  }, [
    airQuality?.location.latitude,
    airQuality?.location.longitude,
    airQuality?.location.name,
    category,
    householdContext,
    location.latitude,
    location.longitude,
    location.name,
    selectedModel,
    token,
  ]);

  useEffect(() => {
    if (!modelsLoaded) return;
    loadAlternatives();
  }, [loadAlternatives, modelsLoaded]);

  const displayed =
    data?.result.alternatives.filter(
      (item) => category === "all" || item.category === category
    ) || [];

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold flex items-center gap-2.5">
              <Leaf className="h-6 w-6 text-bw-accent" />
              Sustainable Alternatives
            </h1>
            <p className="text-sm text-bw-muted mt-1">
              High-leverage urban lifestyle shifts for{" "}
              {airQuality?.location.name || location.name} — without fabricated
              savings claims
            </p>
          </div>
          <button
            type="button"
            onClick={loadAlternatives}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-bw-secondary border border-white/10 text-xs font-medium hover:border-white/25 self-start"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}
              aria-hidden="true"
            />
            Refresh Suggestions
          </button>
        </div>

        <div
          role="group"
          aria-label="Filter alternatives by category"
          className="flex flex-wrap gap-2"
        >
          {CATEGORIES.map((c) => (
            <button
              key={c.key}
              type="button"
              aria-pressed={category === c.key}
              onClick={() => setCategory(c.key)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                category === c.key
                  ? "bg-bw-accent text-bw-bg border-bw-accent font-semibold"
                  : "bg-bw-secondary border-white/10 text-bw-muted hover:text-bw-text"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {error && (
          <UnavailableBanner
            title="Unable to Load Alternatives"
            message={error}
            onRetry={loadAlternatives}
          />
        )}

        {loading ? (
          <LoadingCard lines={6} />
        ) : (
          data && (
            <div className="space-y-5">
              <div className="bw-surface rounded-2xl p-5 space-y-3">
                <p className="text-sm text-bw-text">{data.result.summary}</p>
                <AiSourceBadge
                  aiStatus={data.ai_status}
                  modelUsed={data.model_used}
                  provider={data.provider}
                  fallbackReason={data.fallback_reason}
                />
              </div>

              <div className="grid md:grid-cols-2 gap-5">
                {displayed.map((alt, idx) => (
                  <div
                    key={idx}
                    className="bw-surface rounded-2xl p-5 space-y-3 flex flex-col justify-between"
                  >
                    <div className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[11px] uppercase tracking-wider font-semibold text-bw-teal">
                          {alt.category}
                        </span>
                        <span
                          className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${
                            alt.practical_difficulty === "easy"
                              ? "border-bw-teal/40 text-bw-teal bg-bw-teal/10"
                              : alt.practical_difficulty === "moderate"
                              ? "border-bw-warning/40 text-bw-warning bg-bw-warning/10"
                              : "border-bw-danger/40 text-bw-danger bg-bw-danger/10"
                          }`}
                        >
                          {alt.practical_difficulty}
                        </span>
                      </div>

                      <div className="rounded-xl bg-bw-secondary border border-white/[0.06] p-3 text-xs">
                        <span className="text-bw-muted block">Current habit</span>
                        <span className="text-bw-text mt-0.5 block">
                          {alt.current_behavior}
                        </span>
                      </div>

                      <div className="rounded-xl bg-bw-accent/10 border border-bw-accent/25 p-3 text-xs">
                        <span className="text-bw-accent font-medium block">
                          Suggested alternative
                        </span>
                        <span className="text-bw-text font-semibold mt-0.5 block">
                          {alt.suggested_alternative}
                        </span>
                      </div>

                      <p className="text-xs text-bw-muted leading-relaxed">
                        <strong className="text-bw-text font-medium">
                          Why it matters:{" "}
                        </strong>
                        {alt.why_it_matters}
                      </p>
                    </div>

                    <p className="text-xs text-bw-teal border-t border-white/[0.06] pt-3">
                      {alt.potential_benefit}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )
        )}
      </div>
    </AppShell>
  );
}
