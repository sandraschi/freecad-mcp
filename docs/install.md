# Installation

## Prerequisites Overview

| Component | Required | Purpose | Version |
|:---|:---|:---|:---|
| FreeCAD | **Yes** | CAD kernel (mechanical + architectural) | 1.1.1+ |
| Python + uv | **Yes** | MCP server runtime + package management | 3.12+ |
| Node.js | **Yes** | Vite dashboard frontend | 18+ |
| Docker Desktop | Optional | OpenFOAM CFD solver | 27+ |
| FluidX3D + g++ | Optional | GPU-accelerated CFD (Lattice-Boltzmann) | v3.7+ |
| PrusaSlicer | Optional | 3D printing G-code generation | 2.8+ |
| Ollama | Optional | Local LLM for NL2FOAM + CAD chat | latest |
| just | **Yes** | Task runner (`bootstrap`, `serve`, `lint`) | 1.39+ |

---

## 1. FreeCAD 1.1.1+

FreeCAD provides the OCCT kernel and Python scripting engine. Two modes:

### GUI Mode (recommended)
Launches `FreeCAD.exe` with `fc_bridge.py` as a startup macro. Full AP214 STEP assembly support. TCP bridge on port 10946. Requires a display.

### Headless Mode (fallback)
Uses `FreeCADCmd.exe` subprocess. No GUI needed. Limited STEP support (no AP214 assemblies).

### Install

Download from [FreeCAD 1.1.1+ releases](https://github.com/FreeCAD/FreeCAD/releases). Portable or installed — both work.

Default path: `D:\Dev\repos\FreeCAD\FreeCAD_1.1.1-Windows-x86_64-py311\bin\FreeCAD.exe`

### Override path

```powershell
$env:FREECAD_PATH = "C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe"
```

### Verify

```powershell
& "$env:FREECAD_PATH" --version
# FreeCAD 1.1.1, build ...

# Or check via the FreeCAD Python interpreter:
& "D:\Dev\repos\FreeCAD\FreeCAD_1.1.1-Windows-x86_64-py311\bin\python.exe" -c "import FreeCAD; print(FreeCAD.Version())"
# ['1', '1', '1', ...]
```

---

## 2. Python 3.12+ with uv

Python runs the FastMCP server. `uv` is the fleet package manager — drop-in replacement for pip/venv.

### Install

```powershell
# Python 3.12+ (if not present)
# Download from https://www.python.org/downloads/ — ensure "Add to PATH" is checked.

# uv — fleet standard
powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
```

### Verify

```powershell
py --version                # Python 3.12.x or 3.13.x
uv --version                # uv 0.6.x+

# Confirm uv can resolve the project:
uv lock --check             # (run from repo root)
```

---

## 3. Node.js 18+

The Vite dashboard (port 10945) is a React 19 + TypeScript SPA served by `vite`.

### Install

```powershell
# Via winget (fleet standard):
winget install OpenJS.NodeJS.LTS

# Or download from https://nodejs.org/
```

### Verify

```powershell
node --version              # v18.x or v20.x or v22.x
npm --version               # 10.x+
```

---

## 4. Docker Desktop for Windows (OpenFOAM)

OpenFOAM v10 runs in a Docker container. Used by `cfd_create_domain`, `cfd_configure_physics`, `cfd_run_solver`, `cfd_read_results`, and `cfd_parametric_sweep`.

### Install

1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. Install with WSL 2 backend (default)
3. Start Docker Desktop and wait for the whale icon to stop animating

### Pull the OpenFOAM image

```powershell
docker pull openfoam/openfoam10-paraview56
```

### Verify

```powershell
docker info                 # Server version, running state
docker images openfoam      # Should show openfoam/openfoam10-paraview56
```

### Troubleshooting

- "Docker not available": Start Docker Desktop; check `docker info`
- "Image not found": Re-run `docker pull openfoam/openfoam10-paraview56`
- WSL not installed: `wsl --install` then restart Docker

---

## 5. FluidX3D (GPU CFD)

[FluidX3D](https://github.com/ProjectPhysX/FluidX3D) — 5,000+ stars, OpenCL-based Lattice-Boltzmann CFD. Runs on any GPU (NVIDIA, AMD, Intel, Apple Silicon). Used by all 6 `cfd_fluidx3d_*` tools.

Requires a C++ compiler and an OpenCL-capable GPU.

### Clone the repo

```powershell
git clone https://github.com/ProjectPhysX/FluidX3D.git D:\Dev\repos\FluidX3D
```

### Install a C++ compiler

**Option A — MinGW g++ (recommended for fleet):**

```powershell
winget install GnuWin32.Make
# Then install MinGW-w64 from https://www.mingw-w64.org/ or via MSYS2
```

**Option B — Visual Studio Build Tools (MSVC):**

```powershell
winget install Microsoft.VisualStudio.2022.BuildTools --override "--wait --add Microsoft.VisualStudio.Workload.VCTools"
```

**Option C — WSL g++:**

```powershell
wsl sudo apt update && wsl sudo apt install -y g++ ocl-icd-opencl-dev
```

### Verify

```powershell
g++ --version               # g++.exe (MinGW-W64) 14.x or similar
# OR
cl                          # Microsoft (R) C/C++ Optimizing Compiler

# Confirm FluidX3D repo:
Test-Path -LiteralPath "D:\Dev\repos\FluidX3D\Source"
# True
```

---

## 6. PrusaSlicer 2.8+

Generates G-code from STL meshes via the `slice_stl` tool. Auto-discovers printer/filament/print profiles from a sibling `profiles/` directory.

### Install

Download from [PrusaSlicer releases](https://github.com/prusa3d/PrusaSlicer/releases). Extract anywhere.

### Configure

```powershell
$env:PRUSA_SLICER_PATH = "D:\Dev\repos\PrusaSlicer\PrusaSlicer-2.8.1+win64-202409181359\prusa-slicer.exe"
```

### Verify

```powershell
Test-Path -LiteralPath $env:PRUSA_SLICER_PATH
# True

# Or query via the MCP tool:
# slicer_status → {"success": true, "available": true, "version": "2.8.1", ...}
```

---

## 7. Ollama (Optional)

Local LLM for natural-language CFD configuration (`cfd_nl_config`) and CAD chat. Any Ollama model works; larger models produce better OpenFOAM physics configs.

### Install

```powershell
winget install Ollama.Ollama
```

### Pull a model

```powershell
ollama pull llama3.2        # ~2 GB, good baseline
# or
ollama pull qwen2.5:14b     # ~8 GB, better physics reasoning
```

### Verify

```powershell
ollama --version            # 0.6.x+
ollama list                 # Should show pulled models
```

---

## 8. Bootstrap

Installs all Python and Node.js dependencies from lockfiles.

```powershell
just bootstrap
```

This runs:
- `uv sync --all-extras` — Python packages into `.venv/`
- `cd webapp && npm install` — Node packages into `webapp/node_modules/`

### Verify

```powershell
just health
# curl http://localhost:10944/api/v1/status

# Or check the environment without starting:
uv run python -c "import freecad_mcp; print('OK')"
```

---

## 9. Start

### All-in-one

```powershell
start.ps1
```

Kills any zombies on ports 10944/10945, starts the backend (dual mode: REST + MCP SSE), starts the Vite frontend, and prints URLs:

| Service | Port | URL |
|:---|:---|:---|
| MCP server + REST API | 10944 | `http://localhost:10944/api/v1/status` |
| Web dashboard | 10945 | `http://localhost:10945` |
| MCP SSE transport | 10944 | `http://localhost:10944/sse` |

### Separate launches

```powershell
just serve                  # backend on :10944
just web                    # frontend on :10945
just stdio                  # MCP stdio mode (no webapp)
```

### MCP Client Config

```json
{
  "mcpServers": {
    "freecad": {
      "url": "http://localhost:10944/sse",
      "transport": "sse"
    }
  }
}
```

---

## Complete Verification Checklist

Run all checks before reporting issues:

```powershell
# ── Core ─────────────────────────────────────────────
py --version                          # 3.12+
uv --version                          # 0.6.x+
node --version                        # 18+
just --version                        # 1.39+
Test-Path -LiteralPath ".venv"        # True (after bootstrap)

# ── FreeCAD ─────────────────────────────────────────
Test-Path -LiteralPath $env:FREECAD_PATH  # True (or default exists)

# ── Docker / OpenFOAM ───────────────────────────────
docker info                          # (no error)
docker images openfoam               # openfoam/openfoam10-paraview56

# ── FluidX3D / GPU CFD ──────────────────────────────
Test-Path -LiteralPath "D:\Dev\repos\FluidX3D\Source"  # True
g++ --version                        # (or cl)
# Optional — quick compiler check:
g++ -std=c++17 -x c++ -c - <<< "int main(){}" -o NUL  # (no error)

# ── PrusaSlicer ─────────────────────────────────────
Test-Path -LiteralPath $env:PRUSA_SLICER_PATH  # True (if configured)

# ── Ollama ──────────────────────────────────────────
ollama --version                     # 0.6.x+ (if installed)
```
