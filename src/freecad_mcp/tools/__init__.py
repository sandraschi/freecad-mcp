"""
FreeCAD MCP tool modules — portmanteau re-exports.

Each submodule registers its tools via a register_* function that accepts
the FastMCP instance and server dependencies (bridge, subprocess, paths).
Call all registration functions from server.py after mcp creation.
"""

from freecad_mcp.tools.bim import register_bim_tools
from freecad_mcp.tools.cfd import register_cfd_tools
from freecad_mcp.tools.fluidx3d import register_fluidx3d_tools

__all__ = ["register_bim_tools", "register_cfd_tools", "register_fluidx3d_tools"]
