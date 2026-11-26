"""Documented AQI calculation and categorization utilities.

Strictly separates Indian National AQI (CPCB NAQI) from US EPA AQI.
Never mixes index standards or fabricates missing pollutant readings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# CPCB Indian National Air Quality Index (NAQI) breakpoints
# Units: ug/m3 for PM2.5, PM10, NO2, O3, SO2; mg/m3 for CO
CPCB_BREAKPOINTS: Dict[str, List[Tuple[float, float, int, int]]] = {
    "pm2_5": [
        (0.0, 30.0, 0, 50),
        (30.0, 60.0, 51, 100),
        (60.0, 90.0, 101, 200),
        (90.0, 120.0, 201, 300),
        (120.0, 250.0, 301, 400),
        (250.0, 500.0, 401, 500),
    ],
    "pm10": [
        (0.0, 50.0, 0, 50),
        (50.0, 100.0, 51, 100),
        (100.0, 250.0, 101, 200),
        (250.0, 350.0, 201, 300),
        (350.0, 430.0, 301, 400),
        (430.0, 600.0, 401, 500),
    ],
    "nitrogen_dioxide": [
        (0.0, 40.0, 0, 50),
        (40.0, 80.0, 51, 100),
        (80.0, 180.0, 101, 200),
        (180.0, 280.0, 201, 300),
        (280.0, 400.0, 301, 400),
        (400.0, 800.0, 401, 500),
    ],
    "ozone": [
        (0.0, 50.0, 0, 50),
        (50.0, 100.0, 51, 100),
        (100.0, 168.0, 101, 200),
        (168.0, 208.0, 201, 300),
        (208.0, 748.0, 301, 400),
        (748.0, 1000.0, 401, 500),
    ],
    "carbon_monoxide_mg": [
        (0.0, 1.0, 0, 50),
        (1.0, 2.0, 51, 100),
        (2.0, 10.0, 101, 200),
        (10.0, 17.0, 201, 300),
        (17.0, 34.0, 301, 400),
        (34.0, 50.0, 401, 500),
    ],
    "sulphur_dioxide": [
        (0.0, 40.0, 0, 50),
        (40.0, 80.0, 51, 100),
        (80.0, 380.0, 101, 200),
        (380.0, 800.0, 201, 300),
        (800.0, 1600.0, 301, 400),
        (1600.0, 2100.0, 401, 500),
    ],
}


def _interpolate_sub_index(
    concentration: float, breakpoints: List[Tuple[float, float, int, int]]
) -> int:
    val = max(0.0, concentration)
    for bp_lo, bp_hi, i_lo, i_hi in breakpoints:
        if val <= bp_hi:
            if bp_hi == bp_lo:
                return i_hi
            sub = ((i_hi - i_lo) / (bp_hi - bp_lo)) * (val - bp_lo) + i_lo
            return int(round(sub))
    return 500


def classify_indian_naqi(aqi: Optional[int]) -> Tuple[str, str, str]:
    """Return (category, severity_key, hex_color) for CPCB Indian NAQI."""
    if aqi is None:
        return ("Unavailable", "unknown", "#8F9B91")
    if aqi <= 50:
        return ("Good", "good", "#58D6A0")
    if aqi <= 100:
        return ("Satisfactory", "satisfactory", "#B7F36B")
    if aqi <= 200:
        return ("Moderately Polluted", "moderate", "#F3B94F")
    if aqi <= 300:
        return ("Poor", "poor", "#F3B94F")
    if aqi <= 400:
        return ("Very Poor", "very_poor", "#F16D68")
    return ("Severe", "severe", "#F16D68")


def classify_us_aqi(aqi: Optional[int]) -> Tuple[str, str, str]:
    """Return (category, severity_key, hex_color) for US EPA AQI."""
    if aqi is None:
        return ("Unavailable", "unknown", "#8F9B91")
    if aqi <= 50:
        return ("Good", "good", "#58D6A0")
    if aqi <= 100:
        return ("Moderate", "moderate", "#B7F36B")
    if aqi <= 150:
        return ("Unhealthy for Sensitive Groups", "sensitive", "#F3B94F")
    if aqi <= 200:
        return ("Unhealthy", "unhealthy", "#F16D68")
    if aqi <= 300:
        return ("Very Unhealthy", "very_unhealthy", "#F16D68")
    return ("Hazardous", "hazardous", "#F16D68")


@dataclass
class ComputedIndianNaqi:
    value: Optional[int]
    category: str
    severity: str
    color: str
    dominant_pollutant: Optional[str]
    sub_indices: Dict[str, int]
    methodology: str
    note: str


def compute_indian_naqi(
    pm2_5: Optional[float] = None,
    pm10: Optional[float] = None,
    nitrogen_dioxide: Optional[float] = None,
    ozone: Optional[float] = None,
    carbon_monoxide_ug_m3: Optional[float] = None,
    sulphur_dioxide: Optional[float] = None,
) -> ComputedIndianNaqi:
    """Compute CPCB Indian National AQI from available raw pollutant concentrations.

    Note: Open-Meteo supplies carbon_monoxide in ug/m3, whereas CPCB CO
    breakpoints are in mg/m3; we divide by 1000.0 before interpolating.
    """
    sub_indices: Dict[str, int] = {}
    if pm2_5 is not None:
        sub_indices["PM2.5"] = _interpolate_sub_index(pm2_5, CPCB_BREAKPOINTS["pm2_5"])
    if pm10 is not None:
        sub_indices["PM10"] = _interpolate_sub_index(pm10, CPCB_BREAKPOINTS["pm10"])
    if nitrogen_dioxide is not None:
        sub_indices["NO2"] = _interpolate_sub_index(
            nitrogen_dioxide, CPCB_BREAKPOINTS["nitrogen_dioxide"]
        )
    if ozone is not None:
        sub_indices["O3"] = _interpolate_sub_index(ozone, CPCB_BREAKPOINTS["ozone"])
    if carbon_monoxide_ug_m3 is not None:
        co_mg_m3 = carbon_monoxide_ug_m3 / 1000.0
        sub_indices["CO"] = _interpolate_sub_index(
            co_mg_m3, CPCB_BREAKPOINTS["carbon_monoxide_mg"]
        )
    if sulphur_dioxide is not None:
        sub_indices["SO2"] = _interpolate_sub_index(
            sulphur_dioxide, CPCB_BREAKPOINTS["sulphur_dioxide"]
        )

    has_pm = ("PM2.5" in sub_indices) or ("PM10" in sub_indices)
    if len(sub_indices) < 3 or not has_pm:
        return ComputedIndianNaqi(
            value=None,
            category="Unavailable",
            severity="unknown",
            color="#8F9B91",
            dominant_pollutant=None,
            sub_indices=sub_indices,
            methodology="CPCB Indian National AQI (NAQI)",
            note="CPCB NAQI requires at least 3 pollutants including PM2.5 or PM10.",
        )

    dominant = max(sub_indices, key=lambda k: sub_indices[k])
    aqi_val = sub_indices[dominant]
    category, severity, color = classify_indian_naqi(aqi_val)
    return ComputedIndianNaqi(
        value=aqi_val,
        category=category,
        severity=severity,
        color=color,
        dominant_pollutant=dominant,
        sub_indices=sub_indices,
        methodology="CPCB Indian National AQI (NAQI)",
        note=(
            "Calculated from instantaneous/hourly surface concentrations using CPCB NAQI "
            "breakpoints (official CPCB monitoring averages 24h for PM/NO2/SO2 and 8h for O3/CO)."
        ),
    )


def wmo_weather_description(code: Optional[int]) -> str:
    """Convert WMO weather code from Open-Meteo into human-readable condition."""
    if code is None:
        return "Unavailable"
    mapping = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with heavy hail",
    }
    return mapping.get(code, f"Weather code {code}")


def wind_direction_compass(degrees: Optional[float]) -> str:
    if degrees is None:
        return "N/A"
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = int((degrees / 22.5) + 0.5) % 16
    return dirs[idx]
