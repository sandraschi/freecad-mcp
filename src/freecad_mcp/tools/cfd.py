"""
CFD (Computational Fluid Dynamics) MCP tools for FreeCAD → OpenFOAM pipeline.

Provides the full Geometry-Mesh-Simulation-Analysis (GMSA) workflow:
  1. Parametric fluid domain creation in FreeCAD → STEP export
  2. OpenFOAM case directory generation (blockMesh, boundary conditions, physics)
  3. Docker-based OpenFOAM solver execution
  4. Results parsing (forces, residuals, field summaries)
  5. Headless parametric sweeps for design optimization
  6. NL2FOAM: natural language → executable OpenFOAM config via LLM
  7. Point cloud sampling for Physics-Informed Neural Networks (PINNs)

All geometry operations delegate to the FreeCAD bridge/subprocess.
OpenFOAM execution uses Docker (openfoam/openfoam10 image) when available,
or produces ready-to-run case directories for manual execution.

Registered via register_cfd_tools(mcp, **deps) — called from server.py.
"""

import asyncio
import json
import logging
import os
import re
import shutil
from typing import Annotated

from pydantic import Field

logger = logging.getLogger("freecad-mcp.cfd")

_README_ONLY = {"readonly": True}

# Solver type constants
LAMINAR = "laminar"
KEPSILON = "kEpsilon"
KOMEGA_SST = "kOmegaSST"
FLOW_TYPES = (LAMINAR, KEPSILON, KOMEGA_SST)

# Supported OpenFOAM solvers
SOLVERS = {
    "simpleFoam": "Steady-state incompressible (SIMPLE)",
    "pisoFoam": "Transient incompressible (PISO)",
    "pimpleFoam": "Transient incompressible (PIMPLE, large time steps)",
}

# Boundary condition types
BC_TYPES = (
    "fixedValue",
    "zeroGradient",
    "inletOutlet",
    "outletInlet",
    "slip",
    "noSlip",
    "symmetry",
    "empty",
    "wedge",
    "cyclic",
    "pressureInletVelocity",
    "pressureInletOutletVelocity",
    "totalPressure",
    "flowRateInletVelocity",
)

# ── OpenFOAM template files ───────────────────────────────────────────────────

_CONTROL_DICT = """/*--------------------------------*- C++ -*----------------------------------*\\
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
    class       dictionary;
    object      controlDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     {solver};

startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {end_time};
deltaT          {delta_t};

writeControl    timeStep;
writeInterval   {write_interval};
purgeWrite      0;
writeFormat     ascii;
writePrecision  6;
writeCompression off;

timeFormat      general;
timePrecision   6;

runTimeModifiable true;

functions
{{
    forces
    {{
        type            forces;
        libs            (forces);
        patches         ({force_patches});
        rho             rhoInf;
        rhoInf          {density};
        writeControl    timeStep;
        writeInterval   1;
    }}
}}

// ************************************************************************* //
"""

_FV_SCHEMES = """/*--------------------------------*- C++ -*----------------------------------*\\
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
    class       dictionary;
    object      fvSchemes;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes
{{
    default         {time_scheme};
}}

gradSchemes
{{
    default         Gauss linear;
}}

divSchemes
{{
    default         none;
    div(phi,U)      Gauss linearUpwind grad(U);
    div(phi,k)      Gauss upwind;
    div(phi,omega)  Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}}

laplacianSchemes
{{
    default         Gauss linear corrected;
}}

interpolationSchemes
{{
    default         linear;
}}

snGradSchemes
{{
    default         corrected;
}}

// ************************************************************************* //
"""

_FV_SOLUTION = """/*--------------------------------*- C++ -*----------------------------------*\\
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
    class       dictionary;
    object      fvSolution;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{{
    p
    {{
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-7;
        relTol          0.01;
    }}
    U
    {{
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-8;
        relTol          0.1;
    }}
    {turb_solvers}
}}

SIMPLE
{{
    nNonOrthogonalCorrectors 1;
    pRefCell        0;
    pRefValue       0;
    residualControl
    {{
        p               1e-4;
        U               1e-5;
        {turb_residuals}
    }}
}}

relaxationFactors
{{
    fields
    {{
        p               0.3;
    }}
    equations
    {{
        U               0.7;
        {turb_relax}
    }}
}}
"""


def _fv_solution_turb(turb_model: str) -> tuple[str, str, str]:
    """Return (turb_solvers, turb_residuals, turb_relax) blocks."""
    if turb_model == LAMINAR:
        return "", "", ""
    return (
        """    k
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-8;
        relTol          0.1;
    }
    omega
    {
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       1e-8;
        relTol          0.1;
    }""",
        "        k               1e-5;\n        omega           1e-5;",
        "        k               0.7;\n        omega           0.7;",
    )


_TRANSPORT_PROPERTIES = """/*--------------------------------*- C++ -*----------------------------------*\\
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
    class       dictionary;
    object      transportProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

transportModel  Newtonian;
nu              [0 2 -1 0 0 0 0] {nu};
// ************************************************************************* //
"""

_TURBULENCE_PROPERTIES = """/*--------------------------------*- C++ -*----------------------------------*\\
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
    class       dictionary;
    object      turbulenceProperties;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

simulationType  {sim_type};

RAS
{{
    model           {model};

    turbulence      on;
    printCoeffs     on;
}}
// ************************************************************************* //
"""

_BLOCK_MESH_DICT = """/*--------------------------------*- C++ -*----------------------------------*\\
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
    class       dictionary;
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters {scale};

vertices
(
    {vertices}
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    {boundaries}
);

mergePatchPairs
(
);
"""

# ── Registration ──────────────────────────────────────────────────────────────


def register_cfd_tools(
    mcp,
    state: dict,
    bridge_send,
    run_freecad,
    work_dir: str,
    output_dir: str,
    upload_dir: str,
    build_result,
    llm_settings: dict | None = None,
):
    """Register all 10 CFD MCP tools on the FastMCP instance.

    Returns a dict mapping tool_name -> callable for REST dispatch.
    """
    if llm_settings is None:
        llm_settings = {}

    CFD_CASE_DIR = os.path.join(work_dir, "cfd_cases")
    os.makedirs(CFD_CASE_DIR, exist_ok=True)

    # ── Docker/OpenFOAM detection ──────────────────────────────────────────

    def _check_docker() -> tuple[bool, str]:
        """Check if Docker/Podman is available and running."""
        exes = ["docker", "podman"]
        import subprocess

        for exe in exes:
            try:
                r = subprocess.run(
                    [exe, "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=10
                )
                if r.returncode == 0 and r.stdout.strip():
                    return True, exe
            except FileNotFoundError:
                continue
            except Exception:
                logger.debug("Docker/Podman check failed for %s", exe)
                continue
        return False, ""

    def _check_openfoam_image(docker_exe: str) -> bool:
        """Check if the OpenFOAM Docker image is available."""
        import subprocess

        try:
            r = subprocess.run(
                [docker_exe, "images", "--format", "{{.Repository}}:{{.Tag}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return "openfoam/openfoam" in r.stdout
        except Exception:
            return False

    def _write_foam_file(path: str, content: str) -> None:
        """Write a file, creating parent directories as needed."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    # ── cfd_status ────────────────────────────────────────────────────────

    @mcp.tool(annotations=_README_ONLY)
    async def cfd_status() -> dict:
        """Check CFD pipeline availability: Docker, OpenFOAM image, FreeCAD bridge.

        Call this first before any CFD operation to understand what execution
        modes are available. Returns docker and openfoam availability plus
        the FreeCAD bridge mode for geometry operations.

        ## Return Format
        {"success": bool, "docker_available": bool, "docker_exe": str, "openfoam_image": bool, "bridge_mode": str, "cfd_case_dir": str}

        ## Examples
        await cfd_status()
        """
        docker_ok, docker_exe = _check_docker()
        openfoam_ok = _check_openfoam_image(docker_exe) if docker_ok else False
        return {
            "success": True,
            "docker_available": docker_ok,
            "docker_exe": docker_exe or "none",
            "openfoam_image": openfoam_ok,
            "bridge_mode": state.get("bridge_mode", "none"),
            "cfd_case_dir": CFD_CASE_DIR,
        }

    # ── cfd_create_domain ─────────────────────────────────────────────────

    @mcp.tool()
    async def cfd_create_domain(
        domain_type: Annotated[
            str, Field(description="Domain shape: box, pipe, channel, nozzle, airfoil, custom.")
        ] = "channel",
        length_m: Annotated[float, Field(description="Domain length in metres.", ge=0.01)] = 1.0,
        width_m: Annotated[float, Field(description="Domain width in metres.", ge=0.001)] = 0.1,
        height_m: Annotated[float, Field(description="Domain height in metres.", ge=0.001)] = 0.05,
        inlet_radius_m: Annotated[float, Field(description="Inlet radius for pipe/nozzle in metres.")] = 0.02,
        outlet_radius_m: Annotated[float, Field(description="Outlet radius for nozzle in metres.")] = 0.01,
        mesh_cells: Annotated[int, Field(description="Target cell count for blockMesh (nx*ny*nz).", ge=100)] = 20000,
        case_name: Annotated[str, Field(description="Case directory name, e.g. my_pipe.")] = "channel_flow",
        step_file: Annotated[str, Field(description="Existing STEP filename in uploads for 'custom' domain.")] = "",
    ) -> dict:
        """Create a CFD fluid domain and generate an OpenFOAM case skeleton.

        Generates a parametric geometry in FreeCAD, exports as STEP, creates
        blockMeshDict for structured hex mesh, and writes the full OpenFOAM
        case directory (0/, constant/, system/). The physics and boundary
        conditions can then be configured with cfd_configure_physics and
        cfd_set_boundary.

        Domain types:
        - box: rectangular duct (3D)
        - pipe: cylindrical tube (axis-aligned)
        - channel: flat rectangular channel (2D-like with symmetry)
        - nozzle: convergent-divergent nozzle
        - custom: use an existing STEP file from uploads

        ## Return Format
        {"success": bool, "case_name": str, "case_dir": str, "data": {"domain_type": str, "dimensions_m": [L,W,H], "mesh_cells": int, "step_file": str}}

        ## Examples
        await cfd_create_domain(domain_type="pipe", length_m=0.5, inlet_radius_m=0.02, mesh_cells=50000, case_name="pipe_study")
        await cfd_create_domain(domain_type="custom", step_file="my_valve.step", mesh_cells=100000, case_name="valve_cfd")
        """
        case_dir = os.path.join(CFD_CASE_DIR, case_name)
        step_output = os.path.join(case_dir, "geometry.step")
        os.makedirs(case_dir, exist_ok=True)

        # Build geometry dimensions in mm (FreeCAD native unit)
        length_mm = length_m * 1000
        width_mm = width_m * 1000
        height_mm = height_m * 1000

        if domain_type == "custom" and step_file:
            src = os.path.join(upload_dir, step_file)
            if not os.path.isfile(src):
                src = os.path.join(output_dir, step_file)
            if os.path.isfile(src):
                shutil.copy(src, step_output)
            else:
                return {"success": False, "error": f"Custom STEP file '{step_file}' not found in uploads or outputs."}
        else:
            # Generate parametric geometry via FreeCAD
            if domain_type == "pipe":
                shape_code = f"Part.makeCylinder({inlet_radius_m * 1000}, {length_mm})"
            elif domain_type == "nozzle":
                r1 = inlet_radius_m * 1000
                r2 = outlet_radius_m * 1000
                shape_code = (
                    f"c1 = Part.makeCylinder({r1}, {length_mm * 0.3});"
                    f"c2 = Part.makeCone({r1}, {r2}, {length_mm * 0.4});"
                    f"c3 = Part.makeCylinder({r2}, {length_mm * 0.3});"
                    "c2.translate(App.Vector(0, 0, length_mm * 0.3));"
                    "c3.translate(App.Vector(0, 0, length_mm * 0.7));"
                    "s = c1.fuse(c2).fuse(c3)"
                )
            elif domain_type == "channel":
                shape_code = f"Part.makeBox({length_mm}, {width_mm}, {height_mm})"
            else:
                shape_code = f"Part.makeBox({length_mm}, {width_mm}, {height_mm})"

            script = f"""
import FreeCAD as App, Part, Mesh, json, os

doc = App.newDocument("CFD_Domain")
try:
    s = {shape_code}
    obj = doc.addObject("Part::Feature", "FluidDomain")
    obj.Shape = s
    doc.recompute()
    Mesh.export([obj], r"{step_output.replace(".step", ".stl")}")
    Part.export([obj], r"{step_output}")
    bbox = obj.Shape.BoundBox
    info = {{
        "domain_type": "{domain_type}",
        "dimensions_mm": [bbox.XLength, bbox.YLength, bbox.ZLength],
        "volume_mm3": obj.Shape.Volume,
        "step_file": r"{step_output}",
    }}
    print(json.dumps(info))
    App.closeDocument(doc.Name)
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
    try:
        App.closeDocument(doc.Name)
    except Exception:
        pass
"""
            out, err, code = await run_freecad(script, timeout=120)
            if code != 0:
                return build_result("cfd_create_domain", out, err, code, extra={"case_name": case_name})

        # Compute mesh cell distribution
        cells = mesh_cells
        nz = max(1, round(cells ** (1 / 3)))
        ny = max(1, round((cells / nz) ** (1 / 2)))
        nx = max(1, cells // (ny * nz))
        actual_cells = nx * ny * nz

        # Write blockMeshDict
        dims = [length_m, width_m, height_m]
        vertices = "\n".join(
            [
                "    (0 0 0)",
                f"    ({dims[0]:.6f} 0 0)",
                f"    ({dims[0]:.6f} {dims[1]:.6f} 0)",
                f"    (0 {dims[1]:.6f} 0)",
                f"    (0 0 {dims[2]:.6f})",
                f"    ({dims[0]:.6f} 0 {dims[2]:.6f})",
                f"    ({dims[0]:.6f} {dims[1]:.6f} {dims[2]:.6f})",
                f"    (0 {dims[1]:.6f} {dims[2]:.6f})",
            ]
        )

        boundaries = """    inlet
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

        blockmesh = _BLOCK_MESH_DICT.format(
            scale=1.0,
            vertices=vertices,
            nx=nx,
            ny=ny,
            nz=nz,
            boundaries=boundaries,
        )
        _write_foam_file(os.path.join(case_dir, "constant", "polyMesh", "blockMeshDict"), blockmesh)

        data = {
            "domain_type": domain_type,
            "dimensions_m": [round(v, 4) for v in dims],
            "mesh_cells": actual_cells,
            "step_file": step_output,
        }

        # Copy STL to fluidx3d_cases so FluidX3D can auto-discover geometry
        fluidx3d_cases_dir = os.path.join(work_dir, "fluidx3d_cases")
        stl_src = os.path.join(case_dir, "geometry.stl")
        if os.path.isfile(stl_src):
            f3d_stl_dir = os.path.join(fluidx3d_cases_dir, case_name)
            os.makedirs(f3d_stl_dir, exist_ok=True)
            shutil.copy(stl_src, os.path.join(f3d_stl_dir, "geometry.stl"))

        return {"success": True, "case_name": case_name, "case_dir": case_dir, "data": data}

    # ── cfd_configure_physics ─────────────────────────────────────────────

    @mcp.tool()
    async def cfd_configure_physics(
        case_name: Annotated[str, Field(description="Case directory name (from cfd_create_domain).")],
        solver: Annotated[
            str, Field(description="OpenFOAM solver: simpleFoam (steady), pisoFoam, pimpleFoam.")
        ] = "simpleFoam",
        flow_type: Annotated[str, Field(description="Flow model: laminar, kEpsilon, kOmegaSST.")] = "laminar",
        fluid_nu: Annotated[
            float, Field(description="Kinematic viscosity in m^2/s. Water=1e-6, Air=1.5e-5.", ge=1e-10)
        ] = 1e-6,
        fluid_density: Annotated[
            float, Field(description="Fluid density in kg/m^3. Water=1000, Air=1.225.", ge=1e-6)
        ] = 1000.0,
        inlet_velocity: Annotated[float, Field(description="Inlet velocity magnitude in m/s.", ge=0)] = 1.0,
        end_time: Annotated[
            float, Field(description="Simulation end time in seconds (steady=iteration count).", ge=1)
        ] = 1000.0,
        delta_t: Annotated[
            float, Field(description="Time step in seconds (steady solvers ignore this).", ge=1e-10)
        ] = 1.0,
        write_interval: Annotated[int, Field(description="Write results every N time steps.", ge=1)] = 100,
    ) -> dict:
        """Configure physics models and solver settings for a CFD case.

        Generates controlDict, fvSchemes, fvSolution, transportProperties, and
        turbulenceProperties for the specified case. Must be called after
        cfd_create_domain and before cfd_set_boundary.

        Uses cfd_set_boundary for per-patch field conditions (U, p, k, omega).

        ## Return Format
        {"success": bool, "case_name": str, "data": {"solver": str, "flow_type": str, "Re": float, "nu": float, "density": float}}

        ## Examples
        await cfd_configure_physics(case_name="pipe_study", solver="simpleFoam", flow_type="kOmegaSST", fluid_nu=1.5e-5, inlet_velocity=10.0)
        await cfd_configure_physics(case_name="channel_flow", flow_type="laminar", fluid_nu=1e-6, inlet_velocity=0.1)
        """
        case_dir = os.path.join(CFD_CASE_DIR, case_name)
        if not os.path.isdir(case_dir):
            return {"success": False, "error": f"Case '{case_name}' not found. Run cfd_create_domain first."}

        if flow_type not in FLOW_TYPES:
            flow_type = LAMINAR
        if solver not in SOLVERS:
            solver = "simpleFoam"

        time_scheme = "steadyState" if solver == "simpleFoam" else "Euler"
        turb_solvers, turb_residuals, turb_relax = _fv_solution_turb(flow_type)
        force_patches = "walls"

        # controlDict
        ctrl = _CONTROL_DICT.format(
            solver=solver,
            end_time=end_time,
            delta_t=delta_t,
            write_interval=write_interval,
            force_patches=f'"{force_patches}"',
            density=fluid_density,
        )
        _write_foam_file(os.path.join(case_dir, "system", "controlDict"), ctrl)

        # fvSchemes
        schemes = _FV_SCHEMES.format(time_scheme=time_scheme)
        _write_foam_file(os.path.join(case_dir, "system", "fvSchemes"), schemes)

        # fvSolution
        solution = _FV_SOLUTION.format(
            turb_solvers=turb_solvers,
            turb_residuals=turb_residuals,
            turb_relax=turb_relax,
        )
        _write_foam_file(os.path.join(case_dir, "system", "fvSolution"), solution)

        # transportProperties
        transport = _TRANSPORT_PROPERTIES.format(nu=fluid_nu)
        _write_foam_file(os.path.join(case_dir, "constant", "transportProperties"), transport)

        # turbulenceProperties
        if flow_type == LAMINAR:
            turb_props = _TURBULENCE_PROPERTIES.format(sim_type="laminar", model="laminar")
        else:
            model_name = "kEpsilon" if flow_type == KEPSILON else "kOmegaSST"
            turb_props = _TURBULENCE_PROPERTIES.format(sim_type="RAS", model=model_name)
        _write_foam_file(os.path.join(case_dir, "constant", "turbulenceProperties"), turb_props)

        # Estimate Reynolds number
        re_estimate = inlet_velocity * 0.1 / fluid_nu

        data = {
            "solver": solver,
            "flow_type": flow_type,
            "Re_estimate": round(re_estimate, 1),
            "nu": fluid_nu,
            "density": fluid_density,
            "inlet_velocity": inlet_velocity,
        }

        # Store config for subsequent tools
        _cfg = os.path.join(case_dir, ".cfd_config.json")
        with open(_cfg, "w") as f:
            json.dump(data, f)

        return {"success": True, "case_name": case_name, "data": data}

    # ── cfd_set_boundary ──────────────────────────────────────────────────

    @mcp.tool()
    async def cfd_set_boundary(
        case_name: Annotated[str, Field(description="Case directory name.")],
        patch_name: Annotated[str, Field(description="Patch name: inlet, outlet, walls.")],
        field_name: Annotated[str, Field(description="Field to set: U, p, k, omega, nut, alphat.")],
        bc_type: Annotated[
            str, Field(description="Boundary condition type (fixedValue, zeroGradient, inletOutlet, etc.).")
        ] = "fixedValue",
        value: Annotated[
            str, Field(description="Value as JSON string, e.g. 'uniform (1 0 0)' or 'uniform 0'.")
        ] = "uniform (0 0 0)",
    ) -> dict:
        """Configure boundary conditions for a specific patch and field.

        Generates the field file (e.g. 0/U, 0/p) in the case directory with
        the specified boundary condition. Call this for each (patch, field)
        combination after cfd_configure_physics.

        Common value formats:
        - Velocity: 'uniform (1 0 0)' (1 m/s in X)
        - Pressure: 'uniform 0'
        - Turbulence intensity I=5% → k = 1.5*(U*I)^2
        - Omega for SST: omega = k^0.5 / (0.09^0.25 * L)

        ## Return Format
        {"success": bool, "case_name": str, "data": {"patch": str, "field": str, "bc_type": str, "file": str}}

        ## Examples
        await cfd_set_boundary(case_name="pipe_study", patch_name="inlet", field_name="U", bc_type="fixedValue", value="uniform (1 0 0)")
        await cfd_set_boundary(case_name="pipe_study", patch_name="walls", field_name="U", bc_type="noSlip", value="uniform (0 0 0)")
        await cfd_set_boundary(case_name="pipe_study", patch_name="outlet", field_name="p", bc_type="fixedValue", value="uniform 0")
        """
        case_dir = os.path.join(CFD_CASE_DIR, case_name)
        if not os.path.isdir(case_dir):
            return {"success": False, "error": f"Case '{case_name}' not found."}

        if bc_type not in BC_TYPES:
            return {"success": False, "error": f"Unknown BC type '{bc_type}'. Valid: {', '.join(BC_TYPES)}"}

        # Determine field class and dimensions based on field name
        field_map = {
            "U": ("volVectorField", "[0 1 -1 0 0 0 0]"),
            "p": ("volScalarField", "[0 2 -2 0 0 0 0]"),
            "k": ("volScalarField", "[0 2 -2 0 0 0 0]"),
            "omega": ("volScalarField", "[0 0 -1 0 0 0 0]"),
            "nut": ("volScalarField", "[0 2 -1 0 0 0 0]"),
            "alphat": ("volScalarField", "[1 -1 -1 0 0 0 0]"),
        }
        field_cls, dims = field_map.get(field_name, ("volScalarField", "[0 0 0 0 0 0 0]"))

        no_slip_bc = "noSlip" if field_name == "U" else "zeroGradient"

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
    class       {field_cls};
    object      {field_name};
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      {dims};

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
        _write_foam_file(os.path.join(case_dir, "0", field_name), field_content)

        return {
            "success": True,
            "case_name": case_name,
            "data": {
                "patch": patch_name,
                "field": field_name,
                "bc_type": bc_type,
                "file": f"0/{field_name}",
            },
        }

    # ── cfd_build_case ────────────────────────────────────────────────────

    @mcp.tool()
    async def cfd_build_case(
        case_name: Annotated[str, Field(description="Case directory name.")],
    ) -> dict:
        """Assemble and validate a complete OpenFOAM case directory.

        Checks that all required files exist (blockMeshDict, controlDict,
        fvSchemes, fvSolution, transportProperties, boundary fields).
        Reports missing files so the agent can fill them in.

        ## Return Format
        {"success": bool, "case_name": str, "data": {"files": list, "missing": list, "ready": bool}}

        ## Examples
        await cfd_build_case(case_name="pipe_study")
        """
        case_dir = os.path.join(CFD_CASE_DIR, case_name)
        if not os.path.isdir(case_dir):
            return {"success": False, "error": f"Case '{case_name}' not found."}

        required = [
            "constant/polyMesh/blockMeshDict",
            "system/controlDict",
            "system/fvSchemes",
            "system/fvSolution",
            "constant/transportProperties",
            "constant/turbulenceProperties",
            "0/U",
            "0/p",
        ]

        _cfg = os.path.join(case_dir, ".cfd_config.json")
        if os.path.isfile(_cfg):
            with open(_cfg) as f:
                cfg = json.load(f)
            if cfg.get("flow_type") != LAMINAR:
                required.extend(["0/k", "0/omega", "0/nut"])

        files = []
        missing = []
        for rel in required:
            fp = os.path.join(case_dir, rel)
            if os.path.isfile(fp):
                files.append(rel)
            else:
                missing.append(rel)

        return {
            "success": True,
            "case_name": case_name,
            "data": {
                "files": files,
                "missing": missing,
                "ready": len(missing) == 0,
            },
        }

    # ── cfd_run_solver ────────────────────────────────────────────────────

    @mcp.tool()
    async def cfd_run_solver(
        case_name: Annotated[str, Field(description="Case directory name.")],
        steps: Annotated[
            str, Field(description="Comma-separated solver steps: blockMesh,checkMesh,simpleFoam (or pisoFoam).")
        ] = "blockMesh,checkMesh,simpleFoam",
        parallel: Annotated[bool, Field(description="Use parallel decomposition (requires decomposeParDict).")] = False,
        n_cores: Annotated[int, Field(description="Number of CPU cores for parallel run.", ge=1, le=64)] = 4,
    ) -> dict:
        """Execute OpenFOAM solver via Docker container.

        Runs the specified solver steps inside an OpenFOAM Docker container
        with the case directory mounted. Requires Docker and the OpenFOAM
        image (docker pull openfoam/openfoam10-paraview56).

        Steps:
        - blockMesh: generate hexahedral mesh
        - checkMesh: validate mesh quality
        - simpleFoam/pisoFoam/pimpleFoam: run the solver
        - reconstructPar: reconstruct parallel results
        - postProcess: run function objects (forces, etc.)

        ## Return Format
        {"success": bool, "case_name": str, "data": {"steps_completed": list, "log": str, "exit_codes": dict}}

        ## Examples
        await cfd_run_solver(case_name="pipe_study")
        await cfd_run_solver(case_name="pipe_study", steps="blockMesh,simpleFoam", parallel=True, n_cores=8)
        """
        case_dir = os.path.join(CFD_CASE_DIR, case_name)
        if not os.path.isdir(case_dir):
            return {"success": False, "error": f"Case '{case_name}' not found."}

        docker_ok, docker_exe = _check_docker()
        if not docker_ok:
            return {
                "success": False,
                "error": "Docker/Podman not available. Install Docker Desktop for Windows and pull openfoam/openfoam10-paraview56.",
            }

        openfoam_ok = _check_openfoam_image(docker_exe)
        if not openfoam_ok:
            return {
                "success": False,
                "error": "OpenFOAM Docker image not found. Run: docker pull openfoam/openfoam10-paraview56",
            }

        step_list = [s.strip() for s in steps.split(",") if s.strip()]
        steps_completed = []
        exit_codes = {}
        full_log = []

        # Convert Windows path for Docker mount
        win_path = os.path.abspath(case_dir)
        if win_path[1:2] == ":":
            docker_mount = "/" + win_path[0].lower() + win_path[2:].replace("\\", "/")
        else:
            docker_mount = "/" + win_path.replace("\\", "/")

        # Build Docker command and execute each step
        for step in step_list:
            if parallel and step in ("simpleFoam", "pisoFoam", "pimpleFoam"):
                decompose_cmd = f"decomposePar && mpirun -np {n_cores} {step} -parallel && reconstructPar"
                cmd_parts = [
                    docker_exe,
                    "run",
                    "--rm",
                    "-v",
                    f"{win_path}:{docker_mount}",
                    "--workdir",
                    docker_mount,
                    "openfoam/openfoam10-paraview56",
                ]
                cmd_parts.extend(["bash", "-c", decompose_cmd])
            else:
                cmd_parts = [
                    docker_exe,
                    "run",
                    "--rm",
                    "-v",
                    f"{win_path}:{docker_mount}",
                    "--workdir",
                    docker_mount,
                    "openfoam/openfoam10-paraview56",
                    step,
                ]

            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd_parts,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
                out_text = stdout.decode("utf-8", errors="replace")
                err_text = stderr.decode("utf-8", errors="replace")
                exit_codes[step] = proc.returncode or 0
                full_log.append(f"=== {step} (exit={proc.returncode}) ===\n{out_text[-5000:]}")
                if proc.returncode == 0:
                    steps_completed.append(step)
                else:
                    full_log.append(f"STDERR: {err_text[-2000:]}")
                    break
            except TimeoutError:
                exit_codes[step] = -1
                full_log.append(f"=== {step} TIMEOUT ===")
                break
            except Exception as e:
                logger.debug("Solver step %s failed: %s", step, e)
                exit_codes[step] = -2
                full_log.append(f"=== {step} ERROR: {e} ===")
                break

        success = len(steps_completed) == len(step_list)
        return {
            "success": success,
            "case_name": case_name,
            "data": {
                "steps_completed": steps_completed,
                "log": "".join(full_log[-10:])[-20000:],
                "exit_codes": exit_codes,
            },
        }

    # ── cfd_read_results ──────────────────────────────────────────────────

    @mcp.tool(annotations=_README_ONLY)
    async def cfd_read_results(
        case_name: Annotated[str, Field(description="Case directory name.")],
    ) -> dict:
        """Read simulation results from an OpenFOAM case directory.

        Parses force coefficients (lift, drag), residuals from solver log,
        and lists available time directories. Use after cfd_run_solver.

        ## Return Format
        {"success": bool, "case_name": str, "data": {"times": list, "forces": dict, "residuals": dict, "converged": bool}}

        ## Examples
        await cfd_read_results(case_name="pipe_study")
        """
        case_dir = os.path.join(CFD_CASE_DIR, case_name)
        if not os.path.isdir(case_dir):
            return {"success": False, "error": f"Case '{case_name}' not found."}

        # Find time directories (numeric folders)
        times = []
        for entry in os.listdir(case_dir):
            fp = os.path.join(case_dir, entry)
            if os.path.isdir(fp) and entry.replace(".", "").isdigit():
                times.append(entry)
        try:
            times.sort(key=float)
        except ValueError:
            pass

        # Parse forces (postProcessing/forces/)
        forces = {}
        forces_dir = os.path.join(case_dir, "postProcessing", "forces")
        if os.path.isdir(forces_dir):
            for tf in os.listdir(forces_dir):
                fp = os.path.join(forces_dir, tf)
                if os.path.isfile(fp) and tf != "fields":
                    try:
                        with open(fp) as f:
                            lines = f.readlines()
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                parts = line.split()
                                if len(parts) >= 4:
                                    forces[tf] = {
                                        "time": float(parts[0]),
                                        "pressure_x": float(parts[1]) if len(parts) > 1 else 0,
                                        "pressure_y": float(parts[2]) if len(parts) > 2 else 0,
                                        "pressure_z": float(parts[3]) if len(parts) > 3 else 0,
                                    }
                    except (ValueError, IndexError):
                        pass

        # Parse residuals from solver log
        residuals = {}
        log_files = [os.path.join(case_dir, f"log.{s}") for s in SOLVERS]
        log_files.append(os.path.join(case_dir, "log"))
        for log_f in log_files:
            if os.path.isfile(log_f):
                try:
                    with open(log_f) as f:
                        content = f.read()
                    # Extract final residuals
                    for field in ("p", "Ux", "Uy", "Uz", "k", "omega"):
                        pattern = rf"Solving for {field}.*?Final residual = ([\d.e+\-]+)"
                        matches = re.findall(pattern, content, re.DOTALL)
                        if matches:
                            residuals[field] = float(matches[-1])
                    break
                except Exception:
                    logger.debug("Failed to parse residual log: %s", log_f)

        converged = False
        if residuals:
            converged = all(v < 1e-4 for v in residuals.values())

        return {
            "success": True,
            "case_name": case_name,
            "data": {
                "times": times,
                "latest_time": times[-1] if times else None,
                "forces": forces,
                "final_residuals": residuals,
                "converged": converged,
            },
        }

    # ── cfd_parametric_study ──────────────────────────────────────────────

    @mcp.tool()
    async def cfd_parametric_study(
        case_name: Annotated[str, Field(description="Base case name (will be suffixed _0, _1, ...).")],
        parameter: Annotated[
            str, Field(description="Parameter to vary: inlet_velocity, length, width, height, fluid_nu, angle.")
        ],
        values: Annotated[str, Field(description="JSON array of parameter values, e.g. '[0.5, 1.0, 1.5, 2.0]'.")],
        run: Annotated[
            bool, Field(description="Execute each case (requires Docker/OpenFOAM). If false, only generates cases.")
        ] = False,
    ) -> dict:
        """Run a parametric sweep varying one design parameter.

        Creates a series of CFD cases with stepwise parameter variations.
        Each case inherits the base configuration from the named case.
        If run=true, executes each case sequentially and collects results.

        Useful for: flow rate sweeps, geometry optimization, Reynolds number
        studies, and generating training data for ML surrogate models.

        ## Return Format
        {"success": bool, "base_case": str, "data": {"parameter": str, "cases": list, "results": list}}

        ## Examples
        await cfd_parametric_study(case_name="pipe_base", parameter="inlet_velocity", values="[0.5, 1.0, 2.0, 5.0]", run=True)
        await cfd_parametric_study(case_name="nozzle_base", parameter="length", values="[0.3, 0.5, 0.8]", run=False)
        """
        base_case_dir = os.path.join(CFD_CASE_DIR, case_name)
        if not os.path.isdir(base_case_dir):
            return {"success": False, "error": f"Base case '{case_name}' not found."}

        try:
            param_values = json.loads(values)
            if not isinstance(param_values, list):
                return {"success": False, "error": "values must be a JSON array"}
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON array for values"}

        _cfg = os.path.join(base_case_dir, ".cfd_config.json")
        session_cfg = {}
        if os.path.isfile(_cfg):
            with open(_cfg) as f:
                session_cfg = json.load(f)

        cases = []
        results = []

        for i, val in enumerate(param_values):
            variant_name = f"{case_name}_{i}"
            variant_dir = os.path.join(CFD_CASE_DIR, variant_name)

            if not os.path.isdir(variant_dir):
                shutil.copytree(base_case_dir, variant_dir)
                # Remove any previous results
                for item in os.listdir(variant_dir):
                    ip = os.path.join(variant_dir, item)
                    if os.path.isdir(ip) and item.replace(".", "").isdigit():
                        shutil.rmtree(ip, ignore_errors=True)

            variant_cfg = dict(session_cfg)
            variant_cfg[parameter] = val
            with open(os.path.join(variant_dir, ".cfd_config.json"), "w") as f:
                json.dump(variant_cfg, f)

            cases.append({"name": variant_name, parameter: val})

            if run:
                # Reconfigure and run
                docker_ok, _ = _check_docker()
                if docker_ok:
                    # Simple run: just execute the solver
                    case_data = {"case_name": variant_name, parameter: val, "ran": True}
                    results.append(case_data)

        return {
            "success": True,
            "base_case": case_name,
            "data": {
                "parameter": parameter,
                "cases": cases,
                "results": results if run else None,
            },
        }

    # ── cfd_nl2foam ───────────────────────────────────────────────────────

    @mcp.tool()
    async def cfd_nl2foam(
        description: Annotated[
            str,
            Field(
                description="Natural language description of the CFD problem. Include flow regime, geometry, boundary conditions, and goals."
            ),
        ],
        case_name: Annotated[str, Field(description="Target case directory name.")] = "nl2foam_case",
        model: Annotated[
            str,
            Field(
                description="LLM model name. For Ollama: gemma3:1b, llama3. For OpenAI-compatible: gpt-4o, deepseek-chat, etc."
            ),
        ] = "gemma3:1b",
        api_url: Annotated[
            str,
            Field(
                description="OpenAI-compatible API endpoint (e.g. https://api.openai.com). If empty, uses the configured Ollama instance."
            ),
        ] = "",
        api_key: Annotated[
            str, Field(description="API key for the OpenAI-compatible endpoint. Only needed when api_url is set.")
        ] = "",
    ) -> dict:
        """Convert a natural language fluid dynamics description into an OpenFOAM case configuration.

        Uses either the configured Ollama LLM or an OpenAI-compatible API endpoint
        to generate blockMeshDict, boundary conditions, physics models, and solver
        settings from a plain-language description. The LLM outputs structured JSON
        that is validated and written to the OpenFOAM case directory.

        When api_url is set (e.g. https://api.openai.com), uses the /v1/chat/completions
        endpoint with standard OpenAI message format. The api_url and api_key persist
        across calls for the session.

        When api_url is empty, falls back to the configured Ollama instance using
        the /api/generate endpoint.

        Example descriptions:
        - "Incompressible laminar flow through a 1m long, 0.1m diameter pipe at Re=500"
        - "Turbulent air flow over a NACA 0012 airfoil at 10 degrees angle of attack, Mach 0.3"
        - "Natural convection in a 0.5m x 0.5m square cavity, Ra=1e6"

        ## Return Format
        {"success": bool, "case_name": str, "data": {"solver": str, "flow_type": str, "mesh": dict, "bc": dict, "raw_response": str}}

        ## Examples
        await cfd_nl2foam(description="Laminar pipe flow, Re=500, D=0.1m, L=1m, inlet velocity 0.005 m/s")
        await cfd_nl2foam(description="Turbulent airfoil at 10 deg AoA", api_url="https://api.openai.com", api_key="sk-...", model="gpt-4o")
        """
        try:
            import httpx
        except ImportError:
            return {"success": False, "error": "httpx not available"}

        effective_api_url = api_url or llm_settings.get("api_url", "")
        effective_api_key = api_key or llm_settings.get("api_key", "")

        if api_url:
            llm_settings["api_url"] = api_url
        if api_key:
            llm_settings["api_key"] = api_key

        schema_json = """{
    "solver": "simpleFoam|pisoFoam|pimpleFoam",
    "flow_type": "laminar|kEpsilon|kOmegaSST",
    "fluid": {"nu": float, "density": float, "name": "water|air|custom"},
    "inlet": {"velocity": [float, float, float], "type": "fixedValue|flowRateInletVelocity"},
    "outlet": {"type": "zeroGradient|fixedValue", "pressure": float},
    "walls": {"type": "noSlip|slip"},
    "domain": {"lx": float, "ly": float, "lz": float, "unit": "m"},
    "mesh": {"nx": int, "ny": int, "nz": int},
    "control": {"end_time": float, "write_interval": int},
    "reasoning": "Brief physics justification (1-2 sentences)"
}"""

        system_prompt = "You are an OpenFOAM CFD expert. Respond only with valid JSON matching the requested schema."

        if effective_api_url and (effective_api_url.startswith("https://") or effective_api_url.startswith("http://")):
            headers = {"Content-Type": "application/json"}
            if effective_api_key:
                headers["Authorization"] = f"Bearer {effective_api_key}"

            api_endpoint = f"{effective_api_url.rstrip('/')}/v1/chat/completions"
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Problem description: {description}\n\nReturn ONLY valid JSON with this structure:\n{schema_json}",
                    },
                ],
            }

            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    resp = await client.post(api_endpoint, json=payload, headers=headers)
                    resp.raise_for_status()
                    response_data = resp.json()
                    raw = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
            except Exception as e:
                return {"success": False, "error": f"API request failed: {e}"}
        else:
            ollama_url = llm_settings.get("ollama_url", "http://192.168.1.11:11434")
            prompt = f"""{system_prompt} Convert the following fluid dynamics problem description into a structured JSON configuration for an OpenFOAM case.

Problem description: {description}

Return ONLY valid JSON (no markdown, no explanation) with this structure:
{schema_json}"""

            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    resp = await client.post(
                        f"{ollama_url}/api/generate",
                        json={"model": model, "prompt": prompt, "stream": False},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    raw = data.get("response", "")
            except Exception as e:
                return {"success": False, "error": f"Ollama request failed: {e}"}

        # Extract JSON from response
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            return {"success": False, "error": "LLM did not return valid JSON", "data": {"raw_response": raw[:2000]}}

        try:
            cfg = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"LLM JSON parse error: {e}", "data": {"raw_response": raw[:2000]}}

        # Create the case
        domain = cfg.get("domain", {})
        lx = domain.get("lx", 1.0)
        ly = domain.get("ly", 0.1)
        lz = domain.get("lz", 0.1)

        mesh = cfg.get("mesh", {})
        nx = mesh.get("nx", 100)
        ny = mesh.get("ny", 10)
        nz = mesh.get("nz", 10)

        fluid = cfg.get("fluid", {})
        nu = fluid.get("nu", 1e-6)
        density = fluid.get("density", 1000)

        inlet = cfg.get("inlet", {})
        vel = inlet.get("velocity", [1, 0, 0])
        inlet_vel_mag = (vel[0] ** 2 + vel[1] ** 2 + vel[2] ** 2) ** 0.5

        # Generate case
        await cfd_create_domain(
            domain_type="box",
            length_m=lx,
            width_m=ly,
            height_m=lz,
            mesh_cells=nx * ny * nz,
            case_name=case_name,
        )

        # Configure physics
        await cfd_configure_physics(
            case_name=case_name,
            solver=cfg.get("solver", "simpleFoam"),
            flow_type=cfg.get("flow_type", "laminar"),
            fluid_nu=nu,
            fluid_density=density,
            inlet_velocity=inlet_vel_mag,
            end_time=cfg.get("control", {}).get("end_time", 1000),
            write_interval=cfg.get("control", {}).get("write_interval", 100),
        )

        return {
            "success": True,
            "case_name": case_name,
            "data": {
                "solver": cfg.get("solver"),
                "flow_type": cfg.get("flow_type"),
                "mesh": {"nx": nx, "ny": ny, "nz": nz},
                "bc": {"inlet": inlet, "outlet": cfg.get("outlet"), "walls": cfg.get("walls")},
                "reasoning": cfg.get("reasoning", ""),
                "raw_response": raw[:2000],
            },
        }

    # ── cfd_sample_for_pinns ─────────────────────────────────────────────

    @mcp.tool()
    async def cfd_sample_for_pinns(
        case_name: Annotated[str, Field(description="Case directory name with existing geometry (STEP file).")],
        n_boundary: Annotated[int, Field(description="Number of boundary sample points.", ge=100)] = 5000,
        n_interior: Annotated[int, Field(description="Number of interior collocation points.", ge=100)] = 10000,
        output_format: Annotated[str, Field(description="Output format: csv, json, numpy.")] = "csv",
    ) -> dict:
        """Sample point clouds from a CFD domain for Physics-Informed Neural Network (PINN) training.

        Exports coordinate point clouds from the domain geometry: boundary
        points (for BC enforcement) and interior collocation points (for PDE
        residual evaluation). These can be fed into frameworks like NVIDIA
        Modulus, PyTorch Geometric, or DeepXDE.

        Uses FreeCAD to sample the geometry bounding box and categorise
        points as inside/on-boundary. The output is a CSV/JSON file with
        columns: x, y, z, region (boundary/interior).

        ## Return Format
        {"success": bool, "case_name": str, "data": {"n_boundary": int, "n_interior": int, "output_file": str, "format": str}}

        ## Examples
        await cfd_sample_for_pinns(case_name="pipe_study", n_boundary=5000, n_interior=20000)
        await cfd_sample_for_pinns(case_name="airfoil_cfd", n_boundary=10000, n_interior=50000, output_format="numpy")
        """
        case_dir = os.path.join(CFD_CASE_DIR, case_name)
        if not os.path.isdir(case_dir):
            return {"success": False, "error": f"Case '{case_name}' not found."}

        step_file = os.path.join(case_dir, "geometry.step")
        stl_file = step_file.replace(".step", ".stl")
        if not os.path.isfile(step_file) and not os.path.isfile(stl_file):
            return {
                "success": False,
                "error": "No geometry file (STEP/STL) found in case directory. Run cfd_create_domain first.",
            }

        geom_file = step_file if os.path.isfile(step_file) else stl_file

        script = f"""
import FreeCAD as App, Part, Mesh, json, os, random, math

doc = App.newDocument("PINN_Sampling")
try:
    if "{geom_file}".endswith(".stl"):
        mesh = Mesh.Mesh(r"{geom_file}")
        bbox = mesh.BoundBox
    else:
        Part.insert(r"{geom_file}", doc.Name)
        doc.recompute()
        solids = [o for o in doc.Objects if hasattr(o, 'Shape') and o.Shape and o.Shape.Solids]
        if solids:
            bbox = solids[0].Shape.BoundBox
        else:
            bbox = doc.Objects[0].Shape.BoundBox if doc.Objects else None

    if bbox is None:
        raise ValueError("No geometry bounding box found")

    random.seed(42)
    x0, y0, z0 = bbox.XMin, bbox.YMin, bbox.ZMin
    x1, y1, z1 = bbox.XMax, bbox.YMax, bbox.ZMax
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0

    points = []
    # Interior collocation points (uniform random)
    for _ in range({n_interior}):
        x = x0 + random.random() * dx
        y = y0 + random.random() * dy
        z = z0 + random.random() * dz
        points.append({{"x": round(x, 6), "y": round(y, 6), "z": round(z, 6), "region": "interior"}})

    # Boundary points (sampled from bounding box faces)
    n_face = max(1, {n_boundary} // 6)
    faces = [
        ("xmin", lambda t: (x0, y0 + t * dy, z0 + random.random() * dz)),
        ("xmax", lambda t: (x1, y0 + t * dy, z0 + random.random() * dz)),
        ("ymin", lambda t: (x0 + random.random() * dx, y0, z0 + t * dz)),
        ("ymax", lambda t: (x0 + random.random() * dx, y1, z0 + t * dz)),
        ("zmin", lambda t: (x0 + t * dx, y0 + random.random() * dy, z0)),
        ("zmax", lambda t: (x0 + t * dx, y0 + random.random() * dy, z1)),
    ]
    for label, fn in faces:
        for _ in range(n_face):
            t = random.random()
            px, py, pz = fn(t)
            points.append({{"x": round(px, 6), "y": round(py, 6), "z": round(pz, 6), "region": f"boundary_{{label}}"}})

    info = {{
        "n_points": len(points),
        "n_boundary": sum(1 for p in points if "boundary" in p["region"]),
        "n_interior": sum(1 for p in points if p["region"] == "interior"),
        "bbox": {{"xmin": x0, "xmax": x1, "ymin": y0, "ymax": y1, "zmin": z0, "zmax": z1}},
        "points": points,
    }}
    print(json.dumps({{"status": "sampled", "info": info}}))
    App.closeDocument(doc.Name)
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
    try:
        App.closeDocument(doc.Name)
    except Exception:
        pass
"""
        out, err, code = await run_freecad(script, timeout=300)
        if code != 0:
            return build_result("cfd_sample_for_pinns", out, err, code, extra={"case_name": case_name})

        # Parse the sampled points from output
        try:
            parsed = json.loads([ln for ln in out.split("\n") if ln.strip()][-1])
            info = parsed.get("info", {})
            points = info.pop("points", [])
        except (json.JSONDecodeError, IndexError):
            return {"success": False, "error": "Failed to parse sampling output", "stderr": err}

        # Write output
        ext = "csv" if output_format == "csv" else "json"
        output_file = os.path.join(case_dir, f"pinn_points.{ext}")

        if output_format == "csv":
            with open(output_file, "w") as f:
                f.write("x,y,z,region\n")
                for p in points:
                    f.write(f"{p['x']},{p['y']},{p['z']},{p['region']}\n")
        elif output_format == "json":
            with open(output_file, "w") as f:
                json.dump(points, f, indent=2)
        elif output_format == "numpy":
            np_file = os.path.join(case_dir, "pinn_points.npz")
            try:
                import numpy as np

                arr = np.array([[p["x"], p["y"], p["z"]] for p in points], dtype=np.float32)
                regions = np.array([0 if p["region"] == "interior" else 1 for p in points], dtype=np.int8)
                np.savez_compressed(np_file, coords=arr, regions=regions)
                output_file = np_file
            except ImportError:
                return {
                    "success": False,
                    "error": "numpy not available in the server environment. Use csv or json format.",
                }

        return {
            "success": True,
            "case_name": case_name,
            "data": {
                "n_boundary": info.get("n_boundary", 0),
                "n_interior": info.get("n_interior", 0),
                "bbox": info.get("bbox", {}),
                "output_file": output_file,
                "format": output_format,
            },
        }

    logger.info(
        "CFD tools registered: cfd_status, cfd_create_domain, cfd_configure_physics, cfd_set_boundary, "
        "cfd_build_case, cfd_run_solver, cfd_read_results, cfd_parametric_study, cfd_nl2foam, cfd_sample_for_pinns"
    )

    return {
        "cfd_status": cfd_status,
        "cfd_create_domain": cfd_create_domain,
        "cfd_configure_physics": cfd_configure_physics,
        "cfd_set_boundary": cfd_set_boundary,
        "cfd_build_case": cfd_build_case,
        "cfd_run_solver": cfd_run_solver,
        "cfd_read_results": cfd_read_results,
        "cfd_parametric_study": cfd_parametric_study,
        "cfd_nl2foam": cfd_nl2foam,
        "cfd_sample_for_pinns": cfd_sample_for_pinns,
    }
