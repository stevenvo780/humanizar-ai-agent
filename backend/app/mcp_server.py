"""Read-only MCP stdio transport. Keeps vector storage exclusively inside the API worker."""

from mcp.server.fastmcp import FastMCP

from app.mcp_auth import MCPAPIClient

mcp = FastMCP("Lumen company knowledge")


async def _get(path: str, params: dict[str, str] | None = None) -> str:
    client = MCPAPIClient.from_environment(read_auth=path != "/api/company")
    try:
        return await client.get(path, params)
    finally:
        await client.close()


@mcp.tool()
async def company_info() -> str:
    """Read the configured company's name, description and assistant identity."""
    return await _get("/api/company")


@mcp.tool()
async def search_knowledge(query: str) -> str:
    """Retrieve company knowledge and document/chunk citations from the persistent API store."""
    if not query.strip() or len(query) > 1000:
        raise ValueError("Query must have 1 to 1000 characters.")
    return await _get("/api/search", {"query": query})


if __name__ == "__main__":
    mcp.run(transport="stdio")
