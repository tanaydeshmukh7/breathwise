"use client";

import React, { useState } from "react";
import { Bot, Send, ShieldAlert, Sparkles } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { AiSourceBadge, UnavailableBanner } from "@/components/ui/Primitives";
import { useBreatheWise } from "@/hooks/useBreatheWise";
import { api } from "@/lib/api";
import { getActiveIndexInfo } from "@/lib/aqi";
import {
  ADVISOR_SUGGESTED_PROMPTS,
  HOUSEHOLD_CONTEXT_OPTIONS,
} from "@/lib/constants";
import { AIResponseEnvelope, StructuredAdvisorOutput } from "@/types";

interface ChatTurn {
  role: "user" | "assistant";
  text: string;
  envelope?: AIResponseEnvelope<StructuredAdvisorOutput>;
}

export default function AdvisorPage() {
  const {
    user,
    token,
    location,
    aqiStandard,
    householdContext,
    setHouseholdContext,
    selectedModel,
    setSelectedModel,
    availableModels,
    airQuality,
  } = useBreatheWise();

  const [question, setQuestion] = useState("");
  const [lifestyleNotes, setLifestyleNotes] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeIdx = getActiveIndexInfo(airQuality, aqiStandard);

  const sendQuestion = async (promptText: string) => {
    const trimmed = promptText.trim();
    if (!trimmed || loading) return;
    setError(null);
    setTurns((prev) => [...prev, { role: "user", text: trimmed }]);
    setQuestion("");
    setLoading(true);
    try {
      const res = await api.chatAdvisor(
        {
          message: trimmed,
          conversation_id: conversationId,
          location_name: airQuality?.location.name || location.name,
          latitude: airQuality?.location.latitude || location.latitude,
          longitude: airQuality?.location.longitude || location.longitude,
          household_context: householdContext,
          lifestyle_notes: lifestyleNotes,
          has_air_purifier: user?.has_air_purifier || false,
          model_id: selectedModel,
        },
        token
      );
      if (res.conversation_id) setConversationId(res.conversation_id);
      setTurns((prev) => [
        ...prev,
        { role: "assistant", text: res.result.summary, envelope: res },
      ]);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to reach AI Air Advisor."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <div className="grid lg:grid-cols-12 gap-6">
        {/* Left Context & Model Panel */}
        <aside className="lg:col-span-4 space-y-4">
          <div className="bw-surface rounded-2xl p-5 space-y-4">
            <div className="flex items-center gap-2.5">
              <div className="h-9 w-9 rounded-lg bg-bw-accent/15 border border-bw-accent/30 flex items-center justify-center text-bw-accent">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-base font-semibold">AI Air Advisor</h1>
                <p className="text-xs text-bw-muted">
                  Grounded Gemini environmental guidance
                </p>
              </div>
            </div>

            <div className="rounded-xl bg-bw-secondary border border-white/10 p-3.5 text-xs space-y-1">
              <span className="text-bw-muted">Live Context Passed to Model</span>
              <p className="font-semibold text-bw-text">
                {airQuality?.location.name || location.name} · {activeIdx.methodology}:{" "}
                <span className="font-mono text-bw-accent">
                  {activeIdx.value ?? "N/A"}
                </span>{" "}
                ({activeIdx.category})
              </p>
              <p className="text-bw-muted">
                PM2.5: {airQuality?.pollutants.pm2_5.value ?? "—"} μg/m³ · PM10:{" "}
                {airQuality?.pollutants.pm10.value ?? "—"} μg/m³
              </p>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="advisor-household-context"
                className="text-xs font-medium text-bw-muted block"
              >
                Household Context
              </label>
              <select
                id="advisor-household-context"
                value={householdContext}
                onChange={(e) =>
                  setHouseholdContext(e.target.value as typeof householdContext)
                }
                className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-xs text-bw-text"
              >
                {HOUSEHOLD_CONTEXT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="advisor-ai-model"
                className="text-xs font-medium text-bw-muted block"
              >
                AI Model
              </label>
              <select
                id="advisor-ai-model"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-xs font-mono text-bw-text"
              >
                {availableModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="advisor-lifestyle-notes"
                className="text-xs font-medium text-bw-muted block"
              >
                Lifestyle Preferences (Optional)
              </label>
              <textarea
                id="advisor-lifestyle-notes"
                rows={2}
                value={lifestyleNotes}
                onChange={(e) => setLifestyleNotes(e.target.value)}
                placeholder="e.g., 2-year-old toddler, 20-min metro commute, morning runner"
                className="w-full rounded-xl bg-bw-bg border border-white/10 px-3 py-2 text-xs text-bw-text placeholder:text-bw-muted"
              />
            </div>

            <div className="space-y-2 pt-2 border-t border-white/[0.06]">
              <p className="text-[11px] uppercase tracking-wider text-bw-muted">
                Suggested Questions
              </p>
              <div className="flex flex-col gap-1.5">
                {ADVISOR_SUGGESTED_PROMPTS.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => sendQuestion(p)}
                    disabled={loading}
                    className="text-left text-xs px-3 py-2 rounded-lg bg-bw-secondary hover:bg-bw-card border border-white/5 text-bw-text transition-colors disabled:opacity-50"
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </aside>

        {/* Right Conversation Area */}
        <section className="lg:col-span-8 bw-surface rounded-2xl p-5 sm:p-6 flex flex-col min-h-[600px]">
          <div className="flex-1 space-y-5 overflow-y-auto pr-1">
            {turns.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center py-16 space-y-3">
                <Sparkles className="h-8 w-8 text-bw-accent" />
                <h2 className="text-lg font-semibold">
                  Ask BreatheWise about today&apos;s air
                </h2>
                <p className="text-xs text-bw-muted max-w-md leading-relaxed">
                  Every answer uses live Open-Meteo pollutant & weather data for{" "}
                  {airQuality?.location.name || location.name}, validates structured
                  JSON recommendations with Pydantic, and never invents readings.
                </p>
              </div>
            )}

            {turns.map((turn, idx) => (
              <div
                key={idx}
                className={
                  turn.role === "user" ? "flex justify-end" : "space-y-3"
                }
              >
                {turn.role === "user" ? (
                  <div className="max-w-lg rounded-2xl rounded-tr-sm bg-bw-accent/15 border border-bw-accent/30 px-4 py-3 text-sm text-bw-text">
                    {turn.text}
                  </div>
                ) : (
                  turn.envelope && (
                    <div className="rounded-2xl bg-bw-secondary border border-white/10 p-5 space-y-4">
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <span className="text-xs font-semibold text-bw-teal uppercase tracking-wider">
                          Advisor Assessment
                        </span>
                        <span className="text-[11px] font-mono uppercase px-2 py-0.5 rounded bg-bw-card border border-white/10">
                          Risk: {turn.envelope.result.risk_level}
                        </span>
                      </div>

                      <p className="text-sm text-bw-text leading-relaxed">
                        {turn.envelope.result.summary}
                      </p>

                      {turn.envelope.result.best_outdoor_window && (
                        <div className="rounded-lg bg-bw-bg/70 border border-white/10 px-3 py-2 text-xs">
                          <span className="text-bw-muted">Suggested window: </span>
                          <span className="text-bw-teal font-medium">
                            {turn.envelope.result.best_outdoor_window}
                          </span>
                        </div>
                      )}

                      <div className="grid sm:grid-cols-2 gap-3">
                        {turn.envelope.result.recommendations.map((rec, rIdx) => (
                          <div
                            key={rIdx}
                            className="rounded-xl bg-bw-card/70 border border-white/[0.07] p-3.5 space-y-1.5"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-xs font-semibold text-bw-text">
                                {rec.title}
                              </span>
                              <span
                                className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
                                  rec.priority === "high"
                                    ? "bg-bw-danger/15 text-bw-danger"
                                    : rec.priority === "medium"
                                    ? "bg-bw-warning/15 text-bw-warning"
                                    : "bg-bw-teal/15 text-bw-teal"
                                }`}
                              >
                                {rec.priority}
                              </span>
                            </div>
                            <p className="text-[11px] text-bw-muted">{rec.reason}</p>
                            <p className="text-xs text-bw-accent font-medium">
                              {rec.action}
                            </p>
                          </div>
                        ))}
                      </div>

                      <AiSourceBadge
                        aiStatus={turn.envelope.ai_status}
                        modelUsed={turn.envelope.model_used}
                        fallbackReason={turn.envelope.fallback_reason}
                      />

                      <p className="text-[11px] text-bw-muted flex items-center gap-1.5">
                        <ShieldAlert className="h-3.5 w-3.5 shrink-0" />
                        {turn.envelope.result.precautionary_note}
                      </p>
                    </div>
                  )
                )}
              </div>
            ))}

            {loading && (
              <div
                role="status"
                aria-live="polite"
                className="rounded-xl bg-bw-secondary border border-white/10 p-4 text-xs text-bw-muted animate-pulse"
              >
                Querying {selectedModel} with verified environmental snapshot...
              </div>
            )}
          </div>

          {error && (
            <div className="mt-3">
              <UnavailableBanner title="Advisor Error" message={error} />
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendQuestion(question);
            }}
            className="mt-4 pt-4 border-t border-white/[0.08] flex gap-2"
          >
            <label htmlFor="advisor-question-input" className="sr-only">
              Ask the Air Quality Advisor
            </label>
            <input
              id="advisor-question-input"
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about outdoor exercise, windows, children, commute..."
              className="flex-1 rounded-xl bg-bw-bg border border-white/10 px-4 py-3 text-sm text-bw-text placeholder:text-bw-muted focus:outline-none focus:border-bw-accent/50"
            />
            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-bw-accent text-bw-bg text-sm font-semibold hover:opacity-90 disabled:opacity-50"
            >
              <Send className="h-4 w-4" aria-hidden="true" />
              <span className="hidden sm:inline">Ask</span>
            </button>
          </form>
        </section>
      </div>
    </AppShell>
  );
}
