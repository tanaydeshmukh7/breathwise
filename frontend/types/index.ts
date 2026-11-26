export type AqiStandard = "indian_naqi" | "us_aqi";

export type HouseholdContext =
  | "general"
  | "family_with_children"
  | "elderly_care"
  | "outdoor_athlete"
  | "commuter";

export interface LocationState {
  name: string;
  latitude: number;
  longitude: number;
  source?: "default" | "geolocation" | "search" | "saved";
}

export interface PollutantReading {
  value: number | null;
  unit: string;
}

export interface AirQualityResponse {
  location: {
    name: string;
    latitude: number;
    longitude: number;
    timezone: string;
    timezone_abbreviation: string;
  };
  data_source: string;
  timestamp: string | null;
  fetched_at_utc: string;
  freshness: string;
  missing_fields: string[];
  pollutants: {
    pm2_5: PollutantReading;
    pm10: PollutantReading;
    nitrogen_dioxide: PollutantReading;
    ozone: PollutantReading;
    carbon_monoxide: PollutantReading;
    sulphur_dioxide: PollutantReading;
  };
  indices: {
    indian_naqi: {
      value: number | null;
      category: string;
      severity: string;
      color: string;
      dominant_pollutant: string | null;
      sub_indices: Record<string, number>;
      methodology: string;
      note: string;
    };
    us_aqi: {
      value: number | null;
      category: string;
      severity: string;
      color: string;
      methodology: string;
      note: string;
    };
    european_aqi: {
      value: number | null;
      methodology: string;
    };
  };
}

export interface ForecastPoint {
  time: string;
  pm2_5: number | null;
  pm10: number | null;
  nitrogen_dioxide: number | null;
  ozone: number | null;
  carbon_monoxide: number | null;
  sulphur_dioxide: number | null;
  us_aqi: number | null;
  indian_naqi: number | null;
  indian_naqi_category: string;
}

export interface AirQualityForecastResponse {
  data_source: string;
  timezone: string;
  units: Record<string, string>;
  series: ForecastPoint[];
}

export interface WeatherResponse {
  data_source: string;
  timestamp: string | null;
  timezone: string;
  temperature: {
    value: number | null;
    apparent_value: number | null;
    unit: string;
  };
  humidity: {
    value: number | null;
    unit: string;
  };
  wind: {
    speed: number | null;
    speed_unit: string;
    direction_degrees: number | null;
    direction_compass: string;
  };
  weather_code: number | null;
  condition: string;
  hourly: Array<{
    time: string;
    temperature_2m: number | null;
    relative_humidity_2m: number | null;
    wind_speed_10m: number | null;
    condition: string;
  }>;
}

export interface LocationSearchResult {
  id: number;
  name: string;
  admin1?: string;
  country?: string;
  country_code?: string;
  label: string;
  latitude: number;
  longitude: number;
  timezone?: string;
}

export interface RecommendationItem {
  title: string;
  reason: string;
  action: string;
  priority: "high" | "medium" | "low";
}

export interface StructuredAdvisorOutput {
  summary: string;
  risk_level: "low" | "moderate" | "high" | "very_high" | "severe";
  recommendations: RecommendationItem[];
  best_outdoor_window?: string | null;
  precautionary_note: string;
}

export interface DailyRoutineSlot {
  time: string;
  phase: "morning" | "travel" | "outdoor" | "work_study" | "evening";
  title: string;
  guidance: string;
  aqi_context: string;
  priority: "high" | "medium" | "low";
}

export interface StructuredDailyRoutineOutput {
  summary: string;
  optimal_outdoor_window: string;
  slots: DailyRoutineSlot[];
}

export interface StructuredIndoorOutput {
  ventilation_verdict: "open_windows" | "brief_cross_ventilation" | "keep_closed_filter";
  summary: string;
  key_steps: string[];
  room_guidance: Array<{
    room: string;
    ventilation_action: string;
    filtration_and_dust: string;
    priority: "high" | "medium" | "low";
  }>;
  sensor_disclaimer: string;
}

export interface SustainableAlternativeItem {
  category: "transportation" | "energy" | "household" | "shopping" | "waste" | "community";
  current_behavior: string;
  suggested_alternative: string;
  why_it_matters: string;
  potential_benefit: string;
  practical_difficulty: "easy" | "moderate" | "challenging";
}

export interface StructuredSustainableOutput {
  summary: string;
  alternatives: SustainableAlternativeItem[];
}

export interface AIResponseEnvelope<T> {
  ai_status: "live_gemini" | "live_qwen" | "rule_based_fallback";
  model_used: string;
  provider: string;
  fallback_reason?: string | null;
  data_source: string;
  reading_timestamp?: string | null;
  conversation_id?: string | null;
  result: T;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  city: string;
  latitude: number;
  longitude: number;
  age_group?: string;
  occupation?: string;
  transport_preference?: string;
  exercise_habit?: string;
  household_size: number;
  has_air_purifier: boolean;
  preferred_aqi_standard: AqiStandard;
}

export interface FamilyMember {
  id: string;
  name: string;
  member_type: "adult" | "child" | "elderly";
  sensitivity_notes: string;
  daily_outdoor_minutes: number;
}

export interface SavedRoutine {
  id: string;
  title: string;
  location_name: string;
  summary: string;
  optimal_outdoor_window: string;
  items: DailyRoutineSlot[];
  is_active: boolean;
  created_at: string;
}

export interface ImpactAction {
  id: string;
  category: string;
  action_type: string;
  action_name: string;
  quantity: number;
  unit: string;
  estimated_co2e_avoided_kg: number | null;
  calculation_basis: string;
  is_estimate: boolean;
  completed_at: string;
}

export interface ImpactSummary {
  total_actions: number;
  total_estimated_co2e_avoided_kg: number;
  public_transport_km: number;
  walk_cycle_km: number;
  energy_saved_kwh: number;
  by_category: Record<string, number>;
  weekly_progress: Array<{
    date: string;
    actions: number;
    estimated_co2e_kg: number;
  }>;
  actions: ImpactAction[];
  disclaimer: string;
}
