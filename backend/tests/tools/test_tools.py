import json

import httpx
import pytest

from app.core.security import redact, safe_input
from app.core.settings import Settings
from app.knowledge.store import KnowledgeStore
from app.tools.calculator import calculate
from app.tools.registry import ToolRegistry


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("(29 + 79) * 12", "1296"),
        ("2**8", "256"),
        ("7//2", "3"),
        ("-3 + 5", "2"),
    ],
)
def test_calculation(expression: str, expected: str) -> None:
    assert calculate(expression) == expected


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('id')",
        "2**9999",
        "9**9**9",
        "1/0",
        "True+1",
        "[1,2]",
        "float('nan')",
        "1e999",
        "(" * 20 + "2" + ")" * 20,
    ],
)
def test_calculation_rejects_code_and_huge_numbers(expression: str) -> None:
    if expression == "(" * 20 + "2" + ")" * 20:
        assert calculate(expression) == "2"  # Parentheses without operations consume no AST depth.
    else:
        with pytest.raises((ValueError, SyntaxError, ZeroDivisionError, OverflowError)):
            calculate(expression)


async def test_terminal_named_presets_and_unavailability(
    settings: Settings,
    store: KnowledgeStore,
) -> None:
    registry = ToolRegistry(settings, store)
    await registry.http.aclose()
    calls: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        payload = json.loads(request.content)
        assert payload == {"command": "pwd"}
        return httpx.Response(200, json={"stdout": "/sandbox\n", "stderr": "", "exit_code": 0})

    registry.http = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    try:
        blocked = await registry.run("terminal", {"command": "pwd; cat /etc/passwd"})
        assert blocked.trace.status == "error" and calls == []
        result = await registry.run("terminal", {"command": "pwd"})
        assert result.trace.status == "completed" and calls == ["/run"]
        assert "/sandbox" in result.trace.output
    finally:
        await registry.close()


async def test_unreachable_tools_safe_error(settings: Settings, store: KnowledgeStore) -> None:
    registry = ToolRegistry(settings, store)
    try:
        assert not await registry.sandbox_available()
        trace = (await registry.run("terminal", {"command": "pwd"})).trace
        assert trace.status == "error" and "no disponible" in trace.output
        assert (await registry.run("mcp_company_info", {})).trace.status == "error"
        assert (
            await registry.run("calculate", {"expression": "1+2", "extra": "no"})
        ).trace.status == "error"
    finally:
        await registry.close()


def test_trace_secret_redaction() -> None:
    clean = safe_input(
        {
            "api_key": "private",
            "nested": {"token": "another"},
            "query": "sk-ant-abcdefghijklmnopqrstuvwxyz",
        }
    )
    assert clean["api_key"] == "[REDACTADO]"
    assert clean["nested"]["token"] == "[REDACTADO]"
    assert "sk-ant" not in clean["query"]


@pytest.mark.parametrize(
    "header",
    [
        "Authorization: Basic c3ludGhldGljOm9ubHk=",
        '"Proxy-Authorization": "Basic c3ludGhldGljOm9ubHk="',
        "authorization: Bearer synthetic.jwt.placeholder",
    ],
)
def test_authorization_headers_redacted(header: str) -> None:
    assert "c3ludGhldGlj" not in redact(header)
    assert "synthetic.jwt" not in redact(header)
    assert "[REDACTADO]" in redact(header)


async def test_ui_and_provider_share_tool_contract(
    settings: Settings, store: KnowledgeStore
) -> None:
    registry = ToolRegistry(settings, store)
    try:
        catalog = {item["name"]: item for item in registry.catalog()}
        for schema in registry.schemas():
            assert catalog[schema["name"]]["input_schema"] == schema["input_schema"]
        catalog["calculate"]["input_schema"]["properties"].clear()
        assert registry.catalog()[1]["input_schema"]["properties"]
        blocked = await registry.run("unexpected_tool", {})
        assert blocked.trace.status == "error"
        invalid = await registry.run("calculate", {"expression": 123})
        assert invalid.trace.status == "error"
    finally:
        await registry.close()
