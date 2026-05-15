"""
FreeCAD MCP — CAD + BIM operations via FastMCP 3.2 Unified Gateway.

Provides programmatic access to FreeCAD's OCCT CAD kernel for STEP/STL
conversion, model information, basic geometry creation, and BIM/Arch
workbench tools (walls, slabs, columns, windows, doors, roofs, IFC).

Exports:
    freecad_status — server health
    step_to_stl — convert STEP assembly to STL mesh
    model_info — return metadata from CAD files
    create_shape — box, cylinder, sphere, cone → STL
    bim_create_wall — parametric architectural wall
    bim_create_slab — floor slab (structural element)
    bim_create_column — column (rectangular, circular, H-section)
    bim_create_window — window hosted in auto-generated wall
    bim_create_door — door hosted in auto-generated wall
    bim_create_roof — sloped or flat roof
    bim_export_ifc — export FCStd document to IFC format
    bim_import_ifc — import IFC file to FCStd document
    bim_status — BIM/Arch workbench availability check
"""

from __future__ import annotations

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("freecad-mcp")
