"""FluidX3D GPU integration tests (local only — skipped in CI without GPU)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from freecad_mcp.utils.fluidx3d_integration import integration_ready, run_fluidx3d_integration


@pytest.mark.integration
def test_fluidx3d_integration_ready_reports_reason():
    ready, reason = integration_ready()
    assert isinstance(ready, bool)
    assert reason


@pytest.mark.integration
def test_fluidx3d_gpu_pipeline():
    ready, reason = integration_ready()
    if not ready:
        pytest.skip(reason)

    report = asyncio.run(
        run_fluidx3d_integration(work_dir=Path("D:/Temp/fleet_pipeline/fluidx3d_pytest")),
    )
    assert report.get("mode") == "integration"
    assert report.get("success") is True, report
