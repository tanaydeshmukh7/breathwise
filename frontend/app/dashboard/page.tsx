"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowUpRight,
  Bell,
  Compass,
  Droplets,
  Info,
  RefreshCw,
  Sparkles,
  Thermometer,
  Wind,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AppShell } from "@/components/layout/AppShell";
import {
  AiSourceBadge,
  LoadingCard,
  UnavailableBanner,
} from "@/components/ui/Primitives";
import { useBreatheWise } from "@/hooks/useBreatheWise";
import { api } from "@/lib/api";
import {
  formatHourLabel,
  getActiveIndexInfo,
  getBadgeClasses,
} from "@/lib/aqi";
import { HOUSEHOLD_CONTEXT_OPTIONS } from "@/lib/constants";
import { AIResponseEnvelope, StructuredAdvisorOutput } from "@/types";

export default function DashboardPage() {
  const {
    user,
    token,
    location,
    aqiStandard,
    householdContext,
    setHouseholdContext,
    selectedModel,
    modelsLoaded,
    airQuality,
    forecast,
    weather,
    envLoading,
    envError,
    refreshEnvironment,
  } = useBreatheWise();

  const [chartMetric, setChartMetric] = useState<"aqi" | "pm2_5" | "pm10">("aqi");
  const [chartScope, setChartScope] = useState<"forecast" | "history">("forecast");
  const [analysis, setAnalysis] =
    useState<AIResponseEnvelope<StructuredAdvisorOutput> | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  useEffect(() => {
    if (!airQuality || !modelsLoaded) return;
    let cancelled = false;
    setAnalysisLoading(true);
    setAnalysisError(null);
    api
      .analyzeAir(
        {
          location_name: airQuality.location.name,
          latitude: airQuality.location.latitude,
          longitude: airQuality.location.longitude,
          household_context: householdContext,
          has_air_purifier: user?.has_air_purifier || false,
          model_id: selectedModel || undefined,
        },
        token
      )
      .then((res) => {
        if (!cancelled) setAnalysis(res);
      })
      .catch((err) => {
        if (!cancelled) {
          setAnalysisError(
            err instanceof Error ? err.message : "Failed to generate insight."
          );
        }
      })
      .finally(() => {
        if (!cancelled) setAnalysisLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [airQuality, householdContext, modelsLoaded, selectedModel, token, user?.has_air_purifier]);

  const activeIdx = getActiveIndexInfo(airQuality, aqiStandard);

  const chartData = (() => {
    const series = forecast?.series || [];
    if (chartScope === "history") {
      return series.slice(0, 24).map((p) => ({
        label: formatHourLabel(p.time),
        aqi: aqiStandard === "indian_naqi" ? p.indian_naqi : p.us_aqi,
        pm2_5: p.pm2_5,
        pm10: p.pm10,
      }));
    }
    return series.slice(24, 54).map((p) => ({
      label: formatHourLabel(p.time),
      aqi: aqiStandard === "indian_naqi" ? p.indian_naqi : p.us_aqi,
      pm2_5: p.pm2_5,
      pm10: p.pm10,
    }));
  })();

  const greetingName = user ? user.name.split(" ")[0] : "Neighbor";
  const currentTimeStr = new Date().toLocaleString("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Dashboard Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <p className="text-xs text-bw-muted font-mono">{currentTimeStr}</p>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight mt-1">
              Good day, {greetingName}
            </h1>
            <p className="text-sm text-bw-muted mt-0.5">
              Monitoring{" "}
              <span className="text-bw-text font-medium">
                {airQuality?.location.name || location.name}
              </span>{" "}
              · Environmental & household briefing
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <select
              value={householdContext}
              onChange={(e) =>
                setHouseholdContext(e.target.value as typeof householdContext)
              }
              className="rounded-xl bg-bw-secondary border border-white/10 px-3 py-2 text-xs text-bw-text focus:outline-none focus:border-bw-accent/50"
              aria-label="Household context"
            >
              {HOUSEHOLD_CONTEXT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={refreshEnvironment}
              disabled={envLoading}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-bw-secondary border border-white/10 hover:border-white/25 text-xs font-medium text-bw-text disabled:opacity-50"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${envLoading ? "animate-spin" : ""}`}
                aria-hidden="true"
              />
              Refresh
            </button>

            <Link
              href="/profile"
              className={`relative inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border text-xs transition-colors ${
                (airQuality?.indices.indian_naqi.value ?? 0) >= 150
                  ? "bg-bw-warning/10 border-bw-warning/35 text-bw-warning hover:border-bw-warning/60"
                  : "bg-bw-secondary border-white/10 hover:border-bw-accent/40 text-bw-muted hover:text-bw-text"
              }`}
              title="Notification & Profile Settings"
              aria-label={
                (airQuality?.indices.indian_naqi.value ?? 0) >= 150
                  ? `Elevated air quality alert (${airQuality?.indices.indian_naqi.category}); open profile settings`
                  : "Notification & Profile Settings"
              }
            >
              <Bell className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="hidden sm:inline">Alerts</span>
              {(airQuality?.indices.indian_naqi.value ?? 0) >= 150 && (
                <span
                  aria-hidden="true"
                  className="h-2 w-2 rounded-full bg-bw-warning"
                />
              )}
            </Link>
          </div>
        </div>

        {envError && (
          <UnavailableBanner
            title="Live Environmental Telemetry Unavailable"
            message={envError}
            onRetry={refreshEnvironment}
          />
        )}

        {/* Main AQI + Weather Grid */}
        {envLoading && !airQuality ? (
          <div className="grid lg:grid-cols-12 gap-6">
            <div className="lg:col-span-8">
              <LoadingCard lines={5} />
            </div>
            <div className="lg:col-span-4">
              <LoadingCard lines={5} />
            </div>
          </div>
        ) : (
          airQuality && (
            <div className="grid lg:grid-cols-12 gap-6">
              {/* Main AQI Card */}
              <div className="lg:col-span-8 bw-surface rounded-2xl p-6 space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 text-xs text-bw-muted">
                      <span>{activeIdx.methodology}</span>
                      {activeIdx.dominantPollutant && (
                        <span className="px-2 py-0.5 rounded bg-white/5 text-bw-text font-mono text-[11px]">
                          Lead: {activeIdx.dominantPollutant}
                        </span>
                      )}
                    </div>
                    <div className="flex items-baseline gap-4 mt-2">
                      <span className="font-mono text-5xl font-semibold tracking-tight">
                        {activeIdx.value ?? "N/A"}
                      </span>
                      <span
                        className={`px-3 py-1 rounded-lg border text-xs font-semibold ${getBadgeClasses(
                          activeIdx.color
                        )}`}
                      >
                        {activeIdx.category}
                      </span>
                    </div>
                    {airQuality.indices.indian_naqi.health_implication && (
                      <p className="text-xs text-bw-muted mt-2.5 max-w-xl leading-relaxed">
                        {aqiStandard === "indian_naqi"
                          ? airQuality.indices.indian_naqi.health_implication
                          : `CPCB NAQI advisory note: ${airQuality.indices.indian_naqi.health_implication}`}
                      </p>
                    )}
                  </div>

                  <div className="rounded-xl bg-bw-secondary border border-white/10 px-4 py-3 text-xs space-y-1">
                    <p className="text-bw-muted">
                      {aqiStandard === "indian_naqi"
                        ? "US EPA AQI (for comparison)"
                        : "CPCB Indian NAQI (for comparison)"}
                    </p>
                    <p className="font-mono text-sm font-semibold text-bw-text">
                      {aqiStandard === "indian_naqi"
                        ? `${airQuality.indices.us_aqi.value ?? "N/A"} (${airQuality.indices.us_aqi.category})`
                        : `${airQuality.indices.indian_naqi.value ?? "N/A"} (${airQuality.indices.indian_naqi.category})`}
                    </p>
                  </div>
                </div>

                {/* Raw Pollutant Concentrations */}
                <div>
                  <p className="text-[11px] uppercase tracking-wider text-bw-muted mb-2.5">
                    Raw Pollutant Concentrations (distinct from calculated AQI)
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
                    {[
                      { label: "PM2.5", data: airQuality.pollutants.pm2_5 },
                      { label: "PM10", data: airQuality.pollutants.pm10 },
                      { label: "NO2", data: airQuality.pollutants.nitrogen_dioxide },
                      { label: "O3", data: airQuality.pollutants.ozone },
                      { label: "CO", data: airQuality.pollutants.carbon_monoxide },
                      { label: "SO2", data: airQuality.pollutants.sulphur_dioxide },
                    ].map((item) => (
                      <div
                        key={item.label}
                        className="rounded-xl bg-bw-secondary border border-white/[0.06] p-3"
                      >
                        <span className="text-xs text-bw-muted block">
                          {item.label}
                        </span>
                        <span className="font-mono text-lg font-semibold text-bw-text mt-1 block">
                          {item.data.value !== null ? item.data.value : "—"}
                        </span>
                        <span className="text-[10px] text-bw-muted">
                          {item.data.unit}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2 border-t border-white/[0.06] text-[11px] text-bw-muted">
                  <span className="flex items-center gap-1.5">
                    <Info className="h-3.5 w-3.5 text-bw-teal shrink-0" />
                    {airQuality.data_source} · {airQuality.freshness}
                  </span>
                  {airQuality.missing_fields.length > 0 && (
                    <span className="text-bw-warning">
                      Missing fields: {airQuality.missing_fields.join(", ")}
                    </span>
                  )}
                </div>
              </div>

              {/* Weather Card */}
              <div className="lg:col-span-4 bw-surface rounded-2xl p-6 flex flex-col justify-between space-y-5">
                <div>
                  <span className="text-[11px] uppercase tracking-wider text-bw-muted">
                    Local Weather & Dispersion
                  </span>
                  <div className="flex items-center justify-between mt-3">
                    <div>
                      <p className="font-mono text-4xl font-semibold">
                        {weather?.temperature.value ?? "—"}°C
                      </p>
                      <p className="text-sm text-bw-teal font-medium mt-1">
                        {weather?.condition || "Unavailable"}
                      </p>
                    </div>
                    <Thermometer className="h-9 w-9 text-bw-accent/80" />
                  </div>
                </div>

                <div className="space-y-3 border-t border-white/[0.07] pt-4 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-bw-muted flex items-center gap-2">
                      <Droplets className="h-4 w-4 text-bw-teal" />
                      Relative Humidity
                    </span>
                    <span className="font-mono font-medium">
                      {weather?.humidity.value ?? "—"}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-bw-muted flex items-center gap-2">
                      <Wind className="h-4 w-4 text-bw-accent" />
                      Wind Speed
                    </span>
                    <span className="font-mono font-medium">
                      {weather?.wind.speed ?? "—"}{" "}
                      {weather?.wind.speed_unit || "km/h"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-bw-muted flex items-center gap-2">
                      <Compass className="h-4 w-4 text-bw-muted" />
                      Wind Direction
                    </span>
                    <span className="font-mono font-medium">
                      {weather?.wind.direction_compass || "N/A"} (
                      {weather?.wind.direction_degrees ?? "—"}°)
                    </span>
                  </div>
                </div>

                <p className="text-[11px] text-bw-muted">
                  Low wind speeds (&lt;6 km/h) during cool mornings often trap
                  urban PM2.5 near ground level.
                </p>
              </div>
            </div>
          )
        )}

        {/* Pollution Trend Chart */}
        <div className="bw-surface rounded-2xl p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold">
                Hourly Pollution & Forecast Trend
              </h2>
              <p className="text-xs text-bw-muted">
                {chartScope === "forecast"
                  ? "Upcoming hourly Open-Meteo model forecast"
                  : "Recent 24-hour Open-Meteo historical series"}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex rounded-lg bg-bw-secondary border border-white/10 p-0.5 text-xs">
                {(["forecast", "history"] as const).map((scope) => (
                  <button
                    key={scope}
                    onClick={() => setChartScope(scope)}
                    className={`px-3 py-1 rounded-md capitalize ${
                      chartScope === scope
                        ? "bg-bw-card text-bw-text font-medium"
                        : "text-bw-muted"
                    }`}
                  >
                    {scope}
                  </button>
                ))}
              </div>
              <div className="flex rounded-lg bg-bw-secondary border border-white/10 p-0.5 text-xs">
                {[
                  { key: "aqi", label: aqiStandard === "indian_naqi" ? "IN NAQI" : "US AQI" },
                  { key: "pm2_5", label: "PM2.5" },
                  { key: "pm10", label: "PM10" },
                ].map((m) => (
                  <button
                    key={m.key}
                    onClick={() => setChartMetric(m.key as typeof chartMetric)}
                    className={`px-3 py-1 rounded-md ${
                      chartMetric === m.key
                        ? "bg-bw-accent text-bw-bg font-semibold"
                        : "text-bw-muted"
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="h-72 w-full">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={chartData}
                  margin={{ top: 10, right: 12, left: -12, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="bwAreaGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#B7F36B" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#58D6A0" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    stroke="rgba(244,247,243,0.06)"
                    strokeDasharray="3 3"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="label"
                    stroke="#8F9B91"
                    tick={{ fontSize: 11 }}
                    interval={3}
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
                  <Area
                    type="monotone"
                    dataKey={chartMetric}
                    stroke="#B7F36B"
                    strokeWidth={2}
                    fill="url(#bwAreaGrad)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-bw-muted">
                No hourly trend series available right now.
              </div>
            )}
          </div>
        </div>

        {/* Daily Air Insight + 3 Recommended Actions */}
        {analysisLoading ? (
          <LoadingCard lines={4} />
        ) : analysisError ? (
          <UnavailableBanner
            title="Daily Air Insight Unavailable"
            message={analysisError}
          />
        ) : (
          analysis && (
            <div className="grid lg:grid-cols-12 gap-6">
              <div className="lg:col-span-5 bw-surface rounded-2xl p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-bw-accent uppercase tracking-wider">
                    <Sparkles className="h-3.5 w-3.5" />
                    Daily Air Insight
                  </span>
                  <span className="text-xs px-2.5 py-0.5 rounded bg-bw-secondary border border-white/10 uppercase font-mono">
                    Risk: {analysis.result.risk_level}
                  </span>
                </div>

                <p className="text-sm text-bw-text leading-relaxed">
                  {analysis.result.summary}
                </p>

                {analysis.result.best_outdoor_window && (
                  <div className="rounded-xl bg-bw-secondary border border-white/10 p-3.5 text-xs">
                    <span className="text-bw-muted block">
                      Best Outdoor Window
                    </span>
                    <span className="text-bw-teal font-medium mt-0.5 block">
                      {analysis.result.best_outdoor_window}
                    </span>
                  </div>
                )}

                <AiSourceBadge
                  aiStatus={analysis.ai_status}
                  modelUsed={analysis.model_used}
                  provider={analysis.provider}
                  fallbackReason={analysis.fallback_reason}
                />

                <p className="text-[11px] text-bw-muted flex items-start gap-1.5">
                  <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                  {analysis.result.precautionary_note}
                </p>
              </div>

              <div className="lg:col-span-7 bw-surface rounded-2xl p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-semibold">
                    Recommended Actions Today
                  </h2>
                  <Link
                    href="/advisor"
                    className="inline-flex items-center gap-1 text-xs font-medium text-bw-accent hover:underline"
                  >
                    Ask Advisor <ArrowUpRight className="h-3.5 w-3.5" />
                  </Link>
                </div>

                <div className="space-y-3">
                  {analysis.result.recommendations.slice(0, 3).map((rec, i) => (
                    <div
                      key={i}
                      className="rounded-xl bg-bw-secondary border border-white/[0.07] p-4 space-y-1.5"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="text-sm font-semibold text-bw-text">
                          {rec.title}
                        </h3>
                        <span
                          className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded border ${
                            rec.priority === "high"
                              ? "border-bw-danger/40 text-bw-danger bg-bw-danger/10"
                              : rec.priority === "medium"
                              ? "border-bw-warning/40 text-bw-warning bg-bw-warning/10"
                              : "border-bw-teal/40 text-bw-teal bg-bw-teal/10"
                          }`}
                        >
                          {rec.priority}
                        </span>
                      </div>
                      <p className="text-xs text-bw-muted">{rec.reason}</p>
                      <p className="text-xs text-bw-text font-medium pt-0.5">
                        Action: {rec.action}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )
        )}
      </div>
    </AppShell>
  );
}
