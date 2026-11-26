"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  BookmarkPlus,
  CalendarClock,
  Clock,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import {
  AiSourceBadge,
  LoadingCard,
  UnavailableBanner,
} from "@/components/ui/Primitives";
import { useBreatheWise } from "@/hooks/useBreatheWise";
import { api } from "@/lib/api";
import {
  AIResponseEnvelope,
  SavedRoutine,
  StructuredDailyRoutineOutput,
} from "@/types";

export default function RoutinePage() {
  const {
    user,
    token,
    location,
    householdContext,
    selectedModel,
    airQuality,
  } = useBreatheWise();

  const [routineEnv, setRoutineEnv] =
    useState<AIResponseEnvelope<StructuredDailyRoutineOutput> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedRoutines, setSavedRoutines] = useState<SavedRoutine[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const generateRoutine = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSaveMessage(null);
    try {
      const res = await api.generateDailyRoutine(
        {
          location_name: airQuality?.location.name || location.name,
          latitude: airQuality?.location.latitude || location.latitude,
          longitude: airQuality?.location.longitude || location.longitude,
          household_context: householdContext,
          has_air_purifier: user?.has_air_purifier || false,
          model_id: selectedModel,
        },
        token
      );
      setRoutineEnv(res);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to generate daily routine."
      );
    } finally {
      setLoading(false);
    }
  }, [
    airQuality?.location.latitude,
    airQuality?.location.longitude,
    airQuality?.location.name,
    householdContext,
    location.latitude,
    location.longitude,
    location.name,
    selectedModel,
    token,
    user?.has_air_purifier,
  ]);

  const loadSaved = useCallback(async () => {
    if (!token) return;
    try {
      const res = await api.listRoutines(token);
      setSavedRoutines(res.routines);
    } catch {
      // ignore
    }
  }, [token]);

  useEffect(() => {
    generateRoutine();
  }, [generateRoutine]);

  useEffect(() => {
    loadSaved();
  }, [loadSaved]);

  const handleSaveRoutine = async () => {
    if (!token || !routineEnv) return;
    setSaving(true);
    setSaveMessage(null);
    try {
      const city = airQuality?.location.name || location.name;
      await api.createRoutine(
        {
          title: `${city} Smart Routine (${new Date().toLocaleDateString("en-IN")})`,
          location_name: city,
          summary: routineEnv.result.summary,
          optimal_outdoor_window: routineEnv.result.optimal_outdoor_window,
          items: routineEnv.result.slots,
        },
        token
      );
      setSaveMessage("Routine saved to your account.");
      await loadSaved();
    } catch (err) {
      setSaveMessage(
        err instanceof Error ? err.message : "Could not save routine."
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!token) return;
    try {
      await api.deleteRoutine(id, token);
      setSavedRoutines((prev) => prev.filter((r) => r.id !== id));
    } catch {
      // ignore
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold flex items-center gap-2.5">
              <CalendarClock className="h-6 w-6 text-bw-accent" />
              Smart Daily Routine
            </h1>
            <p className="text-sm text-bw-muted mt-1">
              Forecast-driven daily schedule for{" "}
              <span className="text-bw-text font-medium">
                {airQuality?.location.name || location.name}
              </span>
            </p>
          </div>
          <div className="flex items-center gap-2.5">
            <button
              onClick={generateRoutine}
              disabled={loading}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-bw-secondary border border-white/10 text-xs font-medium hover:border-white/25 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Regenerate from Forecast
            </button>
            {token ? (
              <button
                onClick={handleSaveRoutine}
                disabled={saving || !routineEnv}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-bw-accent text-bw-bg text-xs font-semibold hover:opacity-90 disabled:opacity-50"
              >
                <BookmarkPlus className="h-3.5 w-3.5" />
                {saving ? "Saving..." : "Save Routine"}
              </button>
            ) : (
              <Link
                href="/auth"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-bw-accent/15 border border-bw-accent/30 text-bw-accent text-xs font-semibold"
              >
                Sign in to Save
              </Link>
            )}
          </div>
        </div>

        {saveMessage && (
          <div className="rounded-xl border border-bw-teal/30 bg-bw-teal/10 px-4 py-2.5 text-xs text-bw-teal">
            {saveMessage}
          </div>
        )}

        {error && (
          <UnavailableBanner
            title="Unable to Build Forecast Routine"
            message={error}
            onRetry={generateRoutine}
          />
        )}

        {loading ? (
          <LoadingCard lines={6} />
        ) : (
          routineEnv && (
            <div className="bw-surface rounded-2xl p-6 space-y-5">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.07] pb-4">
                <p className="text-sm text-bw-text max-w-2xl leading-relaxed">
                  {routineEnv.result.summary}
                </p>
                <div className="rounded-xl bg-bw-secondary border border-white/10 px-4 py-2.5 text-xs shrink-0">
                  <span className="text-bw-muted block">Optimal Outdoor Window</span>
                  <span className="text-bw-accent font-semibold mt-0.5 block">
                    {routineEnv.result.optimal_outdoor_window}
                  </span>
                </div>
              </div>

              <div className="space-y-3">
                {routineEnv.result.slots.map((slot, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl bg-bw-secondary border border-white/[0.07] p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                  >
                    <div className="flex items-start gap-4">
                      <div className="px-3 py-1.5 rounded-lg bg-bw-card border border-white/10 font-mono text-sm font-semibold text-bw-accent shrink-0 flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" />
                        {slot.time}
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-bw-text">
                            {slot.title}
                          </span>
                          <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-white/5 text-bw-muted">
                            {slot.phase.replace("_", " ")}
                          </span>
                        </div>
                        <p className="text-xs text-bw-muted leading-relaxed">
                          {slot.guidance}
                        </p>
                      </div>
                    </div>
                    <div className="text-xs font-mono text-bw-teal sm:text-right shrink-0">
                      {slot.aqi_context}
                    </div>
                  </div>
                ))}
              </div>

              <AiSourceBadge
                aiStatus={routineEnv.ai_status}
                modelUsed={routineEnv.model_used}
                fallbackReason={routineEnv.fallback_reason}
              />
            </div>
          )
        )}

        {/* Saved Routines List */}
        {token && (
          <div className="bw-surface rounded-2xl p-6 space-y-4">
            <h2 className="text-base font-semibold">Saved Routines</h2>
            {savedRoutines.length === 0 ? (
              <p className="text-xs text-bw-muted">
                No saved routines yet. Click &ldquo;Save Routine&rdquo; above to
                store today&apos;s schedule.
              </p>
            ) : (
              <div className="grid md:grid-cols-2 gap-4">
                {savedRoutines.map((rt) => (
                  <div
                    key={rt.id}
                    className="rounded-xl bg-bw-secondary border border-white/10 p-4 space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="text-sm font-semibold">{rt.title}</h3>
                        <p className="text-xs text-bw-teal">
                          {rt.optimal_outdoor_window}
                        </p>
                      </div>
                      <button
                        onClick={() => handleDelete(rt.id)}
                        className="p-1.5 rounded-lg text-bw-muted hover:text-bw-danger hover:bg-white/5"
                        title="Delete saved routine"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                    <p className="text-xs text-bw-muted">{rt.summary}</p>
                    <p className="text-[11px] font-mono text-bw-muted">
                      {rt.items.length} scheduled slots · {rt.location_name}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
