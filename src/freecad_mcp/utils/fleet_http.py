"""HTTP helpers for cross-fleet MCP tool calls."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_FREECAD_URL = "http://127.0.0.1:10944"
DEFAULT_QCAD_URL = "http://127.0.0.1:10966"
DEFAULT_RESONITE_URL = "http://127.0.0.1:10979"

_HEALTH_PATHS = ("/api/v1/health", "/api/v1/status", "/api/health", "/health")
_TOOL_PATH = "/api/v1/control/tool"


async def check_http_health(base_url: str) -> bool:
    for path in _HEALTH_PATHS:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(base_url.rstrip("/") + path)
                if response.status_code == 200:
                    return True
        except httpx.HTTPError:
            continue
    return False


async def call_freecad_tool(
    base_url: str,
    tool: str,
    arguments: dict[str, Any] | None = None,
    *,
    timeout: float = 300.0,
) -> dict[str, Any]:
    """Execute an MCP tool via freecad-mcp REST control endpoint."""
    url = base_url.rstrip("/") + _TOOL_PATH
    payload = {"tool": tool, "arguments": arguments or {}}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        logger.warning("FreeCAD tool call failed tool=%s base=%s error=%s", tool, base_url, exc)
        return {"success": False, "error": str(exc), "tool": tool}

    if isinstance(body, dict):
        if "success" not in body and body.get("data") is not None:
            return {**body, "success": True}
        return body
    return {"success": False, "error": "Invalid tool response", "tool": tool}
