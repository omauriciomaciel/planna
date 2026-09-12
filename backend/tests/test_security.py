import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.security import RateLimiter, csrf_origin_allowed, new_secret, sign_cookie, verify_cookie


def test_signed_cookie_rejects_tampering() -> None:
    raw = new_secret()
    signed = sign_cookie(raw)

    assert verify_cookie(signed) == raw
    assert verify_cookie(f"{signed}x") is None


def test_rate_limiter_reopens_after_window() -> None:
    limiter = RateLimiter(limit=2, window_seconds=10)

    assert limiter.allow("member@example.com", now=0)
    assert limiter.allow("member@example.com", now=1)
    assert not limiter.allow("member@example.com", now=2)
    assert limiter.allow("member@example.com", now=11)


def test_csrf_accepts_only_configured_origins() -> None:
    assert csrf_origin_allowed("http://localhost:3000")
    assert not csrf_origin_allowed(None)
    assert not csrf_origin_allowed("https://evil.example")

    client = TestClient(app)
    client.cookies.set("planna_session", "invalid")
    response = client.post(
        "/auth/logout", headers={"Origin": "https://evil.example"}
    )

    assert response.status_code == 403
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-request-id"]


def test_production_requires_https_and_smtp() -> None:
    values = {
        "app_env": "production",
        "cookie_secret": "test-cookie-secret-with-at-least-32-characters",
        "frontend_url": "https://planna.example",
        "public_api_url": "https://planna.example/api",
    }
    with pytest.raises(ValueError, match="SMTP_HOST"):
        Settings(**values)
    with pytest.raises(ValueError, match="HTTPS"):
        Settings(
            **{**values, "frontend_url": "http://planna.example"},
            smtp_host="smtp.example",
        )
