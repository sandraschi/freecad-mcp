"""Create in-process FluidX3D tool callables without starting the full server."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from freecad_mcp.tools.fluidx3d import register_fluidx3d_tools


class _DummyMcp:
    """Minimal stand-in for FastMCP tool registration."""

    def tool(self, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        return decorator


def create_fluidx3d_tools(work_dir: str) -> dict[str, Callable[..., Any]]:
    """Return FluidX3D tool callables bound to an isolated work directory."""
    upload_dir = os.path.join(work_dir, "uploads")
    output_dir = os.path.join(work_dir, "output")
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    async def _noop_bridge(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"success": False, "error": "bridge unavailable in integration harness"}

    async def _noop_freecad(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"success": False, "error": "freecad subprocess unavailable in integration harness"}

    def _noop_build(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"success": True}

    return register_fluidx3d_tools(
        mcp=_DummyMcp(),
        state={},
        bridge_send=_noop_bridge,
        run_freecad=_noop_freecad,
        work_dir=work_dir,
        output_dir=output_dir,
        upload_dir=upload_dir,
        build_result=_noop_build,
    )
