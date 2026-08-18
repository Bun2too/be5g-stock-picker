from fastapi.testclient import TestClient

from app.config import settings
from app.main import app, guest_usage_cache


def auth_headers(extra=None):
    headers = dict(extra or {})
    if settings.api_key:
        headers["X-API-Key"] = settings.api_key
    return headers


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
    assert payload["twStockEnabled"] is False


def test_screen_returns_quota_message_when_guest_limit_is_reached():
    client = TestClient(app)
    guest_usage_cache.clear()
    session_id = "test-session"
    client.cookies.set(settings.guest_session_cookie_name, session_id)
    guest_usage_cache[f"1.2.3.4:{session_id}"] = settings.guest_screen_limit

    response = client.post(
        "/api/screen",
        headers=auth_headers({"x-forwarded-for": "1.2.3.4"}),
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


def test_symbols_and_portfolio_endpoints_disable_tw_by_default():
    client = TestClient(app)

    symbols = client.get("/api/symbols?market=TW&limit=5", headers=auth_headers())
    assert symbols.status_code == 200
    payload = symbols.json()
    assert payload["meta"]["counts"]["US"] >= 1000
    assert payload["meta"]["counts"]["TW"] >= 1500
    assert payload["symbols"]
    assert all(item["market"] == "US" for item in payload["symbols"])

    saved = client.put(
        "/api/portfolio",
        headers=auth_headers({"x-forwarded-for": "5.6.7.8"}),
        json={"symbols": ["NVDA", "2330.TW"]},
    )
    assert saved.status_code == 400
    assert "Taiwan stock symbols are currently disabled" in saved.json()["detail"]

    saved = client.put(
        "/api/portfolio",
        headers=auth_headers({"x-forwarded-for": "5.6.7.8"}),
        json={"symbols": ["NVDA", "NVDA"]},
    )
    assert saved.status_code == 200
    assert saved.json()["symbols"] == ["NVDA"]

    loaded = client.get("/api/portfolio", headers=auth_headers({"x-forwarded-for": "5.6.7.8"}))
    assert loaded.status_code == 200
    assert loaded.json()["symbols"] == ["NVDA"]


def test_tw_screening_is_rejected_while_feature_flag_is_disabled():
    client = TestClient(app)
    guest_usage_cache.clear()

    response = client.post(
        "/api/screen",
        headers=auth_headers(),
        json={
            "horizon": "1y",
            "risk": "medium",
            "strategy": "momentum",
            "universe": "tw_popular",
            "plannedVolumeUsd": 5000,
            "portfolioSize": 8,
            "diversification": "balanced",
        },
    )

    assert response.status_code == 400
    assert "Taiwan stock screening is currently disabled" in response.json()["detail"]


def test_empty_saved_portfolio_screening_is_rejected():
    client = TestClient(app)
    guest_usage_cache.clear()

    response = client.post(
        "/api/screen",
        headers=auth_headers(),
        json={
            "horizon": "1y",
            "risk": "medium",
            "strategy": "momentum",
            "universe": "mixed_portfolio",
            "selectedSymbols": [],
            "plannedVolumeUsd": 5000,
            "portfolioSize": 8,
            "diversification": "balanced",
        },
    )

    assert response.status_code == 400
    assert "requires at least one selected symbol" in response.json()["detail"]
