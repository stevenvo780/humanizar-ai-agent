"""Per-client sliding-window limiters for authentication and public question endpoints."""

import math
import threading
import time
from collections import deque

from fastapi import HTTPException, Request

_limiter_setup_lock = threading.Lock()


class SlidingWindowLimiter:
    """Reject a key with ``limit`` recorded attempts in the last ``window`` seconds."""

    def __init__(
        self,
        limit: int = 10,
        window: float = 300,
        message: str = "Demasiados intentos. Prueba más tarde.",
    ) -> None:
        self.limit, self.window, self.message = limit, window, message
        self._attempts: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, *, record: bool = True) -> None:
        """Raise 429 with ``Retry-After`` when the key is over budget; optionally record it."""
        with self._lock:
            now = time.monotonic()
            if len(self._attempts) > 10000:
                self._attempts = {
                    address: attempts
                    for address, attempts in self._attempts.items()
                    if attempts and attempts[-1] > now - self.window
                }
            attempts = self._attempts.setdefault(key, deque())
            while attempts and attempts[0] <= now - self.window:
                attempts.popleft()
            if len(attempts) >= self.limit:
                retry = max(1, math.ceil(attempts[0] + self.window - now))
                raise HTTPException(429, self.message, headers={"Retry-After": str(retry)})
            if record:
                attempts.append(now)

    def record(self, key: str) -> None:
        with self._lock:
            self._attempts.setdefault(key, deque()).append(time.monotonic())


def client_key(request: Request) -> str:
    """Client address as seen by the server (proxy headers are trusted only per deployment)."""
    return request.client.host if request.client else "unknown"


def app_limiter(
    request: Request, name: str, limit: int, window: float, message: str
) -> SlidingWindowLimiter:
    """One limiter per application and purpose, created lazily on ``app.state.<name>``."""
    with _limiter_setup_lock:
        if not hasattr(request.app.state, name):
            setattr(request.app.state, name, SlidingWindowLimiter(limit, window, message))
        limiter: SlidingWindowLimiter = getattr(request.app.state, name)
    return limiter


def request_limiter(request: Request) -> SlidingWindowLimiter:
    """Login, signup and first-admin setup: 10 attempts per client in 5 minutes."""
    return app_limiter(request, "auth_limiter", 10, 300, "Demasiados intentos. Prueba más tarde.")
