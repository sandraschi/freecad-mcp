"""Unit tests for new CFD extensions: cfd_snappy_mesh, cfd_post_process, cfd_map_loads_to_fem."""

import os
import shutil
from unittest.mock import MagicMock

import pytest

from freecad_mcp.tools.cfd import (
    SOLVERS,
    register_cfd_tools,
)


@pytest.fixture
def cfd_tools(tmp_path):
    mcp = MagicMock()
    mcp.tool = lambda *args, **kwargs: lambda fn: fn
    state = {"bridge_mode": "subprocess"}

    async def mock_run_freecad(script, timeout=120):
        return ('{"status": "ok"}', "", 0)

    async def mock_bridge_send(method, params=None, timeout=120):
        return {"success": True, "data": {}}

    tools = register_cfd_tools(
        mcp=mcp,
        state=state,
        bridge_send=mock_bridge_send,
        run_freecad=mock_run_freecad,
        work_dir=str(tmp_path),
        output_dir=str(tmp_path),
        upload_dir=str(tmp_path),
        build_result=lambda name, out, err, code, extra=None: {"success": code == 0, "output": out, "error": err},
    )
    return tools


def test_buoyant_boussinesq_solver_constant():
    assert "buoyantBoussinesqSimpleFoam" in SOLVERS
    assert "Boussinesq" in SOLVERS["buoyantBoussinesqSimpleFoam"]


@pytest.mark.anyio
async def test_cfd_snappy_mesh_generation(cfd_tools):
    status = await cfd_tools["cfd_status"]()
    case_dir_root = status["cfd_case_dir"]
    case_name = "test_snappy_car"
    case_dir = os.path.join(case_dir_root, case_name)
    os.makedirs(case_dir, exist_ok=True)
    stl_file = os.path.join(case_dir, "car.stl")
    with open(stl_file, "w") as f:
        f.write("solid car endsolid car\n")

    try:
        tool = cfd_tools["cfd_snappy_mesh"]
        res = await tool(
            case_name=case_name,
            stl_file="car.stl",
            refinement_level=3,
            feature_angle_deg=45.0,
            num_surface_layers=2,
        )
        assert res["success"] is True
        assert res["data"]["stl_surface"] == "car.stl"
        assert os.path.isfile(os.path.join(case_dir, "system", "snappyHexMeshDict"))
        assert os.path.isfile(os.path.join(case_dir, "system", "surfaceFeatureExtractDict"))
    finally:
        if os.path.exists(case_dir):
            shutil.rmtree(case_dir, ignore_errors=True)


@pytest.mark.anyio
async def test_cfd_post_process_coefficients(cfd_tools):
    status = await cfd_tools["cfd_status"]()
    case_dir_root = status["cfd_case_dir"]
    case_name = "test_airfoil_case"
    case_dir = os.path.join(case_dir_root, case_name)
    os.makedirs(case_dir, exist_ok=True)

    try:
        tool = cfd_tools["cfd_post_process"]
        res = await tool(
            case_name=case_name,
            frontal_area_m2=0.08,
            inlet_patch="inlet",
            outlet_patch="outlet",
            force_patches=["wing"],
        )
        assert res["success"] is True
        assert res["data"]["drag_coefficient_cd"] > 0
        assert res["data"]["pressure_drop_pa"] > 0
        assert os.path.isfile(os.path.join(case_dir, "cfd_post_summary.json"))
    finally:
        if os.path.exists(case_dir):
            shutil.rmtree(case_dir, ignore_errors=True)


@pytest.mark.anyio
async def test_cfd_map_loads_to_fem(cfd_tools):
    status = await cfd_tools["cfd_status"]()
    case_dir_root = status["cfd_case_dir"]
    case_name = "test_fsi_bracket"
    case_dir = os.path.join(case_dir_root, case_name)
    os.makedirs(case_dir, exist_ok=True)

    try:
        tool = cfd_tools["cfd_map_loads_to_fem"]
        res = await tool(
            case_name=case_name,
            step_file="bracket.step",
            patch_name="wall",
            youngs_modulus_gpa=70.0,
            poissons_ratio=0.33,
        )
        assert res["success"] is True
        assert "estimated_peak_stress_mpa" in res["data"]
    finally:
        if os.path.exists(case_dir):
            shutil.rmtree(case_dir, ignore_errors=True)
