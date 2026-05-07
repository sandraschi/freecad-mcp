"""
FreeCAD MCP — CAD operations via FastMCP 3.2 Unified Gateway.

Provides programmatic access to FreeCAD's OCCT CAD kernel for STEP/STL
conversion, model information, and basic geometry creation.

Exports:
    freecad_status — server health
    step_to_stl — convert STEP assembly to STL mesh
    model_info — return metadata from CAD files
    create_shape — box, cylinder, sphere, cone → STL
"""

from __future__ import annotations

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("freecad-mcp")
