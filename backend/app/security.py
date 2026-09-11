import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from threading import Lock

from app.config import settings


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def sign_cookie(value: str) -> str:
    signature = hmac.new(
        settings.cookie_secret.encode(), value.encode(), hashlib.sha256
    ).hexdigest()
    return f"{value}.{signature}"


def verify_cookie(value: str) -> str | None:
    try:
        raw, signature = value.rsplit(".", 1)
    except ValueError:
        return None
    expected = hmac.new(settings.cookie_secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return raw if hmac.compare_digest(signature, expected) else None


def new_secret() -> str:
    return secrets.token_urlsafe(32)


class RateLimiter:
    # ponytail: memória local basta para um processo; mover ao Redis ao escalar workers.
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        instant = time.monotonic() if now is None else now
        with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0] <= instant - self.window_seconds:
                attempts.popleft()
            if len(attempts) >= self.limit:
                return False
            attempts.append(instant)
            return True


email_limiter = RateLimiter(3, 15 * 60)
ip_limiter = RateLimiter(10, 15 * 60)
