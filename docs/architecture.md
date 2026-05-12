# Architecture

## Component Topology

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Client / Webapp                    │
│                  (Claude Desktop, Cursor,                 │
│                   Vite dashboard :10945)                  │
└────────────┬────────────────────────────────────────────┘
             │ SSE / REST
             ▼
┌─────────────────────────────────────────────────────────┐
│           FastAPI + FastMCP 3.2 (:10944)                 │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │                 Lifespan Handler                   │   │
│  │  1. Verify FreeCAD.exe exists                     │   │
│  │  2. Launch GUI + fc_bridge.py (TCP :10946)        │   │
│  │  3. Wait 15×2s for bridge connect                 │   │
│  │  4. Fall back to subprocess mode if bridge fails   │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  MCP Tools (8)          REST Endpoints (8)               │
│  ┌─────────────────┐   ┌──────────────────────────┐     │
│  │ freecad_status   │   │ GET  /api/v1/status      │     │
│  │ step_to_stl      │   │ POST /api/v1/upload      │     │
│  │ model_info       │   │ GET  /api/v1/download/   │     │
│  │ create_shape     │   │ GET  /api/v1/files        │     │
│  │ slicer_status    │   │ POST /api/v1/control/tool │     │
│  │ slice_stl        │   │ GET  /api/v1/marketplace/ │     │
│  │ freecad_gui      │   │ POST /api/v1/marketplace/ │     │
│  │                  │   │ GET  /api/v1/chat         │     │
│  └─────────────────┘   └──────────────────────────┘     │
└────────┬────────────┬───────────────┬───────────────────┘
         │            │               │
         ▼            ▼               ▼
   ┌──────────┐ ┌───────────┐ ┌──────────────┐
   │ TCP      │ │ FreeCADCmd│ │ PrusaSlicer  │
   │ Bridge   │ │ subprocess│ │ CLI           │
   │ :10946   │ │ (fallback)│ │               │
   └────┬─────┘ └─────┬─────┘ └──────┬───────┘
        │             │               │
        ▼             ▼               ▼
   FreeCAD GUI   FreeCADCmd      prusa-slicer.exe
   + fc_bridge   + temp .py         --slice
        │         scripts              │
        ▼             │               ▼
   OCCT Kernel  ◄─────┘          G-code files
        │
   STL/STEP output
```

## Port Layout

| Port | Service | Protocol |
|:---|:---|:---|
| **10944** | FastAPI + FastMCP SSE | HTTP, SSE |
| **10945** | Vite dev server | HTTP (proxies `/api` → 10944) |
| **10946** | FreeCAD TCP Bridge | JSON-over-TCP |

## Dual Execution Paths

### Path A: TCP Bridge (primary)

`FreeCAD.exe` is launched as a child process with `fc_bridge.py` as a startup macro. The bridge script:
1. Starts a `socketserver.ThreadingTCPServer` on port 10946
2. Accepts JSON messages with `method` + `params`
3. Routes to: `ping`, `status`, `open` (import STEP), `export_stl`, `model_info`, `create_shape`
4. Returns JSON responses

The server connects via `asyncio.open_connection()` and sends/receives JSON lines.

**Why a bridge instead of importing FreeCAD?** FreeCAD's Python modules are 2+ GB and require a specific Python version. Running them in-process would bloat the server and cause version conflicts. The bridge keeps the server at ~50 MB.

### Path B: Subprocess (fallback)

When the TCP bridge can't connect (headless server, FreeCAD not installed), tools fall back to:
1. Writing Python scripts to temp files
2. Spawning `FreeCADCmd.exe <script.py>`
3. Parsing JSON from stdout

Limited to basic STEP (not AP214), STL, and primitive creation.

## File Pipeline

```
uploads/           ← POST /api/v1/upload, marketplace download
  ├── input.step
  ├── input.stl
  └── ...

        │ step_to_stl, model_info, create_shape
        ▼

outputs/           ← GET /api/v1/download/{name}
  ├── output.stl
  └── ...

        │ slice_stl
        ▼

gcode/             ← GET /api/v1/download/{name}
  └── output.gcode
```

Work directory defaults to `%TEMP%\freecad_mcp_work`. Override with `FREECAD_MCP_WORK_DIR`.
