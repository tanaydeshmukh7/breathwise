import { API_BASE_URL } from "./constants";
import {
  AIResponseEnvelope,
  AirQualityForecastResponse,
  AirQualityResponse,
  FamilyMember,
  ImpactAction,
  ImpactSummary,
  LocationSearchResult,
  SavedRoutine,
  StructuredAdvisorOutput,
  StructuredDailyRoutineOutput,
  StructuredIndoorOutput,
  StructuredSustainableOutput,
  UserContextPayload,
  UserProfile,
  WeatherResponse,
} from "@/types";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  const text = await res.text();
  let data: Record<string, unknown> = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    const detail = data?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : typeof detail === "object" && detail !== null && "message" in detail
        ? String((detail as { message: unknown }).message)
        : `Request failed with status ${res.status}`;
    throw new ApiError(message, res.status);
  }
  return data as T;
}

export const api = {
  health: () =>
    request<{
      status: string;
      database: { mode: string; connected: boolean; detail: string };
      ai: { configured: boolean; active_model: string; available_models: string[] };
    }>("/api/health"),

  getCurrentAqi: (lat: number, lon: number, city?: string) =>
    request<AirQualityResponse>(
      `/api/aqi/current?lat=${lat}&lon=${lon}${city ? `&city=${encodeURIComponent(city)}` : ""}`
    ),

  getAqiForecast: (lat: number, lon: number, hours = 36, pastDays = 1) =>
    request<AirQualityForecastResponse>(
      `/api/aqi/forecast?lat=${lat}&lon=${lon}&hours=${hours}&past_days=${pastDays}`
    ),

  getAqiHistory: (lat: number, lon: number) =>
    request<{
      location_key: string;
      total_stored_snapshots: number;
      open_meteo_recent_history: AirQualityForecastResponse["series"];
    }>(`/api/aqi/history?lat=${lat}&lon=${lon}`),

  getCurrentWeather: (lat: number, lon: number) =>
    request<WeatherResponse>(`/api/weather/current?lat=${lat}&lon=${lon}`),

  searchLocations: (q: string) =>
    request<{ query: string; results: LocationSearchResult[] }>(
      `/api/locations/search?q=${encodeURIComponent(q)}`
    ),

  // AI
  listModels: () =>
    request<{
      active_model: string;
      available_models: string[];
      provider: string;
      provider_key: string;
      configured: boolean;
    }>("/api/ai/models"),

  analyzeAir: (payload: UserContextPayload, token?: string | null) =>
    request<AIResponseEnvelope<StructuredAdvisorOutput>>(
      "/api/ai/analyze",
      { method: "POST", body: JSON.stringify(payload) },
      token
    ),

  chatAdvisor: (
    payload: UserContextPayload & {
      message: string;
      conversation_id?: string | null;
    },
    token?: string | null
  ) =>
    request<AIResponseEnvelope<StructuredAdvisorOutput>>(
      "/api/ai/chat",
      { method: "POST", body: JSON.stringify(payload) },
      token
    ),

  generateDailyRoutine: (payload: UserContextPayload, token?: string | null) =>
    request<AIResponseEnvelope<StructuredDailyRoutineOutput>>(
      "/api/ai/daily-routine",
      { method: "POST", body: JSON.stringify(payload) },
      token
    ),

  generateIndoorAdvice: (
    payload: UserContextPayload & {
      has_air_purifier: boolean;
      cooking_fuel: "lpg_induction" | "mixed" | "solid_biomass";
      uses_incense_or_dhoop: boolean;
    },
    token?: string | null
  ) =>
    request<AIResponseEnvelope<StructuredIndoorOutput>>(
      "/api/ai/indoor-advice",
      { method: "POST", body: JSON.stringify(payload) },
      token
    ),

  generateSustainableAlternatives: (
    payload: UserContextPayload & { focus_category?: string },
    token?: string | null
  ) =>
    request<AIResponseEnvelope<StructuredSustainableOutput>>(
      "/api/ai/sustainable-alternatives",
      { method: "POST", body: JSON.stringify(payload) },
      token
    ),

  // Auth
  register: (payload: {
    name: string;
    email: string;
    password: string;
    city: string;
    latitude: number;
    longitude: number;
  }) =>
    request<{ access_token: string; user: UserProfile }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: (payload: { email: string; password: string }) =>
    request<{ access_token: string; user: UserProfile }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getMe: (token: string) => request<UserProfile>("/api/auth/me", {}, token),

  // Profile & Family
  getProfile: (token: string) =>
    request<{
      user: UserProfile;
      preferences: {
        notifications_enabled: boolean;
        alert_threshold_naqi: number;
        preferred_locations: Array<{ label: string; latitude: number; longitude: number }>;
        personal_preferences: string;
      };
      family_profiles: FamilyMember[];
    }>("/api/users/profile", {}, token),

  updateProfile: (payload: Record<string, unknown>, token: string) =>
    request<{ user: UserProfile }>(
      "/api/users/profile",
      { method: "PUT", body: JSON.stringify(payload) },
      token
    ),

  addFamilyMember: (
    payload: {
      name: string;
      member_type: "adult" | "child" | "elderly";
      sensitivity_notes: string;
      daily_outdoor_minutes: number;
    },
    token: string
  ) =>
    request<{ family_member: FamilyMember }>(
      "/api/users/family",
      { method: "POST", body: JSON.stringify(payload) },
      token
    ),

  deleteFamilyMember: (memberId: string, token: string) =>
    request<{ deleted: boolean }>(
      `/api/users/family/${memberId}`,
      { method: "DELETE" },
      token
    ),

  // Routines
  listRoutines: (token: string) =>
    request<{ routines: SavedRoutine[]; total: number }>("/api/routines", {}, token),

  createRoutine: (
    payload: {
      title: string;
      location_name: string;
      summary: string;
      optimal_outdoor_window: string;
      items: SavedRoutine["items"];
    },
    token: string
  ) =>
    request<{ routine: SavedRoutine }>(
      "/api/routines",
      { method: "POST", body: JSON.stringify(payload) },
      token
    ),

  deleteRoutine: (routineId: string, token: string) =>
    request<{ deleted: boolean }>(
      `/api/routines/${routineId}`,
      { method: "DELETE" },
      token
    ),

  // Impact
  getImpactCatalog: () =>
    request<{
      methodology_note: string;
      actions: Array<{
        action_type: string;
        category: string;
        default_label: string;
        unit: string;
        kg_co2e_per_unit: number | null;
        basis: string;
      }>;
    }>("/api/impact/catalog"),

  getImpactSummary: (token: string) =>
    request<ImpactSummary>("/api/impact/summary", {}, token),

  logImpactAction: (
    payload: {
      category: string;
      action_type: string;
      action_name: string;
      quantity: number;
      notes?: string;
    },
    token: string
  ) =>
    request<{ action: ImpactAction }>(
      "/api/impact/actions",
      { method: "POST", body: JSON.stringify(payload) },
      token
    ),
};
