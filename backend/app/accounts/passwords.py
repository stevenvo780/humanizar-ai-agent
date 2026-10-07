"""Argon2 password hashing bounded by a small number of concurrent hashing slots."""

import secrets
import threading

from pwdlib import PasswordHash

_passwords = PasswordHash.recommended()
_hash_slots = threading.BoundedSemaphore(2)
# Unknown accounts still pay one verification, so timing does not reveal registered emails.
_dummy_hash = _passwords.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    with _hash_slots:
        return _passwords.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    with _hash_slots:
        try:
            return _passwords.verify(
                password, password_hash if password_hash is not None else _dummy_hash
            )
        except Exception:
            return False
