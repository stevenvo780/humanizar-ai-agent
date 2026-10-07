"""Approved company identity and product discovery configuration, never price data."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(min_length=1, max_length=120)
    keywords: list[str] = Field(min_length=1, max_length=20)

    @field_validator("name")
    @classmethod
    def product_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El nombre del producto no puede estar vacío.")
        return value.strip()

    @field_validator("keywords")
    @classmethod
    def product_keywords(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or len(value) > 80 for value in values):
            raise ValueError("Las palabras del catálogo deben tener entre 1 y 80 caracteres.")
        return [value.strip() for value in values]


# Default public identity (Softop), derived only from its published FAQ. Another COMPANY_NAME
# never inherits these strings: it gets the generic assistant name and UI prompts instead.
DEFAULT_COMPANY_NAME = "Softop"
DEFAULT_ASSISTANT_NAME = "Asistente Softop"
DEFAULT_COMPANY_DESCRIPTION = (
    "Software de gestión para ópticas: ventas, inventario, agenda, reportes, garantías y caja."
)
DEFAULT_SUGGESTED_QUESTIONS = (
    "¿Cómo registro una venta de lentes?",
    "¿Qué hago si el inventario no cuadra?",
    "¿Cómo genero un reporte mensual?",
    "¿Cómo cierro caja al final del día?",
)
