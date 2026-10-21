# FreeCAD MCP — Product Requirements Document

**Version**: 0.6.0
**Status**: Shipped
**Updated**: 2026-10-21

## Purpose

FreeCAD MCP exposes FreeCAD 3D modeling, BIM/architecture design, CFD fluid simulation (OpenFOAM CPU + FluidX3D GPU), FEM structural analysis (CalculiX), and 3D printing workflows through 59 MCP tools and a web dashboard. The server operates as a headless geometry engine via TCP bridge or FreeCADCmd subprocess.

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
| 11968 | FreeCAD TCP bridge (internal) |

## Shipped Features

### Core CAD (8 tools)
- STEP/STP → STL conversion with AP214 support
- Model inspection (volume, bounding box, object count)
- Geometric primitive generation (box, cylinder, sphere, cone), verified STL export
- Parametric portmanteau (`freecad_model`): primitives, gears, fasteners, sketch,
  TechDraw, assemblies, generative, fillet, booleans, toy car
- Live bridge control and agentic design loop
- FreeCAD GUI launcher

### BIM / Architecture (10 tools)
- Parametric walls, slabs, columns (rectangular/circular/H-section)
- Windows (casement, sliding, fixed, awning) and doors (simple, glass, sliding)
- Sloped and flat roofs
- IFC import/export for industry-standard BIM exchange
- Mesh-to-solid conversion

### CFD / OpenFOAM (13 tools)
- Parametric domain creation (channel, pipe, box, nozzle, custom STEP)
- Physics configuration (laminar/kEpsilon/kOmegaSST)
- Boundary conditions (14 types: fixedValue, zeroGradient, noSlip, etc.)
- Docker-based solver execution (blockMesh, checkMesh, simpleFoam/pisoFoam/pimpleFoam)
- Results parsing (forces, residuals, convergence)
- Parametric sweeps for design optimization
- NL2FOAM: natural language → executable OpenFOAM case via LLM
- PINN sampling: point cloud export for neural network training
- snappyHexMesh config generation for complex CAD surfaces
- Post-processing: Cd/Cl, pressure drop, head loss (refuses when no solver output)
- CFD → FEM load mapping (FSI)

### FluidX3D GPU CFD (12 tools)
- Native GPU Lattice-Boltzmann via OpenCL (any GPU vendor)
- Auto-clone to %TEMP% on first use
- C++ setup generation with LBM unit conversion
- GPU compilation and execution
- Results parsing (forces, MLUPS throughput)
- Physics explanation (Reynolds number, flow regime)
- OBJ streamline export for game engine/VR pipeline
- WebM video render pipeline (VTK → heatmap PNG → ffmpeg → WebM)
- Pre-built runner binary support (compile once, run any config)
- Parametric sweeps, surrogate training and prediction

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

### Web Dashboard (18 pages)
- Dashboard with hero, onboarding cue and live KPIs (FreeCAD, Docker, FluidX3D, files)
- Guided Demo: cube → toy car → depot CRUD in one wizard (real API calls)
- Parts Studio: primitives, gears, fasteners, sketch, TechDraw, generative
- Depot with full CRUD and metadata
- Convert, Models (3D STL viewer), Marketplace
- BIM demo, CFD demos, Toy Car
- FluidX3D pipeline (setup, compile, run, results, render, explain)
- OpenFOAM workspace and Pipeline wizard
- Chat with skill badge and personalities
- Settings with LLM provider discovery
- Apps launcher, Logs viewer, Help reference

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

- v0.6.x: finish the Pyright typing pass and rebuild the `freecad-expert` skill
- v0.7: Inbox / Tools / Skills webapp pages; streaming chat endpoint
- v0.7: `/api/llm/{providers,models,onboarding}`; GPU detection wired into Settings
- v0.8: Multi-GPU FluidX3D; live simulation progress via WebSocket
- v0.9: Thermal and free-surface LBM; OpenFOAM → FluidX3D hybrid pipeline
