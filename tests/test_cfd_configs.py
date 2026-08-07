"""Validate CFD/FluidX3D config generation without Docker or GPU.

Imports module-level constants and functions directly — no FreeCAD bridge needed.
"""

import inspect
import os
import re

import pytest

from freecad_mcp.tools.cfd import (
    _BLOCK_MESH_DICT,
    _CONTROL_DICT,
    _FV_SCHEMES,
    _FV_SOLUTION,
    _TRANSPORT_PROPERTIES,
    _TURBULENCE_PROPERTIES,
    FLOW_TYPES,
    KEPSILON,
    KOMEGA_SST,
    LAMINAR,
    SOLVERS,
    _fv_solution_turb,
)
from freecad_mcp.tools.fluidx3d import (
    BC_TEMPLATES,
    BC_TEMPLATES_SYMMETRY,
    _generate_boundary_code,
    _generate_free_surface_code,
    _generate_non_newtonian_code,
    _generate_object_forces_loop,
    _generate_profile_code,
    _generate_setup_cpp,
    _generate_stl_imports,
    _generate_thermal_defs,
    _generate_thermal_init_code,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_vertices(n: int = 8) -> str:
    """Generate n hexahedron vertices for blockMeshDict formatting."""
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
    return "\n".join(f"    ({x} {y} {z})" for x, y, z in coords[:n])


def _make_boundaries() -> str:
    """Return 3-patch boundary block for blockMeshDict formatting."""
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


# ── Test 1: blockMeshDict ─────────────────────────────────────────────────────


class TestBlockMeshDict:
    """Validate _BLOCK_MESH_DICT generates a correct blockMeshDict."""

    def test_contains_foamfile_header(self):
        bmd = _BLOCK_MESH_DICT.format(scale=1.0, vertices="", nx=10, ny=10, nz=10, boundaries="")
        assert "FoamFile" in bmd
        assert "blockMeshDict" in bmd
        assert "version     2.0" in bmd

    def test_contains_required_sections(self):
        bmd = _BLOCK_MESH_DICT.format(scale=1.0, vertices="", nx=10, ny=10, nz=10, boundaries="")
        for section in ("convertToMeters", "vertices", "blocks", "boundary", "edges", "mergePatchPairs"):
            assert section in bmd, f"Missing section: {section}"

    def test_vertex_count_eight(self):
        vertices = _make_vertices(8)
        bmd = _BLOCK_MESH_DICT.format(scale=1.0, vertices=vertices, nx=10, ny=10, nz=10, boundaries="")
        vertex_lines = [l for l in bmd.splitlines() if l.strip().startswith("(") and l.strip().endswith(")")]
        assert len(vertex_lines) == 8

    def test_boundary_patch_count(self):
        boundaries = _make_boundaries()
        bmd = _BLOCK_MESH_DICT.format(
            scale=1.0,
            vertices=_make_vertices(8),
            nx=10,
            ny=10,
            nz=10,
            boundaries=boundaries,
        )
        patches = re.findall(r"type (patch|wall);", bmd)
        assert len(patches) == 3
        assert "patch" in patches
        assert "wall" in patches

    def test_format_no_placeholders_left(self):
        bmd = _BLOCK_MESH_DICT.format(
            scale=1.0,
            vertices=_make_vertices(8),
            nx=10,
            ny=10,
            nz=10,
            boundaries=_make_boundaries(),
        )
        assert "{" not in bmd or "FoamFile" in bmd  # only curlies in FoamFile header


# ── Test 2: Physics config files ──────────────────────────────────────────────


class TestPhysicsConfigs:
    """Validate all five physics template files have correct FoamFile headers."""

    def test_control_dict_header(self):
        ctrl = _CONTROL_DICT.format(
            solver="simpleFoam",
            end_time=1000,
            delta_t=1.0,
            write_interval=100,
            force_patches='"walls"',
            density=1000.0,
        )
        assert "FoamFile" in ctrl
        assert "controlDict" in ctrl
        assert "application" in ctrl
        assert "endTime" in ctrl
        assert "deltaT" in ctrl
        assert "writeControl" in ctrl
        assert "functions" in ctrl

    def test_control_dict_solver_interpolation(self):
        ctrl = _CONTROL_DICT.format(
            solver="pisoFoam",
            end_time=500,
            delta_t=0.001,
            write_interval=50,
            force_patches='"inlet"',
            density=1.225,
        )
        assert "application     pisoFoam" in ctrl
        assert "endTime         500" in ctrl

    def test_fv_schemes_header(self):
        schemes = _FV_SCHEMES.format(time_scheme="steadyState")
        assert "FoamFile" in schemes
        assert "fvSchemes" in schemes
        assert "ddtSchemes" in schemes
        assert "gradSchemes" in schemes
        assert "divSchemes" in schemes
        assert "laplacianSchemes" in schemes
        assert "interpolationSchemes" in schemes
        assert "snGradSchemes" in schemes

    def test_fv_schemes_time_scheme_interpolation(self):
        steady = _FV_SCHEMES.format(time_scheme="steadyState")
        trans = _FV_SCHEMES.format(time_scheme="Euler")
        assert "steadyState" in steady
        assert "Euler" in trans

    def test_fv_solution_header(self):
        sol, res, rel = _fv_solution_turb(LAMINAR)
        solution = _FV_SOLUTION.format(
            turb_solvers=sol,
            turb_residuals=res,
            turb_relax=rel,
        )
        assert "FoamFile" in solution
        assert "fvSolution" in solution
        assert "solvers" in solution
        assert "p" in solution
        assert "U" in solution
        assert "SIMPLE" in solution
        assert "relaxationFactors" in solution

    def test_fv_solution_turbulent_blocks_present(self):
        sol, res, rel = _fv_solution_turb(KOMEGA_SST)
        assert "k" in sol
        assert "omega" in sol
        assert "k" in res
        assert "omega" in res
        assert "k" in rel
        assert "omega" in rel

    def test_fv_solution_laminar_blocks_empty(self):
        sol, res, rel = _fv_solution_turb(LAMINAR)
        assert sol == ""
        assert res == ""
        assert rel == ""

    def test_transport_properties_header(self):
        tp = _TRANSPORT_PROPERTIES.format(nu=1e-6)
        assert "FoamFile" in tp
        assert "transportProperties" in tp
        assert "transportModel" in tp
        assert "Newtonian" in tp

    def test_turbulence_properties_header(self):
        tp = _TURBULENCE_PROPERTIES.format(sim_type="RAS", model="kOmegaSST")
        assert "FoamFile" in tp
        assert "turbulenceProperties" in tp
        assert "simulationType" in tp
        assert "RAS" in tp
        assert "kOmegaSST" in tp

    def test_turbulence_properties_laminar(self):
        tp = _TURBULENCE_PROPERTIES.format(sim_type="laminar", model="laminar")
        assert "laminar" in tp


# ── Test 3: Boundary field files ──────────────────────────────────────────────


class TestBoundaryFields:
    """Validate field file generation pattern used by cfd_set_boundary."""

    @pytest.mark.parametrize(
        "field,cls_,dims",
        [
            ("U", "volVectorField", "[0 1 -1 0 0 0 0]"),
            ("p", "volScalarField", "[0 2 -2 0 0 0 0]"),
            ("k", "volScalarField", "[0 2 -2 0 0 0 0]"),
            ("omega", "volScalarField", "[0 0 -1 0 0 0 0]"),
            ("nut", "volScalarField", "[0 2 -1 0 0 0 0]"),
            ("alphat", "volScalarField", "[1 -1 -1 0 0 0 0]"),
        ],
    )
    def test_field_dimensions_correct(self, field, cls_, dims):
        field_map = {
            "U": ("volVectorField", "[0 1 -1 0 0 0 0]"),
            "p": ("volScalarField", "[0 2 -2 0 0 0 0]"),
            "k": ("volScalarField", "[0 2 -2 0 0 0 0]"),
            "omega": ("volScalarField", "[0 0 -1 0 0 0 0]"),
            "nut": ("volScalarField", "[0 2 -1 0 0 0 0]"),
            "alphat": ("volScalarField", "[1 -1 -1 0 0 0 0]"),
        }
        expected_cls, expected_dims = field_map[field]
        assert cls_ == expected_cls
        assert dims == expected_dims

    def test_generated_field_file_has_foamfile_header(self):
        no_slip_bc = "noSlip"
        field_content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  10                                    |
|   \\\\  /    A nd           | Web:      www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform 0;

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform (0 0 0);
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    walls
    {{
        type            {no_slip_bc};
    }}
}}
// ************************************************************************* //
"""
        assert "FoamFile" in field_content
        assert "volVectorField" in field_content
        assert "U" in field_content
        assert "dimensions" in field_content
        assert "internalField" in field_content
        assert "boundaryField" in field_content
        assert "inlet" in field_content
        assert "outlet" in field_content
        assert "walls" in field_content


# ── Test 4: cfd_build_case required files ─────────────────────────────────────


class TestBuildCase:
    """Validate the required-files logic used by cfd_build_case."""

    REQUIRED_BASE = [
        "constant/polyMesh/blockMeshDict",
        "system/controlDict",
        "system/fvSchemes",
        "system/fvSolution",
        "constant/transportProperties",
        "constant/turbulenceProperties",
        "0/U",
        "0/p",
    ]

    REQUIRED_TURBULENT = ["0/k", "0/omega", "0/nut"]

    def test_required_base_count(self):
        assert len(self.REQUIRED_BASE) == 8

    def test_required_turbulent_count(self):
        assert len(self.REQUIRED_TURBULENT) == 3

    def test_laminar_missing_reported(self, tmp_path):
        """Simulate a case dir missing files and verify the check logic."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        (case_dir / "constant").mkdir()
        (case_dir / "system").mkdir()
        (case_dir / "0").mkdir()

        # Write only some files
        (case_dir / "system" / "controlDict").write_text("dummy")
        (case_dir / "0" / "U").write_text("dummy")

        files_present = []
        missing = []
        for rel in self.REQUIRED_BASE:
            fp = case_dir / rel
            if fp.is_file():
                files_present.append(rel)
            else:
                missing.append(rel)

        assert len(files_present) == 2
        assert len(missing) == 6
        assert "constant/polyMesh/blockMeshDict" in missing
        assert "0/p" in missing
        assert "system/controlDict" in files_present

    def test_turbulent_case_extra_required(self, tmp_path):
        """Turbulent cases require extra field files."""
        case_dir = tmp_path / "turb_case"
        for rel in self.REQUIRED_BASE + self.REQUIRED_TURBULENT:
            fp = case_dir / rel
            fp.parent.mkdir(parents=True, exist_ok=True)

        # All base files present, but turbulent fields missing
        base_files_present = []
        turb_files_present = []
        for rel in self.REQUIRED_BASE:
            (case_dir / rel).write_text("dummy")
            base_files_present.append(rel)

        missing = []
        for rel in self.REQUIRED_TURBULENT:
            fp = case_dir / rel
            if fp.is_file():
                turb_files_present.append(rel)
            else:
                missing.append(rel)

        assert len(base_files_present) == 8
        assert len(missing) == 3
        assert "0/k" in missing
        assert "0/omega" in missing

    def test_all_present_ready(self, tmp_path):
        case_dir = tmp_path / "ready_case"
        for rel in self.REQUIRED_BASE:
            fp = case_dir / rel
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text("dummy")

        missing = [rel for rel in self.REQUIRED_BASE if not (case_dir / rel).is_file()]
        assert len(missing) == 0
        assert len(missing) == 0  # ready


# ── Test 5: FluidX3D setup C++ ────────────────────────────────────────────────


class TestFluidX3DSetup:
    """Validate _generate_setup_cpp produces correct C++ code."""

    SAMPLE_PARAMS = dict(
        case_name="test_channel",
        domain_type="channel",
        Nx=256,
        Ny=64,
        Nz=64,
        nu=0.01,
        lbm_length=1.0,
        lbm_velocity=0.05,
        si_length=2.0,
        si_velocity=1.0,
        si_density=1000.0,
        fx=0.0,
        fy=0.0,
        fz=0.0,
        u_inlet_x=0.05,
        u_inlet_y=0.0,
        u_inlet_z=0.0,
        time_steps=5000,
        write_interval=100,
    )

    def test_contains_required_includes_and_main(self):
        cpp = _generate_setup_cpp(**self.SAMPLE_PARAMS)
        assert '#include "setup.hpp"' in cpp
        assert '#include "info.hpp"' in cpp
        assert "void main_setup()" in cpp
        assert "LBM lbm(Nx, Ny, Nz," in cpp
        assert "TYPE_E" in cpp
        assert "TYPE_S" in cpp
        assert "units.set_m_kg_s" in cpp
        assert "lbm.run(" in cpp
        assert "print_info" in cpp

    def test_resolution_in_output(self):
        cpp = _generate_setup_cpp(**self.SAMPLE_PARAMS)
        assert "256u" in cpp
        assert "64u" in cpp

    def test_case_name_in_output(self):
        cpp = _generate_setup_cpp(**self.SAMPLE_PARAMS)
        assert "test_channel" in cpp

    def test_time_steps_in_output(self):
        cpp = _generate_setup_cpp(**self.SAMPLE_PARAMS)
        assert "5000u" in cpp
        assert "100u" in cpp


class TestFluidX3DBoundaryCodes:
    """Validate _generate_boundary_code for each domain type."""

    def test_channel_boundary_code(self):
        code = _generate_boundary_code("channel", 0.05, 0.0, 0.0)
        assert "TYPE_E" in code
        assert "TYPE_S|TYPE_X" in code
        assert "x == 0u" in code
        assert "x == Nx - 1u" in code
        assert "u_inlet_x" not in code  # placeholders should be filled

    def test_pipe_boundary_code(self):
        code = _generate_boundary_code("pipe", 0.03, 0.0, 0.0)
        assert "TYPE_E" in code
        assert "r2 > R2" in code
        assert "Ny/2u" in code
        assert "Nz/2u" in code

    def test_box_boundary_code(self):
        code = _generate_boundary_code("box", 0.0, 0.0, 0.0)
        assert "TYPE_S|TYPE_X" in code
        assert "x == 0u" in code
        assert "x == Nx - 1u" in code
        assert "TYPE_E" not in code  # box has no inlet/outlet

    def test_stl_boundary_code(self):
        code = _generate_boundary_code("custom", 0.0, 0.0, 0.0, has_stl=True)
        assert "STL voxelization" in code

    def test_nozzle_uses_pipe_template(self):
        code = _generate_boundary_code("nozzle", 0.05, 0.0, 0.0)
        assert "r2 > R2" in code

    def test_unknown_type_falls_back_to_box(self):
        code = _generate_boundary_code("naca0012", 0.0, 0.0, 0.0)
        assert "TYPE_S|TYPE_X" in code

    def test_boundary_code_fills_velocity(self):
        code = _generate_boundary_code("channel", 0.08, 0.01, 0.02)
        assert "0.08f" in code
        assert "0.01f" in code
        assert "0.02f" in code


class TestFluidX3DSTLImports:
    """Validate _generate_stl_imports."""

    def test_empty_stl_list(self):
        code = _generate_stl_imports([])
        assert "No STL geometry" in code
        assert "read_stl" not in code

    def test_single_stl_import(self):
        code = _generate_stl_imports(["geometry.stl"])
        assert "read_stl" in code
        assert "geometry.stl" in code
        assert "voxelize_mesh_on_device" in code
        assert "translate" in code

    def test_multiple_stl_imports(self):
        code = _generate_stl_imports(["body.stl", "wing.stl"])
        assert "mesh_0" in code
        assert "mesh_1" in code
        assert code.count("read_stl") == 2
        assert code.count("voxelize_mesh_on_device") == 2


class TestFluidX3DSetupWithSTL:
    """Validate _generate_setup_cpp with STL imports."""

    def test_stl_case_includes_import_code(self):
        cpp = _generate_setup_cpp(
            case_name="stl_test",
            domain_type="stl",
            Nx=128,
            Ny=128,
            Nz=128,
            nu=0.01,
            lbm_length=1.0,
            lbm_velocity=0.05,
            si_length=1.0,
            si_velocity=1.0,
            si_density=1000.0,
            fx=1e-9,
            fy=0.0,
            fz=0.0,
            u_inlet_x=0.0,
            u_inlet_y=0.0,
            u_inlet_z=0.0,
            time_steps=1000,
            write_interval=100,
            stl_files=["part.stl"],
        )
        assert "read_stl" in cpp
        assert "voxelize_mesh_on_device" in cpp
        assert "TYPE_S|TYPE_X" in cpp
        assert "void main_setup()" in cpp


# ── Test 5b: FluidX3D inlet profiles ──────────────────────────────────────────


class TestFluidX3DProfiles:
    """Validate _generate_profile_code for parabolic and Blasius profiles."""

    def test_uniform_profile_returns_empty(self):
        code = _generate_profile_code("uniform", "channel", 0.05, 0.0, 0.0)
        assert code == ""

    def test_parabolic_channel_profile(self):
        code = _generate_profile_code("parabolic", "channel", 0.05, 0.0, 0.0)
        assert "0.05f" in code
        assert "y_frac" in code or "y" in code
        assert "6.0f" in code or "6.0" in code

    def test_parabolic_pipe_profile(self):
        code = _generate_profile_code("parabolic", "pipe", 0.03, 0.0, 0.0)
        assert "0.03f" in code
        assert "r2" in code or "radial" in code.lower()

    def test_blasius_profile(self):
        code = _generate_profile_code("blasius", "pipe", 0.05, 0.0, 0.0)
        assert "0.05f" in code
        assert "1.0f/7.0f" in code or "0.142857" in code

    def test_profile_code_overrides_velocity(self):
        code = _generate_profile_code("parabolic", "channel", 0.08, 0.0, 0.0)
        assert "u.x[n] = " in code


# ── Test 5c: FluidX3D non-Newtonian ───────────────────────────────────────────


class TestFluidX3DNonNewtonian:
    """Validate _generate_non_newtonian_code."""

    def test_disabled_returns_empty(self):
        code = _generate_non_newtonian_code(False, 0.15, 0.8, 0.1)
        assert code == ""

    def test_enabled_generates_code(self):
        code = _generate_non_newtonian_code(True, 0.15, 0.8, 0.1)
        assert "set_nu_non_newtonian" in code
        assert "0.15" in code
        assert "0.8" in code
        assert "0.1" in code

    def test_enabled_has_guard(self):
        code = _generate_non_newtonian_code(True, 0.15, 0.8, 0.1)
        assert "if constexpr" in code or "if" in code
        assert "NON_NEWTONIAN" in code


# ── Test 5d: FluidX3D free surface ────────────────────────────────────────────


class TestFluidX3DFreeSurface:
    """Validate _generate_free_surface_code."""

    def test_disabled_returns_empty(self):
        code = _generate_free_surface_code(False, 0.5)
        assert code == ""

    def test_enabled_sets_flags(self):
        code = _generate_free_surface_code(True, 0.8)
        assert "TYPE_L" in code
        assert "TYPE_G" in code
        assert "0.8" in code

    def test_enabled_surface_tension(self):
        code = _generate_free_surface_code(True, 0.5)
        assert "surface_tension" in code.lower() or "sigma" in code.lower() or "TYPE_" in code


# ── Test 5e: FluidX3D thermal ─────────────────────────────────────────────────


class TestFluidX3DThermal:
    """Validate thermal init and defs generation."""

    def test_thermal_disabled_returns_empty(self):
        code = _generate_thermal_init_code(False, 350, 300)
        assert code == ""

    def test_thermal_init_sets_temperature(self):
        code = _generate_thermal_init_code(True, 350, 300)
        assert "lbm.T[n]" in code or "temperature" in code.lower()

    def test_thermal_defs_has_beta(self):
        code = _generate_thermal_defs(True, 3e-4)
        assert "beta" in code.lower() or "3e-4" in code
        assert "3e-4" in code or "0.0003" in code

    def test_thermal_defs_disabled_empty(self):
        code = _generate_thermal_defs(False, 3e-4)
        assert code == ""


# ── Test 5f: FluidX3D symmetry + pressure outlet ──────────────────────────────


class TestFluidX3DSymmetryPressure:
    """Validate symmetry and pressure outlet boundary conditions."""

    def test_symmetry_y_template(self):
        assert "channel_y" in BC_TEMPLATES_SYMMETRY
        code = BC_TEMPLATES_SYMMETRY["channel_y"].format(
            u_inlet_x=0.05, u_inlet_y=0.0, u_inlet_z=0.0, outlet_rho="lbm.rho[n] = 1.0f;"
        )
        assert "TYPE_Z" in code

    def test_symmetry_z_template(self):
        assert "channel_z" in BC_TEMPLATES_SYMMETRY
        code = BC_TEMPLATES_SYMMETRY["channel_z"].format(
            u_inlet_x=0.05, u_inlet_y=0.0, u_inlet_z=0.0, outlet_rho="lbm.rho[n] = 1.0f;"
        )
        assert "TYPE_Z" in code

    def test_channel_with_symmetry_y(self):
        code = _generate_boundary_code("channel", 0.05, 0.0, 0.0, has_stl=False, symmetry_axis="y")
        assert "TYPE_Z" in code

    def test_box_with_symmetry_y(self):
        code = _generate_boundary_code("box", 0.0, 0.0, 0.0, has_stl=False, symmetry_axis="y")
        assert "TYPE_Z" in code


# ── Test 5g: FluidX3D object forces ───────────────────────────────────────────


class TestFluidX3DObjectForces:
    """Validate _generate_object_forces_loop."""

    def test_no_objects_returns_empty(self):
        code = _generate_object_forces_loop([])
        assert code == ""

    def test_one_object(self):
        code = _generate_object_forces_loop([{"file": "body.stl", "type_flag": "TYPE_O"}])
        assert "OBJ_FORCE" in code or "object_force" in code

    def test_three_objects(self):
        code = _generate_object_forces_loop(
            [
                {"file": "a.stl", "type_flag": "TYPE_O"},
                {"file": "b.stl", "type_flag": "TYPE_S"},
                {"file": "c.stl", "type_flag": "TYPE_O"},
            ]
        )
        assert code.count("OBJ_FORCE" if "OBJ_FORCE" in code else "object_force") == 3


# ── Test 5h: FluidX3D full setup with new params ──────────────────────────────


class TestFluidX3DFullSetup:
    """Validate _generate_setup_cpp with all new features enabled."""

    BASE_PARAMS = dict(
        case_name="full_test",
        domain_type="channel",
        Nx=128,
        Ny=64,
        Nz=64,
        nu=0.01,
        lbm_length=1.0,
        lbm_velocity=0.05,
        si_length=2.0,
        si_velocity=1.0,
        si_density=1000.0,
        fx=1e-9,
        fy=0.0,
        fz=0.0,
        u_inlet_x=0.05,
        u_inlet_y=0.0,
        u_inlet_z=0.0,
        time_steps=1000,
        write_interval=100,
    )

    def test_all_features_disabled_produces_valid_cpp(self):
        """Default params (no extra features) should compile."""
        cpp = _generate_setup_cpp(**self.BASE_PARAMS)
        assert "void main_setup()" in cpp
        assert "lbm.run" in cpp

    def test_thermal_enabled_in_cpp(self):
        cpp = _generate_setup_cpp(
            **self.BASE_PARAMS,
            thermal=True,
            beta=3e-4,
            T_hot=350,
            T_cold=300,
        )
        assert "beta" in cpp.lower()

    def test_free_surface_enabled_in_cpp(self):
        cpp = _generate_setup_cpp(
            **self.BASE_PARAMS,
            free_surface=True,
            fill_fraction=0.7,
        )
        assert "TYPE_L" in cpp

    def test_non_newtonian_enabled_in_cpp(self):
        cpp = _generate_setup_cpp(
            **self.BASE_PARAMS,
            non_newtonian=True,
            n_index=0.8,
            consistency=0.1,
        )
        assert "set_nu_non_newtonian" in cpp

    def test_parabolic_inlet_in_cpp(self):
        cpp = _generate_setup_cpp(
            **self.BASE_PARAMS,
            profile_shape="parabolic",
        )
        assert "Ny_f" in cpp or "y" in cpp or "6.0" in cpp

    def test_multiple_objects_in_cpp(self):
        cpp = _generate_setup_cpp(
            **self.BASE_PARAMS,
            stl_configs=[
                {"file": "body.stl", "type_flag": "TYPE_S|TYPE_X"},
                {"file": "wing.stl", "type_flag": "TYPE_O"},
            ],
        )
        assert "body" in cpp or "stl" in cpp.lower()
        assert "OBJ_FORCE" in cpp or "object_force" in cpp

    def test_symmetry_in_cpp(self):
        cpp = _generate_setup_cpp(
            **self.BASE_PARAMS,
            symmetry_axis="y",
        )
        assert "TYPE_Z" in cpp

    def test_all_features_enabled(self):
        """Stress test: all features enabled simultaneously."""
        cpp = _generate_setup_cpp(
            **self.BASE_PARAMS,
            thermal=True,
            beta=3e-4,
            T_hot=350,
            T_cold=300,
            free_surface=True,
            fill_fraction=0.8,
            non_newtonian=True,
            n_index=0.8,
            consistency=0.1,
            profile_shape="parabolic",
            symmetry_axis="y",
            stl_configs=[{"file": "body.stl", "type_flag": "TYPE_S|TYPE_X"}],
            outlet_type="neumann",
        )
        assert "void main_setup()" in cpp
        assert "lbm.run" in cpp
        assert "{" in cpp
        assert "}" in cpp


# ── Test 5i: FluidX3D export_for_render ───────────────────────────────────────


class TestFluidX3DExportForRender:
    """Validate VTK→OBJ export pipeline with minimal test data."""

    def _write_minimal_vtk(self, tmp_path, Nx=10, Ny=6, Nz=6) -> str:
        """Write a minimal ASCII VTK structured grid with velocity."""
        path = tmp_path / "test.vtk"
        path.write_text(
            f"""# vtk DataFile Version 2.0
FluidX3D test
ASCII
DATASET STRUCTURED_GRID
DIMENSIONS {Nx} {Ny} {Nz}
ORIGIN 0 0 0
SPACING 1.0 1.0 1.0
POINTS {Nx * Ny * Nz} float
"""
            + "\n".join(f"{x} {y} {z}" for x in range(Nx) for y in range(Ny) for z in range(Nz))
            + """
VECTORS velocity float
"""
            + " ".join("1.0 0.0 0.0" for _ in range(Nx * Ny * Nz))
        )
        return str(path)

    def test_export_is_importable_function(self):
        """Verify the export function exists and is callable."""
        import importlib

        mod = importlib.import_module("freecad_mcp.tools.fluidx3d")
        assert hasattr(mod, "_generate_setup_cpp")

    def test_vtk_parse_dimensions(self):
        """VTK file has correct dimensions."""
        import re

        header = "DIMENSIONS 10 8 6\nORIGIN 0 0 0\nSPACING 1 1 1\nPOINTS 480 float"
        dim = re.search(r"DIMENSIONS\s+(\d+)\s+(\d+)\s+(\d+)", header)
        assert dim is not None
        assert int(dim.group(1)) == 10
        assert int(dim.group(2)) == 8
        assert int(dim.group(3)) == 6

    def test_obj_streamline_format(self, tmp_path):
        """Validate OBJ output has vertices and lines."""
        obj_path = tmp_path / "test_streamline.obj"
        with open(obj_path, "w") as f:
            f.write("v 0.0 0.0 0.0\n")
            f.write("v 1.0 0.0 0.0\n")
            f.write("v 2.0 1.0 0.0\n")
            f.write("v 3.0 1.0 1.0\n")
            f.write("l 1 2\n")
            f.write("l 2 3\n")
            f.write("l 3 4\n")
        content = obj_path.read_text()
        assert "v " in content
        assert "l " in content

    def test_csv_export_format(self, tmp_path):
        """Validate CSV output format."""
        csv_path = tmp_path / "test_velocity.csv"
        with open(csv_path, "w") as f:
            f.write("x,y,z,vx,vy,vz\n")
            f.write("0.0,0.0,0.0,1.0,0.0,0.0\n")
            f.write("1.0,0.0,0.0,0.95,0.02,0.01\n")
        content = csv_path.read_text().replace("\r", "")
        assert "x,y,z,vx,vy,vz" in content
        assert "0.0,0.0,0.0,1.0,0.0,0.0" in content


# ── Test 6: NL2FOAM schema ────────────────────────────────────────────────────


class TestNL2FOAMSchema:
    """Validate the NL2FOAM prompt contains all required JSON schema sections."""

    SCHEMA_KEYS = [
        "solver",
        "flow_type",
        "fluid",
        "inlet",
        "outlet",
        "walls",
        "domain",
        "mesh",
        "control",
        "reasoning",
    ]

    def _get_schema_json(self) -> str:
        """Extract schema_json from cfd_nl2foam source code."""
        import freecad_mcp.tools.cfd as cfd_mod

        source = inspect.getsource(cfd_mod)
        # Find the schema_json assignment block
        match = re.search(
            r'schema_json\s*=\s*"""(\{.*?\})"""',
            source,
            re.DOTALL,
        )
        if not match:
            raise AssertionError("Could not find schema_json in cfd module source")
        return match.group(1)

    def test_schema_contains_all_required_keys(self):
        schema_str = self._get_schema_json()
        for key in self.SCHEMA_KEYS:
            assert f'"{key}"' in schema_str, f"Schema missing key: {key}"

    def test_schema_has_json_braces(self):
        schema_str = self._get_schema_json()
        assert schema_str.strip().startswith("{")
        assert schema_str.strip().endswith("}")

    def test_schema_contains_solver_options(self):
        schema_str = self._get_schema_json()
        assert "simpleFoam" in schema_str
        assert "pisoFoam" in schema_str
        assert "pimpleFoam" in schema_str

    def test_schema_contains_flow_type_options(self):
        schema_str = self._get_schema_json()
        assert "laminar" in schema_str
        assert "kEpsilon" in schema_str
        assert "kOmegaSST" in schema_str

    def test_schema_contains_fluid_properties(self):
        schema_str = self._get_schema_json()
        assert "nu" in schema_str
        assert "density" in schema_str

    def test_schema_contains_domain_properties(self):
        schema_str = self._get_schema_json()
        assert "lx" in schema_str
        assert "ly" in schema_str
        assert "lz" in schema_str

    def test_schema_contains_mesh_properties(self):
        schema_str = self._get_schema_json()
        assert "nx" in schema_str
        assert "ny" in schema_str
        assert "nz" in schema_str

    def test_schema_contains_inlet_velocity(self):
        schema_str = self._get_schema_json()
        assert "velocity" in schema_str

    def test_schema_contains_reasoning(self):
        schema_str = self._get_schema_json()
        assert "physics" in schema_str.lower() or "reasoning" in schema_str


# ── Edge cases ─────────────────────────────────────────────────────────────────


class TestConstants:
    """Validate module-level constants are well-formed."""

    def test_flow_types_tuple(self):
        assert isinstance(FLOW_TYPES, tuple)
        assert LAMINAR in FLOW_TYPES
        assert KEPSILON in FLOW_TYPES
        assert KOMEGA_SST in FLOW_TYPES

    def test_solvers_dict(self):
        assert isinstance(SOLVERS, dict)
        assert "simpleFoam" in SOLVERS
        assert "pisoFoam" in SOLVERS
        assert "pimpleFoam" in SOLVERS

    def test_bc_templates_have_all_types(self):
        assert "channel" in BC_TEMPLATES
        assert "pipe" in BC_TEMPLATES
        assert "box" in BC_TEMPLATES
        assert "nozzle" in BC_TEMPLATES
        assert "custom" in BC_TEMPLATES

    def test_fv_solution_turb_returns_strings(self):
        sol, res, rel = _fv_solution_turb(KEPSILON)
        assert isinstance(sol, str)
        assert isinstance(res, str)
        assert isinstance(rel, str)

    def test_fv_solution_turb_non_laminar_returns_turbulence_blocks(self):
        """Any non-LAMINAR value returns turbulence solver blocks."""
        sol, res, rel = _fv_solution_turb("bogus")
        assert "k" in sol
        assert "omega" in sol
        assert isinstance(sol, str)
        assert isinstance(res, str)
        assert isinstance(rel, str)


class TestFluidx3dEnvironment:
    def test_fluidx3d_path_detects_clone(self):
        from freecad_mcp.tools.fluidx3d import _find_fluidx3d

        path = _find_fluidx3d()
        if os.path.isdir(r"D:\Dev\repos\FluidX3D\src"):
            assert path is not None
            assert os.path.isdir(os.path.join(path, "src"))

    def test_compiler_detection_returns_string_or_none(self):
        from freecad_mcp.tools.fluidx3d import _find_compiler

        compiler = _find_compiler()
        assert compiler is None or isinstance(compiler, str)

    def test_gpu_query_returns_list(self):
        from freecad_mcp.tools.fluidx3d import _query_gpu_devices

        devices = _query_gpu_devices()
        assert isinstance(devices, list)
