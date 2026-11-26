"""Security, authorization, resilience, and edge-case tests for BreatheWise."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.config import Settings
from app.main import app
from app.middleware.rate_limit import SlidingWindowRateLimiter
from app.services.aqi_calculator import indian_naqi_health_implication
from app.services.environmental_provider import (
    EnvironmentalProviderError,
    OpenMeteoProvider,
)
from app.services.impact_calculator import calculate_action_estimate


def _make_request(ip_header: str = "203.0.113.10") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/ai/chat",
        "headers": [(b"x-real-ip", ip_header.encode("latin-1"))],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_auth_and_object_id_rejections_and_security_headers():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in (
            "/api/auth/me",
            "/api/users/profile",
            "/api/routines",
            "/api/impact/summary",
            "/api/ai/conversations",
        ):
            res = await client.get(path)
            assert res.status_code == 401, f"Expected 401 on {path}, got {res.status_code}"

        # Security headers set by middleware
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert "strict-origin" in (res.headers.get("Referrer-Policy") or "")
        assert "geolocation" in (res.headers.get("Permissions-Policy") or "")

        # Invalid/tampered bearer token rejected
        bad_auth = await client.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"}
        )
        assert bad_auth.status_code == 401

        # Valid user registration + malformed ObjectId returns 400
        reg = await client.post(
            "/api/auth/register",
            json={
                "name": "Security Audit User",
                "email": "security.audit@example.com",
                "password": "StrongPassword123!",
                "city": "Pune",
            },
        )
        assert reg.status_code == 201, reg.text
        headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

        bad_rt_put = await client.put(
            "/api/routines/not-a-valid-object-id",
            headers=headers,
            json={"title": "Should Fail"},
        )
        assert bad_rt_put.status_code == 400

        bad_rt_del = await client.delete(
            "/api/routines/not-a-valid-object-id",
            headers=headers,
        )
        assert bad_rt_del.status_code == 400

        bad_fam_del = await client.delete(
            "/api/users/family/not-a-valid-object-id",
            headers=headers,
        )
        assert bad_fam_del.status_code == 400


@pytest.mark.asyncio
async def test_cross_user_ownership_isolation_for_routines_and_family():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_a = await client.post(
            "/api/auth/register",
            json={
                "name": "Owner User",
                "email": "owner.isolation@example.com",
                "password": "StrongPassword123!",
                "city": "Pune",
            },
        )
        user_b = await client.post(
            "/api/auth/register",
            json={
                "name": "Other User",
                "email": "other.isolation@example.com",
                "password": "StrongPassword123!",
                "city": "Pune",
            },
        )
        assert user_a.status_code == 201
        assert user_b.status_code == 201

        headers_a = {"Authorization": f"Bearer {user_a.json()['access_token']}"}
        headers_b = {"Authorization": f"Bearer {user_b.json()['access_token']}"}

        # User A creates a family member and a routine
        fam = await client.post(
            "/api/users/family",
            headers=headers_a,
            json={"name": "Aaji", "member_type": "elderly", "daily_outdoor_minutes": 20},
        )
        assert fam.status_code == 201
        member_id = fam.json()["family_member"]["id"]

        rt = await client.post(
            "/api/routines",
            headers=headers_a,
            json={
                "title": "Owner Morning Plan",
                "location_name": "Pune",
                "summary": "Safe afternoon window.",
                "optimal_outdoor_window": "14:00–16:00",
                "items": [
                    {
                        "time": "14:00",
                        "phase": "outdoor",
                        "title": "Walk",
                        "guidance": "Keep pace moderate.",
                        "aqi_context": "NAQI 95",
                        "priority": "medium",
                    }
                ],
            },
        )
        assert rt.status_code == 201
        routine_id = rt.json()["routine"]["id"]

        # User B must not modify or delete User A's resources
        res_put = await client.put(
            f"/api/routines/{routine_id}",
            headers=headers_b,
            json={"title": "Hijacked"},
        )
        assert res_put.status_code == 404

        res_del_rt = await client.delete(f"/api/routines/{routine_id}", headers=headers_b)
        assert res_del_rt.status_code == 404

        res_del_fam = await client.delete(
            f"/api/users/family/{member_id}", headers=headers_b
        )
        assert res_del_fam.status_code == 404


@pytest.mark.asyncio
async def test_conversation_persistence_and_user_scoping():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg1 = await client.post(
            "/api/auth/register",
            json={
                "name": "Conv User One",
                "email": "conv.one@example.com",
                "password": "StrongPassword123!",
            },
        )
        reg2 = await client.post(
            "/api/auth/register",
            json={
                "name": "Conv User Two",
                "email": "conv.two@example.com",
                "password": "StrongPassword123!",
            },
        )
        assert reg1.status_code == 201
        assert reg2.status_code == 201
        h1 = {"Authorization": f"Bearer {reg1.json()['access_token']}"}
        h2 = {"Authorization": f"Bearer {reg2.json()['access_token']}"}

        chat1 = await client.post(
            "/api/ai/chat",
            headers=h1,
            json={
                "message": "Should I open balcony windows right now?",
                "location_name": "Pune",
                "latitude": 18.5204,
                "longitude": 73.8567,
                "household_context": "general",
            },
        )
        assert chat1.status_code == 200
        conv_id = chat1.json()["conversation_id"]
        assert conv_id is not None

        # Follow-up turn appends to same conversation
        chat2 = await client.post(
            "/api/ai/chat",
            headers=h1,
            json={
                "message": "What about in the evening?",
                "conversation_id": conv_id,
                "location_name": "Pune",
                "latitude": 18.5204,
                "longitude": 73.8567,
                "household_context": "general",
            },
        )
        assert chat2.status_code == 200
        assert chat2.json()["conversation_id"] == conv_id

        convs1 = await client.get("/api/ai/conversations", headers=h1)
        assert convs1.status_code == 200
        matching = [c for c in convs1.json()["conversations"] if c["id"] == conv_id]
        assert len(matching) == 1
        assert len(matching[0]["messages"]) == 4

        convs2 = await client.get("/api/ai/conversations", headers=h2)
        assert convs2.status_code == 200
        assert all(c["id"] != conv_id for c in convs2.json()["conversations"])


@pytest.mark.asyncio
async def test_sliding_window_rate_limiter_enforces_limit_and_prunes():
    limiter = SlidingWindowRateLimiter("test_group", lambda: 2)
    req = _make_request("198.51.100.42")
    await limiter(req)
    await limiter(req)
    with pytest.raises(HTTPException) as exc_info:
        await limiter(req)
    assert exc_info.value.status_code == 429

    # Verify stale bucket pruning triggers when key count exceeds cap
    limiter._MAX_TRACKED_KEYS = 2
    limiter._hits["test_group:stale1"].append(-1000.0)
    limiter._hits["test_group:stale2"].append(-1000.0)
    await limiter(_make_request("198.51.100.99"))
    assert "test_group:stale1" not in limiter._hits
    assert "test_group:stale2" not in limiter._hits


def test_production_security_config_validation():
    insecure = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="replace-with-a-secure-random-64-char-secret",
    )
    assert insecure.has_secure_jwt_secret is False
    warnings = insecure.check_production_security()
    assert len(warnings) == 1
    assert "JWT_SECRET_KEY" in warnings[0]

    secure = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="a" * 64,
    )
    assert secure.has_secure_jwt_secret is True
    assert secure.check_production_security() == []

    dev = Settings(ENVIRONMENT="development", JWT_SECRET_KEY="short")
    assert dev.check_production_security() == []


def test_impact_calculator_quantitative_qualitative_and_custom_cases():
    co2, unit, _ = calculate_action_estimate("public_transport_km", 10.0)
    assert unit == "km"
    assert co2 == pytest.approx(1.0)

    kwh_co2, kwh_unit, _ = calculate_action_estimate("electricity_saved_kwh", -5.0)
    assert kwh_unit == "kWh"
    assert kwh_co2 == 0.0

    qual_co2, qual_unit, qual_basis = calculate_action_estimate("no_open_burning", 2.0)
    assert qual_co2 is None
    assert qual_unit == "event"
    assert "not fabricated" in qual_basis.lower()

    custom_co2, custom_unit, _ = calculate_action_estimate("unknown_custom_action", 3.0)
    assert custom_co2 is None
    assert custom_unit == "action"


def test_indian_naqi_health_implication_coverage():
    for cat in ("Good", "Satisfactory", "Moderately Polluted", "Poor", "Very Poor", "Severe", "Unavailable"):
        text = indian_naqi_health_implication(cat)
        assert isinstance(text, str) and len(text) > 10


@pytest.mark.asyncio
async def test_open_meteo_provider_missing_fields_and_error_handling(monkeypatch):
    provider = OpenMeteoProvider(timeout=5.0)

    # Short location query returns [] without remote call
    assert await provider.search_locations("p") == []

    # Partial payload marks missing pollutants and returns CPCB health_implication
    async def mock_partial_aq(*args, **kwargs):
        return {
            "latitude": 18.52,
            "longitude": 73.85,
            "timezone": "Asia/Kolkata",
            "current_units": {"pm2_5": "μg/m³"},
            "current": {
                "time": "2026-11-26T10:00",
                "pm2_5": 55.0,
                "pm10": None,
                "nitrogen_dioxide": 25.0,
                "ozone": 60.0,
                "carbon_monoxide": None,
                "sulphur_dioxide": None,
                "us_aqi": 140,
            },
        }

    monkeypatch.setattr(provider, "_fetch_json", mock_partial_aq)
    aq = await provider.get_current_air_quality(18.52, 73.85, "Pune")
    assert set(aq["missing_fields"]) == {"PM10", "CO", "SO2"}
    assert aq["indices"]["indian_naqi"]["value"] is not None
    assert aq["indices"]["indian_naqi"]["health_implication"]

    # Timeout and HTTP 500 map cleanly to EnvironmentalProviderError
    req = httpx.Request("GET", provider.AQ_URL)
    timeout_client = MagicMock()
    timeout_client.__aenter__ = AsyncMock(return_value=timeout_client)
    timeout_client.__aexit__ = AsyncMock(return_value=False)
    timeout_client.get = AsyncMock(side_effect=httpx.ReadTimeout("timeout", request=req))
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: timeout_client)

    real_provider = OpenMeteoProvider(timeout=5.0)
    with pytest.raises(EnvironmentalProviderError, match="timed out"):
        await real_provider._fetch_json(real_provider.AQ_URL, {})

    resp_500 = httpx.Response(500, request=req)
    err_client = MagicMock()
    err_client.__aenter__ = AsyncMock(return_value=err_client)
    err_client.__aexit__ = AsyncMock(return_value=False)
    err_client.get = AsyncMock(return_value=resp_500)
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: err_client)

    with pytest.raises(EnvironmentalProviderError, match="HTTP 500"):
        await real_provider._fetch_json(real_provider.AQ_URL, {})
