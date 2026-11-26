"""End-to-end API route tests for auth, persistence, routines, impact, and AI."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["database"]["connected"] is True


@pytest.mark.asyncio
async def test_auth_profile_routines_and_impact_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register
        reg = await client.post(
            "/api/auth/register",
            json={
                "name": "Aarav Kulkarni",
                "email": "aarav.kulkarni@gmail.com",
                "password": "StrongPassword123!",
                "city": "Pune",
                "latitude": 18.5204,
                "longitude": 73.8567,
            },
        )
        assert reg.status_code == 201, reg.text
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Duplicate registration rejected
        dup = await client.post(
            "/api/auth/register",
            json={
                "name": "Aarav Kulkarni",
                "email": "aarav.kulkarni@gmail.com",
                "password": "StrongPassword123!",
            },
        )
        assert dup.status_code == 409

        # Login
        login = await client.post(
            "/api/auth/login",
            json={
                "email": "aarav.kulkarni@gmail.com",
                "password": "StrongPassword123!",
            },
        )
        assert login.status_code == 200

        # /me
        me = await client.get("/api/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == "aarav.kulkarni@gmail.com"

        # Profile & family member
        fam = await client.post(
            "/api/users/family",
            headers=headers,
            json={
                "name": "Meera",
                "member_type": "elderly",
                "sensitivity_notes": "Prefers gentle indoor morning walks on hazy days",
                "daily_outdoor_minutes": 30,
            },
        )
        assert fam.status_code == 201
        member_id = fam.json()["family_member"]["id"]

        prof = await client.get("/api/users/profile", headers=headers)
        assert prof.status_code == 200
        assert len(prof.json()["family_profiles"]) == 1

        # Save Routine CRUD
        rt = await client.post(
            "/api/routines",
            headers=headers,
            json={
                "title": "Pune Winter Smog Routine",
                "location_name": "Pune",
                "summary": "Avoid morning peak haze.",
                "optimal_outdoor_window": "14:00–16:00",
                "items": [
                    {
                        "time": "07:00",
                        "phase": "morning",
                        "title": "Check NAQI",
                        "guidance": "Check reading before opening windows.",
                        "aqi_context": "NAQI 135",
                        "priority": "high",
                    }
                ],
            },
        )
        assert rt.status_code == 201
        routine_id = rt.json()["routine"]["id"]

        listed = await client.get("/api/routines", headers=headers)
        assert listed.status_code == 200
        assert listed.json()["total"] >= 1

        upd = await client.put(
            f"/api/routines/{routine_id}",
            headers=headers,
            json={"title": "Updated Pune Routine"},
        )
        assert upd.status_code == 200
        assert upd.json()["routine"]["title"] == "Updated Pune Routine"

        # Impact logging
        act = await client.post(
            "/api/impact/actions",
            headers=headers,
            json={
                "category": "transportation",
                "action_type": "walk_cycle_km",
                "action_name": "Cycled to Shivajinagar office",
                "quantity": 6.0,
            },
        )
        assert act.status_code == 201
        assert act.json()["action"]["estimated_co2e_avoided_kg"] == pytest.approx(1.026, rel=1e-2)

        summary = await client.get("/api/impact/summary", headers=headers)
        assert summary.status_code == 200
        assert summary.json()["total_actions"] >= 1
        assert summary.json()["walk_cycle_km"] >= 6.0

        # Cleanup family + routine
        del_fam = await client.delete(f"/api/users/family/{member_id}", headers=headers)
        assert del_fam.status_code == 200
        del_rt = await client.delete(f"/api/routines/{routine_id}", headers=headers)
        assert del_rt.status_code == 200


@pytest.mark.asyncio
async def test_live_open_meteo_and_ai_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        aq = await client.get("/api/aqi/current?lat=18.5204&lon=73.8567&city=Pune")
        assert aq.status_code == 200, aq.text
        aq_json = aq.json()
        assert aq_json["location"]["name"] == "Pune"
        assert "indian_naqi" in aq_json["indices"]
        assert "us_aqi" in aq_json["indices"]
        assert aq_json["indices"]["indian_naqi"]["methodology"] == "CPCB Indian National AQI (NAQI)"

        wx = await client.get("/api/weather/current?lat=18.5204&lon=73.8567")
        assert wx.status_code == 200
        assert wx.json()["temperature"]["value"] is not None

        loc = await client.get("/api/locations/search?q=Pune")
        assert loc.status_code == 200
        assert len(loc.json()["results"]) >= 1

        chat = await client.post(
            "/api/ai/chat",
            json={
                "message": "Is it safe to walk outside today?",
                "location_name": "Pune",
                "latitude": 18.5204,
                "longitude": 73.8567,
                "household_context": "family_with_children",
            },
        )
        assert chat.status_code == 200
        chat_json = chat.json()
        assert chat_json["provider"] == "google_gemini"
        assert chat_json["ai_status"] in ("live_gemini", "rule_based_fallback")
        assert len(chat_json["result"]["recommendations"]) >= 1

        routine = await client.post(
            "/api/ai/daily-routine",
            json={
                "location_name": "Pune",
                "latitude": 18.5204,
                "longitude": 73.8567,
                "household_context": "general",
            },
        )
        assert routine.status_code == 200
        assert routine.json()["provider"] == "google_gemini"
        assert len(routine.json()["result"]["slots"]) >= 3

        verify = await client.get("/api/ai/verify")
        assert verify.status_code == 200
        assert verify.json()["provider"] == "google_gemini"
        assert "model_id" in verify.json()


@pytest.mark.asyncio
async def test_unavailable_environmental_provider_returns_503(monkeypatch):
    from app.routes import environment as env_routes
    from app.services.environmental_provider import EnvironmentalProviderError

    class FailingProvider:
        async def get_current_air_quality(self, *args, **kwargs):
            raise EnvironmentalProviderError("Simulated upstream outage")

    monkeypatch.setattr(env_routes, "get_environmental_provider", lambda _: FailingProvider())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/aqi/current?lat=18.5204&lon=73.8567")
    assert res.status_code == 503
    assert res.json()["detail"]["error"] == "environmental_provider_unavailable"

