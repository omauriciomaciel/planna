from app.security import RateLimiter, new_secret, sign_cookie, verify_cookie


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
