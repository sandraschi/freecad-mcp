"""CAD file depot tools - persistent file management for the FreeCAD MCP server."""

import json
import logging
import os
from datetime import datetime
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

logger = logging.getLogger("freecad-mcp")

_EXT_CAD = {".step", ".stp", ".stl", ".ifc", ".ifcxml", ".fcstd", ".iges", ".igs", ".obj", ".dxf", ".dwg"}


def register_depot_tools(
    mcp: FastMCP,
    state: dict,
    depot_dir: str,
    create_shape_func,
):
    """Register depot CRUD tools. Returns dict mapping tool_name -> callable."""

    def _meta_path(filename: str) -> str:
        return os.path.join(depot_dir, f"{filename}.meta.json")

    def _read_meta(filename: str) -> dict:
        mp = _meta_path(filename)
        if os.path.isfile(mp):
            try:
                with open(mp) as f:
                    return json.load(f)
            except Exception:
                logger.debug("Failed to read meta for %s", filename, exc_info=True)
        return {}

    def _write_meta(filename: str, meta: dict):
        with open(_meta_path(filename), "w") as f:
            json.dump(meta, f, indent=2, default=str)

    def _ensure_meta(filename: str):
        meta = _read_meta(filename)
        changed = False
        if "created" not in meta:
            meta["created"] = datetime.now().isoformat()
            changed = True
        if "description" not in meta:
            meta["description"] = ""
            changed = True
        if "tags" not in meta:
            meta["tags"] = []
            changed = True
        if changed:
            _write_meta(filename, meta)
        return meta

    def _depot_list() -> list[dict]:
        files = {}
        for f in os.listdir(depot_dir):
            fp = os.path.join(depot_dir, f)
            if not os.path.isfile(fp):
                continue
            _base, ext = os.path.splitext(f)
            if ext == ".meta.json":
                continue
            if ext.lower() not in _EXT_CAD:
                continue
            meta = _ensure_meta(f)
            files[f] = {
                "name": f,
                "size_bytes": os.path.getsize(fp),
                "size_kb": round(os.path.getsize(fp) / 1024, 1),
                "modified": datetime.fromtimestamp(os.path.getmtime(fp)).isoformat(),
                "meta": meta,
            }
        return sorted(files.values(), key=lambda x: x["modified"], reverse=True)

    @mcp.tool(annotations={"readonly": True})
    async def cad_depot() -> dict:
        """
        List all CAD files in the persistent file depot with metadata.

        The depot stores STEP, STL, IFC, FCStd, IGES, OBJ, and DXF files.
        Includes file size, creation date, description, and tags.

        ## Return Format
        {"success": bool, "data": {"files": [{"name": ..., "size_kb": ..., "modified": ..., "meta": {...}}]}}

        ## Examples
        await cad_depot()
        """
        return {"success": True, "data": {"files": _depot_list()}}

    @mcp.tool()
    async def cad_create(
        shape_type: Annotated[str, Field(description="Shape type: box, cylinder, sphere, cone.")] = "box",
        params: Annotated[
            dict | None,
            Field(
                default=None,
                description="Shape parameters: width/height/depth for box, radius/height for cylinder/sphere/cone.",
            ),
        ] = None,
        output_name: Annotated[
            str, Field(default="", description="Output STL filename. Auto-generated if empty.")
        ] = "",
        description: Annotated[
            str, Field(default="", description="Optional description stored in depot metadata.")
        ] = "",
    ) -> dict:
        """
        Create a CAD shape (box, cylinder, sphere, cone) and save the result STL to the depot.

        Delegates to FreeCAD's OCCT kernel via create_shape. The resulting STL
        is stored in the persistent depot directory with file metadata.

        ## Return Format
        {"success": bool, "filename": str, "data": {"size_kb": float}}

        ## Examples
        await cad_create(shape_type="box", params={"width": 50, "height": 30, "depth": 20})
        await cad_create(shape_type="cylinder", params={"radius": 10, "height": 40})
        await cad_create(shape_type="sphere", params={"radius": 25}, description="Test sphere")
        """
        out_name = output_name or f"{shape_type}_{int(datetime.now().timestamp())}.stl"
        # Delegate to create_shape - it saves to OUTPUT_DIR, we copy to depot
        result = await create_shape_func(
            shape_type=shape_type,
            params=params or {},
            output_name=out_name,
        )
        if not result.get("success"):
            return result

        # Copy output STL to depot
        output_path = result.get("output", out_name)
        src = os.path.join(state.get("output_dir", ""), output_path)
        dst = os.path.join(depot_dir, output_path)
        if os.path.isfile(src):
            import shutil

            shutil.copy2(src, dst)

        meta = {
            "created": datetime.now().isoformat(),
            "description": description,
            "tags": ["created"],
            "shape_type": shape_type,
        }
        _write_meta(output_path, meta)
        sz_kb = round(os.path.getsize(dst) / 1024, 1) if os.path.isfile(dst) else 0

        return {
            "success": True,
            "filename": output_path,
            "data": {"size_kb": sz_kb, "shape_type": shape_type, **result.get("data", {})},
        }

    return {"cad_depot": cad_depot, "cad_create": cad_create}
