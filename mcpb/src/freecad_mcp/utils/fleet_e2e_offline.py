"""In-process fleet pipeline smoke (no HTTP, Docker, or GPU required)."""

from __future__ import annotations

from pathlib import Path

from freecad_mcp.tools.cfd import _BLOCK_MESH_DICT
from freecad_mcp.tools.fluidx3d import _generate_setup_cpp


def _make_boundaries() -> str:
    return """    inlet
    {
        type patch;
        faces
        (
            (0 3 7 4)
        );
    }
    outlet
    {
        type patch;
        faces
        (
            (1 5 6 2)
        );
    }
    walls
    {
        type wall;
        faces
        (
            (0 4 5 1)
            (2 6 7 3)
            (0 1 2 3)
            (4 7 6 5)
        );
    }"""


def _make_vertices() -> str:
    coords = [
        (0, 0, 0),
        (1, 0, 0),
        (1, 1, 0),
        (0, 1, 0),
        (0, 0, 1),
        (1, 0, 1),
        (1, 1, 1),
        (0, 1, 1),
    ]
    return "\n".join(f"    ({x} {y} {z})" for x, y, z in coords)


async def run_offline_smoke(*, work_dir: Path) -> dict[str, object]:
    """Validate qcad-style STL handoff + OpenFOAM + FluidX3D config generation."""
    steps: list[dict[str, object]] = []
    work_dir.mkdir(parents=True, exist_ok=True)

    stl_path = work_dir / "qcad_extrude.stl"
    stl_path.write_bytes(
        b"solid qcad_extrude\n"
        b"  facet normal 0 0 1\n"
        b"    outer loop\n"
        b"      vertex 0 0 0\n"
        b"      vertex 1 0 0\n"
        b"      vertex 0 1 0\n"
        b"    endloop\n"
        b"  endfacet\n"
        b"endsolid qcad_extrude\n",
    )
    steps.append(
        {
            "name": "qcad_stl_fixture",
            "success": stl_path.is_file() and stl_path.stat().st_size > 0,
            "detail": {"path": str(stl_path), "bytes": stl_path.stat().st_size},
        },
    )

    try:
        block_mesh = _BLOCK_MESH_DICT.format(
            scale=1.0,
            vertices=_make_vertices(),
            nx=20,
            ny=10,
            nz=10,
            boundaries=_make_boundaries(),
        )
        openfoam_ok = "blockMesh" in block_mesh and "inlet" in block_mesh
        case_dir = work_dir / "cfd_cases" / "fleet_channel"
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "blockMeshDict").write_text(block_mesh, encoding="utf-8")
        steps.append(
            {
                "name": "openfoam_block_mesh",
                "success": openfoam_ok,
                "detail": {"case_dir": str(case_dir), "bytes": len(block_mesh)},
            },
        )
    except Exception as exc:
        steps.append({"name": "openfoam_block_mesh", "success": False, "detail": {"error": str(exc)}})

    try:
        setup_cpp = _generate_setup_cpp(
            case_name="fleet_channel_gpu",
            domain_type="channel",
            Nx=64,
            Ny=32,
            Nz=32,
            nu=0.01,
            lbm_length=1.0,
            lbm_velocity=0.05,
            si_length=1.0,
            si_velocity=0.05,
            si_density=1000.0,
            fx=0.0,
            fy=0.0,
            fz=0.0,
            u_inlet_x=0.05,
            u_inlet_y=0.0,
            u_inlet_z=0.0,
            time_steps=1000,
            write_interval=100,
        )
        fluidx_ok = "LBM lbm" in setup_cpp and "main_setup()" in setup_cpp
        f3d_case = work_dir / "fluidx3d_cases" / "fleet_channel_gpu"
        f3d_case.mkdir(parents=True, exist_ok=True)
        setup_file = f3d_case / "setup.cpp"
        setup_file.write_text(setup_cpp, encoding="utf-8")
        steps.append(
            {
                "name": "fluidx3d_setup_cpp",
                "success": fluidx_ok,
                "detail": {"setup_file": str(setup_file), "bytes": len(setup_cpp)},
            },
        )
    except Exception as exc:
        steps.append({"name": "fluidx3d_setup_cpp", "success": False, "detail": {"error": str(exc)}})

    import json

    export_manifest = {
        "case_name": "fleet_channel_gpu",
        "vtk_path": str(work_dir / "fleet_channel_gpu.vtk"),
        "obj_streamlines": str(work_dir / "fleet_channel_gpu_streamlines.obj"),
        "csv_fields": str(work_dir / "fleet_channel_gpu_fields.csv"),
        "handoff_targets": ["resonite-mcp", "godot-mcp", "robotics-mcp"],
    }
    manifest_path = work_dir / "fleet_export_manifest.json"
    manifest_path.write_text(json.dumps(export_manifest, indent=2), encoding="utf-8")
    steps.append(
        {
            "name": "render_export_manifest",
            "success": manifest_path.is_file(),
            "detail": export_manifest,
        },
    )

    bim_src = Path(__file__).resolve().parents[1] / "tools" / "bim.py"
    bim_registered = bim_src.is_file() and "mesh_to_solid" in bim_src.read_text(encoding="utf-8")
    steps.append(
        {
            "name": "mesh_to_solid_registered",
            "success": bim_registered,
            "detail": {"bridge": "qcad plan_extrude STL -> FreeCAD B-Rep"},
        },
    )

    return {
        "success": all(bool(s.get("success")) for s in steps),
        "mode": "offline",
        "steps": steps,
    }
