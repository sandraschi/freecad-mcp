# Installation

## Prerequisites

| Tool | Required | Notes |
|:---|:---|:---|
| **Python 3.12+** | Yes | `C:\Windows\py.exe` or `uv` |
| **uv** | Yes | `C:\Users\sandr\.local\bin\uv.exe` — fleet package manager |
| **FreeCAD 1.1.1+** | Yes | Portable or installed. Set `FREECAD_PATH` if not at default location. |
| **PrusaSlicer 2.8+** | Optional | For G-code generation (`slice_stl` tool). Set `PRUSA_SLICER_PATH`. |
| **Node.js 20+** | Yes | For the Vite dashboard. |

## FreeCAD Setup

The server needs FreeCAD's Python interpreter and OCCT kernel. Two modes:

### GUI Mode (recommended)
Launches `FreeCAD.exe` with `fc_bridge.py` as a startup macro. Provides full AP214 STEP assembly support and a TCP bridge on port 10946. Requires a display.

Default path: `D:\Dev\repos\FreeCAD\FreeCAD_1.1.1-Windows-x86_64-py311\bin\FreeCAD.exe`

### Headless Mode (fallback)
Uses `FreeCADCmd.exe` subprocess. No GUI needed. Limited STEP support (no AP214 assemblies, 0 solids on complex files).

To override the path:
```powershell
$env:FREECAD_PATH = "C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe"
```

## PrusaSlicer Setup

Download from [PrusaSlicer releases](https://github.com/prusa3d/PrusaSlicer/releases). Extract anywhere and set:

```powershell
$env:PRUSA_SLICER_PATH = "D:\Dev\repos\PrusaSlicer\PrusaSlicer-2.8.1+win64-202409181359\prusa-slicer.exe"
```

The `slicer_status` tool confirms availability. Profiles are auto-detected from the sibling `profiles/` directory.

## Bootstrap

```powershell
just bootstrap   # uv sync --all-extras && cd webapp && npm install
```

## Start

```powershell
# All-in-one (backend + frontend + browser):
start.ps1

# Or separately:
just serve       # backend on :10944
just web         # frontend on :10945

# MCP stdio mode (no webapp):
just stdio
```

## Verify

```powershell
just health       # curl http://localhost:10944/api/v1/status
```

Open `http://localhost:10945` for the dashboard.
