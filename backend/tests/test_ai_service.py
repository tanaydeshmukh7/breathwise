"""Tests for AI service: Gemini integration, JSON parsing, Pydantic validation, and safe fallbacks."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from google.genai import errors as genai_errors
from openai import APIStatusError, APITimeoutError, RateLimitError

from app.config import Settings
from app.schemas.ai import StructuredAdvisorOutput
from app.services.ai_service import AIService, _extract_json_object


def _sample_env():
    return {
        "air_quality": {
            "location": {"name": "Pune", "latitude": 18.52, "longitude": 73.85},
            "data_source": "Open-Meteo Air Quality API",
            "timestamp": "2026-11-26T09:30",
            "pollutants": {
                "pm2_5": {"value": 68.5, "unit": "μg/m³"},
                "pm10": {"value": 92.0, "unit": "μg/m³"},
                "nitrogen_dioxide": {"value": 24.0, "unit": "μg/m³"},
                "ozone": {"value": 55.0, "unit": "μg/m³"},
            },
            "indices": {
                "indian_naqi": {
                    "value": 129,
                    "category": "Moderately Polluted",
                    "dominant_pollutant": "PM2.5",
                },
                "us_aqi": {"value": 157, "category": "Unhealthy"},
            },
        },
        "weather": {
            "temperature": {"value": 24.5, "unit": "°C"},
            "humidity": {"value": 52, "unit": "%"},
            "wind": {"speed": 4.2, "speed_unit": "km/h"},
            "condition": "Mainly clear",
        },
    }


def _sample_forecast():
    return {
        "best_window": "Around 14:00 (forecast Indian NAQI 95, PM2.5 52.0 μg/m³)",
        "upcoming_hours": [
            {"time": "2026-11-26T07:00", "indian_naqi": 140, "pm2_5": 72.0},
            {"time": "2026-11-26T14:00", "indian_naqi": 95, "pm2_5": 52.0},
        ],
    }


def _mock_gemini_client(generate_side_effect_or_return):
    mock_client = MagicMock()
    if isinstance(generate_side_effect_or_return, Exception):
        mock_generate = AsyncMock(side_effect=generate_side_effect_or_return)
    else:
        mock_generate = AsyncMock(return_value=generate_side_effect_or_return)
    mock_client.aio.models.generate_content = mock_generate
    return mock_client, mock_generate


def test_extract_json_handles_fences_and_think_tags():
    raw = """<think>Analyzing PM2.5...</think>
```json
{
  "summary": "PM2.5 is moderately elevated.",
  "risk_level": "high",
  "recommendations": [
    {"title": "Move workout indoors", "reason": "PM2.5 is 68.5", "action": "Exercise inside", "priority": "high"}
  ]
}
```"""
    parsed = _extract_json_object(raw)
    model = StructuredAdvisorOutput.model_validate(parsed)
    assert model.risk_level == "high"
    assert model.recommendations[0].title == "Move workout indoors"


@pytest.mark.asyncio
async def test_gemini_fallback_when_api_key_missing():
    settings = Settings(AI_PROVIDER="gemini", GEMINI_API_KEY="", ENVIRONMENT="development")
    svc = AIService(settings)
    out, status_str, model_used, err = await svc.analyze_air_quality(
        _sample_env(), {"household_context": "family_with_children"}
    )
    assert status_str == "rule_based_fallback"
    assert model_used == "gemini-2.5-flash"
    assert "GEMINI_API_KEY" in (err or "")
    assert "129" in out.summary
    assert len(out.recommendations) == 3


@pytest.mark.asyncio
async def test_gemini_valid_structured_responses_all_features(monkeypatch):
    settings = Settings(
        AI_PROVIDER="gemini",
        GEMINI_API_KEY="AIzaDummyTestKey",
        GEMINI_MODEL="gemini-2.5-flash",
        ENVIRONMENT="development",
    )
    svc = AIService(settings)

    advisor_payload = json.dumps(
        {
            "summary": "Pune Indian NAQI is 129 (Moderately Polluted) with PM2.5 at 68.5 μg/m³.",
            "risk_level": "high",
            "best_outdoor_window": "14:00–16:00",
            "precautionary_note": "General environmental precaution only — not medical advice.",
            "recommendations": [
                {
                    "title": "Shift intense cardio indoors",
                    "reason": "PM2.5 is 68.5 μg/m³.",
                    "action": "Do indoor mobility or strength training.",
                    "priority": "high",
                }
            ],
        }
    )
    resp = MagicMock()
    resp.text = advisor_payload
    mock_client, mock_gen = _mock_gemini_client(resp)
    monkeypatch.setattr(svc, "_create_gemini_client", lambda: mock_client)

    out, status_str, model_used, err = await svc.analyze_air_quality(
        _sample_env(), {"household_context": "general"}
    )
    assert status_str == "live_gemini"
    assert err is None
    assert model_used == "gemini-2.5-flash"
    assert out.recommendations[0].title == "Shift intense cardio indoors"
    assert mock_gen.await_args.kwargs["model"] == "gemini-2.5-flash"

    # Chat advisor with conversation history
    chat_out, chat_status, _, _ = await svc.chat_advisor(
        "Is it safe to walk outside?",
        _sample_env(),
        {"household_context": "family_with_children"},
        _sample_forecast(),
        [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}],
    )
    assert chat_status == "live_gemini"
    assert chat_out.risk_level == "high"

    # Daily routine
    routine_resp = MagicMock()
    routine_resp.text = json.dumps(
        {
            "summary": "Schedule based on Pune forecast.",
            "optimal_outdoor_window": "14:00–16:00",
            "slots": [
                {
                    "time": "07:00",
                    "phase": "morning",
                    "title": "Check NAQI",
                    "guidance": "Delay outdoor run.",
                    "aqi_context": "Forecast NAQI 140",
                    "priority": "high",
                },
                {
                    "time": "14:00",
                    "phase": "outdoor",
                    "title": "Afternoon walk",
                    "guidance": "Walk in park.",
                    "aqi_context": "Forecast NAQI 95",
                    "priority": "medium",
                },
                {
                    "time": "20:00",
                    "phase": "evening",
                    "title": "Close windows",
                    "guidance": "Use kitchen exhaust.",
                    "aqi_context": "Evening haze",
                    "priority": "high",
                },
            ],
        }
    )
    mock_client2, _ = _mock_gemini_client(routine_resp)
    monkeypatch.setattr(svc, "_create_gemini_client", lambda: mock_client2)
    r_out, r_status, _, _ = await svc.generate_daily_routine(
        _sample_env(), {"household_context": "general"}, _sample_forecast()
    )
    assert r_status == "live_gemini"
    assert len(r_out.slots) == 3


@pytest.mark.asyncio
async def test_gemini_malformed_output_falls_back_safely(monkeypatch):
    settings = Settings(
        AI_PROVIDER="gemini",
        GEMINI_API_KEY="AIzaDummyTestKey",
        GEMINI_MODEL="gemini-2.5-flash",
        ENVIRONMENT="development",
    )
    svc = AIService(settings)

    bad_resp = MagicMock()
    bad_resp.text = "Not valid JSON at all"
    mock_client, _ = _mock_gemini_client(bad_resp)
    monkeypatch.setattr(svc, "_create_gemini_client", lambda: mock_client)

    out, status_str, model_used, err = await svc.analyze_air_quality(
        _sample_env(), {"household_context": "general"}
    )
    assert status_str == "rule_based_fallback"
    assert model_used == "gemini-2.5-flash"
    assert "Malformed AI output" in (err or "")
    assert out.risk_level == "high"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code,msg,expected_substr",
    [
        (400, "API_KEY_INVALID", "Invalid or unauthorized GEMINI_API_KEY"),
        (401, "Unauthorized", "Invalid or unauthorized GEMINI_API_KEY"),
        (429, "RESOURCE_EXHAUSTED", "rate limit or quota exhausted"),
        (404, "NOT_FOUND", "unavailable or not found"),
    ],
)
async def test_gemini_api_errors_handled_without_substitution(
    monkeypatch, code, msg, expected_substr
):
    settings = Settings(
        AI_PROVIDER="gemini",
        GEMINI_API_KEY="AIzaDummyTestKey",
        GEMINI_MODEL="gemini-2.5-flash",
        ENVIRONMENT="development",
    )
    svc = AIService(settings)
    err_exc = genai_errors.APIError(
        code, {"error": {"code": code, "message": msg, "status": msg}}
    )
    mock_client, mock_gen = _mock_gemini_client(err_exc)
    monkeypatch.setattr(svc, "_create_gemini_client", lambda: mock_client)

    _, status_str, model_used, err = await svc.analyze_air_quality(
        _sample_env(), {"household_context": "general"}
    )
    assert status_str == "rule_based_fallback"
    assert model_used == "gemini-2.5-flash"
    assert expected_substr in (err or "")
    assert mock_gen.await_count == 1


@pytest.mark.asyncio
async def test_gemini_timeout_handled_clearly(monkeypatch):
    settings = Settings(
        AI_PROVIDER="gemini",
        GEMINI_API_KEY="AIzaDummyTestKey",
        GEMINI_MODEL="gemini-2.5-flash",
        GEMINI_TIMEOUT_SECONDS=10.0,
        ENVIRONMENT="development",
    )
    svc = AIService(settings)
    mock_client, mock_gen = _mock_gemini_client(asyncio.TimeoutError())
    monkeypatch.setattr(svc, "_create_gemini_client", lambda: mock_client)

    _, status_str, model_used, err = await svc.analyze_air_quality(
        _sample_env(), {"household_context": "general"}
    )
    assert status_str == "rule_based_fallback"
    assert model_used == "gemini-2.5-flash"
    assert "timed out" in (err or "").lower()
    assert mock_gen.await_count == 1


@pytest.mark.asyncio
async def test_verify_ai_connection_gemini_reports_status(monkeypatch):
    settings = Settings(
        AI_PROVIDER="gemini",
        GEMINI_API_KEY="AIzaDummyTestKey",
        GEMINI_MODEL="gemini-2.5-flash",
        ENVIRONMENT="development",
    )
    svc = AIService(settings)

    resp = MagicMock()
    resp.text = '{"status": "ok", "service": "BreatheWise"}'
    resp.model_version = "gemini-2.5-flash"
    mock_client, _ = _mock_gemini_client(resp)
    monkeypatch.setattr(svc, "_create_gemini_client", lambda: mock_client)

    report = await svc.verify_ai_connection()
    assert report["ok"] is True
    assert report["http_status"] == 200
    assert report["model_id"] == "gemini-2.5-flash"
    assert report["provider"] == "google_gemini"
    assert report["response"] == '{"status": "ok", "service": "BreatheWise"}'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,expected_substr",
    [
        (402, "HTTP 402"),
        (401, "HTTP 401"),
        (429, "HTTP 429"),
    ],
)
async def test_legacy_huggingface_errors_retained_without_substitution(
    monkeypatch, status_code, expected_substr
):
    settings = Settings(
        AI_PROVIDER="huggingface",
        HF_TOKEN="hf_test_dummy",
        HF_MODEL="Qwen/Qwen2.5-72B-Instruct",
        HF_FALLBACK_MODELS="Qwen/Qwen3-32B",
        ENVIRONMENT="development",
    )
    svc = AIService(settings)

    req = httpx.Request("POST", "https://router.huggingface.co/v1/chat/completions")
    resp = httpx.Response(status_code=status_code, request=req)
    exc = (
        RateLimitError("rate limit", response=resp, body=None)
        if status_code == 429
        else APIStatusError("api error", response=resp, body=None)
    )

    mock_create = AsyncMock(side_effect=exc)
    mock_client = MagicMock()
    mock_client.chat.completions.create = mock_create
    monkeypatch.setattr(svc, "_create_client", lambda: mock_client)

    _, status_str, model_used, err = await svc.analyze_air_quality(
        _sample_env(), {"household_context": "general"}
    )
    assert status_str == "rule_based_fallback"
    assert model_used == "Qwen/Qwen2.5-72B-Instruct"
    assert expected_substr in (err or "")
    assert mock_create.await_count == 1
