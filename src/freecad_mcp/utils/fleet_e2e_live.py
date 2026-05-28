"""Live HTTP fleet chain: qcad DXF -> STL -> freecad FluidX3D setup."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from freecad_mcp.utils.fleet_http import (
    DEFAULT_FREECAD_URL,
    DEFAULT_QCAD_URL,
    call_freecad_tool,
    call_qcad_tool,
    check_http_health,
    download_bytes,
    upload_bytes,
)

logger = logging.getLogger(__name__)

DEFAULT_DXF = Path("D:/Dev/repos/qcad-mcp/tests/fixtures/simple_floorplan.dxf")


async def run_live_chain(
    *,
    qcad_url: str = DEFAULT_QCAD_URL,
    freecad_url: str = DEFAULT_FREECAD_URL,
    dxf_path: Path | None = None,
    stl_name: str = "fleet_chain.stl",
    case_name: str = "fleet_qcad_chain",
    run_gpu: bool = False,
) -> dict[str, object]:
    """HTTP handoff: upload DXF -> plan_extrude -> STL upload -> FluidX3D setup."""
    steps: list[dict[str, object]] = []

    qcad_online = await check_http_health(qcad_url)
    freecad_online = await check_http_health(freecad_url)
    steps.append(
        {
            "name": "fleet_probe",
            "success": qcad_online and freecad_online,
            "detail": {"qcad_online": qcad_online, "freecad_online": freecad_online},
        },
    )
    if not qcad_online or not freecad_online:
        return {"success": False, "mode": "live_chain", "steps": steps}

    source = dxf_path or Path(os.environ.get("QCAD_FLEET_DXF", str(DEFAULT_DXF)))
    if not source.is_file():
        steps.append({"name": "dxf_fixture", "success": False, "detail": {"path": str(source)}})
        return {"success": False, "mode": "live_chain", "steps": steps}

    dxf_bytes = source.read_bytes()
    dxf_name = f"fleet_chain_{int(time.time())}.dxf"
    upload_qcad = await upload_bytes(qcad_url, "/api/v1/upload", dxf_name, dxf_bytes)
    steps.append({"name": "qcad_upload_dxf", "success": bool(upload_qcad.get("success")), "detail": upload_qcad})

    extrude = await call_qcad_tool(
        qcad_url,
        "plan_extrude",
        {
            "file_name": dxf_name,
            "output_name": stl_name,
            "wall_height": 2.8,
            "wall_thickness": 0.25,
        },
    )
    steps.append({"name": "qcad_plan_extrude", "success": bool(extrude.get("success")), "detail": extrude})
    if not extrude.get("success"):
        return {"success": False, "mode": "live_chain", "steps": steps}

    try:
        stl_bytes = await download_bytes(qcad_url, f"/api/v1/download/{stl_name}")
        steps.append(
            {
                "name": "qcad_download_stl",
                "success": len(stl_bytes) > 0,
                "detail": {"stl_name": stl_name, "bytes": len(stl_bytes)},
            },
        )
    except Exception as exc:
        steps.append({"name": "qcad_download_stl", "success": False, "detail": {"error": str(exc)}})
        return {"success": False, "mode": "live_chain", "steps": steps}

    upload_fc = await upload_bytes(freecad_url, "/api/v1/upload", stl_name, stl_bytes)
    steps.append({"name": "freecad_upload_stl", "success": bool(upload_fc.get("success")), "detail": upload_fc})

    setup = await call_freecad_tool(
        freecad_url,
        "cfd_fluidx3d_setup",
        {
            "case_name": case_name,
            "domain_type": "stl",
            "stl_file": stl_name,
            "resolution_x": 64,
            "resolution_y": 32,
            "resolution_z": 32,
            "length_m": 1.0,
            "velocity_ms": 0.02,
            "time_steps": 2000,
            "write_interval": 500,
        },
    )
    steps.append({"name": "freecad_fluidx3d_setup", "success": bool(setup.get("success")), "detail": setup})

    if run_gpu:
        compile_result = await call_freecad_tool(freecad_url, "cfd_fluidx3d_compile", {"case_name": case_name})
        steps.append(
            {"name": "freecad_fluidx3d_compile", "success": bool(compile_result.get("success")), "detail": compile_result},
        )
        if compile_result.get("success"):
            run_result = await call_freecad_tool(
                freecad_url,
                "cfd_fluidx3d_run",
                {
                    "case_name": case_name,
                    "gpu_device": os.environ.get("FREECAD_F3D_GPU_DEVICE", "0"),
                    "timeout_s": int(os.environ.get("FREECAD_F3D_RUN_TIMEOUT_S", "180")),
                },
            )
            steps.append(
                {"name": "freecad_fluidx3d_run", "success": bool(run_result.get("success")), "detail": run_result},
            )

    required = [s for s in steps if s.get("name") != "fleet_probe"]
    success = all(bool(s.get("success")) for s in required)
    return {"success": success, "mode": "live_chain", "case_name": case_name, "steps": steps}
