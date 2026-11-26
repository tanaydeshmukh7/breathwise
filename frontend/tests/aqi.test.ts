import test from "node:test";
import assert from "node:assert/strict";
import {
  formatHourLabel,
  getActiveIndexInfo,
  getBadgeClasses,
} from "../lib/aqi";
import {
  ADVISOR_SUGGESTED_PROMPTS,
  DEFAULT_LOCATION,
  HOUSEHOLD_CONTEXT_OPTIONS,
  PRESET_CITIES,
} from "../lib/constants";
import type { AirQualityResponse } from "../types";

const SAMPLE_AQ: AirQualityResponse = {
  location: {
    name: "Pune",
    latitude: 18.5204,
    longitude: 73.8567,
    timezone: "Asia/Kolkata",
    timezone_abbreviation: "IST",
  },
  data_source: "Open-Meteo Air Quality API",
  timestamp: "2026-11-26T09:00",
  fetched_at_utc: "2026-11-26T03:30:00Z",
  freshness: "Updated at 2026-11-26T09:00 (local)",
  missing_fields: [],
  pollutants: {
    pm2_5: { value: 48.2, unit: "μg/m³" },
    pm10: { value: 78.4, unit: "μg/m³" },
    nitrogen_dioxide: { value: 21.0, unit: "μg/m³" },
    ozone: { value: 64.0, unit: "μg/m³" },
    carbon_monoxide: { value: 510.0, unit: "μg/m³" },
    sulphur_dioxide: { value: 11.2, unit: "μg/m³" },
  },
  indices: {
    indian_naqi: {
      value: 80,
      category: "Satisfactory",
      severity: "low",
      color: "#B7F36B",
      dominant_pollutant: "PM2.5",
      sub_indices: { PM2_5: 80, PM10: 78 },
      methodology: "CPCB Indian National AQI (NAQI)",
      note: "Computed locally from Open-Meteo concentrations.",
      health_implication: "Minor breathing discomfort to sensitive people.",
    },
    us_aqi: {
      value: 132,
      category: "Unhealthy for Sensitive Groups",
      severity: "moderate",
      color: "#F3B94F",
      methodology: "US EPA Air Quality Index (0–500)",
      note: "Directly provided by Open-Meteo.",
    },
    european_aqi: {
      value: 48,
      methodology: "European Environment Agency (EAQI)",
    },
  },
};

test("getActiveIndexInfo handles null response cleanly", () => {
  const inInfo = getActiveIndexInfo(null, "indian_naqi");
  assert.equal(inInfo.value, null);
  assert.equal(inInfo.category, "Unavailable");
  assert.match(inInfo.methodology, /CPCB Indian National AQI/);

  const usInfo = getActiveIndexInfo(null, "us_aqi");
  assert.equal(usInfo.value, null);
  assert.match(usInfo.methodology, /US EPA/);
});

test("getActiveIndexInfo separates Indian NAQI and US AQI cleanly", () => {
  const inInfo = getActiveIndexInfo(SAMPLE_AQ, "indian_naqi");
  assert.equal(inInfo.value, 80);
  assert.equal(inInfo.category, "Satisfactory");
  assert.equal(inInfo.dominantPollutant, "PM2.5");

  const usInfo = getActiveIndexInfo(SAMPLE_AQ, "us_aqi");
  assert.equal(usInfo.value, 132);
  assert.equal(usInfo.category, "Unhealthy for Sensitive Groups");
  assert.equal(usInfo.dominantPollutant, null);
});

test("getBadgeClasses maps documented severity colors case-insensitively", () => {
  assert.match(getBadgeClasses("#58d6a0"), /#58D6A0/);
  assert.match(getBadgeClasses("#B7F36B"), /#B7F36B/);
  assert.match(getBadgeClasses("#F3B94F"), /#F3B94F/);
  assert.match(getBadgeClasses("#F16D68"), /#F16D68/);
  assert.match(getBadgeClasses("#000000"), /bg-bw-muted/);
});

test("formatHourLabel extracts HH:MM from ISO timestamps", () => {
  assert.equal(formatHourLabel("2026-11-26T09:30"), "09:30");
  assert.equal(formatHourLabel("invalid-timestamp"), "invalid-timestamp");
});

test("constants expose Pune default and required household profiles", () => {
  assert.equal(DEFAULT_LOCATION.name, "Pune");
  assert.ok(PRESET_CITIES.some((c) => c.name === "Pune"));
  assert.ok(HOUSEHOLD_CONTEXT_OPTIONS.some((o) => o.value === "elderly_care"));
  assert.ok(ADVISOR_SUGGESTED_PROMPTS.length >= 5);
});
