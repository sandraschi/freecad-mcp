"""FluidX3D GPU integration smoke - requires local clone, compiler, and OpenCL GPU."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from freecad_mcp.tools.fluidx3d import _find_compiler, _find_fluidx3d, _query_gpu_devices
from freecad_mcp.utils.fluidx3d_tools import create_fluidx3d_tools

logger = logging.getLogger(__name__)

DEFAULT_CASE_NAME = "fleet_f3d_integration"
DEFAULT_WORK_DIR = Path("D:/Temp/fleet_pipeline/fluidx3d_integration")


def integration_ready() -> tuple[bool, str]:
    """Return (ready, reason). Skips when FluidX3D, compiler, or GPU is missing."""
    if os.environ.get("FREECAD_SKIP_FLUIDX3D_INTEGRATION", "").lower() in ("1", "true", "yes"):
        return False, "FREECAD_SKIP_FLUIDX3D_INTEGRATION set"

    f3d_path = _find_fluidx3d()
    if not f3d_path:
        return False, "FluidX3D not found (set FLUIDX3D_PATH or clone to D:/Dev/repos/FluidX3D)"

    compiler = _find_compiler()
    if not compiler:
        return False, "No C++ compiler (g++ or MSVC required)"

    gpus = _query_gpu_devices()
    if not gpus:
        return False, "No OpenCL GPU devices detected (clinfo/OpenCL runtime)"

    return True, f"ready: {f3d_path}, compiler={compiler}, gpus={len(gpus)}"


async def run_fluidx3d_integration(
    *,
    work_dir: Path | None = None,
    case_name: str = DEFAULT_CASE_NAME,
    run_timeout_s: int | None = None,
) -> dict[str, object]:
    """Run setup -> compile -> run -> results -> export on a tiny channel case."""
    ready, reason = integration_ready()
    if not ready:
        return {"success": False, "mode": "integration", "skipped": True, "reason": reason, "steps": []}

    root = work_dir or DEFAULT_WORK_DIR
    root.mkdir(parents=True, exist_ok=True)
    tools = create_fluidx3d_tools(str(root))
    steps: list[dict[str, object]] = []

    timeout_s = run_timeout_s or int(os.environ.get("FREECAD_F3D_RUN_TIMEOUT_S", "180"))

    status = await tools["cfd_fluidx3d_status"]()
    steps.append(
        {
            "name": "fluidx3d_status",
            "success": bool(status.get("success")) and bool(status.get("ready")),
            "detail": status,
        },
    )

    setup = await tools["cfd_fluidx3d_setup"](
        case_name=case_name,
        domain_type="channel",
        resolution_x=32,
        resolution_y=16,
        resolution_z=16,
        length_m=0.5,
        velocity_ms=0.02,
        time_steps=1500,
        write_interval=500,
    )
    steps.append({"name": "fluidx3d_setup", "success": bool(setup.get("success")), "detail": setup})

    compile_result = await tools["cfd_fluidx3d_compile"](case_name=case_name)
    steps.append(
        {"name": "fluidx3d_compile", "success": bool(compile_result.get("success")), "detail": compile_result},
    )

    run_result: dict[str, Any] = {"success": False, "skipped": True}
    if compile_result.get("success"):
        run_result = await tools["cfd_fluidx3d_run"](
            case_name=case_name,
            gpu_device=os.environ.get("FREECAD_F3D_GPU_DEVICE", "0"),
            timeout_s=timeout_s,
        )
    steps.append({"name": "fluidx3d_run", "success": bool(run_result.get("success")), "detail": run_result})

    results = await tools["cfd_fluidx3d_results"](case_name=case_name)
    steps.append({"name": "fluidx3d_results", "success": bool(results.get("success")), "detail": results})

    export: dict[str, Any] = {"success": False, "skipped": True}
    vtk_files = (run_result.get("data") or {}).get("vtk_files") if isinstance(run_result.get("data"), dict) else None
    if run_result.get("success") and vtk_files:
        export = await tools["cfd_fluidx3d_export_for_render"](
            case_name=case_name,
            n_streamlines=8,
            streamline_length=40,
            export_csv=True,
        )
    steps.append(
        {
            "name": "fluidx3d_export_for_render",
            "success": bool(export.get("success")),
            "detail": export,
            "optional": not bool(vtk_files),
        },
    )

    required = [s for s in steps if not s.get("optional")]
    success = all(bool(s.get("success")) for s in required)
    return {
        "success": success,
        "mode": "integration",
        "case_name": case_name,
        "work_dir": str(root),
        "steps": steps,
    }
