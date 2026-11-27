"use client";

import React, { useCallback, useEffect, useState } from "react";
import { CheckSquare, Home, Info, RefreshCw, Square } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import {
  AiSourceBadge,
  LoadingCard,
  UnavailableBanner,
} from "@/components/ui/Primitives";
import { useBreatheWise } from "@/hooks/useBreatheWise";
import { api } from "@/lib/api";
import { AIResponseEnvelope, StructuredIndoorOutput } from "@/types";

const DEFAULT_CHECKLIST = [
  "Run kitchen exhaust chimney or fan during all high-heat cooking",
  "Replace dry sweeping with damp microfiber mopping for floor dust",
  "Keep incense, dhoop, and scented candles unlit during smog days",
  "Seal window gaps facing busy roads during rush hour",
  "Check HEPA filter pre-screen and clean accumulated dust",
  "Maintain comfortable 40–60% indoor humidity to limit mold and dust mites",
];

export default function IndoorPage() {
  const { user, token, location, householdContext, selectedModel, modelsLoaded, airQuality } =
    useBreatheWise();

  const [hasPurifier, setHasPurifier] = useState(user?.has_air_purifier || false);
  const [cookingFuel, setCookingFuel] = useState<
    "lpg_induction" | "mixed" | "solid_biomass"
  >("lpg_induction");
  const [usesIncense, setUsesIncense] = useState(false);

  const [advice, setAdvice] =
    useState<AIResponseEnvelope<StructuredIndoorOutput> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checked, setChecked] = useState<Record<number, boolean>>({});

  useEffect(() => {
    if (user) {
      setHasPurifier(user.has_air_purifier);
    }
  }, [user]);

  const fetchAdvice = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.generateIndoorAdvice(
        {
          location_name: airQuality?.location.name || location.name,
          latitude: airQuality?.location.latitude || location.latitude,
          longitude: airQuality?.location.longitude || location.longitude,
          household_context: householdContext,
          has_air_purifier: hasPurifier,
          cooking_fuel: cookingFuel,
          uses_incense_or_dhoop: usesIncense,
          model_id: selectedModel || undefined,
        },
        token
      );
      setAdvice(res);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load indoor guidance."
      );
    } finally {
      setLoading(false);
    }
  }, [
    airQuality?.location.latitude,
    airQuality?.location.longitude,
    airQuality?.location.name,
    cookingFuel,
    hasPurifier,
    householdContext,
    location.latitude,
    location.longitude,
    location.name,
    selectedModel,
    token,
    usesIncense,
  ]);

  useEffect(() => {
    if (!modelsLoaded) return;
    fetchAdvice();
  }, [fetchAdvice, modelsLoaded]);

  const verdictLabel = (v: StructuredIndoorOutput["ventilation_verdict"]) => {
    if (v === "open_windows")
      return { text: "Open Windows for Fresh Air", cls: "text-bw-teal border-bw-teal/40 bg-bw-teal/10" };
    if (v === "brief_cross_ventilation")
      return { text: "Brief Midday Cross-Ventilation Only", cls: "text-bw-warning border-bw-warning/40 bg-bw-warning/10" };
    return { text: "Keep Windows Closed & Filter Indoors", cls: "text-bw-danger border-bw-danger/40 bg-bw-danger/10" };
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold flex items-center gap-2.5">
              <Home className="h-6 w-6 text-bw-teal" />
              Indoor Air Quality Guide
            </h1>
            <p className="text-sm text-bw-muted mt-1">
              Ventilation, filtration & source-control guidance calibrated to outdoor conditions in{" "}
              {airQuality?.location.name || location.name}
            </p>
          </div>
          <button
            onClick={fetchAdvice}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-bw-secondary border border-white/10 text-xs font-medium hover:border-white/25 self-start"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Update Guidance
          </button>
        </div>

        {/* Household Indoor Controls */}
        <div className="bw-surface rounded-2xl p-5 grid sm:grid-cols-3 gap-4 items-center">
          <label className="flex items-center gap-3 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={hasPurifier}
              onChange={(e) => setHasPurifier(e.target.checked)}
              className="h-4 w-4 accent-[#B7F36B]"
            />
            <span>HEPA Air Purifier Available</span>
          </label>

          <label className="flex items-center gap-3 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={usesIncense}
              onChange={(e) => setUsesIncense(e.target.checked)}
              className="h-4 w-4 accent-[#B7F36B]"
            />
            <span>Incense / Dhoop Used Indoors</span>
          </label>

          <div className="flex items-center gap-2">
            <label
              htmlFor="indoor-cooking-fuel"
              className="text-xs text-bw-muted shrink-0"
            >
              Cooking Fuel:
            </label>
            <select
              id="indoor-cooking-fuel"
              value={cookingFuel}
              onChange={(e) =>
                setCookingFuel(e.target.value as typeof cookingFuel)
              }
              className="flex-1 rounded-lg bg-bw-bg border border-white/10 px-2.5 py-1.5 text-xs text-bw-text"
            >
              <option value="lpg_induction">LPG / Electric Induction</option>
              <option value="mixed">Mixed</option>
              <option value="solid_biomass">Solid / Biomass</option>
            </select>
          </div>
        </div>

        {error && (
          <UnavailableBanner
            title="Indoor Guide Unavailable"
            message={error}
            onRetry={fetchAdvice}
          />
        )}

        {loading ? (
          <LoadingCard lines={5} />
        ) : (
          advice && (
            <div className="space-y-6">
              <div className="bw-surface rounded-2xl p-6 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span
                    className={`px-3 py-1.5 rounded-lg border text-xs font-semibold ${
                      verdictLabel(advice.result.ventilation_verdict).cls
                    }`}
                  >
                    {verdictLabel(advice.result.ventilation_verdict).text}
                  </span>
                  <span className="text-xs text-bw-muted flex items-center gap-1.5">
                    <Info className="h-3.5 w-3.5 text-bw-teal" />
                    No indoor sensor connected — guidance derived from outdoor telemetry
                  </span>
                </div>

                <p className="text-sm text-bw-text leading-relaxed">
                  {advice.result.summary}
                </p>

                <div className="grid md:grid-cols-3 gap-4 pt-2">
                  {advice.result.room_guidance.map((room, idx) => (
                    <div
                      key={idx}
                      className="rounded-xl bg-bw-secondary border border-white/10 p-4 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-bw-text">
                          {room.room}
                        </h3>
                        <span className="text-[10px] font-mono uppercase text-bw-teal">
                          {room.priority}
                        </span>
                      </div>
                      <p className="text-xs text-bw-muted">
                        <strong className="text-bw-text font-medium">
                          Ventilation:{" "}
                        </strong>
                        {room.ventilation_action}
                      </p>
                      <p className="text-xs text-bw-muted">
                        <strong className="text-bw-text font-medium">
                          Dust & Filtration:{" "}
                        </strong>
                        {room.filtration_and_dust}
                      </p>
                    </div>
                  ))}
                </div>

                <AiSourceBadge
                  aiStatus={advice.ai_status}
                  modelUsed={advice.model_used}
                  provider={advice.provider}
                  fallbackReason={advice.fallback_reason}
                />

                <p className="text-[11px] text-bw-muted">
                  {advice.result.sensor_disclaimer}
                </p>
              </div>
            </div>
          )
        )}

        {/* Interactive Indoor Air Checklist */}
        <div className="bw-surface rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">
              Daily Indoor Protection Checklist
            </h2>
            <span className="font-mono text-xs text-bw-accent">
              {Object.values(checked).filter(Boolean).length} /{" "}
              {DEFAULT_CHECKLIST.length} completed
            </span>
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            {DEFAULT_CHECKLIST.map((item, idx) => {
              const isDone = !!checked[idx];
              return (
                <button
                  key={idx}
                  type="button"
                  aria-pressed={isDone}
                  onClick={() =>
                    setChecked((prev) => ({ ...prev, [idx]: !prev[idx] }))
                  }
                  className={`text-left rounded-xl border p-3.5 flex items-start gap-3 transition-colors ${
                    isDone
                      ? "bg-bw-accent/10 border-bw-accent/35 text-bw-text"
                      : "bg-bw-secondary border-white/[0.07] text-bw-muted hover:text-bw-text"
                  }`}
                >
                  {isDone ? (
                    <CheckSquare className="h-4 w-4 text-bw-accent shrink-0 mt-0.5" />
                  ) : (
                    <Square className="h-4 w-4 shrink-0 mt-0.5" />
                  )}
                  <span className="text-xs leading-relaxed">{item}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
