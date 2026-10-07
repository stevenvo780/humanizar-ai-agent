"""Identity records, session lifetime and domain errors shared by SQLite and PostgreSQL."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Role = Literal["admin", "customer"]
REFRESH_SECONDS = 7 * 24 * 60 * 60


@dataclass(frozen=True)
class User:
    id: str
    name: str
    email: str
    role: Role
    password_hash: str = field(repr=False)


@dataclass(frozen=True)
class Customer:
    id: str
    name: str
    email: str
    created_at: datetime
    role: Literal["customer"] = "customer"


def validate_customer_page(limit: int, offset: int) -> None:
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
        raise ValueError("La paginación de clientes es inválida.")


class SetupAlreadyComplete(ValueError):
    pass


class RegistrationUnavailable(ValueError):
    pass
