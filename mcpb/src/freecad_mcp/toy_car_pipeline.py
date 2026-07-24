"""Multi-source toy car pipeline: Blender sculpt, marketplace STL, FreeCAD parametric."""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

import httpx

from freecad_mcp.toy_car_build import blender_build_and_export_script

logger = logging.getLogger(__name__)

DEFAULT_BLENDER_MCP_URL = os.environ.get("BLENDER_MCP_URL", "http://127.0.0.1:10849")
BLENDER_TOOL_PATH = "/tool"


async def call_blender_tool(
    tool: str,
    params: dict[str, Any] | None = None,
    *,
    base_url: str | None = None,
    timeout: float = 300.0,
) -> dict[str, Any]:
    """Invoke blender-mcp /tool bridge."""
    url = (base_url or DEFAULT_BLENDER_MCP_URL).rstrip("/") + BLENDER_TOOL_PATH
    payload = {"tool": tool, "params": params or {}}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        logger.warning("Blender tool call failed tool=%s error=%s", tool, exc)
        return {"success": False, "error": str(exc), "tool": tool}

    if isinstance(body, dict):
        if body.get("success") is False:
            return body
        if "success" not in body:
            return {**body, "success": True}
        return body
    return {"success": False, "error": "Invalid blender tool response", "tool": tool}


def _parse_blender_tool_payload(raw: dict[str, Any]) -> dict[str, Any]:
    data = raw.get("data")
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"output": data, "success": raw.get("success", True)}
    if isinstance(data, dict):
        return data
    return raw


async def build_toy_car_via_blender(
    export_stl: str,
    *,
    body_length_mm: float,
    blender_url: str | None = None,
) -> dict[str, Any]:
    """Sculpt sports car in Blender headlessly and export STL."""
    try:
        script = blender_build_and_export_script(
            export_stl=export_stl,
            body_length_mm=body_length_mm,
        )
    except FileNotFoundError as exc:
        return {"success": False, "error": str(exc), "source": "blender"}

    health = await call_blender_tool("script_execute", {"code": "print('ping')"}, base_url=blender_url, timeout=30)
    if not health.get("success"):
        return {
            "success": False,
            "error": "blender-mcp unavailable at "
            f"{blender_url or DEFAULT_BLENDER_MCP_URL}. Start blender-mcp HTTP server.",
            "source": "blender",
            "hint": "uv run python run_server.py --http in blender-mcp repo",
        }

    result = await call_blender_tool(
        "script_execute",
        {"code": script},
        base_url=blender_url,
        timeout=300,
    )
    if not result.get("success"):
        return {**result, "source": "blender"}

    payload = _parse_blender_tool_payload(result)
    if payload.get("success") is False:
        return {**payload, "source": "blender"}

    if not os.path.isfile(export_stl):
        return {
            "success": False,
            "error": "Blender export did not produce STL",
            "source": "blender",
            "blender_output": payload.get("output", ""),
        }

    size_kb = round(os.path.getsize(export_stl) / 1024, 1)
    return {
        "success": True,
        "source": "blender",
        "export_stl": export_stl,
        "size_kb": size_kb,
        "style": "sports_car",
        "blender_output": payload.get("output", ""),
    }


async def build_toy_car_via_marketplace(
    export_stl: str,
    *,
    query: str,
    marketplace_search,
    marketplace_download,
    source: str = "printables",
) -> dict[str, Any]:
    """Search marketplace and copy first STL download to output."""
    search = await marketplace_search(source=source, query=query, category="", limit=10, page=1)
    if not search.get("success"):
        return {**search, "car_source": "marketplace"}

    results = search.get("results") or []
    if not results:
        return {
            "success": False,
            "error": f"No marketplace results for query: {query}",
            "car_source": "marketplace",
        }

    last_error = "No downloadable STL found"
    for item in results:
        file_url = item.get("file_url") or item.get("download_url") or ""
        model_id = str(item.get("id") or item.get("model_id") or "")
        title = item.get("title") or item.get("name") or "model"
        if not file_url:
            continue
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in title[:40])
        filename = safe_name if safe_name.lower().endswith(".stl") else f"{safe_name}.stl"
        dl = await marketplace_download(
            source=source,
            model_id=model_id,
            file_url=file_url,
            filename=filename,
        )
        if not dl.get("success"):
            last_error = dl.get("error", last_error)
            continue

        src = dl.get("path", "")
        extracted = dl.get("extracted") or []
        if extracted:
            for entry in extracted:
                name = entry.get("filename", "")
                if name.lower().endswith(".stl"):
                    src = str(Path(src).parent / name)
                    break

        if not src or not os.path.isfile(src):
            last_error = "Download succeeded but STL path missing"
            continue

        if not src.lower().endswith(".stl"):
            last_error = f"Downloaded format is not STL: {src}"
            continue

        os.makedirs(os.path.dirname(export_stl) or ".", exist_ok=True)
        shutil.copy2(src, export_stl)
        return {
            "success": True,
            "car_source": "marketplace",
            "export_stl": export_stl,
            "size_kb": round(os.path.getsize(export_stl) / 1024, 1),
            "marketplace_title": title,
            "marketplace_id": model_id,
            "marketplace_source": source,
        }

    return {
        "success": False,
        "error": last_error,
        "car_source": "marketplace",
        "query": query,
    }


async def resolve_toy_car_auto(
    export_stl: str,
    *,
    body_length_mm: float,
    marketplace_query: str,
    marketplace_search,
    marketplace_download,
    blender_url: str | None = None,
) -> dict[str, Any]:
    """Try blender, then marketplace, caller falls back to parametric."""
    blender_result = await build_toy_car_via_blender(
        export_stl,
        body_length_mm=body_length_mm,
        blender_url=blender_url,
    )
    if blender_result.get("success"):
        blender_result["car_source"] = "auto"
        blender_result["resolved_via"] = "blender"
        return blender_result

    market_result = await build_toy_car_via_marketplace(
        export_stl,
        query=marketplace_query,
        marketplace_search=marketplace_search,
        marketplace_download=marketplace_download,
    )
    if market_result.get("success"):
        market_result["car_source"] = "auto"
        market_result["resolved_via"] = "marketplace"
        market_result["blender_fallback_error"] = blender_result.get("error")
        return market_result

    return {
        "success": False,
        "error": "auto resolution failed for blender and marketplace",
        "car_source": "auto",
        "blender_error": blender_result.get("error"),
        "marketplace_error": market_result.get("error"),
    }
