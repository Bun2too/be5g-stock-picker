from fastapi.testclient import TestClient

from app.config import settings
from app.main import app, guest_usage_cache


def test_healthz_returns_status_payload():
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "alpacaConfigured" in payload
    assert "mode" in payload
    assert "feed" in payload
    assert payload["guestQuota"]["limit"] == settings.guest_screen_limit


def test_screen_returns_quota_message_when_guest_limit_is_reached():
    client = TestClient(app)
    guest_usage_cache.clear()
    session_id = "test-session"
    client.cookies.set(settings.guest_session_cookie_name, session_id)
    guest_usage_cache[f"1.2.3.4:{session_id}"] = settings.guest_screen_limit

    response = client.post(
        "/api/screen",
        headers={"x-forwarded-for": "1.2.3.4"},
        json={
            "horizon": "1y",
            "risk": "medium",
            "strategy": "momentum",
            "universe": "mega_caps",
            "plannedVolumeUsd": 5000,
            "portfolioSize": 8,
            "diversification": "balanced",
        },
    )

    assert response.status_code == 429
    payload = response.json()
    assert "subscription" in payload["detail"]["message"]
    assert payload["detail"]["quota"]["remaining"] == 0
