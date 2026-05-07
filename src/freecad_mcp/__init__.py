"""
FreeCAD MCP — CAD operations via FastMCP 3.2 Unified Gateway.

Provides programmatic access to FreeCAD's CAD kernel for:
- STEP → STL conversion
- Model information (bodies, volume, faces)
- Basic geometry creation
- Mesh export
"""

from __future__ import annotations

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("freecad-mcp")
