"""PyInstaller entry point — dual transport: MCP_PORT → HTTP, else stdio.

Gate J: when launched from Tauri (FREECAD_TAURI=1 or FREECAD_MCP_TAURI=1) never
hijack stdio — force HTTP even if MCP_PORT is unset. Also shims isatty() so
libraries that gate on tty do not switch to stdio mode.
"""

import _datetime  # noqa: F401
import _strptime  # noqa: F401
import os
import sys

import mcp.types  # noqa: F401

sys.path.insert(0, ".")

# Gate J: isatty shim — when Tauri sets FREECAD_TAURI=1, pretend stdout is not a tty
# so any library checking sys.stdout.isatty() does not enable stdio transport.
if os.environ.get("FREECAD_TAURI") == "1" or os.environ.get("FREECAD_MCP_TAURI") == "1":
    try:
        if hasattr(sys.stdout, "isatty"):
            sys.stdout.isatty = lambda: False  # type: ignore[method-assign]
        if hasattr(sys.stderr, "isatty"):
            sys.stderr.isatty = lambda: False  # type: ignore[method-assign]
    except Exception:
        pass

from freecad_mcp.server import main

# Gate J: Tauri sidecar must not fall through to stdio — force HTTP
is_tauri = os.environ.get("FREECAD_TAURI") == "1" or os.environ.get("FREECAD_MCP_TAURI") == "1"
port = os.environ.get("MCP_PORT") or os.environ.get("PORT")
if is_tauri and not port:
    port = "10944"
if port:
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    sys.argv = ["run_server.py", "--mode", "http", "--host", host, "--port", str(port)]
elif is_tauri:
    # Fallback: Tauri without port env — still force http on default
    sys.argv = ["run_server.py", "--mode", "http", "--host", "127.0.0.1", "--port", "10944"]
main()
