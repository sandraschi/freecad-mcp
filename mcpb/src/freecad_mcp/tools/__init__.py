"""
FreeCAD MCP tool modules — portmanteau re-exports.

Each submodule registers its tools via a register_* function that accepts
the FastMCP instance and server dependencies (bridge, subprocess, paths).
Call all registration functions from server.py after mcp creation.
"""

from freecad_mcp.tools.bim import register_bim_tools
from freecad_mcp.tools.bridge_tools import register_bridge_tools
from freecad_mcp.tools.cfd import register_cfd_tools
from freecad_mcp.tools.depot import register_depot_tools
from freecad_mcp.tools.fem import register_fem_tools
from freecad_mcp.tools.fluidx3d import register_fluidx3d_tools
from freecad_mcp.tools.model_tools import register_model_tools

__all__ = [
    "register_bim_tools",
    "register_bridge_tools",
    "register_cfd_tools",
    "register_depot_tools",
    "register_fem_tools",
    "register_fluidx3d_tools",
    "register_model_tools",
]
