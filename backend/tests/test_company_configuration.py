from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.company import ProductDefinition
from app.ingestion import ParsedDocument
from app.main import create_app
from app.settings import Settings
from app.storage import KnowledgeStore
from app.tools import ToolRegistry


def test_company_defaults_only_apply_to_humanizar(settings: Settings) -> None:
    humanizar = settings.model_copy(update={"company_name": "Humanizar"})
    assert humanizar.website == "https://humanizar.tech/"
    assert humanizar.products and humanizar.suggested_questions
    other = settings.model_copy(update={"company_name": "Acme"})
    assert other.website is None and other.products == () and other.suggested_questions is None
    with TestClient(create_app(other)) as client:
        company = client.get("/api/company").json()
        assert company["company_name"] == "Acme"
        assert "website" not in company and "suggested_questions" not in company
        tools = client.get("/api/tools").json()["tools"]
        assert "Humanizar" not in str(tools)
        for item in tools:
            schema = item["input_schema"]
            assert schema["type"] == "object" and schema["additionalProperties"] is False
            assert set(schema["required"]) == set(schema["properties"])
    independent = settings.__class__(
        company_name="Acme", llm_mode="demo", data_dir=settings.data_dir
    )
    assert independent.assistant_name == "Lumen" and independent.company_description == ""


@pytest.mark.parametrize(
    "update",
    [
        {"company_website": "https://user:password@example.invalid"},
        {"company_website": "javascript:alert(1)"},
        {"company_website": "http://example.invalid:99999"},
        {"company_suggested_questions": [""]},
        {"company_suggested_questions": ["x"] * 9},
        {"company_products": [{"name": "AcmeStock", "keywords": ["inventario"], "price": 29}]},
        {"company_products": [{"name": " ", "keywords": ["inventario"]}]},
        {"company_products": [{"name": "AcmeStock", "keywords": [""]}]},
    ],
)
def test_public_company_configuration_validation(
    settings: Settings, update: dict[str, Any]
) -> None:
    with pytest.raises(ValidationError):
        settings.__class__(**(settings.model_dump() | update))


async def test_configured_product_needs_company_document_evidence(
    settings: Settings, store: KnowledgeStore
) -> None:
    custom = settings.__class__(
        **(
            settings.model_dump()
            | {
                "company_name": "Acme",
                "company_website": "https://acme.example/",
                "company_suggested_questions": ["¿Qué hace AcmeStock?"],
                "company_products": [{"name": "AcmeStock", "keywords": ["inventario", "stock"]}],
            }
        )
    )
    registry = ToolRegistry(custom, store)
    try:
        missing = await registry.run("recommend_product", {"process": "inventario"})
        assert missing.sources == [] and '"recommendations": []' in missing.trace.output
        store.add_documents(
            [
                ParsedDocument(
                    "acme.md", "AcmeStock controla inventario y stock. No hay precios publicados."
                )
            ]
        )
        found = await registry.run("recommend_product", {"process": "inventario"})
        assert found.sources and "AcmeStock" in found.trace.output
        assert "No hay precios publicados" in found.trace.output
        assert "Humanizar" not in found.trace.output and "Cauce" not in found.trace.output
        assert custom.website == "https://acme.example/"
        assert custom.suggested_questions == ["¿Qué hace AcmeStock?"]
    finally:
        await registry.close()


def test_no_implicit_humanizar_products_for_other_company(settings: Settings) -> None:
    settings = settings.model_copy(update={"company_name": "Acme"})
    assert settings.products == ()
    override = settings.model_copy(
        update={"company_products": [ProductDefinition(name="AcmeStock", keywords=["inventario"])]}
    )
    assert override.products[0].name == "AcmeStock"
