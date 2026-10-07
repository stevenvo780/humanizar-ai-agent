from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.business.company import (
    DEFAULT_ASSISTANT_NAME,
    DEFAULT_COMPANY_DESCRIPTION,
    DEFAULT_COMPANY_NAME,
    DEFAULT_SUGGESTED_QUESTIONS,
    ProductDefinition,
)
from app.core.settings import Settings
from app.knowledge.ingestion import ParsedDocument
from app.knowledge.store import KnowledgeStore
from app.main import create_app
from app.tools.registry import ToolRegistry


def test_default_identity_only_applies_to_the_default_company(settings: Settings) -> None:
    default = settings.__class__(llm_mode="demo", data_dir=settings.data_dir)
    assert default.company_name == DEFAULT_COMPANY_NAME == "Softop"
    assert default.assistant_name == DEFAULT_ASSISTANT_NAME
    assert default.company_description == DEFAULT_COMPANY_DESCRIPTION
    assert default.suggested_questions == list(DEFAULT_SUGGESTED_QUESTIONS)
    assert default.website is None and default.products == ()
    other = settings.model_copy(update={"company_name": "Acme"})
    assert other.website is None and other.products == () and other.suggested_questions is None
    with TestClient(create_app(other)) as client:
        company = client.get("/api/company").json()
        assert company["company_name"] == "Acme"
        assert "website" not in company and "suggested_questions" not in company
        tools = client.get("/api/tools").json()["tools"]
        assert DEFAULT_COMPANY_NAME not in str(tools)
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
        {"company_suggested_questions": ["x"] * 13},
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
        assert DEFAULT_COMPANY_NAME not in found.trace.output
        assert custom.website == "https://acme.example/"
        assert custom.suggested_questions == ["¿Qué hace AcmeStock?"]
    finally:
        await registry.close()


def test_no_implicit_products_for_other_company(settings: Settings) -> None:
    settings = settings.model_copy(update={"company_name": "Acme"})
    assert settings.products == ()
    override = settings.model_copy(
        update={"company_products": [ProductDefinition(name="AcmeStock", keywords=["inventario"])]}
    )
    assert override.products[0].name == "AcmeStock"
