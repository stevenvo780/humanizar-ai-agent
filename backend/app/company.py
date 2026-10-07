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


HUMANIZAR_PRODUCTS = (
    ProductDefinition(name="POS Saldantia", keywords=["venta", "tienda", "inventario", "pos"]),
    ProductDefinition(
        name="Deméter", keywords=["distribuidora", "alimento", "ruta", "despacho", "cartera"]
    ),
    ProductDefinition(name="Graf Commerce", keywords=["catalogo", "tienda", "comercio", "pedido"]),
    ProductDefinition(name="Xenía", keywords=["crm", "cliente", "embudo", "comercial"]),
    ProductDefinition(name="Cauce V3", keywords=["coordinacion", "gobierno", "flota", "agente"]),
    ProductDefinition(name="Agora", keywords=["investigacion", "markdown", "logica"]),
    ProductDefinition(name="Aletheia", keywords=["marketing", "metrica", "campana"]),
    ProductDefinition(name="Apothḗke", keywords=["almacen", "inventario", "pedido"]),
    ProductDefinition(
        name="Koinonía", keywords=["comunidad", "publicacion", "biblioteca", "evento"]
    ),
    ProductDefinition(name="Chrónos", keywords=["hora", "proyecto", "freelancer"]),
    ProductDefinition(name="Gravitatoria", keywords=["cotizacion", "entrega", "fisico"]),
    ProductDefinition(name="Prizma", keywords=["dian", "facturacion", "credito", "pos"]),
    ProductDefinition(name="Práxis", keywords=["ingenieria", "integral"]),
    ProductDefinition(name="Érgon", keywords=["personalizado", "software", "desarrollo"]),
    ProductDefinition(
        name="Agentes de IA a medida",
        keywords=["atencion", "cobranza", "conciliacion", "whatsapp", "correo"],
    ),
)

HUMANIZAR_QUESTIONS = [
    "¿Qué productos y servicios ofrece Humanizar?",
    "¿Cómo funcionan los agentes de IA a medida de Humanizar?",
    "¿Qué es Cauce V3?",
    "¿Cómo puedo contactar a Humanizar para solicitar una demostración?",
]
