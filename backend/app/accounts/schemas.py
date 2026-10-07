"""Public account request/response models; passwords stay SecretStr end to end."""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: str
    role: Literal["admin", "customer"]


class PublicCustomer(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: str
    role: Literal["customer"]
    created_at: datetime


class CustomerListResponse(BaseModel):
    customers: list[PublicCustomer]
    total: int
    limit: int
    offset: int


class CustomerCreatedResponse(BaseModel):
    customer: PublicCustomer


class SessionResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: PublicUser


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def normalized_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Correo inválido.")
        return normalized

    @field_validator("name")
    @classmethod
    def stripped_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Nombre inválido.")
        return value.strip()


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)
