import { HouseholdContext, LocationState } from "@/types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (typeof window !== "undefined" &&
  window.location.hostname !== "localhost" &&
  window.location.hostname !== "127.0.0.1"
    ? ""
    : "http://localhost:8000");

export const DEFAULT_LOCATION: LocationState = {
  name: process.env.NEXT_PUBLIC_DEFAULT_CITY || "Pune",
  latitude: Number(process.env.NEXT_PUBLIC_DEFAULT_LAT || 18.5204),
  longitude: Number(process.env.NEXT_PUBLIC_DEFAULT_LON || 73.8567),
  source: "default",
};

export const PRESET_CITIES: LocationState[] = [
  { name: "Pune", latitude: 18.5204, longitude: 73.8567, source: "saved" },
  { name: "Delhi", latitude: 28.6139, longitude: 77.209, source: "saved" },
  { name: "Mumbai", latitude: 19.076, longitude: 72.8777, source: "saved" },
  { name: "Bengaluru", latitude: 12.9716, longitude: 77.5946, source: "saved" },
];

export const HOUSEHOLD_CONTEXT_OPTIONS: Array<{
  value: HouseholdContext;
  label: string;
  description: string;
}> = [
  {
    value: "general",
    label: "General Household",
    description: "Balanced daily guidance for urban residents",
  },
  {
    value: "family_with_children",
    label: "Family with Children",
    description: "Extra caution for school commutes & outdoor play",
  },
  {
    value: "elderly_care",
    label: "Elderly Care",
    description: "Conservative respiratory exposure thresholds",
  },
  {
    value: "outdoor_athlete",
    label: "Outdoor Runner / Cyclist",
    description: "Focused on peak-hour timing & workout swaps",
  },
  {
    value: "commuter",
    label: "Daily Commuter",
    description: "Transit mode choices & corridor exposure tips",
  },
];

export const ADVISOR_SUGGESTED_PROMPTS = [
  "Is it safe to exercise outside right now?",
  "When should I take my morning walk today?",
  "How can I protect my family and elderly parents today?",
  "Should I keep my windows open or closed?",
  "How can I reduce indoor pollution while cooking?",
  "What is causing today's air quality levels?",
  "What can I do today to reduce my pollution footprint?",
];
