"""Per-client sliding-window limiter for login, signup and first-admin setup."""

import threading
import time
from collections import deque

from fastapi import HTTPException, Request

_limiter_setup_lock = threading.Lock()


class LoginRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, *, record: bool = True) -> None:
        """Reject a key with 10 recorded attempts in 5 minutes; optionally record this one."""
        with self._lock:
            now = time.monotonic()
            if len(self._attempts) > 10000:
                self._attempts = {
                    address: attempts
                    for address, attempts in self._attempts.items()
                    if attempts and attempts[-1] > now - 300
                }
            attempts = self._attempts.setdefault(key, deque())
            while attempts and attempts[0] <= now - 300:
                attempts.popleft()
            if len(attempts) >= 10:
                raise HTTPException(
                    429, "Demasiados intentos. Prueba más tarde.", headers={"Retry-After": "300"}
                )
            if record:
                attempts.append(now)

    def record(self, key: str) -> None:
        with self._lock:
            self._attempts.setdefault(key, deque()).append(time.monotonic())


def request_limiter(request: Request) -> LoginRateLimiter:
    """One limiter per application, created lazily on ``app.state.auth_limiter``."""
    with _limiter_setup_lock:
        if not hasattr(request.app.state, "auth_limiter"):
            request.app.state.auth_limiter = LoginRateLimiter()
        limiter: LoginRateLimiter = request.app.state.auth_limiter
    return limiter
