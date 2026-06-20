# FreeCAD MCP — Status & Roadmap

**Last updated:** 2026-06-20

---

## Project Status

Production-ready MCP server exposing FreeCAD (mechanical CAD + BIM/architecture) and CFD pipelines (OpenFOAM + FluidX3D GPU) as AI-accessible tools. 37 MCP tools across 5 domains. Dual-transport (stdio + SSE). REST API and Vite web dashboard.

### Current version
- **Repo version**: 0.5.0 (pyproject.toml), 0.6.0-dev (unreleased — FluidX3D Runner + pipeline improvements)
- **Tool count**: 37 registered MCP tools
- **Tests**: 56 passing (CFD config validation)

### Domains

| Domain | Tools | Status |
|--------|-------|--------|
| Mechanical CAD | 7 | Stable |
| Architecture/BIM | 9 | Stable |
| CFD / OpenFOAM (CPU) | 10 | Stable |
| FluidX3D (GPU) | 7 | Stable |
| Model marketplaces | 3 | Stable |
| Prefab UI cards | 1 | Stable |

---

## What Works

### Mechanical CAD
- [x] `freecad_status` — FreeCAD version + bridge mode detection
- [x] `step_to_stl` — STEP/STP to STL mesh (TCP bridge for AP214, subprocess fallback)
- [x] `model_info` — Object count, solids, volume, bounding box
- [x] `create_shape` — Box, cylinder, sphere, cone as STL
- [x] `slicer_status` — PrusaSlicer availability
- [x] `slice_stl` — STL to G-code with configurable profiles
- [x] `freecad_gui` — Launch FreeCAD desktop app

### Architecture / BIM
- [x] `bim_status` — Arch workbench availability
- [x] `bim_create_wall` — Parametric wall (mm, rotation, placement)
- [x] `bim_create_slab` — Floor slab
- [x] `bim_create_column` — Rectangular, circular, H-section
- [x] `bim_create_window` — Fixed/casement/sliding/awning in host wall
- [x] `bim_create_door` — Simple/glass/sliding-glass in host wall
- [x] `bim_create_roof` — Sloped or flat roof
- [x] `bim_export_ifc` — FCStd to IFC
- [x] `bim_import_ifc` — IFC to FCStd

### CFD / OpenFOAM (CPU, Docker)
- [x] `cfd_status` — Docker + OpenFOAM image check
- [x] `cfd_create_domain` — Channel/pipe/box/nozzle/custom domain → STEP + blockMeshDict
- [x] `cfd_configure_physics` — Solver, turbulence model, fluid properties → OpenFOAM dicts
- [x] `cfd_set_boundary` — Per-patch BCs (14 types, all field files)
- [x] `cfd_build_case` — Validate case completeness
- [x] `cfd_run_solver` — Docker execution (blockMesh → checkMesh → simpleFoam/pisoFoam)
- [x] `cfd_read_results` — Parse forces, residuals, convergence
- [x] `cfd_parametric_study` — Parameter sweeps for design optimization / ML datasets
- [x] `cfd_nl2foam` — Natural language → OpenFOAM config via Ollama or OpenAI API
- [x] `cfd_sample_for_pinns` — Point cloud export for PINNs (CSV/JSON/NumPy)

### FluidX3D (GPU, OpenCL)
- [x] `cfd_fluidx3d_status` — FluidX3D clone + C++ compiler check
- [x] `cfd_fluidx3d_setup` — Generate C++ setup.cpp + config.json (dual-path)
- [x] `cfd_fluidx3d_compile` — Compile via g++/MSVC against FluidX3D source
- [x] `cfd_fluidx3d_run` — Execute GPU binary (runner path or compiled path)
- [x] `cfd_fluidx3d_results` — Parse forces, MLUPS throughput, convergence
- [x] `cfd_fluidx3d_explain` — Interpret flow physics (Re, regime, solver notes)
- [x] `cfd_fluidx3d_prebuilt` — Auto-detect pre-compiled runner binary

### Model Marketplaces
- [x] `marketplace_search` — Printables (GraphQL), Thingiverse (REST), GrabCAD (REST)
- [x] `marketplace_download` — Download + auto-extract ZIP
- [x] `marketplace_categories` — Category list per source
- [x] `show_marketplace_card` — Prefab UI card for MCP chat

### REST API
- [x] `GET /api/v1/status` — Server health
- [x] `GET /api/v1/health` — Full health (FreeCAD + Docker + FluidX3D + compiler + uptime)
- [x] `POST /api/v1/upload` — File upload
- [x] `GET /api/v1/download/{name}` — File download
- [x] `GET /api/v1/files` — File listing
- [x] `POST /api/v1/control/tool` — Execute any MCP tool
- [x] `GET /api/v1/case-files/{case}/{file}` — Case directory file serving (STL, VTK)
- [x] Marketplace APIs (search, download, categories)
- [x] Settings (GET/PUT)
- [x] Chat (Ollama proxy)

### Webapp Dashboard (port 10945)
- [x] Dashboard — FreeCAD + OpenFOAM + FluidX3D status cards, quick actions
- [x] Convert — STEP to STL upload/conversion
- [x] Models — File browser + Three.js STL viewer
- [x] Marketplace — Search/browse/import
- [x] BIM Demo — 8 tab form for building elements
- [x] CFD — 10 tab workspace (OpenFOAM pipeline)
- [x] FluidX3D — 6 tab workspace (GPU pipeline)
- [x] Pipeline — 6 step wizard (geometry → solver → physics → BC → run → results)
- [x] Chat — Ollama CAD expert
- [x] Logs — Live SSE log stream
- [x] Settings — API keys, LLM config
- [x] Help — 11 tabs (FreeCAD, history, scripting, workbenches, comparison, tools, CFD, OpenFOAM, marketplace, 3D printing, links)

### Documentation
- [x] `docs/install.md` — 9 prerequisites with verification commands
- [x] `docs/architecture.md` — TCP bridge, subprocess fallback, ports
- [x] `docs/mcp-tools.md` — All 37 tools with examples
- [x] `docs/cfd-guide.md` — Complete CFD pipeline (388 lines)
- [x] `docs/openfoam.md` — OpenFOAM fundamentals + GPU options
- [x] `docs/flow-visualization.md` — FluidX3D graphics mode + ParaView
- [x] `docs/ai-tooling.md` — Sampling, chat, agentic workflows
- [x] `docs/about-freecad.md` — FreeCAD overview

### Quality
- [x] Ruff linting (Python) — clean
- [x] TypeScript compilation (webapp) — passes
- [x] 56 unit tests for CFD config validation
- [x] Pre-commit hooks (Ruff format + lint)

---

## What's In Progress

### FluidX3D Runner (binary)
- [x] `runner.cpp` — JSON-driven LBM solver (D3Q19, SRT, equilibrium BCs, forces, VTK)
- [x] `CMakeLists.txt` — Build system
- [x] `build-fluidx3d-runner.ps1` — Windows build script
- [x] `.github/workflows/build-fluidx3d-runner.yml` — CI (4 platforms)
- [ ] Pre-compiled binary distributed as GitHub release asset
- [ ] Auto-download binary on `cfd_fluidx3d_status` if missing

---

## What's Next (Roadmap)

### Short term
- [ ] Python-package the FluidX3D runner concept (download binary automatically if not found)
- [ ] CLI mode: `freecad-mcp --mode cfd-pipeline --case pipe --run-gpu`
- [ ] Add `cfd_fluidx3d_export_for_render` — convert VTK to OBJ/GLB for Unity/Resonite
- [ ] Visual flow rendering: animate FluidX3D VTK time series as MP4 via ffmpeg

### Medium term
- [ ] Multi-GPU FluidX3D support (domain decomposition across multiple GPUs)
- [ ] Live CFD dashboard: WebSocket stream of simulation progress + inline force chart
- [ ] GPU benchmark page: auto-detect OpenCL devices, run standard benchmark, report MLUPS
- [ ] Thermal LBM extension (natural convection, Rayleigh-Benard)
- [ ] Free surface LBM (wave sloshing, dam break, hydraulic jump)

### Long term
- [ ] Hybrid OpenFOAM + FluidX3D pipeline: OpenFOAM meshes → FluidX3D GPU solve
- [ ] Automatic surrogate training: parametric sweep → auto-train PINN → serve inference API
- [ ] CfdOF workbench bridge integration (full FreeCAD GUI CFDD workbench control)
- [ ] Embedded ParaViewWeb in dashboard for inline CFD visualization
- [ ] Reinforcement learning loop: RL agent controls geometry → OpenFOAM/FluidX3D → reward
