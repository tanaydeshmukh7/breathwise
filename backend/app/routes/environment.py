"""Environmental data routes: AQI current, forecast, history, weather, location search."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo import DESCENDING

from app.config import Settings, get_settings
from app.database import DatabaseHandle, get_db, utcnow
from app.services.environmental_provider import (
    EnvironmentalProviderError,
    get_environmental_provider,
)
from app.utils.security import sanitize_text, serialize_doc

router = APIRouter(prefix="/api", tags=["Environmental Data"])


def _resolve_coords(
    lat: Optional[float], lon: Optional[float], settings: Settings
) -> tuple[float, float]:
    return (
        lat if lat is not None else settings.DEFAULT_LATITUDE,
        lon if lon is not None else settings.DEFAULT_LONGITUDE,
    )


@router.get("/aqi/current")
async def get_current_aqi(
    lat: Optional[float] = Query(default=None, ge=-90, le=90),
    lon: Optional[float] = Query(default=None, ge=-180, le=180),
    city: Optional[str] = Query(default=None, max_length=100),
    db: DatabaseHandle = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    latitude, longitude = _resolve_coords(lat, lon, settings)
    location_name = sanitize_text(city, 100) if city else (
        settings.DEFAULT_CITY if lat is None and lon is None else None
    )
    provider = get_environmental_provider(settings)
    try:
        reading = await provider.get_current_air_quality(
            latitude, longitude, location_name=location_name
        )
    except EnvironmentalProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "environmental_provider_unavailable", "message": str(exc)},
        ) from exc

    # Persist reading snapshot to aqi_history (best-effort)
    location_key = f"{round(latitude, 2)}:{round(longitude, 2)}"
    recorded_at = reading.get("timestamp") or utcnow().isoformat()
    existing = await db.aqi_history.find_one(
        {"location_key": location_key, "recorded_at": recorded_at}
    )
    if not existing:
        await db.aqi_history.insert_one(
            {
                "location_key": location_key,
                "location_name": reading["location"]["name"],
                "latitude": latitude,
                "longitude": longitude,
                "recorded_at": recorded_at,
                "data_source": reading["data_source"],
                "indian_naqi": reading["indices"]["indian_naqi"]["value"],
                "indian_naqi_category": reading["indices"]["indian_naqi"]["category"],
                "us_aqi": reading["indices"]["us_aqi"]["value"],
                "pm2_5": reading["pollutants"]["pm2_5"]["value"],
                "pm10": reading["pollutants"]["pm10"]["value"],
                "nitrogen_dioxide": reading["pollutants"]["nitrogen_dioxide"]["value"],
                "ozone": reading["pollutants"]["ozone"]["value"],
                "created_at": utcnow(),
            }
        )

    return reading


@router.get("/aqi/forecast")
async def get_aqi_forecast(
    lat: Optional[float] = Query(default=None, ge=-90, le=90),
    lon: Optional[float] = Query(default=None, ge=-180, le=180),
    hours: int = Query(default=48, ge=12, le=120),
    past_days: int = Query(default=1, ge=0, le=7),
    settings: Settings = Depends(get_settings),
):
    latitude, longitude = _resolve_coords(lat, lon, settings)
    provider = get_environmental_provider(settings)
    try:
        return await provider.get_air_quality_forecast(
            latitude, longitude, hours=hours, past_days=past_days
        )
    except EnvironmentalProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "environmental_provider_unavailable", "message": str(exc)},
        ) from exc


@router.get("/aqi/history")
async def get_aqi_history(
    lat: Optional[float] = Query(default=None, ge=-90, le=90),
    lon: Optional[float] = Query(default=None, ge=-180, le=180),
    limit: int = Query(default=24, ge=1, le=168),
    page: int = Query(default=1, ge=1),
    db: DatabaseHandle = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    latitude, longitude = _resolve_coords(lat, lon, settings)
    location_key = f"{round(latitude, 2)}:{round(longitude, 2)}"
    skip = (page - 1) * limit
    cursor = (
        db.aqi_history.find({"location_key": location_key})
        .sort("recorded_at", DESCENDING)
        .skip(skip)
        .limit(limit)
    )
    stored = [serialize_doc(doc) for doc in await cursor.to_list(length=limit)]
    total = await db.aqi_history.count_documents({"location_key": location_key})

    # Also return past-days series from Open-Meteo so users see historical hourly context immediately
    provider = get_environmental_provider(settings)
    historical_hourly = []
    try:
        forecast = await provider.get_air_quality_forecast(
            latitude, longitude, hours=24, past_days=3
        )
        historical_hourly = forecast.get("series", [])[:72]
    except EnvironmentalProviderError:
        historical_hourly = []

    return {
        "location_key": location_key,
        "page": page,
        "limit": limit,
        "total_stored_snapshots": total,
        "stored_snapshots": stored,
        "open_meteo_recent_history": historical_hourly,
    }


@router.get("/weather/current")
async def get_current_weather(
    lat: Optional[float] = Query(default=None, ge=-90, le=90),
    lon: Optional[float] = Query(default=None, ge=-180, le=180),
    settings: Settings = Depends(get_settings),
):
    latitude, longitude = _resolve_coords(lat, lon, settings)
    provider = get_environmental_provider(settings)
    try:
        return await provider.get_current_weather(latitude, longitude)
    except EnvironmentalProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "weather_provider_unavailable", "message": str(exc)},
        ) from exc


@router.get("/locations/search")
async def search_locations(
    q: str = Query(..., min_length=2, max_length=100),
    count: int = Query(default=6, ge=1, le=15),
    settings: Settings = Depends(get_settings),
):
    provider = get_environmental_provider(settings)
    try:
        results = await provider.search_locations(sanitize_text(q, 100), count=count)
        return {"query": q, "results": results}
    except EnvironmentalProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "geocoding_unavailable", "message": str(exc)},
        ) from exc
