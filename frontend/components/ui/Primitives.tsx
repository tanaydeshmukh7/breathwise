"use client";

import React from "react";
import { AlertTriangle, RefreshCw, Sparkles } from "lucide-react";

export function BrandMark({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 36 36"
      fill="none"
      className={className}
      aria-label="BreatheWise logo"
    >
      <rect
        x="1"
        y="1"
        width="34"
        height="34"
        rx="9"
        fill="#151E19"
        stroke="rgba(183, 243, 107, 0.35)"
        strokeWidth="1.5"
      />
      <path
        d="M9 19.5C9 15.5 12.2 12 16.5 12C19.6 12 21.6 13.7 22.8 15.6C24.5 15.2 27 16.2 27 18.9C27 21.4 24.9 23.2 22.3 23.2H12.2C10.3 23.2 9 21.6 9 19.5Z"
        stroke="#B7F36B"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M12.5 26.5H23.5"
        stroke="#58D6A0"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function LoadingCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="bw-surface rounded-xl p-6 animate-pulse space-y-3">
      <div className="h-4 w-1/3 rounded bg-white/10" />
      {Array.from({ length: lines }).map((_, idx) => (
        <div
          key={idx}
          className="h-3 rounded bg-white/5"
          style={{ width: `${90 - idx * 14}%` }}
        />
      ))}
    </div>
  );
}

export function UnavailableBanner({
  title,
  message,
  onRetry,
}: {
  title: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-xl border border-bw-danger/30 bg-bw-danger/10 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 text-bw-danger shrink-0 mt-0.5" />
        <div>
          <h3 className="text-sm font-semibold text-bw-text">{title}</h3>
          <p className="text-xs text-bw-muted mt-1 leading-relaxed">{message}</p>
        </div>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-white/10 bg-bw-secondary hover:bg-white/5 text-xs font-medium text-bw-text shrink-0 transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Retry
        </button>
      )}
    </div>
  );
}

export function AiSourceBadge({
  aiStatus,
  modelUsed,
  fallbackReason,
}: {
  aiStatus: "live_gemini" | "live_qwen" | "rule_based_fallback";
  modelUsed: string;
  fallbackReason?: string | null;
}) {
  const isLive = aiStatus === "live_gemini" || aiStatus === "live_qwen";
  const liveLabel =
    aiStatus === "live_gemini"
      ? `Live Gemini Intelligence (${modelUsed})`
      : `Live Qwen Intelligence (${modelUsed})`;
  const providerTag =
    aiStatus === "live_gemini"
      ? "Google Gemini API"
      : aiStatus === "live_qwen"
      ? "Hugging Face Router"
      : "Grounded Open-Meteo Rules";
  return (
    <div
      className={`rounded-lg border px-3 py-2 text-xs flex flex-col gap-1 ${
        isLive
          ? "border-bw-teal/30 bg-bw-teal/10 text-bw-teal"
          : "border-bw-warning/30 bg-bw-warning/10 text-bw-warning"
      }`}
    >
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="inline-flex items-center gap-1.5 font-medium">
          <Sparkles className="h-3.5 w-3.5" />
          {isLive
            ? liveLabel
            : `Verified-Data Deterministic Fallback (${modelUsed} unavailable)`}
        </span>
        <span className="font-mono text-[11px] opacity-80">
          {providerTag}
        </span>
      </div>
      {!isLive && fallbackReason && (
        <p className="text-[11px] text-bw-muted leading-snug">{fallbackReason}</p>
      )}
    </div>
  );
}
