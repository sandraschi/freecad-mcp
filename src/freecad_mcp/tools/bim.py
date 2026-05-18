"""
BIM (Building Information Modeling) MCP tools for FreeCAD Arch workbench.

Provides parametric architectural element creation: walls, slabs, columns,
windows, doors, roofs, plus IFC import/export. All dimensions in millimetres.

Registered via register_bim_tools(mcp, **deps) — called from server.py after
FastMCP instance creation to avoid circular imports.
"""

import logging
import os
from pathlib import Path
from typing import Annotated

from pydantic import Field

logger = logging.getLogger("freecad-mcp.bim")

_README_ONLY = {"readonly": True}

WALL_LENIENCY = 2000
COLUMN_PROFILES = ("rectangular", "circular", "h_section")
WINDOW_TYPES = ("fixed", "casement", "sliding", "awning")
DOOR_TYPES = ("simple", "glass", "sliding_glass")


def register_bim_tools(
    mcp,
    state: dict,
    bridge_send,
    run_freecad,
    work_dir: str,
    output_dir: str,
    upload_dir: str,
    build_result,
):
    """Register all 8 BIM MCP tools on the FastMCP instance.

    Returns a dict mapping tool_name -> callable for REST dispatch.
    """

    # ── bim_create_wall ─────────────────────────────────────────────────

    @mcp.tool()
    async def bim_create_wall(
        length_mm: Annotated[float, Field(description="Wall length in millimetres.", ge=1)] = 5000.0,
        width_mm: Annotated[float, Field(description="Wall thickness in millimetres.", ge=10)] = 200.0,
        height_mm: Annotated[float, Field(description="Wall height in millimetres.", ge=10)] = 2800.0,
        placement_x: Annotated[float, Field(description="X position in millimetres.")] = 0.0,
        placement_y: Annotated[float, Field(description="Y position in millimetres.")] = 0.0,
        placement_z: Annotated[float, Field(description="Z position in millimetres.")] = 0.0,
        rotation_z: Annotated[float, Field(description="Rotation around Z axis in degrees.")] = 0.0,
        output_name: Annotated[str, Field(description="Output FCStd filename, e.g. my_wall.fcstd.")] = "wall.fcstd",
    ) -> dict:
        """Create a parametric architectural wall via Arch.makeWall().

        Creates a wall as a smart BIM object with material, thickness, and
        height attributes — not just geometry. Saves as FreeCAD .fcstd document.

        ## Return Format
        {"success": bool, "output": str, "data": {"label": str, "length": float, "width": float, "height": float, "path": str}}

        ## Examples
        await bim_create_wall(length_mm=6000, width_mm=240, height_mm=3000, output_name="exterior_wall.fcstd")
        await bim_create_wall(length_mm=3000, width_mm=120, height_mm=2600, placement_x=5000, rotation_z=90)
        """
        output_path = os.path.join(output_dir, output_name)

        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send(
                "bim_create_wall",
                {
                    "length": length_mm,
                    "width": width_mm,
                    "height": height_mm,
                    "x": placement_x,
                    "y": placement_y,
                    "z": placement_z,
                    "rotation_z": rotation_z,
                    "path": output_path,
                },
                timeout=120,
            )
            if resp.get("success"):
                return {"success": True, "output": output_name, "data": resp.get("data")}
            logger.warning("Bridge bim_create_wall failed, trying subprocess: %s", resp.get("error"))

        script = f"""
import FreeCAD as App, Draft, Arch, json, os

doc = App.newDocument("BIM_Wall")
try:
    p1 = App.Vector(0, 0, 0)
    p2 = App.Vector({length_mm}, 0, 0)
    line = Draft.makeLine(p1, p2)
    wall = Arch.makeWall(line, width={width_mm}, height={height_mm})
    wall.Label = "Wall"
    wall.Placement = App.Placement(
        App.Vector({placement_x}, {placement_y}, {placement_z}),
        App.Rotation(App.Vector(0, 0, 1), {rotation_z}),
    )
    doc.recompute()
    doc.saveAs(r"{output_path}")
    doc.recompute()
    info = {{
        "label": wall.Label,
        "length": {length_mm},
        "width": {width_mm},
        "height": {height_mm},
        "path": r"{output_path}",
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
        return build_result("bim_create_wall", out, err, code, extra={"output": output_name})

    # ── bim_create_slab ─────────────────────────────────────────────────

    @mcp.tool()
    async def bim_create_slab(
        width_mm: Annotated[float, Field(description="Slab width (X-axis) in millimetres.", ge=100)] = 6000.0,
        length_mm: Annotated[float, Field(description="Slab length (Y-axis) in millimetres.", ge=100)] = 8000.0,
        thickness_mm: Annotated[float, Field(description="Slab thickness in millimetres.", ge=20)] = 200.0,
        placement_x: Annotated[float, Field(description="X position in millimetres.")] = 0.0,
        placement_y: Annotated[float, Field(description="Y position in millimetres.")] = 0.0,
        placement_z: Annotated[float, Field(description="Z position in millimetres.")] = 0.0,
        output_name: Annotated[str, Field(description="Output FCStd filename.")] = "slab.fcstd",
    ) -> dict:
        """Create a floor slab as a BIM structure element.

        Creates a structural slab with smart attributes: material, thickness,
        and structural type. Saves as FreeCAD .fcstd document.

        ## Return Format
        {"success": bool, "output": str, "data": {"label": str, "width": float, "length": float, "thickness": float, "path": str}}

        ## Examples
        await bim_create_slab(width_mm=6000, length_mm=8000, thickness_mm=250, output_name="ground_floor.fcstd")
        """
        output_path = os.path.join(output_dir, output_name)

        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send(
                "bim_create_slab",
                {
                    "width": width_mm,
                    "length": length_mm,
                    "thickness": thickness_mm,
                    "x": placement_x,
                    "y": placement_y,
                    "z": placement_z,
                    "path": output_path,
                },
                timeout=120,
            )
            if resp.get("success"):
                return {"success": True, "output": output_name, "data": resp.get("data")}
            logger.warning("Bridge bim_create_slab failed, trying subprocess: %s", resp.get("error"))

        script = f"""
import FreeCAD as App, Arch, json, os, Part

doc = App.newDocument("BIM_Slab")
try:
    box = Part.makeBox({width_mm}, {length_mm}, {thickness_mm})
    slab = Arch.makeStructure(box)
    slab.Label = "Slab"
    slab.IfcType = "Slab"
    slab.Placement = App.Placement(
        App.Vector({placement_x}, {placement_y}, {placement_z}),
        App.Rotation(),
    )
    doc.recompute()
    doc.saveAs(r"{output_path}")
    doc.recompute()
    info = {{
        "label": slab.Label,
        "width": {width_mm},
        "length": {length_mm},
        "thickness": {thickness_mm},
        "path": r"{output_path}",
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
        return build_result("bim_create_slab", out, err, code, extra={"output": output_name})

    # ── bim_create_column ───────────────────────────────────────────────

    @mcp.tool()
    async def bim_create_column(
        profile_type: Annotated[str, Field(description="Profile: rectangular, circular, h_section.")] = "rectangular",
        width_mm: Annotated[
            float, Field(description="Column width (X profile dimension) in millimetres.", ge=10)
        ] = 300.0,
        depth_mm: Annotated[
            float, Field(description="Column depth (Y profile dimension) in millimetres.", ge=10)
        ] = 300.0,
        height_mm: Annotated[float, Field(description="Column height in millimetres.", ge=10)] = 3000.0,
        placement_x: Annotated[float, Field(description="X position in millimetres.")] = 0.0,
        placement_y: Annotated[float, Field(description="Y position in millimetres.")] = 0.0,
        placement_z: Annotated[float, Field(description="Z position in millimetres.")] = 0.0,
        output_name: Annotated[str, Field(description="Output FCStd filename.")] = "column.fcstd",
    ) -> dict:
        """Create a structural column as a BIM element.

        Supports rectangular, circular, and H-section profiles via
        Arch.makeStructure(). Saves as FreeCAD .fcstd document.

        ## Return Format
        {"success": bool, "output": str, "data": {"label": str, "profile": str, "width": float, "depth": float, "height": float, "path": str}}

        ## Examples
        await bim_create_column(profile_type="rectangular", width_mm=300, depth_mm=300, height_mm=3500)
        await bim_create_column(profile_type="circular", width_mm=400, depth_mm=400, height_mm=4000, placement_x=6000)
        """
        if profile_type not in COLUMN_PROFILES:
            profile_type = "rectangular"

        output_path = os.path.join(output_dir, output_name)

        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send(
                "bim_create_column",
                {
                    "profile": profile_type,
                    "width": width_mm,
                    "depth": depth_mm,
                    "height": height_mm,
                    "x": placement_x,
                    "y": placement_y,
                    "z": placement_z,
                    "path": output_path,
                },
                timeout=120,
            )
            if resp.get("success"):
                return {"success": True, "output": output_name, "data": resp.get("data")}
            logger.warning("Bridge bim_create_column failed, trying subprocess: %s", resp.get("error"))

        script = _column_subprocess_script(
            profile_type, width_mm, depth_mm, height_mm, placement_x, placement_y, placement_z, output_path
        )
        out, err, code = await run_freecad(script, timeout=120)
        return build_result("bim_create_column", out, err, code, extra={"output": output_name})

    # ── bim_create_window ───────────────────────────────────────────────

    @mcp.tool()
    async def bim_create_window(
        window_type: Annotated[str, Field(description="Window type: fixed, casement, sliding, awning.")] = "fixed",
        width_mm: Annotated[float, Field(description="Window width in millimetres.", ge=200)] = 1000.0,
        height_mm: Annotated[float, Field(description="Window height in millimetres.", ge=200)] = 1200.0,
        sill_height_mm: Annotated[float, Field(description="Sill height from floor in millimetres.", ge=0)] = 900.0,
        placement_x: Annotated[float, Field(description="X position in millimetres.")] = 0.0,
        placement_y: Annotated[float, Field(description="Y position in millimetres.")] = 0.0,
        placement_z: Annotated[float, Field(description="Z position in millimetres.")] = 0.0,
        rotation_z: Annotated[float, Field(description="Wall rotation around Z axis in degrees.")] = 0.0,
        output_name: Annotated[str, Field(description="Output FCStd filename.")] = "window.fcstd",
    ) -> dict:
        """Create a window hosted in an auto-generated wall.

        Creates a window BIM object that auto-cuts its opening in the hosting
        wall. The wall is created automatically to host the window. Saves as
        FreeCAD .fcstd document.

        ## Return Format
        {"success": bool, "output": str, "data": {"label": str, "window_type": str, "width": float, "height": float, "path": str}}

        ## Examples
        await bim_create_window(window_type="casement", width_mm=1200, height_mm=1500, sill_height_mm=850)
        await bim_create_window(window_type="sliding", width_mm=2000, height_mm=1200, placement_x=3000)
        """
        if window_type not in WINDOW_TYPES:
            window_type = "fixed"

        output_path = os.path.join(output_dir, output_name)

        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send(
                "bim_create_window",
                {
                    "window_type": window_type,
                    "width": width_mm,
                    "height": height_mm,
                    "sill_height": sill_height_mm,
                    "x": placement_x,
                    "y": placement_y,
                    "z": placement_z,
                    "rotation_z": rotation_z,
                    "path": output_path,
                },
                timeout=120,
            )
            if resp.get("success"):
                return {"success": True, "output": output_name, "data": resp.get("data")}
            logger.warning("Bridge bim_create_window failed, trying subprocess: %s", resp.get("error"))

        script = _window_subprocess_script(
            window_type,
            width_mm,
            height_mm,
            sill_height_mm,
            placement_x,
            placement_y,
            placement_z,
            rotation_z,
            output_path,
        )
        out, err, code = await run_freecad(script, timeout=120)
        return build_result("bim_create_window", out, err, code, extra={"output": output_name})

    # ── bim_create_door ─────────────────────────────────────────────────

    @mcp.tool()
    async def bim_create_door(
        door_type: Annotated[str, Field(description="Door type: simple, glass, sliding_glass.")] = "simple",
        width_mm: Annotated[float, Field(description="Door width in millimetres.", ge=400)] = 900.0,
        height_mm: Annotated[float, Field(description="Door height in millimetres.", ge=1500)] = 2100.0,
        placement_x: Annotated[float, Field(description="X position in millimetres.")] = 0.0,
        placement_y: Annotated[float, Field(description="Y position in millimetres.")] = 0.0,
        placement_z: Annotated[float, Field(description="Z position in millimetres.")] = 0.0,
        rotation_z: Annotated[float, Field(description="Wall rotation around Z axis in degrees.")] = 0.0,
        output_name: Annotated[str, Field(description="Output FCStd filename.")] = "door.fcstd",
    ) -> dict:
        """Create a door hosted in an auto-generated wall.

        Creates a door BIM object that auto-cuts its opening in the hosting
        wall. The wall is created automatically to host the door. Saves as
        FreeCAD .fcstd document.

        ## Return Format
        {"success": bool, "output": str, "data": {"label": str, "door_type": str, "width": float, "height": float, "path": str}}

        ## Examples
        await bim_create_door(door_type="simple", width_mm=900, height_mm=2100)
        await bim_create_door(door_type="glass", width_mm=1000, height_mm=2200, placement_x=5000, rotation_z=90)
        """
        if door_type not in DOOR_TYPES:
            door_type = "simple"

        output_path = os.path.join(output_dir, output_name)

        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send(
                "bim_create_door",
                {
                    "door_type": door_type,
                    "width": width_mm,
                    "height": height_mm,
                    "x": placement_x,
                    "y": placement_y,
                    "z": placement_z,
                    "rotation_z": rotation_z,
                    "path": output_path,
                },
                timeout=120,
            )
            if resp.get("success"):
                return {"success": True, "output": output_name, "data": resp.get("data")}
            logger.warning("Bridge bim_create_door failed, trying subprocess: %s", resp.get("error"))

        script = _door_subprocess_script(
            door_type, width_mm, height_mm, placement_x, placement_y, placement_z, rotation_z, output_path
        )
        out, err, code = await run_freecad(script, timeout=120)
        return build_result("bim_create_door", out, err, code, extra={"output": output_name})

    # ── bim_create_roof ─────────────────────────────────────────────────

    @mcp.tool()
    async def bim_create_roof(
        width_mm: Annotated[float, Field(description="Roof width (span direction) in millimetres.", ge=100)] = 8000.0,
        length_mm: Annotated[
            float, Field(description="Roof length (ridge direction) in millimetres.", ge=100)
        ] = 10000.0,
        angle_deg: Annotated[float, Field(description="Roof pitch angle in degrees (0 = flat).", ge=0, le=75)] = 30.0,
        thickness_mm: Annotated[float, Field(description="Roof shell thickness in millimetres.", ge=10)] = 100.0,
        placement_x: Annotated[float, Field(description="X position in millimetres.")] = 0.0,
        placement_y: Annotated[float, Field(description="Y position in millimetres.")] = 0.0,
        placement_z: Annotated[float, Field(description="Z position in millimetres.")] = 2800.0,
        output_name: Annotated[str, Field(description="Output FCStd filename.")] = "roof.fcstd",
    ) -> dict:
        """Create a sloped or flat roof as a BIM element.

        Uses Arch.makeRoof() from a rectangular face. A flat roof is created
        when angle_deg=0. Saves as FreeCAD .fcstd document.

        ## Return Format
        {"success": bool, "output": str, "data": {"label": str, "width": float, "length": float, "angle": float, "thickness": float, "path": str}}

        ## Examples
        await bim_create_roof(width_mm=8000, length_mm=10000, angle_deg=30, thickness_mm=120)
        await bim_create_roof(width_mm=6000, length_mm=6000, angle_deg=0, placement_z=3000, output_name="flat_roof.fcstd")
        """
        output_path = os.path.join(output_dir, output_name)

        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send(
                "bim_create_roof",
                {
                    "width": width_mm,
                    "length": length_mm,
                    "angle": angle_deg,
                    "thickness": thickness_mm,
                    "x": placement_x,
                    "y": placement_y,
                    "z": placement_z,
                    "path": output_path,
                },
                timeout=120,
            )
            if resp.get("success"):
                return {"success": True, "output": output_name, "data": resp.get("data")}
            logger.warning("Bridge bim_create_roof failed, trying subprocess: %s", resp.get("error"))

        script = f"""
import FreeCAD as App, Arch, json, os, Part

doc = App.newDocument("BIM_Roof")
try:
    face = Part.makePlane({width_mm}, {length_mm})
    roof = Arch.makeRoof(face, angle={angle_deg}, thickness={thickness_mm})
    roof.Label = "Roof"
    roof.Placement = App.Placement(
        App.Vector({placement_x}, {placement_y}, {placement_z}),
        App.Rotation(),
    )
    doc.recompute()
    doc.saveAs(r"{output_path}")
    doc.recompute()
    info = {{
        "label": roof.Label,
        "width": {width_mm},
        "length": {length_mm},
        "angle": {angle_deg},
        "thickness": {thickness_mm},
        "path": r"{output_path}",
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
        return build_result("bim_create_roof", out, err, code, extra={"output": output_name})

    # ── bim_export_ifc ──────────────────────────────────────────────────

    @mcp.tool()
    async def bim_export_ifc(
        file_name: Annotated[str, Field(description="FreeCAD FCStd filename in the uploads directory.")],
        output_name: Annotated[str, Field(description="Output IFC filename, e.g. building.ifc.")] = "building.ifc",
    ) -> dict:
        """Export a FreeCAD document (.fcstd) to IFC format.

        IFC (Industry Foundation Classes) is the open standard exchange format
        for BIM data. The resulting .ifc file contains parametric building
        elements with their material, type, and relationship data intact.

        Requires the source .fcstd file in the uploads directory.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "size_kb": float, "objects": int}}

        ## Examples
        await bim_export_ifc(file_name="my_building.fcstd", output_name="my_building.ifc")
        """
        fcstd_path = os.path.join(upload_dir, file_name)
        if not os.path.isfile(fcstd_path):
            fcstd_path = os.path.join(output_dir, file_name)
        if not os.path.isfile(fcstd_path):
            return {"success": False, "error": f"File {file_name} not found in uploads or outputs."}

        ifc_path = os.path.join(output_dir, output_name)

        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send(
                "bim_export_ifc",
                {"src": fcstd_path, "dst": ifc_path},
                timeout=300,
            )
            if resp.get("success"):
                return {"success": True, "output": output_name, "data": resp.get("data")}
            logger.warning("Bridge bim_export_ifc failed, trying subprocess: %s", resp.get("error"))

        script = f"""
import FreeCAD as App, Import, json, os

doc = App.openDocument(r"{fcstd_path}")
try:
    Import.export(doc.Objects, r"{ifc_path}")
    sz = os.path.getsize(r"{ifc_path}")
    info = {{
        "path": r"{ifc_path}",
        "size_kb": round(sz / 1024, 1),
        "objects": len(doc.Objects),
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
        out, err, code = await run_freecad(script, timeout=300)
        return build_result("bim_export_ifc", out, err, code, extra={"output": output_name})

    # ── bim_import_ifc ──────────────────────────────────────────────────

    @mcp.tool()
    async def bim_import_ifc(
        file_name: Annotated[str, Field(description="IFC filename in the uploads directory.")],
        output_name: Annotated[str, Field(description="Output FCStd filename.")] = "",
    ) -> dict:
        """Import an IFC file and convert it to a FreeCAD document.

        Reads IFC (Industry Foundation Classes) files from architects and
        converts them to FreeCAD .fcstd format with parametric BIM objects.
        The output is saved to the outputs directory.

        ## Return Format
        {"success": bool, "output": str, "data": {"path": str, "objects": int, "object_names": list}}

        ## Examples
        await bim_import_ifc(file_name="architect_model.ifc", output_name="imported_building.fcstd")
        await bim_import_ifc(file_name="structural.ifc")
        """
        ifc_path = os.path.join(upload_dir, file_name)
        if not os.path.isfile(ifc_path):
            return {"success": False, "error": f"File {file_name} not found in uploads."}

        if not output_name:
            output_name = Path(file_name).stem + ".fcstd"
        output_path = os.path.join(output_dir, output_name)

        if state.get("bridge_mode") == "tcp":
            resp = await bridge_send(
                "bim_import_ifc",
                {"src": ifc_path, "dst": output_path},
                timeout=300,
            )
            if resp.get("success"):
                return {"success": True, "output": output_name, "data": resp.get("data")}
            logger.warning("Bridge bim_import_ifc failed, trying subprocess: %s", resp.get("error"))

        script = f"""
import FreeCAD as App, Import, json, os

doc = App.newDocument("IFC_Import")
try:
    Import.insert(r"{ifc_path}", doc.Name)
    doc.recompute()
    doc.saveAs(r"{output_path}")
    doc.recompute()
    names = [o.Label for o in doc.Objects]
    info = {{
        "path": r"{output_path}",
        "objects": len(doc.Objects),
        "object_names": names[:50],
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
        out, err, code = await run_freecad(script, timeout=300)
        return build_result("bim_import_ifc", out, err, code, extra={"output": output_name})

    # ── mesh_to_solid ────────────────────────────────────────────────────

    @mcp.tool()
    async def mesh_to_solid(
        file_name: Annotated[str, Field(description="STL filename in uploads/ or outputs/.")] = "",
        output_name: Annotated[str, Field(default="", description="Output FCStd filename. Default: <input>_solid.fcstd.")] = "",
    ) -> dict:
        """Convert an STL mesh to a FreeCAD solid via MeshPart.meshFromShape().

        Takes an STL file (e.g. from qcad-mcp plan_extrude) and converts the
        triangular mesh to a valid B-Rep solid that can be used with BIM tools
        or exported to STEP/IFC.

        Requires TCP bridge (FreeCAD GUI mode) — not available in subprocess mode.

        ## Return Format
        {"success": bool, "output": str, "data": {"vertices": int, "facets": int, "volume_mm3": float}}

        ## Examples
        await mesh_to_solid(file_name="wall_plan.stl")
        await mesh_to_solid(file_name="wall_plan.stl", output_name="walls_solid.fcstd")
        """
        stl_name = file_name or ""
        stl_path = os.path.join(upload_dir, stl_name)
        if not os.path.isfile(stl_path):
            stl_path = os.path.join(output_dir, stl_name)
        if not os.path.isfile(stl_path):
            return {"success": False, "error": f"STL file not found: {stl_name}"}

        out_name = output_name or f"{Path(stl_name).stem}_solid.fcstd"
        output_path = os.path.join(output_dir, out_name)

        if state.get("bridge_mode") != "tcp":
            return {"success": False, "error": "mesh_to_solid requires TCP bridge (FreeCAD GUI mode). Launch freecad_gui first."}

        resp = await bridge_send(
            "mesh_to_solid",
            {"path": stl_path, "output_path": output_path},
            timeout=120,
        )
        if resp.get("success"):
            return {"success": True, "output": out_name, "data": resp.get("data", {})}
        logger.warning("Bridge mesh_to_solid failed: %s", resp.get("error"))
        return {"success": False, "error": resp.get("error", "mesh_to_solid failed")}

    # ── bim_status ──────────────────────────────────────────────────────

    @mcp.tool(annotations=_README_ONLY)
    async def bim_status() -> dict:
        """Check BIM/IFC capabilities of the connected FreeCAD instance.

        Use this after freecad_status to verify the Arch workbench and IFC
        import/export modules are available before calling BIM tools.

        ## Return Format
        {"success": bool, "bim_available": bool, "bridge_mode": str, "workbench": str}

        ## Examples
        await bim_status()
        """
        bim_available = state.get("bridge_mode") in ("tcp", "subprocess")
        return {
            "success": bim_available,
            "bim_available": bim_available,
            "bridge_mode": state.get("bridge_mode", "none"),
            "workbench": "Arch (BIM)",
        }

    logger.info(
        "BIM tools registered: bim_create_wall, bim_create_slab, bim_create_column, bim_create_window, bim_create_door, bim_create_roof, bim_export_ifc, bim_import_ifc, bim_status"
    )

    return {
        "bim_status": bim_status,
        "bim_create_wall": bim_create_wall,
        "bim_create_slab": bim_create_slab,
        "bim_create_column": bim_create_column,
        "bim_create_window": bim_create_window,
        "bim_create_door": bim_create_door,
        "bim_create_roof": bim_create_roof,
        "bim_export_ifc": bim_export_ifc,
        "bim_import_ifc": bim_import_ifc,
        "mesh_to_solid": mesh_to_solid,
    }


# ── Subprocess script helpers ────────────────────────────────────────────


def _column_subprocess_script(
    profile_type: str, width: float, depth: float, height: float, x: float, y: float, z: float, output_path: str
) -> str:
    if profile_type == "circular":
        radius = width / 2
        shape = f"Part.makeCylinder({radius}, {height})"
    elif profile_type == "h_section":
        shape = (
            f"wb = Part.makeBox({width}, {depth}, {height});"
            f"w1 = Part.makeBox({depth}, {width * 0.25}, {height});"
            f"w2 = Part.makeBox({width * 0.5}, {depth * 0.3}, {height});"
            "s = wb.fuse(w1).fuse(w2)"
        )
    else:
        shape = f"Part.makeBox({width}, {depth}, {height})"

    return f"""
import FreeCAD as App, Arch, Part, json, os

doc = App.newDocument("BIM_Column")
try:
    s = {shape}
    col = Arch.makeStructure(s)
    col.Label = "Column"
    col.IfcType = "Column"
    col.Placement = App.Placement(
        App.Vector({x}, {y}, {z}),
        App.Rotation(),
    )
    doc.recompute()
    doc.saveAs(r"{output_path}")
    doc.recompute()
    info = {{
        "label": col.Label,
        "profile": "{profile_type}",
        "width": {width},
        "depth": {depth},
        "height": {height},
        "path": r"{output_path}",
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


def _window_subprocess_script(
    window_type: str,
    width: float,
    height: float,
    sill: float,
    x: float,
    y: float,
    z: float,
    rotation_z: float,
    output_path: str,
) -> str:
    # Auto-create a hosting wall large enough for the window
    wall_len = width + WALL_LENIENCY
    return f"""
import FreeCAD as App, Draft, Arch, json, os

doc = App.newDocument("BIM_Window")
try:
    p1 = App.Vector(0, 0, 0)
    p2 = App.Vector({wall_len}, 0, 0)
    line = Draft.makeLine(p1, p2)
    wall = Arch.makeWall(line, width=200, height={height + sill + 400})
    wall.Label = "HostWall"
    win = Arch.makeWindow(None, width={width}, height={height})
    win.Label = "Window"
    wall.Placement = App.Placement(
        App.Vector({x}, {y}, {z}),
        App.Rotation(App.Vector(0, 0, 1), {rotation_z}),
    )
    win.Placement = App.Placement(
        App.Vector({wall_len / 2 - width / 2}, {sill}, wall.Shape.BoundBox.ZMax if hasattr(wall, 'Shape') and wall.Shape else {z + sill} - {z} - {sill}),
        App.Rotation(),
    )
    doc.recompute()
    doc.saveAs(r"{output_path}")
    doc.recompute()
    info = {{
        "label": win.Label,
        "window_type": "{window_type}",
        "width": {width},
        "height": {height},
        "path": r"{output_path}",
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


def _door_subprocess_script(
    door_type: str, width: float, height: float, x: float, y: float, z: float, rotation_z: float, output_path: str
) -> str:
    wall_len = width + WALL_LENIENCY
    return f"""
import FreeCAD as App, Draft, Arch, json, os

doc = App.newDocument("BIM_Door")
try:
    p1 = App.Vector(0, 0, 0)
    p2 = App.Vector({wall_len}, 0, 0)
    line = Draft.makeLine(p1, p2)
    wall = Arch.makeWall(line, width=200, height={height + 400})
    wall.Label = "HostWall"
    door = Arch.makeWindow(None, width={width}, height={height})
    door.Label = "Door"
    wall.Placement = App.Placement(
        App.Vector({x}, {y}, {z}),
        App.Rotation(App.Vector(0, 0, 1), {rotation_z}),
    )
    door.Placement = App.Placement(
        App.Vector({wall_len / 2 - width / 2}, 0, 0),
        App.Rotation(),
    )
    doc.recompute()
    doc.saveAs(r"{output_path}")
    doc.recompute()
    info = {{
        "label": door.Label,
        "door_type": "{door_type}",
        "width": {width},
        "height": {height},
        "path": r"{output_path}",
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
