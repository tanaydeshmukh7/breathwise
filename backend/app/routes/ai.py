"""AI routes: chat, analyze, daily-routine, indoor-advice, sustainable-alternatives."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo import DESCENDING

from app.config import Settings, get_settings
from app.database import DatabaseHandle, get_db, get_optional_db, utcnow
from app.middleware.rate_limit import ai_rate_limiter
from app.schemas.ai import (
    AIResponseEnvelope,
    AdvisorChatRequest,
    AnalyzeAirRequest,
    DailyRoutineRequest,
    IndoorAdviceRequest,
    SustainableAlternativesRequest,
)
from app.services.ai_service import AIService
from app.services.auth_service import get_current_user, get_optional_user
from app.services.environmental_provider import (
    EnvironmentalProviderError,
    get_environmental_provider,
)
from app.utils.security import parse_object_id, sanitize_text, serialize_doc

router = APIRouter(prefix="/api/ai", tags=["AI Air Advisor"])


async def _gather_env_snapshot(
    lat: float,
    lon: float,
    location_name: str,
    settings: Settings,
    include_forecast: bool = False,
) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    provider = get_environmental_provider(settings)
    try:
        aq_coro = provider.get_current_air_quality(lat, lon, location_name=location_name)
        weather_coro = provider.get_current_weather(lat, lon)
        if include_forecast:
            forecast_coro = provider.get_air_quality_forecast(
                lat, lon, hours=24, past_days=0
            )
            aq, weather, forecast = await asyncio.gather(
                aq_coro, weather_coro, forecast_coro
            )
        else:
            aq, weather = await asyncio.gather(aq_coro, weather_coro)
            forecast = None
    except EnvironmentalProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "environmental_data_unavailable",
                "message": (
                    "Cannot generate grounded AI recommendations because live "
                    f"environmental data is unavailable: {exc}"
                ),
            },
        ) from exc

    env_snapshot = {"air_quality": aq, "weather": weather}
    forecast_summary: Optional[Dict[str, Any]] = None
    if forecast and forecast.get("series"):
        upcoming = forecast["series"][:24]
        valid_points = [p for p in upcoming if p.get("indian_naqi") is not None]
        best_pt = min(valid_points, key=lambda p: p["indian_naqi"]) if valid_points else None
        worst_pt = max(valid_points, key=lambda p: p["indian_naqi"]) if valid_points else None
        best_window = (
            f"Around {str(best_pt['time']).split('T')[-1]} (forecast Indian NAQI {best_pt['indian_naqi']}, PM2.5 {best_pt['pm2_5']} μg/m³)"
            if best_pt
            else "Check hourly chart"
        )
        forecast_summary = {
            "best_window": best_window,
            "lowest_forecast_point": best_pt,
            "peak_forecast_point": worst_pt,
            "upcoming_hours": upcoming[:12],
        }
    return env_snapshot, forecast_summary


async def _build_user_context(
    req_ctx: Any, user: Optional[dict], db: Optional[DatabaseHandle]
) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {
        "location_name": sanitize_text(req_ctx.location_name, 100),
        "household_context": req_ctx.household_context,
        "lifestyle_notes": sanitize_text(req_ctx.lifestyle_notes, 400),
        "has_air_purifier": req_ctx.has_air_purifier,
    }
    if user:
        ctx.update(
            {
                "name": user.get("name"),
                "age_group": user.get("age_group"),
                "occupation": user.get("occupation"),
                "transport_preference": user.get("transport_preference"),
                "exercise_habit": user.get("exercise_habit"),
                "household_size": user.get("household_size"),
                "has_air_purifier": user.get("has_air_purifier", req_ctx.has_air_purifier),
            }
        )
        if db is not None:
            members = await db.family_profiles.find({"user_id": user["id"]}).to_list(length=12)
            if members:
                ctx["family_members"] = [
                    {
                        "name": m.get("name"),
                        "member_type": m.get("member_type"),
                        "sensitivity_notes": m.get("sensitivity_notes", ""),
                    }
                    for m in members
                ]
    return ctx


async def _record_recommendation(
    db: Optional[DatabaseHandle],
    user: Optional[dict],
    kind: str,
    env_snapshot: Dict[str, Any],
    result_dict: Dict[str, Any],
    ai_status: str,
    model_used: str,
) -> None:
    if db is None:
        return
    aq = env_snapshot["air_quality"]
    await db.recommendations.insert_one(
        {
            "user_id": user["id"] if user else None,
            "kind": kind,
            "location_name": aq["location"]["name"],
            "indian_naqi": aq["indices"]["indian_naqi"]["value"],
            "us_aqi": aq["indices"]["us_aqi"]["value"],
            "ai_status": ai_status,
            "model_used": model_used,
            "result": result_dict,
            "created_at": utcnow(),
        }
    )


def _provider_label(settings: Settings) -> str:
    return (
        "google_gemini"
        if settings.active_ai_provider == "gemini"
        else "huggingface_router"
    )


@router.get("/models")
async def list_ai_models(settings: Settings = Depends(get_settings)):
    is_gemini = settings.active_ai_provider == "gemini"
    return {
        "active_model": settings.active_ai_model,
        "available_models": settings.active_available_models,
        "provider": (
            "Google Gemini API (google-genai SDK)"
            if is_gemini
            else "Hugging Face Inference Providers (OpenAI-compatible router)"
        ),
        "provider_key": settings.active_ai_provider,
        "configured": bool(
            settings.GEMINI_API_KEY.strip()
            if is_gemini
            else settings.HF_TOKEN.strip()
        ),
    }


@router.get("/verify", dependencies=[Depends(ai_rate_limiter)])
async def verify_ai_endpoint(
    model_id: Optional[str] = Query(default=None, max_length=120),
    settings: Settings = Depends(get_settings),
):
    """Run one minimal completion against the active AI provider and report actual status."""
    ai = AIService(settings)
    return await ai.verify_ai_connection(requested_model=model_id)


@router.get("/conversations")
async def list_conversations(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    db: Optional[DatabaseHandle] = Depends(get_optional_db),
):
    docs = (
        await db.conversations.find({"user_id": current_user["id"]})
        .sort("updated_at", DESCENDING)
        .limit(limit)
        .to_list(length=limit)
    )
    return {"conversations": [serialize_doc(d) for d in docs]}


@router.post(
    "/analyze",
    response_model=AIResponseEnvelope,
    dependencies=[Depends(ai_rate_limiter)],
)
async def analyze_air(
    body: AnalyzeAirRequest,
    db: Optional[DatabaseHandle] = Depends(get_optional_db),
    settings: Settings = Depends(get_settings),
    user: Optional[dict] = Depends(get_optional_user),
):
    env_snapshot, _ = await _gather_env_snapshot(
        body.latitude, body.longitude, body.location_name, settings, include_forecast=False
    )
    user_ctx = await _build_user_context(body, user, db)
    ai = AIService(settings)
    result, ai_status, model_used, err = await ai.analyze_air_quality(
        env_snapshot, user_ctx, requested_model=body.model_id
    )
    result_dict = result.model_dump()
    await _record_recommendation(
        db, user, "air_analysis", env_snapshot, result_dict, ai_status, model_used
    )
    return AIResponseEnvelope(
        ai_status=ai_status,  # type: ignore[arg-type]
        model_used=model_used,
        provider=_provider_label(settings),
        fallback_reason=err,
        data_source=env_snapshot["air_quality"]["data_source"],
        reading_timestamp=env_snapshot["air_quality"]["timestamp"],
        environmental_snapshot=env_snapshot,
        result=result_dict,
    )


@router.post(
    "/chat",
    response_model=AIResponseEnvelope,
    dependencies=[Depends(ai_rate_limiter)],
)
async def chat_advisor(
    body: AdvisorChatRequest,
    db: Optional[DatabaseHandle] = Depends(get_optional_db),
    settings: Settings = Depends(get_settings),
    user: Optional[dict] = Depends(get_optional_user),
):
    question = sanitize_text(body.message, 1200)
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty."
        )

    env_snapshot, forecast_summary = await _gather_env_snapshot(
        body.latitude, body.longitude, body.location_name, settings, include_forecast=True
    )
    user_ctx = await _build_user_context(body, user, db)

    history: List[Dict[str, str]] = []
    conv_id = body.conversation_id
    if user and conv_id and db is not None:
        oid = parse_object_id(conv_id)
        conv = await db.conversations.find_one({"_id": oid, "user_id": user["id"]})
        if conv:
            history = conv.get("messages", [])

    ai = AIService(settings)
    result, ai_status, model_used, err = await ai.chat_advisor(
        question,
        env_snapshot,
        user_ctx,
        forecast_summary,
        history,
        requested_model=body.model_id,
    )
    result_dict = result.model_dump()

    now = utcnow()
    new_turns = [
        {"role": "user", "content": question, "timestamp": now.isoformat()},
        {
            "role": "assistant",
            "content": result.summary,
            "structured": result_dict,
            "ai_status": ai_status,
            "model_used": model_used,
            "timestamp": now.isoformat(),
        },
    ]

    if user and db is not None:
        if conv_id:
            oid = parse_object_id(conv_id)
            upd = await db.conversations.update_one(
                {"_id": oid, "user_id": user["id"]},
                {
                    "$push": {"messages": {"$each": new_turns}},
                    "$set": {"updated_at": now, "location_name": body.location_name},
                },
            )
            if upd.matched_count == 0:
                conv_id = None
        if not conv_id:
            ins = await db.conversations.insert_one(
                {
                    "user_id": user["id"],
                    "location_name": body.location_name,
                    "title": question[:80],
                    "messages": new_turns,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            conv_id = str(ins.inserted_id)

    return AIResponseEnvelope(
        ai_status=ai_status,  # type: ignore[arg-type]
        model_used=model_used,
        provider=_provider_label(settings),
        fallback_reason=err,
        data_source=env_snapshot["air_quality"]["data_source"],
        reading_timestamp=env_snapshot["air_quality"]["timestamp"],
        conversation_id=conv_id,
        environmental_snapshot=env_snapshot,
        result=result_dict,
    )


@router.post(
    "/daily-routine",
    response_model=AIResponseEnvelope,
    dependencies=[Depends(ai_rate_limiter)],
)
async def generate_daily_routine(
    body: DailyRoutineRequest,
    db: Optional[DatabaseHandle] = Depends(get_optional_db),
    settings: Settings = Depends(get_settings),
    user: Optional[dict] = Depends(get_optional_user),
):
    env_snapshot, forecast_summary = await _gather_env_snapshot(
        body.latitude, body.longitude, body.location_name, settings, include_forecast=True
    )
    user_ctx = await _build_user_context(body, user, db)
    ai = AIService(settings)
    result, ai_status, model_used, err = await ai.generate_daily_routine(
        env_snapshot, user_ctx, forecast_summary or {}, requested_model=body.model_id
    )
    result_dict = result.model_dump()
    await _record_recommendation(
        db, user, "daily_routine", env_snapshot, result_dict, ai_status, model_used
    )
    return AIResponseEnvelope(
        ai_status=ai_status,  # type: ignore[arg-type]
        model_used=model_used,
        provider=_provider_label(settings),
        fallback_reason=err,
        data_source=env_snapshot["air_quality"]["data_source"],
        reading_timestamp=env_snapshot["air_quality"]["timestamp"],
        environmental_snapshot=env_snapshot,
        result=result_dict,
    )


@router.post(
    "/indoor-advice",
    response_model=AIResponseEnvelope,
    dependencies=[Depends(ai_rate_limiter)],
)
async def generate_indoor_advice(
    body: IndoorAdviceRequest,
    db: Optional[DatabaseHandle] = Depends(get_optional_db),
    settings: Settings = Depends(get_settings),
    user: Optional[dict] = Depends(get_optional_user),
):
    env_snapshot, _ = await _gather_env_snapshot(
        body.latitude, body.longitude, body.location_name, settings, include_forecast=False
    )
    user_ctx = await _build_user_context(body, user, db)
    indoor_ctx = {
        "cooking_fuel": body.cooking_fuel,
        "uses_incense_or_dhoop": body.uses_incense_or_dhoop,
        "has_air_purifier": body.has_air_purifier,
    }
    ai = AIService(settings)
    result, ai_status, model_used, err = await ai.generate_indoor_advice(
        env_snapshot, user_ctx, indoor_ctx, requested_model=body.model_id
    )
    result_dict = result.model_dump()
    await _record_recommendation(
        db, user, "indoor_advice", env_snapshot, result_dict, ai_status, model_used
    )
    return AIResponseEnvelope(
        ai_status=ai_status,  # type: ignore[arg-type]
        model_used=model_used,
        provider=_provider_label(settings),
        fallback_reason=err,
        data_source=env_snapshot["air_quality"]["data_source"],
        reading_timestamp=env_snapshot["air_quality"]["timestamp"],
        environmental_snapshot=env_snapshot,
        result=result_dict,
    )


@router.post(
    "/sustainable-alternatives",
    response_model=AIResponseEnvelope,
    dependencies=[Depends(ai_rate_limiter)],
)
async def generate_sustainable_alternatives(
    body: SustainableAlternativesRequest,
    db: Optional[DatabaseHandle] = Depends(get_optional_db),
    settings: Settings = Depends(get_settings),
    user: Optional[dict] = Depends(get_optional_user),
):
    env_snapshot, _ = await _gather_env_snapshot(
        body.latitude, body.longitude, body.location_name, settings, include_forecast=False
    )
    user_ctx = await _build_user_context(body, user, db)
    ai = AIService(settings)
    result, ai_status, model_used, err = await ai.generate_sustainable_alternatives(
        env_snapshot,
        user_ctx,
        focus_category=body.focus_category,
        requested_model=body.model_id,
    )
    result_dict = result.model_dump()
    await _record_recommendation(
        db,
        user,
        "sustainable_alternatives",
        env_snapshot,
        result_dict,
        ai_status,
        model_used,
    )
    return AIResponseEnvelope(
        ai_status=ai_status,  # type: ignore[arg-type]
        model_used=model_used,
        provider=_provider_label(settings),
        fallback_reason=err,
        data_source=env_snapshot["air_quality"]["data_source"],
        reading_timestamp=env_snapshot["air_quality"]["timestamp"],
        environmental_snapshot=env_snapshot,
        result=result_dict,
    )
