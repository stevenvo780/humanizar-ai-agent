import re
from typing import Any, cast

# Deliberately narrow patterns; company documents remain useful while common leaked keys do not.
SECRET_PATTERN = re.compile(
    r"sk-ant-[A-Za-z0-9_-]{12,}|sk-[A-Za-z0-9_-]{24,}|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16}|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"(?i:(?:proxy-)?authorization)[\"']?\s*[:=]\s*[\"']?"
    r"(?i:basic|bearer)\s+[A-Za-z0-9._~+/=-]+|"
    r"(?i:ANTHROPIC_API_KEY|QDRANT_API_KEY|API_TOKEN|PASSWORD)[\"']?\s*[:=]\s*"
    r"[\"']?[^\s\"']{6,}"
)
SENSITIVE_FIELDS = re.compile(r"(?i)(?:password|secret|token|authorization|api[_-]?key|cookie)")


def redact(text: str) -> str:
    return SECRET_PATTERN.sub("[REDACTADO]", text)


def safe_input(value: dict[str, Any]) -> dict[str, Any]:
    def clean(item: Any) -> Any:
        if isinstance(item, str):
            return redact(item)
        if isinstance(item, dict):
            return {
                str(key): "[REDACTADO]" if SENSITIVE_FIELDS.search(str(key)) else clean(val)
                for key, val in item.items()
            }
        if isinstance(item, list):
            return [clean(val) for val in item]
        return item

    return cast(dict[str, Any], clean(value))
