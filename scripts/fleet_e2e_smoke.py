"""Fleet E2E smoke: qcad DXF/STL -> freecad CFD -> export handoff."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from freecad_mcp.utils.fleet_e2e_offline import run_offline_smoke
from freecad_mcp.utils.fleet_http import (
    DEFAULT_FREECAD_URL,
    DEFAULT_QCAD_URL,
    call_freecad_tool,
    check_http_health,
)


async def _probe(name: str, url: str) -> dict[str, object]:
    return {"service": name, "url": url, "online": await check_http_health(url)}


async def run_e2e_smoke(
    *,
    offline: bool = False,
    offline_work_dir: Path | None = None,
) -> dict[str, object]:
    if offline:
        work = offline_work_dir or Path("D:/Temp/fleet_pipeline/freecad_e2e_offline")
        return await run_offline_smoke(work_dir=work)

    steps: list[dict[str, object]] = []
    probes = await asyncio.gather(
        _probe("freecad-mcp", DEFAULT_FREECAD_URL),
        _probe("qcad-mcp", DEFAULT_QCAD_URL),
    )
    steps.append({"name": "fleet_probe", "success": True, "detail": probes})

    freecad_online = next(p for p in probes if p["service"] == "freecad-mcp")["online"]
    qcad_online = next(p for p in probes if p["service"] == "qcad-mcp")["online"]

    if freecad_online:
        cfd_status = await call_freecad_tool(DEFAULT_FREECAD_URL, "cfd_status")
        steps.append({"name": "cfd_status", "success": bool(cfd_status.get("success")), "detail": cfd_status})

        f3d_status = await call_freecad_tool(DEFAULT_FREECAD_URL, "cfd_fluidx3d_status")
        steps.append(
            {"name": "fluidx3d_status", "success": bool(f3d_status.get("success")), "detail": f3d_status},
        )

        prebuilt = await call_freecad_tool(DEFAULT_FREECAD_URL, "cfd_fluidx3d_prebuilt")
        steps.append(
            {"name": "fluidx3d_prebuilt", "success": bool(prebuilt.get("success")), "detail": prebuilt},
        )
    else:
        steps.append({"name": "cfd_status", "success": False, "detail": {"skipped": "freecad offline"}})
        steps.append({"name": "fluidx3d_status", "success": False, "detail": {"skipped": "freecad offline"}})
        steps.append({"name": "fluidx3d_prebuilt", "success": False, "detail": {"skipped": "freecad offline"}})

    if qcad_online:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{DEFAULT_QCAD_URL.rstrip('/')}/api/v1/health")
                qcad_health = response.status_code == 200
        except Exception as exc:
            qcad_health = False
            steps.append({"name": "qcad_health", "success": False, "detail": {"error": str(exc)}})
        else:
            steps.append({"name": "qcad_health", "success": qcad_health, "detail": {"status_code": 200}})
    else:
        steps.append({"name": "qcad_health", "success": False, "detail": {"skipped": "qcad offline"}})

    required = [s for s in steps if s.get("name") != "fleet_probe"]
    success = all(bool(s.get("success")) for s in required) if required else False
    return {"success": success, "mode": "http", "steps": steps}


def main() -> None:
    parser = argparse.ArgumentParser(description="FreeCAD fleet E2E smoke")
    parser.add_argument("--offline", action="store_true", help="In-process pipeline config smoke (CI)")
    parser.add_argument("--offline-work-dir", default="")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any step fails")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    work_dir = Path(args.offline_work_dir) if args.offline_work_dir else None
    report = asyncio.run(run_e2e_smoke(offline=args.offline, offline_work_dir=work_dir))
    print(json.dumps(report, indent=2))
    if not args.json:
        mode = report.get("mode", "http")
        print(f"\nE2E smoke ({mode}) {'SUCCESS' if report['success'] else 'FAILED'}")
    if args.strict and not report.get("success"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
