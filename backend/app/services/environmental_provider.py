"""Configurable environmental data provider interface and Open-Meteo client."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.config import Settings
from app.services.aqi_calculator import (
    classify_us_aqi,
    compute_indian_naqi,
    wind_direction_compass,
    wmo_weather_description,
)


class EnvironmentalProviderError(Exception):
    """Raised when an upstream environmental data provider fails or is unreachable."""


class EnvironmentalDataProvider(ABC):
    """Abstract interface allowing future expansion to CPCB/IQAir/sensor networks."""

    provider_name: str

    @abstractmethod
    async def get_current_air_quality(
        self, latitude: float, longitude: float, location_name: Optional[str] = None
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_air_quality_forecast(
        self,
        latitude: float,
        longitude: float,
        hours: int = 48,
        past_days: int = 1,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_current_weather(
        self, latitude: float, longitude: float
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def search_locations(self, query: str, count: int = 6) -> List[Dict[str, Any]]:
        pass


class OpenMeteoProvider(EnvironmentalDataProvider):
    """Live environmental data provider backed by Open-Meteo Air Quality, Weather & Geocoding APIs."""

    provider_name = "Open-Meteo"
    AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
    WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

    def __init__(self, timeout: float = 12.0) -> None:
        self._timeout = timeout

    async def _fetch_json(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.TimeoutException as exc:
            raise EnvironmentalProviderError(
                f"{self.provider_name} request timed out."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise EnvironmentalProviderError(
                f"{self.provider_name} returned HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise EnvironmentalProviderError(
                f"Failed to reach {self.provider_name}: {type(exc).__name__}"
            ) from exc

    @staticmethod
    def _compute_freshness(reading_time: Optional[str]) -> str:
        if not reading_time:
            return "Unknown timestamp"
        # Open-Meteo returns local ISO timestamp like '2026-11-26T09:30'
        return f"Updated at {reading_time} (local)"

    async def get_current_air_quality(
        self, latitude: float, longitude: float, location_name: Optional[str] = None
    ) -> Dict[str, Any]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "pm2_5,pm10,nitrogen_dioxide,ozone,"
                "carbon_monoxide,sulphur_dioxide,us_aqi,european_aqi"
            ),
            "timezone": "auto",
        }
        raw = await self._fetch_json(self.AQ_URL, params)
        current = raw.get("current") or {}
        units = raw.get("current_units") or {}

        pm2_5 = current.get("pm2_5")
        pm10 = current.get("pm10")
        no2 = current.get("nitrogen_dioxide")
        o3 = current.get("ozone")
        co = current.get("carbon_monoxide")
        so2 = current.get("sulphur_dioxide")
        us_aqi_val = current.get("us_aqi")
        eaqi_val = current.get("european_aqi")

        missing_fields: List[str] = []
        for field_key, label in (
            ("pm2_5", "PM2.5"),
            ("pm10", "PM10"),
            ("nitrogen_dioxide", "NO2"),
            ("ozone", "O3"),
            ("carbon_monoxide", "CO"),
            ("sulphur_dioxide", "SO2"),
        ):
            if current.get(field_key) is None:
                missing_fields.append(label)

        indian_naqi = compute_indian_naqi(
            pm2_5=pm2_5,
            pm10=pm10,
            nitrogen_dioxide=no2,
            ozone=o3,
            carbon_monoxide_ug_m3=co,
            sulphur_dioxide=so2,
        )
        us_cat, us_sev, us_color = classify_us_aqi(
            int(us_aqi_val) if us_aqi_val is not None else None
        )

        reading_time = current.get("time")
        fetched_at = datetime.now(timezone.utc).isoformat()

        return {
            "location": {
                "name": location_name or f"{latitude:.3f}, {longitude:.3f}",
                "latitude": raw.get("latitude", latitude),
                "longitude": raw.get("longitude", longitude),
                "timezone": raw.get("timezone", "auto"),
                "timezone_abbreviation": raw.get("timezone_abbreviation", ""),
            },
            "data_source": "Open-Meteo Air Quality API (CAMS regional/global atmospheric model)",
            "timestamp": reading_time,
            "fetched_at_utc": fetched_at,
            "freshness": self._compute_freshness(reading_time),
            "missing_fields": missing_fields,
            "pollutants": {
                "pm2_5": {"value": pm2_5, "unit": units.get("pm2_5", "μg/m³")},
                "pm10": {"value": pm10, "unit": units.get("pm10", "μg/m³")},
                "nitrogen_dioxide": {
                    "value": no2,
                    "unit": units.get("nitrogen_dioxide", "μg/m³"),
                },
                "ozone": {"value": o3, "unit": units.get("ozone", "μg/m³")},
                "carbon_monoxide": {
                    "value": co,
                    "unit": units.get("carbon_monoxide", "μg/m³"),
                },
                "sulphur_dioxide": {
                    "value": so2,
                    "unit": units.get("sulphur_dioxide", "μg/m³"),
                },
            },
            "indices": {
                "indian_naqi": {
                    "value": indian_naqi.value,
                    "category": indian_naqi.category,
                    "severity": indian_naqi.severity,
                    "color": indian_naqi.color,
                    "dominant_pollutant": indian_naqi.dominant_pollutant,
                    "sub_indices": indian_naqi.sub_indices,
                    "methodology": indian_naqi.methodology,
                    "note": indian_naqi.note,
                    "health_implication": indian_naqi.health_implication,
                },
                "us_aqi": {
                    "value": int(us_aqi_val) if us_aqi_val is not None else None,
                    "category": us_cat,
                    "severity": us_sev,
                    "color": us_color,
                    "methodology": "US EPA Air Quality Index (0–500)",
                    "note": "Directly provided by Open-Meteo using US EPA AQI breakpoints.",
                },
                "european_aqi": {
                    "value": int(eaqi_val) if eaqi_val is not None else None,
                    "methodology": "European Environment Agency (EAQI)",
                },
            },
        }

    async def get_air_quality_forecast(
        self,
        latitude: float,
        longitude: float,
        hours: int = 48,
        past_days: int = 1,
    ) -> Dict[str, Any]:
        forecast_days = max(1, min(5, (hours + 23) // 24))
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": (
                "pm2_5,pm10,nitrogen_dioxide,ozone,"
                "carbon_monoxide,sulphur_dioxide,us_aqi,european_aqi"
            ),
            "forecast_days": forecast_days,
            "past_days": max(0, min(7, past_days)),
            "timezone": "auto",
        }
        raw = await self._fetch_json(self.AQ_URL, params)
        hourly = raw.get("hourly") or {}
        times: List[str] = hourly.get("time") or []

        series: List[Dict[str, Any]] = []
        for idx, ts in enumerate(times):
            pm2_5 = _safe_at(hourly.get("pm2_5"), idx)
            pm10 = _safe_at(hourly.get("pm10"), idx)
            no2 = _safe_at(hourly.get("nitrogen_dioxide"), idx)
            o3 = _safe_at(hourly.get("ozone"), idx)
            co = _safe_at(hourly.get("carbon_monoxide"), idx)
            so2 = _safe_at(hourly.get("sulphur_dioxide"), idx)
            us_aqi_val = _safe_at(hourly.get("us_aqi"), idx)
            naqi = compute_indian_naqi(
                pm2_5=pm2_5,
                pm10=pm10,
                nitrogen_dioxide=no2,
                ozone=o3,
                carbon_monoxide_ug_m3=co,
                sulphur_dioxide=so2,
            )
            series.append(
                {
                    "time": ts,
                    "pm2_5": pm2_5,
                    "pm10": pm10,
                    "nitrogen_dioxide": no2,
                    "ozone": o3,
                    "carbon_monoxide": co,
                    "sulphur_dioxide": so2,
                    "us_aqi": int(us_aqi_val) if us_aqi_val is not None else None,
                    "indian_naqi": naqi.value,
                    "indian_naqi_category": naqi.category,
                }
            )

        return {
            "data_source": "Open-Meteo Air Quality API",
            "timezone": raw.get("timezone", "auto"),
            "units": raw.get("hourly_units") or {},
            "series": series,
        }

    async def get_current_weather(
        self, latitude: float, longitude: float
    ) -> Dict[str, Any]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "wind_speed_10m,wind_direction_10m,weather_code"
            ),
            "hourly": (
                "temperature_2m,relative_humidity_2m,"
                "wind_speed_10m,weather_code"
            ),
            "forecast_days": 2,
            "timezone": "auto",
        }
        raw = await self._fetch_json(self.WEATHER_URL, params)
        current = raw.get("current") or {}
        units = raw.get("current_units") or {}
        w_code = current.get("weather_code")
        wind_deg = current.get("wind_direction_10m")

        hourly = raw.get("hourly") or {}
        times: List[str] = hourly.get("time") or []
        hourly_series: List[Dict[str, Any]] = []
        for idx, ts in enumerate(times[:24]):
            code_i = _safe_at(hourly.get("weather_code"), idx)
            hourly_series.append(
                {
                    "time": ts,
                    "temperature_2m": _safe_at(hourly.get("temperature_2m"), idx),
                    "relative_humidity_2m": _safe_at(
                        hourly.get("relative_humidity_2m"), idx
                    ),
                    "wind_speed_10m": _safe_at(hourly.get("wind_speed_10m"), idx),
                    "condition": wmo_weather_description(
                        int(code_i) if code_i is not None else None
                    ),
                }
            )

        return {
            "data_source": "Open-Meteo Weather Forecast API",
            "timestamp": current.get("time"),
            "timezone": raw.get("timezone", "auto"),
            "temperature": {
                "value": current.get("temperature_2m"),
                "apparent_value": current.get("apparent_temperature"),
                "unit": units.get("temperature_2m", "°C"),
            },
            "humidity": {
                "value": current.get("relative_humidity_2m"),
                "unit": units.get("relative_humidity_2m", "%"),
            },
            "wind": {
                "speed": current.get("wind_speed_10m"),
                "speed_unit": units.get("wind_speed_10m", "km/h"),
                "direction_degrees": wind_deg,
                "direction_compass": wind_direction_compass(wind_deg),
            },
            "weather_code": w_code,
            "condition": wmo_weather_description(
                int(w_code) if w_code is not None else None
            ),
            "hourly": hourly_series,
        }

    async def search_locations(self, query: str, count: int = 6) -> List[Dict[str, Any]]:
        if not query or len(query.strip()) < 2:
            return []
        params = {
            "name": query.strip(),
            "count": max(1, min(15, count)),
            "language": "en",
            "format": "json",
        }
        raw = await self._fetch_json(self.GEOCODING_URL, params)
        results = raw.get("results") or []
        formatted: List[Dict[str, Any]] = []
        for item in results:
            parts = [item.get("name"), item.get("admin1"), item.get("country")]
            label = ", ".join([p for p in parts if p])
            formatted.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "admin1": item.get("admin1"),
                    "country": item.get("country"),
                    "country_code": item.get("country_code"),
                    "label": label,
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                    "timezone": item.get("timezone"),
                }
            )
        return formatted


def _safe_at(arr: Optional[List[Any]], idx: int) -> Any:
    if not arr or idx >= len(arr):
        return None
    return arr[idx]


def get_environmental_provider(_: Settings) -> EnvironmentalDataProvider:
    return OpenMeteoProvider()
