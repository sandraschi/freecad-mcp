# FreeCAD MCP — Product Requirements Document

**Version**: 0.5.0  
**Status**: Active Development  
**Updated**: 2026-07-24

## Purpose

FreeCAD MCP exposes FreeCAD 3D modeling, BIM/architecture design, CFD fluid simulation (OpenFOAM CPU + FluidX3D GPU), FEM structural analysis (CalculiX), and 3D printing workflows through 50+ MCP tools and a web dashboard. The server operates as a headless geometry engine via TCP bridge or FreeCADCmd subprocess.

## Target Users

- **AI agents**: Claude Desktop, Cursor, Continue — agentic CAD workflows
- **Engineers**: Mechanical, civil, aerospace — parametric CAD + simulation + printing
- **Architects**: BIM building design with IFC import/export
- **CFD engineers**: Fluid simulation with OpenFOAM and GPU-accelerated FluidX3D
- **3D printing enthusiasts**: STL slicing and marketplace search

## Architecture

```
MCP Client (AI) ──→ FastAPI + FastMCP ──→ FreeCAD (TCP bridge / subprocess)
       │                    │
       │              Web Dashboard (Vite)
       │                    │
       └─── REST API ──────┘
```

## Ports

| Port | Service |
|------|---------|
| 10944 | FastAPI + MCP SSE + REST API |
| 10945 | Vite web dashboard |
| 10946 | FreeCAD TCP bridge (internal) |

## Shipped Features

### Core CAD (6 tools)
- STEP/STP → STL conversion with AP214 support
- Model inspection (volume, bounding box, object count)
- Geometric primitive generation (box, cylinder, sphere, cone)
- FreeCAD GUI launcher

### BIM / Architecture (10 tools)
- Parametric walls, slabs, columns (rectangular/circular/H-section)
- Windows (casement, sliding, fixed, awning) and doors (simple, glass, sliding)
- Sloped and flat roofs
- IFC import/export for industry-standard BIM exchange
- Mesh-to-solid conversion

### CFD / OpenFOAM (10 tools)
- Parametric domain creation (channel, pipe, box, nozzle, custom STEP)
- Physics configuration (laminar/kEpsilon/kOmegaSST)
- Boundary conditions (14 types: fixedValue, zeroGradient, noSlip, etc.)
- Docker-based solver execution (blockMesh, checkMesh, simpleFoam/pisoFoam/pimpleFoam)
- Results parsing (forces, residuals, convergence)
- Parametric sweeps for design optimization
- NL2FOAM: natural language → executable OpenFOAM case via LLM
- PINN sampling: point cloud export for neural network training

### FluidX3D GPU CFD (9 tools)
- Native GPU Lattice-Boltzmann via OpenCL (any GPU vendor)
- Auto-clone to %TEMP% on first use
- C++ setup generation with LBM unit conversion
- GPU compilation and execution
- Results parsing (forces, MLUPS throughput)
- Physics explanation (Reynolds number, flow regime)
- OBJ streamline export for game engine/VR pipeline
- WebM video render pipeline (VTK → heatmap PNG → ffmpeg → WebM)
- Pre-built runner binary support (compile once, run any config)

### FEM / Structural Analysis (8 tools)
- CalculiX solver integration
- Material presets (steel, aluminum, titanium, carbon fiber, 10 total)
- Boundary conditions (fixed, force, pressure)
- Gmsh meshing with configurable element size
- End-to-end `run_fem_analysis` convenience tool

### Slicing & 3D Printing (2 tools)
- PrusaSlicer integration
- Configurable printer, filament, quality profiles

### Marketplace (4 tools)
- Printables, Thingiverse, GrabCAD search and download
- Prefab UI card for in-chat browsing
- ZIP auto-extract for Thingiverse downloads

### CAD File Depot (2 tools)
- Persistent storage with metadata (description, tags, shape type)
- Full CRUD via REST API

### Web Dashboard (11 pages)
- Dashboard with live KPIs (FreeCAD, Docker, FluidX3D, files)
- Models page with 3D STL viewer
- FluidX3D pipeline (6 tabs: Status, Setup, Compile, Run, Results, Video, Explain)
- BIM demo page
- Settings with LLM configuration
- Chat with personality selector
- Pipeline wizard
- Help with 12 reference tabs
- Status/logs viewer

### NSIS Desktop Installer
- Tauri 2.0 native wrapper
- Embedded PyInstaller backend
- CUA smoke testing (install → launch → verify → uninstall)
- Session context injection (Claude Code, Cursor, Copilot, Windsurf, OpenCode)

## Technical Stack

- **Backend**: Python 3.13+, FastMCP 3.4.4+, FastAPI, uvicorn
- **Frontend**: React 19, Vite, TailwindCSS, TypeScript, Lucide icons
- **Desktop**: Tauri 2.0, Rust, NSIS installer
- **CFD**: Docker (OpenFOAM 10), OpenCL (FluidX3D)
- **CAD**: FreeCAD 1.1.1, OpenCASCADE (OCCT)
- **QA**: ruff, biome, tsc, pytest, Playwright, CUA/pywinauto

## Future

- v0.6: Webapp SOTA overhaul (Zustand, local LLM glom-on, color-scheme dark)
- v0.7: snappyHexMesh for complex CFD geometry
- v0.8: Multi-GPU FluidX3D, parametric sweeps for FluidX3D
