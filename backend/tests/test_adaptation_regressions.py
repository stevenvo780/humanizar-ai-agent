"""Regressions for behaviour that commonly breaks while adapting the baseline to a new brief."""

from pathlib import Path

import pytest

from app.knowledge_bootstrap import load_initial_knowledge
from app.security import SECRET_PATTERN, redact
from app.settings import Settings
from app.storage import KnowledgeStore
from app.tool_definitions import ToolDefinition, flag, number, text


def test_tool_definitions_accept_typed_and_optional_parameters() -> None:
    definition = ToolDefinition(
        "quote",
        "Cotización de prueba",
        {"plan": text(40), "seats": number(1, 500, integer=True), "annual": flag()},
        optional=frozenset({"annual"}),
    )
    assert definition.input_schema["required"] == ["plan", "seats"]
    definition.validate({"plan": "pro", "seats": 10})
    definition.validate({"plan": "pro", "seats": 10, "annual": True})
    for invalid in (
        {"plan": "pro"},
        {"plan": "pro", "seats": 0},
        {"plan": "pro", "seats": 2.5},
        {"plan": "pro", "seats": True},
        {"plan": "pro", "seats": 3, "annual": "yes"},
        {"plan": "pro", "seats": 3, "extra": "x"},
    ):
        with pytest.raises(ValueError):
            definition.validate(invalid)


@pytest.mark.parametrize(
    "prose",
    [
        "Para cambiar tu password: ingresa a Ajustes",
        "PASSWORD: restablecer desde el portal",
        "API_TOKEN: solicitarlo al administrador",
        "Password: mínimo 8 caracteres",
        'Para cambiar tu password: "[REDACTED]"',
    ],
)
def test_secret_pattern_ignores_company_prose(prose: str) -> None:
    assert SECRET_PATTERN.search(prose) is None


@pytest.mark.parametrize(
    "secret",
    [
        "PASSWORD=abcdefghi",
        '{"PASSWORD":"exam-placeholder"}',
        "password: 'hunter2hunter'",
        # Built at runtime so secret scanners do not flag a synthetic fixture.
        "API_TOKEN: " + "synthetic" + "123456",
    ],
)
def test_secret_pattern_still_detects_credentials(secret: str) -> None:
    assert "[REDACTADO]" in redact(secret)


def test_bad_initial_document_is_skipped(
    settings: Settings, store: KnowledgeStore, tmp_path: Path
) -> None:
    directory = tmp_path / "corpus"
    directory.mkdir()
    (directory / "ok.md").write_text("Softop ofrece soporte técnico.")
    (directory / "empty.md").write_text("")
    (directory / "leak.txt").write_text("PASSWORD=abcdefghi")
    load_initial_knowledge(store, settings.model_copy(update={"knowledge_dir": directory}))
    assert {document.name for document in store.list_documents().documents} == {"ok.md"}


def test_empty_knowledge_dir_disables_initial_corpus(settings: Settings) -> None:
    configured = Settings.model_validate({**settings.model_dump(), "knowledge_dir": ""})
    assert configured.knowledge_dir is None
