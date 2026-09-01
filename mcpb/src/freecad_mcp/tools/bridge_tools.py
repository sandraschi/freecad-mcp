"""FreeCAD bridge portmanteau - Hands-In live GUI control."""

from __future__ import annotations

import logging
import os
from typing import Annotated, Any

from pydantic import Field

from freecad_mcp.model_ops import validate_bridge_script

logger = logging.getLogger("freecad-mcp.bridge")

_READ_ONLY = {"readonly": True}
_MUTATING = {"mutating": True}
_EXECUTION_MODES = ("auto", "hands_in", "hands_off")


def resolve_execution_mode(state: dict, mode: str | None = None) -> str:
    """Resolve auto/hands_in/hands_off to an effective execution path."""
    selected = (mode or state.get("execution_mode") or "auto").lower()
    if selected not in _EXECUTION_MODES:
        selected = "auto"
    if selected == "auto":
        return "hands_in" if state.get("bridge_mode") == "tcp" else "hands_off"
    return selected


def register_bridge_tools(
    mcp,
    state: dict,
    bridge_send,
    output_dir: str,
    freecad_path: str,
    start_bridge,
    connect_bridge,
):
    """Register freecad_bridge portmanteau tool."""

    @mcp.tool(annotations=_MUTATING)
    async def freecad_bridge(
        operation: Annotated[
            str,
            Field(
                description=(
                    "Operation: status, set_execution_mode, ensure_gui, list_objects, "
                    "screenshot_view, execute_script, new_document"
                ),
            ),
        ] = "status",
        execution_mode: Annotated[
            str,
            Field(description="Routing mode: auto, hands_in, hands_off."),
        ] = "auto",
        document: Annotated[str, Field(description="Target document name (optional).")] = "",
        document_label: Annotated[str, Field(description="Label for new documents.")] = "MCP_Model",
        script: Annotated[str, Field(description="Python script for execute_script (FreeCAD API only).")] = "",
        width: Annotated[int, Field(description="Screenshot width.", ge=320)] = 1280,
        height: Annotated[int, Field(description="Screenshot height.", ge=240)] = 720,
        screenshot_path: Annotated[str, Field(description="Optional PNG output path.")] = "",
        include_base64: Annotated[bool, Field(description="Include base64 PNG in response.")] = True,
    ) -> dict[str, Any]:
        """Hands-In / Hands-Off bridge control for live FreeCAD GUI sessions.

        Hands-In uses the TCP bridge (FreeCAD.exe + fc_bridge.py) for live modeling,
        viewport screenshots, and object inspection. Hands-Off uses FreeCADCmd subprocess.

        ## Operations
        - status: bridge connectivity and effective execution mode
        - set_execution_mode: persist auto | hands_in | hands_off preference
        - ensure_gui: start/connect FreeCAD bridge if needed
        - list_objects: object tree for active/target document
        - screenshot_view: capture 3D viewport PNG (vision loops)
        - execute_script: run bounded Python in live document context
        - new_document: create empty document in live GUI

        ## Examples
        await freecad_bridge(operation="status")
        await freecad_bridge(operation="ensure_gui")
        await freecad_bridge(operation="screenshot_view", width=1920, height=1080)
        await freecad_bridge(operation="execute_script", script="doc.addObject('Part::Feature','Box').Shape = Part.makeBox(10,10,10)")
        """
        op = operation.strip().lower()
        mode = resolve_execution_mode(state, execution_mode or None)

        if op == "set_execution_mode":
            selected = execution_mode.lower()
            if selected not in _EXECUTION_MODES:
                return {"success": False, "error": f"Invalid execution_mode: {execution_mode}"}
            state["execution_mode"] = selected
            return {
                "success": True,
                "execution_mode": selected,
                "effective_mode": resolve_execution_mode(state),
                "bridge_mode": state.get("bridge_mode"),
            }

        if op == "status":
            return {
                "success": True,
                "bridge_mode": state.get("bridge_mode"),
                "bridge_connected": state.get("bridge_mode") == "tcp",
                "execution_mode": state.get("execution_mode", "auto"),
                "effective_mode": mode,
                "freecad_ok": state.get("freecad_ok", False),
                "freecad_version": state.get("freecad_version"),
            }

        if op == "ensure_gui":
            if state.get("bridge_mode") != "tcp":
                started = start_bridge()
                if started:
                    connected = await connect_bridge()
                    if connected:
                        state["bridge_mode"] = "tcp"
            return {
                "success": state.get("bridge_mode") == "tcp",
                "bridge_mode": state.get("bridge_mode"),
                "message": "Bridge connected" if state.get("bridge_mode") == "tcp" else "Bridge unavailable",
            }

        if mode != "hands_in":
            return {
                "success": False,
                "error": "Operation requires Hands-In mode (live FreeCAD GUI bridge). "
                "Call freecad_bridge(operation='ensure_gui') or set execution_mode='hands_in'.",
                "effective_mode": mode,
            }

        if state.get("bridge_mode") != "tcp":
            return {
                "success": False,
                "error": "FreeCAD bridge not connected. Call freecad_bridge(operation='ensure_gui').",
                "effective_mode": mode,
            }

        params: dict[str, Any] = {"document_label": document_label}
        if document:
            params["document"] = document

        if op == "new_document":
            resp = await bridge_send("new_document", params, timeout=30)
            return {"success": bool(resp.get("success")), **resp, "effective_mode": mode}

        if op == "list_objects":
            resp = await bridge_send("list_objects", params, timeout=30)
            return {"success": bool(resp.get("success")), **resp, "effective_mode": mode}

        if op == "screenshot_view":
            png_path = screenshot_path or os.path.join(output_dir, "freecad_viewport.png")
            resp = await bridge_send(
                "screenshot_view",
                {"path": png_path, "width": width, "height": height, **params},
                timeout=60,
            )
            if not resp.get("success"):
                return {"success": False, **resp, "effective_mode": mode}
            data = resp.get("data") or {}
            if not include_base64 and isinstance(data, dict):
                data = {k: v for k, v in data.items() if k != "base64_png"}
            return {"success": True, "data": data, "effective_mode": mode}

        if op == "execute_script":
            ok, reason = validate_bridge_script(script)
            if not ok:
                return {"success": False, "error": reason, "effective_mode": mode}
            resp = await bridge_send("execute_script", {**params, "script": script}, timeout=120)
            return {"success": bool(resp.get("success")), **resp, "effective_mode": mode}

        return {"success": False, "error": f"Unknown operation: {operation}"}

    return {"freecad_bridge": freecad_bridge}
