import { AirQualityResponse, AqiStandard } from "@/types";

export function getActiveIndexInfo(
  aq: AirQualityResponse | null,
  standard: AqiStandard
) {
  if (!aq) {
    return {
      value: null as number | null,
      category: "Unavailable",
      color: "#8F9B91",
      methodology:
        standard === "indian_naqi"
          ? "CPCB Indian National AQI (NAQI)"
          : "US EPA Air Quality Index (0–500)",
      dominantPollutant: null as string | null,
      note: "",
    };
  }
  if (standard === "indian_naqi") {
    const idx = aq.indices.indian_naqi;
    return {
      value: idx.value,
      category: idx.category,
      color: idx.color,
      methodology: idx.methodology,
      dominantPollutant: idx.dominant_pollutant,
      note: idx.note,
    };
  }
  const us = aq.indices.us_aqi;
  return {
    value: us.value,
    category: us.category,
    color: us.color,
    methodology: us.methodology,
    dominantPollutant: null,
    note: us.note,
  };
}

export function getBadgeClasses(colorHex: string): string {
  switch (colorHex.toUpperCase()) {
    case "#58D6A0":
      return "bg-[#58D6A0]/15 text-[#58D6A0] border-[#58D6A0]/30";
    case "#B7F36B":
      return "bg-[#B7F36B]/15 text-[#B7F36B] border-[#B7F36B]/30";
    case "#F3B94F":
      return "bg-[#F3B94F]/15 text-[#F3B94F] border-[#F3B94F]/30";
    case "#F16D68":
      return "bg-[#F16D68]/15 text-[#F16D68] border-[#F16D68]/30";
    default:
      return "bg-bw-muted/15 text-bw-muted border-bw-muted/30";
  }
}

export function formatHourLabel(isoTime: string): string {
  const parts = isoTime.split("T");
  if (parts.length === 2) {
    return parts[1].slice(0, 5);
  }
  return isoTime;
}
