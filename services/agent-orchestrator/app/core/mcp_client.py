"""MCP client for the local SPC MCP server (streamable HTTP transport).

The SPC agent's tools are thin wrappers (see app/tools/spc_tools.py) that call
into this module, so SPC computation runs in the dedicated `spc-mcp` service via
the Model Context Protocol rather than inside the orchestrator. A fresh session
is opened per call, which keeps the integration stateless and resilient to the
MCP server restarting.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from loguru import logger
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from .config import settings


@asynccontextmanager
async def _session():
    async with streamablehttp_client(settings.spc_mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def _text(result) -> str:
    parts = [c.text for c in result.content if getattr(c, "type", None) == "text"]
    return "\n".join(parts) if parts else "(no text content returned)"


async def list_tools() -> list[dict]:
    """List the tools the MCP server advertises (for /spc/mcp/tools + health)."""
    async with _session() as s:
        res = await s.list_tools()
        return [{"name": t.name, "description": (t.description or "").strip(),
                 "input_schema": t.inputSchema or {}} for t in res.tools]


async def call_text(name: str, args: dict) -> str:
    """Call an MCP tool and return its concatenated text content."""
    try:
        async with _session() as s:
            res = await s.call_tool(name, args)
            if getattr(res, "isError", False):
                return f"ERROR from MCP tool {name}: {_text(res)}"
            return _text(res)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"MCP call {name} failed: {exc}")
        return f"ERROR: SPC MCP unavailable for {name}: {exc}"


async def call_image(name: str, args: dict) -> tuple[str, str | None, str | None]:
    """Call an MCP tool; return (text, base64_image, mime_type)."""
    async with _session() as s:
        res = await s.call_tool(name, args)
        text = _text(res)
        for c in res.content:
            if getattr(c, "type", None) == "image":
                return text, c.data, getattr(c, "mimeType", "image/png")
        return text, None, None


async def healthy() -> int:
    """Return the number of MCP tools available (0 if the server is down)."""
    try:
        return len(await list_tools())
    except Exception:  # noqa: BLE001
        return 0
