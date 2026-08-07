"""PyInstaller entry point — dual transport: MCP_PORT → HTTP, else stdio."""

import _datetime  # noqa: F401
import _strptime  # noqa: F401
import os
import sys

import mcp.types  # noqa: F401

sys.path.insert(0, ".")

from freecad_mcp.server import main

port = os.environ.get("MCP_PORT") or os.environ.get("PORT")
if port:
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    sys.argv = ["run_server.py", "--mode", "http", "--host", host, "--port", str(port)]
main()
