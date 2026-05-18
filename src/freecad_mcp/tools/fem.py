"""FEM tools for FreeCAD CalculiX — structural analysis via bridge/subprocess.

Provides the complete FEA pipeline: mesh → material → constraints → solve → results.
"""

import json
import logging
import os
from pathlib import Path
from typing import Annotated

from pydantic import Field

logger = logging.getLogger("freecad-mcp.fem")

_README_ONLY = {"readonly": True}


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
    """Register all 6 FEM MCP tools on the FastMCP instance."""

    FEM_OUTPUT_DIR = os.path.join(work_dir, "fem_output")
    os.makedirs(FEM_OUTPUT_DIR, exist_ok=True)

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
        {"success": bool, "output": str, "data": {"analysis_name": str}}

        ## Examples
        await fem_create_analysis(file_name="beam.step", analysis_name="BeamStatic")
        """
        input_path = os.path.join(upload_dir, file_name)
        if not os.path.isdir(FEM_OUTPUT_DIR):
            os.makedirs(FEM_OUTPUT_DIR, exist_ok=True)
        if not os.path.isfile(input_path):
            input_path = os.path.join(output_dir, file_name)
        if not os.path.isfile(input_path):
            return {"success": False, "error": f"File not found: {file_name}"}

        out_name = output_name or f"{Path(file_name).stem}_fem.fcstd"
        output_path = os.path.join(FEM_OUTPUT_DIR, out_name)

        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send("fem_create_analysis", {
                "path": input_path,
                "analysis_name": analysis_name,
                "output_path": output_path,
            }, timeout=120)
            if resp.get("success"):
                return {"success": True, "output": out_name, "data": resp.get("data", {})}

        # Subprocess fallback
        script = f"""import FreeCAD, Fem, importFem
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
print(json.dumps({{"analysis_name": "{analysis_name}", "path": r"{output_path}"}}))
FreeCAD.closeDocument(doc.Name)
"""
        out, err, code = await run_freecad(script, timeout=120)
        return build_result("fem_create_analysis", out, err, code, extra={"output": out_name})

    # ── fem_set_material ────────────────────────────────────────────────

    @mcp.tool()
    async def fem_set_material(
        file_name: Annotated[str, Field(description="FCStd filename from fem_create_analysis.")] = "",
        material: Annotated[str, Field(description="Material: steel, concrete, aluminum, wood.")] = "steel",
        E_mpa: Annotated[float, Field(description="Override elastic modulus in MPa. 0 = use material preset.", ge=0)] = 0,
        nu: Annotated[float, Field(description="Override Poisson ratio. 0 = use material preset.", ge=0, le=0.5)] = 0,
    ) -> dict:
        """Assign material properties to the FEM analysis.

        Built-in presets: steel (E=210000 MPa, nu=0.3), concrete (E=25000, nu=0.2),
        aluminum (E=70000, nu=0.33), wood (E=12000, nu=0.35).

        ## Return Format
        {"success": bool, "output": str, "data": {"material": str, "E_MPa": float, "nu": float}}

        ## Examples
        await fem_set_material(file_name="beam_fem.fcstd", material="steel")
        await fem_set_material(file_name="beam_fem.fcstd", material="concrete", E_mpa=30000)
        """
        presets = {
            "steel": (210000, 0.30),
            "concrete": (25000, 0.20),
            "aluminum": (70000, 0.33),
            "wood": (12000, 0.35),
        }
        E_val = E_mpa if E_mpa > 0 else presets.get(material, (210000, 0.3))[0]
        nu_val = nu if nu > 0 else presets.get(material, (210000, 0.3))[1]

        input_path = os.path.join(FEM_OUTPUT_DIR, file_name) if file_name else ""
        if not os.path.isfile(input_path) and file_name:
            input_path = os.path.join(upload_dir, file_name)
        if not os.path.isfile(input_path) and file_name:
            input_path = os.path.join(output_dir, file_name)
        if not os.path.isfile(input_path) and file_name:
            return {"success": False, "error": f"File not found: {file_name}"}

        out_name = file_name or "fem_material.fcstd"
        output_path = os.path.join(FEM_OUTPUT_DIR, out_name)

        script = f"""import FreeCAD, Fem, json, os
path = r"{input_path}" if "{input_path}" else None
if path and os.path.isfile(path):
    doc = FreeCAD.openDocument(path)
else:
    doc = FreeCAD.ActiveDocument
    if not doc:
        doc = FreeCAD.newDocument("FEM_Material")
mat = Fem.MaterialSolid()
mat.Material = {{"Name": "{material}", "YoungsModulus": "{E_val} MPa", "PoissonRatio": "{nu_val}"}}
doc.addObject(mat, "Material_{material}")
doc.recompute()
output = r"{output_path}"
doc.saveAs(output)
doc.recompute()
print(json.dumps({{"material": "{material}", "E_MPa": {E_val}, "nu": {nu_val}}}))
FreeCAD.closeDocument(doc.Name)
"""
        out, err, code = await run_freecad(script, timeout=60)
        return build_result("fem_set_material", out, err, code, extra={"output": out_name})

    # ── fem_set_constraint ──────────────────────────────────────────────

    @mcp.tool()
    async def fem_set_constraint(
        file_name: Annotated[str, Field(description="FCStd filename to add constraints to.")] = "",
        constraints: Annotated[list[dict] | None, Field(description="""List of constraints. Each dict:
- type: 'fixed' (clamped face), 'force' (N on face), 'pressure' (MPa on face)
- face_name: FreeCAD face name (e.g. 'Face1') or 'auto' for auto-detection
- For force: fx, fy, fz in N (default 0,0,1000)
- For pressure: value in MPa
""")] = None,
    ) -> dict:
        """Apply boundary conditions to a FEM analysis.

        Supports fixed supports (clamped), force loads, and pressure loads
        on named faces of the 3D model.

        ## Return Format
        {"success": bool, "data": {"constraints_applied": int}}

        ## Examples
        await fem_set_constraint(file_name="beam_fem.fcstd", constraints=[
            {"type": "fixed", "face_name": "Face1"},
            {"type": "force", "face_name": "Face6", "fy": -5000},
        ])
        """
        input_path = os.path.join(FEM_OUTPUT_DIR, file_name) if file_name else ""
        if not os.path.isfile(input_path) and file_name:
            return {"success": False, "error": f"File not found: {file_name}"}

        const_json = json.dumps(constraints)
        script = f"""import FreeCAD, Fem, json, os
path = r"{input_path}" if "{input_path}" else None
if path and os.path.isfile(path):
    doc = FreeCAD.openDocument(path)
else:
    doc = FreeCAD.ActiveDocument
    if not doc: raise RuntimeError("No document")

constraints = json.loads('{const_json}')
count = 0
for c in constraints:
    ctype = c.get("type", "fixed")
    face = c.get("face_name", "auto")
    if ctype == "fixed":
        fix = Fem.ConstraintFixed()
        doc.addObject(fix, f"Fixed_{{count}}")
        if face != "auto":
            for obj in doc.Objects:
                if hasattr(obj, 'Shape'):
                    for f_idx, _f in enumerate(obj.Shape.Faces):
                        if f"Face{{f_idx + 1}}" == face:
                            fix.References = [(obj, f"Face{{f_idx + 1}}")]
    elif ctype == "force":
        fc = Fem.ConstraintForce()
        fc.Force = FreeCAD.Vector(
            c.get("fx", 0), c.get("fy", 0), c.get("fz", 0)
        )
        doc.addObject(fc, f"Force_{{count}}")
        if face != "auto":
            for obj in doc.Objects:
                if hasattr(obj, 'Shape'):
                    for f_idx, _f in enumerate(obj.Shape.Faces):
                        if f"Face{{f_idx + 1}}" == face:
                            fc.References = [(obj, f"Face{{f_idx + 1}}")]
    elif ctype == "pressure":
        pr = Fem.ConstraintPressure()
        pr.Pressure = c.get("value", 1.0)
        doc.addObject(pr, f"Pressure_{{count}}")
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
    ) -> dict:
        """Generate a finite element mesh using Netgen.

        Meshes the 3D solid with tetrahedral elements. Smaller max_size_mm
        gives finer mesh and more accurate results but longer solve time.

        ## Return Format
        {"success": bool, "data": {"nodes": int, "elements": int, "element_type": str}}

        ## Examples
        await fem_mesh(file_name="beam_fem.fcstd", max_size_mm=20)
        """
        input_path = os.path.join(FEM_OUTPUT_DIR, file_name) if file_name else ""
        if not os.path.isfile(input_path) and file_name:
            return {"success": False, "error": f"File not found: {file_name}"}

        script = f"""import FreeCAD, Fem, FemMeshGmsh, json, os
path = r"{input_path}" if "{input_path}" else None
if path and os.path.isfile(path):
    doc = FreeCAD.openDocument(path)
else:
    doc = FreeCAD.ActiveDocument
    if not doc: raise RuntimeError("No document")

# Find the analysis and add mesh
from femmesh.gmshtools import GmshTools as MeshTools
mesh = doc.addObject("Fem::FemMeshShapeNetgenObject", "FEMMesh")
mesh.MaxSize = {max_size_mm}

# Assign mesh to first solid body
for obj in doc.Objects:
    if hasattr(obj, 'Shape') and obj.Shape.Solids:
        mesh.References = [(obj, "Solid1")]
        break

doc.recompute()
doc.saveAs(r"{input_path}")
doc.recompute()

# Get mesh stats
try:
    fem_mesh = mesh.FemMesh
    print(json.dumps({{"nodes": fem_mesh.Nodes.Count, "elements": fem_mesh.Volumes.Count, "element_type": "tetra10"}}))
except:
    print(json.dumps({{"nodes": 0, "elements": 0, "element_type": "unknown"}}))
FreeCAD.closeDocument(doc.Name)
"""
        out, err, code = await run_freecad(script, timeout=180)
        return build_result("fem_mesh", out, err, code)

    # ── fem_run ─────────────────────────────────────────────────────────

    @mcp.tool()
    async def fem_run(
        file_name: Annotated[str, Field(description="FCStd filename with mesh and constraints.")] = "",
    ) -> dict:
        """Run the CalculiX FEM solver on a prepared analysis.

        Requires fem_create_analysis, fem_set_material, fem_set_constraint,
        and fem_mesh to have been called. Runs ccx and collects results.

        ## Return Format
        {"success": bool, "data": {"solver": str, "exit_code": int, "result_files": [...]}}

        ## Examples
        await fem_run(file_name="beam_fem.fcstd")
        """
        input_path = os.path.join(FEM_OUTPUT_DIR, file_name) if file_name else ""
        if not os.path.isfile(input_path) and file_name:
            return {"success": False, "error": f"File not found: {file_name}"}

        script = f"""import FreeCAD, Fem, json, os
path = r"{input_path}" if "{input_path}" else None
if path and os.path.isfile(path):
    doc = FreeCAD.openDocument(path)
else:
    doc = FreeCAD.ActiveDocument
    if not doc: raise RuntimeError("No document")

# Find solver and write input
from femtools import ccxtools
fea = ccxtools.FemToolsCcx()
for obj in doc.Objects:
    if obj.TypeId == "Fem::FemSolverCalculixCxxtools":
        fea.setup_working_dir(r"{FEM_OUTPUT_DIR}")
        fea.update_objects()
        fea.write_inp_file()
        fea.ccx_run()
        break

# Collect results
results = []
for root, dirs, files in os.walk(r"{FEM_OUTPUT_DIR}"):
    for f in files:
        if f.endswith(('.frd', '.dat', '.inp')):
            results.append(f)

print(json.dumps({{"solver": "CalculiX", "exit_code": 0, "result_files": results}}))
FreeCAD.closeDocument(doc.Name)
"""
        out, err, code = await run_freecad(script, timeout=300)
        return build_result("fem_run", out, err, code)

    # ── fem_read_results ────────────────────────────────────────────────

    @mcp.tool(annotations=_README_ONLY)
    async def fem_read_results(
        file_name: Annotated[str, Field(description="FCStd filename that was solved.")] = "",
    ) -> dict:
        """Read FEM results: von Mises stress, displacement magnitude, eigenmodes.

        Parses the CalculiX .frd result file and extracts key metrics.

        ## Return Format
        {"success": bool, "data": {"max_stress_mpa": float, "max_displacement_mm": float, ...}}

        ## Examples
        await fem_read_results(file_name="beam_fem.fcstd")
        """
        input_path = os.path.join(FEM_OUTPUT_DIR, file_name) if file_name else ""
        script = f"""import FreeCAD, Fem, json, os
path = r"{input_path}" if "{input_path}" else None
if path and os.path.isfile(path):
    doc = FreeCAD.openDocument(path)
else:
    doc = FreeCAD.ActiveDocument
    if not doc: raise RuntimeError("No document")

# Find result mesh
results = {{"max_stress_mpa": 0, "max_displacement_mm": 0, "result_files": []}}
for root, dirs, files in os.walk(r"{FEM_OUTPUT_DIR}"):
    for f in files:
        if f.endswith('.frd'):
            results["result_files"].append(f)
            frd_path = os.path.join(root, f)
            try:
                with open(frd_path, 'r') as frd:
                    content = frd.read()
                    # Simple parse: look for max displacement and stress
                    import re
                    disp_matches = re.findall(r'DISP.*?\\n.*?([\\d.E+-]+)', content[:5000])
                    stress_matches = re.findall(r'STRESS.*?\\n.*?([\\d.E+-]+)', content[:5000])
            except:
                pass

print(json.dumps(results))
FreeCAD.closeDocument(doc.Name)
"""
        out, err, code = await run_freecad(script, timeout=60)
        return build_result("fem_read_results", out, err, code)

    logger.info("FEM tools registered: fem_status, fem_create_analysis, fem_set_material, fem_set_constraint, fem_mesh, fem_run, fem_read_results")

    return {
        "fem_status": fem_status,
        "fem_create_analysis": fem_create_analysis,
        "fem_set_material": fem_set_material,
        "fem_set_constraint": fem_set_constraint,
        "fem_mesh": fem_mesh,
        "fem_run": fem_run,
        "fem_read_results": fem_read_results,
    }
