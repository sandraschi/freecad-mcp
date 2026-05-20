"""FEM tools for FreeCAD CalculiX — structural analysis via bridge/subprocess.

Provides the complete FEA pipeline: mesh → material → constraints → solve → results.
Includes a convenience run_fem_analysis end-to-end tool.
"""

import json
import logging
import os
from pathlib import Path
from typing import Annotated

from pydantic import Field

logger = logging.getLogger("freecad-mcp.fem")

_README_ONLY = {"readonly": True}

_MATERIAL_PRESETS = {
    "steel": ("Steel", 210000, 0.30),
    "concrete": ("Concrete", 25000, 0.20),
    "aluminum": ("Aluminum", 70000, 0.33),
    "wood": ("Wood", 12000, 0.35),
    "titanium": ("Titanium", 110000, 0.34),
    "stainless": ("Stainless", 193000, 0.29),
    "brass": ("Brass", 100000, 0.35),
    "copper": ("Copper", 117000, 0.36),
    "nylon": ("Nylon", 3000, 0.39),
    "carbon_fiber": ("Carbon Fiber", 150000, 0.30),
}


def register_fem_tools(
    mcp,
    state: dict,
    bridge_send,
    run_freecad,
    work_dir: str,
    output_dir: str,
    upload_dir: str,
    build_result,
):
    """Register all 8 FEM MCP tools on the FastMCP instance."""

    FEM_OUTPUT_DIR = os.path.join(work_dir, "fem_output")
    os.makedirs(FEM_OUTPUT_DIR, exist_ok=True)

    def _find_file(file_name: str) -> str | None:
        """Search for file across upload, output, and fem_output dirs."""
        if not file_name:
            return None
        for base in (FEM_OUTPUT_DIR, upload_dir, output_dir):
            p = os.path.join(base, file_name)
            if os.path.isfile(p):
                return p
        return None

    # ── fem_status ──────────────────────────────────────────────────────

    @mcp.tool(annotations=_README_ONLY)
    async def fem_status() -> dict:
        """Check FEM workbench and CalculiX solver availability.

        ## Return Format
        {"success": bool, "fem_available": bool, "bridge_mode": str, "solver": str}

        ## Examples
        await fem_status()
        """
        return {
            "success": True,
            "fem_available": state.get("bridge_mode") in ("tcp", "subprocess"),
            "bridge_mode": state.get("bridge_mode", "none"),
            "solver": "CalculiX (ccx)",
        }

    # ── fem_create_analysis ─────────────────────────────────────────────

    @mcp.tool()
    async def fem_create_analysis(
        file_name: Annotated[str, Field(description="STEP/FCStd filename in uploads to analyze.")] = "",
        analysis_name: Annotated[str, Field(description="Analysis case name.")] = "StructuralAnalysis",
        output_name: Annotated[str, Field(default="", description="Output FCStd filename.")] = "",
    ) -> dict:
        """Create a structural analysis container on a 3D model.

        Loads a STEP or FCStd file and sets up the FEM analysis framework
        (solver, analysis container). Follow with fem_set_material and
        fem_set_constraint, then fem_mesh and fem_run.

        ## Return Format
        {"success": bool, "output": str, "data": {"analysis_name": str, "objects": [...]}}

        ## Examples
        await fem_create_analysis(file_name="beam.step", analysis_name="BeamStatic")
        """
        input_path = _find_file(file_name)
        if not input_path:
            return {"success": False, "error": f"File not found: {file_name}"}

        out_name = output_name or f"{Path(file_name).stem}_fem.fcstd"
        output_path = os.path.join(FEM_OUTPUT_DIR, out_name)

        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send(
                "fem_create_analysis",
                {
                    "path": input_path,
                    "analysis_name": analysis_name,
                    "output_path": output_path,
                },
                timeout=120,
            )
            if resp.get("success"):
                return {"success": True, "output": out_name, "data": resp.get("data", {})}

        script = f"""import FreeCAD, Fem, json
doc = FreeCAD.openDocument(r"{input_path}")

analysis = Fem.FemAnalysis()
doc.addObject(analysis, "{analysis_name}")

solver = Fem.FemSolverCalculixCxxtools()
doc.addObject(solver)
solver.WorkingDir = r"{FEM_OUTPUT_DIR}"
analysis.addObject(solver)

doc.recompute()
doc.saveAs(r"{output_path}")
doc.recompute()

objects = [{{"name": o.Name, "type": o.TypeId}} for o in doc.Objects]
print(json.dumps({{"analysis_name": "{analysis_name}", "path": r"{output_path}", "objects": objects}}))
FreeCAD.closeDocument(doc.Name)
"""
        out, err, code = await run_freecad(script, timeout=120)
        return build_result("fem_create_analysis", out, err, code, extra={"output": out_name})

    # ── fem_set_material ────────────────────────────────────────────────

    @mcp.tool()
    async def fem_set_material(
        file_name: Annotated[str, Field(description="FCStd filename from fem_create_analysis.")] = "",
        material: Annotated[
            str,
            Field(
                description="Material: steel, concrete, aluminum, wood, titanium, stainless, brass, copper, nylon, carbon_fiber."
            ),
        ] = "steel",
        E_mpa: Annotated[
            float, Field(description="Override elastic modulus in MPa. 0 = use material preset.", ge=0)
        ] = 0,
        nu: Annotated[float, Field(description="Override Poisson ratio. 0 = use material preset.", ge=0, le=0.5)] = 0,
        density_kgm3: Annotated[
            float, Field(description="Override density kg/m³. 0 = auto from material, 7800 for steel.", ge=0)
        ] = 0,
        yield_mpa: Annotated[
            float, Field(description="Override yield strength MPa. 0 = auto from material, 250 for steel.", ge=0)
        ] = 0,
    ) -> dict:
        """Assign material properties to the FEM analysis.

        Built-in presets include 10 common engineering materials.
        The material object is linked to the analysis container automatically.

        ## Return Format
        {"success": bool, "output": str, "data": {"material": str, "E_MPa": float, "nu": float, "density_kgm3": float, "yield_MPa": float}}

        ## Examples
        await fem_set_material(file_name="beam_fem.fcstd", material="steel")
        await fem_set_material(file_name="beam_fem.fcstd", material="aluminum", E_mpa=69000)
        """
        mat_name, preset_E, preset_nu = _MATERIAL_PRESETS.get(material, _MATERIAL_PRESETS["steel"])
        E_val = E_mpa if E_mpa > 0 else preset_E
        nu_val = nu if nu > 0 else preset_nu

        # Density and yield strength defaults per material
        density_defaults = {
            "steel": 7800,
            "concrete": 2400,
            "aluminum": 2700,
            "wood": 600,
            "titanium": 4420,
            "stainless": 8000,
            "brass": 8500,
            "copper": 8960,
            "nylon": 1150,
            "carbon_fiber": 1600,
        }
        yield_defaults = {
            "steel": 250,
            "concrete": 30,
            "aluminum": 240,
            "wood": 40,
            "titanium": 880,
            "stainless": 275,
            "brass": 200,
            "copper": 210,
            "nylon": 75,
            "carbon_fiber": 800,
        }
        density = density_kgm3 if density_kgm3 > 0 else density_defaults.get(material, 7800)
        yield_mpa_val = yield_mpa if yield_mpa > 0 else yield_defaults.get(material, 250)

        input_path = _find_file(file_name)
        if file_name and not input_path:
            return {"success": False, "error": f"File not found: {file_name}"}

        out_name = file_name or "fem_material.fcstd"
        output_path = os.path.join(FEM_OUTPUT_DIR, out_name)

        script = f"""import FreeCAD, Fem, json, os
path = r"{input_path}" if "{input_path}" and os.path.isfile(r"{input_path}") else None
if path:
    doc = FreeCAD.openDocument(path)
else:
    doc = FreeCAD.ActiveDocument
    if not doc:
        doc = FreeCAD.newDocument("FEM_Material")

mat = Fem.MaterialSolid()
mat.Material = {{
    "Name": "{mat_name}",
    "YoungsModulus": "{E_val} MPa",
    "PoissonRatio": "{nu_val}",
    "Density": "{density} kg/m^3",
}}
doc.addObject(mat, "Material_{material}_{E_val}MPa")

# Link to analysis container
for obj in doc.Objects:
    if obj.TypeId == "Fem::FemAnalysis":
        obj.addObject(mat)
        break

doc.recompute()
doc.saveAs(r"{output_path}")
doc.recompute()
print(json.dumps({{"material": "{mat_name}", "E_MPa": {E_val}, "nu": {nu_val}, "density_kgm3": {density}, "yield_MPa": {yield_mpa_val}}}))
FreeCAD.closeDocument(doc.Name)
"""
        out, err, code = await run_freecad(script, timeout=60)
        return build_result("fem_set_material", out, err, code, extra={"output": out_name})

    # ── fem_set_constraint ──────────────────────────────────────────────

    @mcp.tool()
    async def fem_set_constraint(
        file_name: Annotated[str, Field(description="FCStd filename to add constraints to.")] = "",
        constraints: Annotated[
            list[dict] | None,
            Field(
                description="""List of constraints. Each dict:
- type: 'fixed' (clamped face), 'force' (N on face), 'pressure' (MPa on face)
- face_name: FreeCAD face name (e.g. 'Face1') or 'auto' for auto-detection
- For force: fx, fy, fz in N (default 0,0,1000)
- For pressure: value in MPa
"""
            ),
        ] = None,
    ) -> dict:
        """Apply boundary conditions to a FEM analysis.

        Supports fixed supports (clamped), force loads, and pressure loads
        on named faces of the 3D model. Constraints are automatically linked
        to the analysis container.

        ## Return Format
        {"success": bool, "data": {"constraints_applied": int}}

        ## Examples
        await fem_set_constraint(file_name="beam_fem.fcstd", constraints=[
            {"type": "fixed", "face_name": "Face1"},
            {"type": "force", "face_name": "Face6", "fy": -5000},
        ])
        """
        input_path = _find_file(file_name)
        if file_name and not input_path:
            return {"success": False, "error": f"File not found: {file_name}"}

        const_json = json.dumps(constraints)
        script = f"""import FreeCAD, Fem, json, os
path = r"{input_path}" if "{input_path}" and os.path.isfile(r"{input_path}") else None
if path:
    doc = FreeCAD.openDocument(path)
else:
    doc = FreeCAD.ActiveDocument
    if not doc: raise RuntimeError("No document")

# Find analysis container
analysis = None
for obj in doc.Objects:
    if obj.TypeId == "Fem::FemAnalysis":
        analysis = obj
        break

constraints = json.loads('{const_json}')
count = 0
for c in constraints:
    ctype = c.get("type", "fixed")
    face = c.get("face_name", "auto")
    if ctype == "fixed":
        fix = Fem.ConstraintFixed()
        doc.addObject(fix, f"Fixed_{{count}}")
        if analysis: analysis.addObject(fix)
        if face != "auto":
            for obj in doc.Objects:
                if hasattr(obj, 'Shape') and obj.Shape.Faces:
                    for f_idx, _f in enumerate(obj.Shape.Faces):
                        if f"Face{{f_idx + 1}}" == face:
                            fix.References = [(obj, f"Face{{f_idx + 1}}")]
    elif ctype == "force":
        fc = Fem.ConstraintForce()
        fc.Force = FreeCAD.Vector(
            c.get("fx", 0), c.get("fy", 0), c.get("fz", 0)
        )
        doc.addObject(fc, f"Force_{{count}}")
        if analysis: analysis.addObject(fc)
        if face != "auto":
            for obj in doc.Objects:
                if hasattr(obj, 'Shape') and obj.Shape.Faces:
                    for f_idx, _f in enumerate(obj.Shape.Faces):
                        if f"Face{{f_idx + 1}}" == face:
                            fc.References = [(obj, f"Face{{f_idx + 1}}")]
    elif ctype == "pressure":
        pr = Fem.ConstraintPressure()
        pr.Pressure = c.get("value", 1.0)
        doc.addObject(pr, f"Pressure_{{count}}")
        if analysis: analysis.addObject(pr)
        if face != "auto":
            for obj in doc.Objects:
                if hasattr(obj, 'Shape') and obj.Shape.Faces:
                    for f_idx, _f in enumerate(obj.Shape.Faces):
                        if f"Face{{f_idx + 1}}" == face:
                            pr.References = [(obj, f"Face{{f_idx + 1}}")]
    count += 1

doc.recompute()
doc.saveAs(r"{input_path}")
doc.recompute()
print(json.dumps({{"constraints_applied": count}}))
FreeCAD.closeDocument(doc.Name)
"""
        out, err, code = await run_freecad(script, timeout=120)
        return build_result("fem_set_constraint", out, err, code)

    # ── fem_mesh ────────────────────────────────────────────────────────

    @mcp.tool()
    async def fem_mesh(
        file_name: Annotated[str, Field(description="FCStd filename to mesh.")] = "",
        max_size_mm: Annotated[float, Field(description="Maximum element size in mm.", ge=1)] = 50.0,
        min_size_mm: Annotated[float, Field(description="Minimum element size in mm. 0 = auto (max/10).", ge=0)] = 0,
        second_order: Annotated[
            bool, Field(description="Use second-order tetrahedra (tetra10) for bending accuracy.")
        ] = True,
    ) -> dict:
        """Generate a finite element mesh using Gmsh (FemMeshGmsh).

        Meshes the 3D solid and links to the analysis container. Smaller
        element size gives finer mesh and more accurate results but longer
        solve time. Second-order elements (tetra10) strongly recommended
        for bending-dominated problems.

        ## Return Format
        {"success": bool, "data": {"nodes": int, "elements": int, "element_size_mm": float, "element_order": int}}

        ## Examples
        await fem_mesh(file_name="beam_fem.fcstd", max_size_mm=10, second_order=True)
        await fem_mesh(file_name="beam_fem.fcstd", max_size_mm=50, min_size_mm=5)
        """
        input_path = _find_file(file_name)
        if file_name and not input_path:
            return {"success": False, "error": f"File not found: {file_name}"}

        min_str = f"{min_size_mm}" if min_size_mm > 0 else f"{max_size_mm / 10.0}"
        order = 2 if second_order else 1

        script = f"""import FreeCAD, Fem, json, os, importFem
path = r"{input_path}" if "{input_path}" and os.path.isfile(r"{input_path}") else None
if path:
    doc = FreeCAD.openDocument(path)
else:
    doc = FreeCAD.ActiveDocument
    if not doc: raise RuntimeError("No document")

# Find analysis container
analysis = None
for obj in doc.Objects:
    if obj.TypeId == "Fem::FemAnalysis":
        analysis = obj
        break

if not analysis:
    print(json.dumps({{"error": "No FemAnalysis found. Run fem_create_analysis first."}}))
else:
    # Use Gmsh mesher for better quality
    mesh = doc.addObject("Fem::FemMeshGmsh", "FEMMeshGmsh")
    mesh.MaxSize = {max_size_mm}
    mesh.MinSize = {min_str}
    mesh.SecondOrderLinear = {str(second_order).lower()}
    mesh.ElementOrder = "{order}nd" if {order} == 2 else "1st"

    # Assign mesh to first solid body
    for obj in doc.Objects:
        if hasattr(obj, 'Shape') and obj.Shape.Solids:
            mesh.References = [(obj, "Solid1")]
            break

    analysis.addObject(mesh)

    doc.recompute()
    doc.saveAs(r"{input_path}")
    doc.recompute()

    try:
        fem_mesh_obj = mesh.FemMesh
        print(json.dumps({{"nodes": fem_mesh_obj.Nodes.Count, "elements": fem_mesh_obj.Volumes.Count,
            "element_size_mm": {max_size_mm}, "element_order": {order}}}))
    except Exception as e:
        print(json.dumps({{"nodes": 0, "elements": 0, "element_size_mm": {max_size_mm},
            "element_order": {order}, "warning": str(e)}}))
FreeCAD.closeDocument(doc.Name)
"""
        out, err, code = await run_freecad(script, timeout=180)
        return build_result("fem_mesh", out, err, code)

    # ── fem_run ─────────────────────────────────────────────────────────

    @mcp.tool()
    async def fem_run(
        file_name: Annotated[str, Field(description="FCStd filename with mesh and constraints.")] = "",
        timeout_s: Annotated[int, Field(description="Solver timeout in seconds.", ge=30, le=3600)] = 300,
    ) -> dict:
        """Run the CalculiX FEM solver on a prepared analysis.

        Requires fem_create_analysis, fem_set_material, fem_set_constraint,
        and fem_mesh to have been called. Generates .inp, runs ccx, and
        collects .frd/.dat result files.

        ## Return Format
        {"success": bool, "data": {"solver": str, "exit_code": int, "result_files": [...], "working_dir": str}}

        ## Examples
        await fem_run(file_name="beam_fem.fcstd")
        await fem_run(file_name="large_model.fcstd", timeout_s=600)
        """
        input_path = _find_file(file_name)
        if file_name and not input_path:
            return {"success": False, "error": f"File not found: {file_name}"}

        script = f"""import FreeCAD, Fem, json, os
path = r"{input_path}" if "{input_path}" and os.path.isfile(r"{input_path}") else None
if path:
    doc = FreeCAD.openDocument(path)
else:
    doc = FreeCAD.ActiveDocument
    if not doc: raise RuntimeError("No document")

from femtools import ccxtools
fea = ccxtools.FemToolsCcx()
fea.setup_working_dir(r"{FEM_OUTPUT_DIR}")
fea.update_objects()

try:
    fea.write_inp_file()
    fea.ccx_run()
    exit_code = 0
    error_msg = ""
except Exception as e:
    exit_code = 1
    error_msg = str(e)

# Collect results
results = []
for root, dirs, files in os.walk(r"{FEM_OUTPUT_DIR}"):
    for f in files:
        if f.endswith(('.frd', '.dat', '.inp')):
            results.append(f)

print(json.dumps({{
    "solver": "CalculiX ccx",
    "exit_code": exit_code,
    "error": error_msg,
    "result_files": results,
    "working_dir": r"{FEM_OUTPUT_DIR}",
}}))
FreeCAD.closeDocument(doc.Name)
"""
        out, err, code = await run_freecad(script, timeout=timeout_s)
        return build_result("fem_run", out, err, code)

    # ── fem_read_results ────────────────────────────────────────────────

    @mcp.tool(annotations=_README_ONLY)
    async def fem_read_results(
        file_name: Annotated[str, Field(description="FCStd filename that was solved.")] = "",
    ) -> dict:
        """Read FEM results from a solved analysis.

        Parses CalculiX .frd and .dat result files to extract:
        - Max von Mises stress (MPa)
        - Max displacement magnitude (mm)
        - Min/max principal stresses
        - Node count and available result components

        ## Return Format
        {"success": bool, "data": {"max_von_mises_MPa": float, "max_displacement_mm": float, "max_principal_MPa": float, "min_principal_MPa": float, "nodes": int, "components": [...]}}

        ## Examples
        await fem_read_results(file_name="beam_fem.fcstd")
        """
        script = f"""import os, json, re

fem_dir = r"{FEM_OUTPUT_DIR}"
results = {{
    "max_von_mises_MPa": 0.0,
    "max_displacement_mm": 0.0,
    "max_principal_MPa": 0.0,
    "min_principal_MPa": 0.0,
    "nodes": 0,
    "components": [],
    "result_files": [],
}}

# Look for .frd files first (most complete)
frd_files = []
for root, dirs, files in os.walk(fem_dir):
    for f in files:
        if f.endswith('.frd'):
            frd_files.append(os.path.join(root, f))
        elif f.endswith('.dat'):
            results["result_files"].append(f)

if frd_files:
    frd_path = max(frd_files, key=os.path.getsize)

    try:
        with open(frd_path, 'r') as frd:
            lines = frd.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Node count: line starts with "    2" (single step FRD) or "    3" (multi step)
            if line.startswith("    2") or line.startswith("    3"):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        nodes = int(parts[1])
                        if nodes > results["nodes"]:
                            results["nodes"] = nodes
                    except ValueError:
                        pass
                i += 1
                continue

            # Component labels: lines starting with -1 with STRESS or DISP
            if line.startswith("   -1") or line.startswith("  -1"):
                # The next lines may contain component names
                j = i + 1
                while j < len(lines) and len(lines[j].strip()) == 0:
                    j += 1
                if j < len(lines):
                    label_line = lines[j].strip()
                    if label_line and not label_line[0].isdigit():
                        results["components"].append(label_line)
                i = j + 1
                continue

            # Data lines: -1 terminated chunks with numeric values
            i += 1

        results["result_files"].append(os.path.basename(frd_path))

        # Parse displacement and stress values with a structured approach
        with open(frd_path, 'r') as frd:
            content = frd.read()

        # Extract DISP node blocks — format: node# dx dy dz
        disp_matches = list(re.finditer(
            r'^\\s*-1\\s*\\n\\s*DISP.*?\\n(.*?)(?=\\s*-1\\s*$|\\Z)',
            content, re.MULTILINE | re.DOTALL
        ))
        for m in disp_matches:
            block = m.group(1)
            for val in re.findall(r'[\\d.Ee+-]+', block):
                try:
                    d = abs(float(val))
                    if d > results["max_displacement_mm"]:
                        results["max_displacement_mm"] = d
                except ValueError:
                    pass

        # Extract STRESS node blocks — each node has 6 components (Sxx, Syy, Szz, Sxy, Sxz, Syz)
        stress_matches = list(re.finditer(
            r'^\\s*-1\\s*\\n\\s*STRESS.*?\\n(.*?)(?=\\s*-1\\s*$|\\Z)',
            content, re.MULTILINE | re.DOTALL
        ))
        for m in stress_matches:
            block = m.group(1)
            vals = [float(v) for v in re.findall(r'[\\d.Ee+-]+', block)]
            # Values come in groups of 6 stress components per node
            for k in range(0, len(vals) - 5, 6):
                try:
                    sx, sy, sz, sxy, sxz, syz = vals[k:k+6]
                    # von Mises stress
                    von_mises = ((0.5 * (
                        (sx - sy)**2 + (sy - sz)**2 + (sz - sx)**2 +
                        6 * (sxy**2 + sxz**2 + syz**2)
                    )) ** 0.5)
                    if von_mises > results["max_von_mises_MPa"]:
                        results["max_von_mises_MPa"] = von_mises
                    # Principal stresses
                    mx = max(sx, sy, sz)
                    mn = min(sx, sy, sz)
                    if mx > results["max_principal_MPa"]:
                        results["max_principal_MPa"] = mx
                    if mn < results["min_principal_MPa"]:
                        results["min_principal_MPa"] = mn
                except (IndexError, ValueError):
                    pass

    except Exception as e:
        results["parse_error"] = str(e)

# Round for readability
for key in ("max_von_mises_MPa", "max_displacement_mm", "max_principal_MPa", "min_principal_MPa"):
    results[key] = round(results[key], 4)

print(json.dumps(results))
"""
        out, err, code = await run_freecad(script, timeout=60)
        return build_result("fem_read_results", out, err, code)

    # ── run_fem_analysis ────────────────────────────────────────────────

    @mcp.tool()
    async def run_fem_analysis(
        file_name: Annotated[
            str, Field(description="STEP/STP/FCStd file to analyze. Must be in uploads or outputs directory.")
        ],
        material: Annotated[
            str,
            Field(
                description="Material: steel, concrete, aluminum, wood, titanium, stainless, brass, copper, nylon, carbon_fiber."
            ),
        ] = "steel",
        constraints: Annotated[
            list[dict],
            Field(
                description="""Boundary conditions. Each dict:
- type: 'fixed' (clamped face) | 'force' (N on face) | 'pressure' (MPa on face)
- face_name: FreeCAD face name (e.g. 'Face1') or 'auto' for auto-detect
- For force: fx, fy, fz in N (e.g. {"fx": 0, "fy": -1000, "fz": 0})
- For pressure: value in MPa (e.g. {"value": 5.0})
Example: [{"type": "fixed", "face_name": "Face1"}, {"type": "force", "face_name": "Face6", "fy": -5000}]
"""
            ),
        ] = [{"type": "fixed", "face_name": "Face1"}],
        mesh_size_mm: Annotated[float, Field(description="Maximum mesh element size in mm.", ge=1, le=500)] = 20.0,
        mesh_min_mm: Annotated[float, Field(description="Minimum element size mm. 0 = auto (mesh_size/10).", ge=0)] = 0,
        second_order: Annotated[bool, Field(description="Second-order tetrahedra for bending accuracy.")] = True,
        analysis_name: Annotated[str, Field(description="Analysis case name.")] = "FEM_Analysis",
        E_mpa: Annotated[float, Field(description="Override elastic modulus MPa. 0 = use material preset.", ge=0)] = 0,
        nu: Annotated[float, Field(description="Override Poisson ratio.", ge=0, le=0.5)] = 0,
        force_N: Annotated[
            float, Field(description="Shorthand: apply force in -Y on last face. 0 = use constraints list.", ge=0)
        ] = 0,
    ) -> dict:
        """Run a complete structural FEM analysis end-to-end.

        Convenience tool that chains the full pipeline: create analysis →
        set material → apply constraints → generate mesh → solve → read results.

        For a simple cantilever beam analysis, just specify the file,
        material, and constrain one face with a force on the opposite face.
        The tool returns max von Mises stress, max displacement, and yield
        check against the material's yield strength.

        ## Return Format
        {"success": bool, "data": {"max_von_mises_MPa": float, "max_displacement_mm": float, "yield_MPa": float, "safety_factor": float, "material": str, "mesh_nodes": int, "mesh_elements": int, "solver": str}}

        ## Examples
        await run_fem_analysis(file_name="beam.step", material="steel", constraints=[
            {"type": "fixed", "face_name": "Face1"},
            {"type": "force", "face_name": "Face6", "fy": -5000},
        ], mesh_size_mm=10)

        await run_fem_analysis(file_name="bracket.step", material="aluminum", force_N=2000)
        """
        # --- Validate input ---
        input_path = _find_file(file_name)
        if not input_path:
            return {"success": False, "error": f"File not found: {file_name}"}

        # --- Build constraints if force_N shorthand used ---
        if force_N > 0 and not constraints:
            constraints = [
                {"type": "fixed", "face_name": "Face1"},
                {"type": "force", "face_name": "Face6", "fy": -force_N},
            ]

        if not constraints:
            constraints = [{"type": "fixed", "face_name": "Face1"}]

        out_name = f"{Path(file_name).stem}_fem.fcstd"

        # --- Step 1: Create analysis ---
        result1 = await fem_create_analysis(
            file_name=file_name,
            analysis_name=analysis_name,
            output_name=out_name,
        )
        if not result1.get("success"):
            return {
                "success": False,
                "error": f"fem_create_analysis failed: {result1.get('error', 'unknown')}",
                "step": "create_analysis",
            }

        # --- Step 2: Set material ---
        result2 = await fem_set_material(
            file_name=out_name,
            material=material,
            E_mpa=E_mpa,
            nu=nu,
        )
        mat_data = result2.get("data", {})
        yield_mpa = mat_data.get("yield_MPa", 250)

        # --- Step 3: Apply constraints ---
        await fem_set_constraint(
            file_name=out_name,
            constraints=constraints,
        )

        # --- Step 4: Generate mesh ---
        result4 = await fem_mesh(
            file_name=out_name,
            max_size_mm=mesh_size_mm,
            min_size_mm=mesh_min_mm,
            second_order=second_order,
        )
        mesh_data = result4.get("data", {})

        # --- Step 5: Run solver ---
        result5 = await fem_run(file_name=out_name)
        if not result5.get("success"):
            return {"success": False, "error": f"fem_run failed: {result5.get('error', 'unknown')}", "step": "solve"}

        # --- Step 6: Read results ---
        result6 = await fem_read_results(file_name=out_name)
        results_data = result6.get("data", {})

        max_vm = results_data.get("max_von_mises_MPa", 0)
        max_disp = results_data.get("max_displacement_mm", 0)
        safety = round(yield_mpa / max_vm, 2) if max_vm > 0 else float("inf")

        return {
            "success": True,
            "message": (
                f"FEM complete. Max von Mises stress: {max_vm:.2f} MPa "
                f"(yield: {yield_mpa:.0f} MPa, safety factor: {safety}). "
                f"Max displacement: {max_disp:.4f} mm. "
                f"Mesh: {mesh_data.get('nodes', 0)} nodes, {mesh_data.get('elements', 0)} elements."
            ),
            "data": {
                "max_von_mises_MPa": max_vm,
                "max_displacement_mm": max_disp,
                "yield_MPa": yield_mpa,
                "safety_factor": safety,
                "material": mat_data.get("material", material),
                "mesh_nodes": mesh_data.get("nodes", 0),
                "mesh_elements": mesh_data.get("elements", 0),
                "solver": "CalculiX ccx",
                "output_file": out_name,
            },
        }

    logger.info(
        "FEM tools registered: fem_status, fem_create_analysis, fem_set_material, "
        "fem_set_constraint, fem_mesh, fem_run, fem_read_results, run_fem_analysis"
    )

    return {
        "fem_status": fem_status,
        "fem_create_analysis": fem_create_analysis,
        "fem_set_material": fem_set_material,
        "fem_set_constraint": fem_set_constraint,
        "fem_mesh": fem_mesh,
        "fem_run": fem_run,
        "fem_read_results": fem_read_results,
        "run_fem_analysis": run_fem_analysis,
    }
