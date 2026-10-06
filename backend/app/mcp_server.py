"""Read-only MCP stdio transport. Keeps vector storage exclusively inside the API worker."""

import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Lumen company knowledge")


async def _get(path: str, params: dict[str, str] | None = None) -> str:
    url = os.environ.get("LUMEN_API_URL", "http://127.0.0.1:8000").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
            response = await client.get(url + path, params=params)
            response.raise_for_status()
            return response.text
    except httpx.HTTPError as exc:
        raise ValueError(
            "Lumen API unavailable; start the API before using its MCP tools."
        ) from exc


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
