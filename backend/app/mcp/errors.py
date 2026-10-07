"""MCP client failures with fixed public messages; none ever includes a credential."""


class MCPAuthenticationRequired(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "API authentication required (401). Run the private mcp-login CLI "
            "or renew LUMEN_API_TOKEN."
        )


class MCPForbidden(ValueError):
    def __init__(self) -> None:
        super().__init__("API access forbidden (403) for this account.")


class MCPUnavailable(ValueError):
    def __init__(self) -> None:
        super().__init__(
            "Lumen API unavailable. Verify the API connection privately; "
            "the saved session is preserved."
        )
