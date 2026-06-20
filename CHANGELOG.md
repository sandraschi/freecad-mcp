# Changelog

All notable changes to the FreeCAD MCP server and webapp.

## [Unreleased] — 2026-06-20

### Added
- **FluidX3D Runner**: Pre-compiled standalone GPU CFD binary. `runner.cpp` reads `config.json` at runtime — no recompilation per case. D3Q19 LBM with SRT collision, equilibrium boundaries, force extraction, VTK export. Supports channel/pipe/box domains, STL import, structured JSON output for MCP parsing.
- **build-fluidx3d-runner.ps1**: Windows build script (clones FluidX3D, injects runner, compiles via g++ or MSVC). Auto-detects compiler and FluidX3D path.
- **CMakeLists.txt**: CMake build system for the runner. Requires `FLUIDX3D_SOURCE_DIR` and OpenCL. Platform-optimized flags (MSVC /EHsc/O2, g++ -O3).
- **GitHub Actions workflow**: Cross-platform CI build (Windows MSVC, Windows g++, Linux g++, macOS clang++). Uploads binaries on tagged releases.
- **Auto-detect runner**: `_find_prebuilt` now checks for `fluidx3d-runner.exe` first — checks `FLUIDX3D_BINARY` env var, case `bin/`, runner build output.
- **config.json generation**: `cfd_fluidx3d_setup` writes both `.f3d_config.json` (compile path) and `config.json` (runner path).
- **Runner-first execution**: `cfd_fluidx3d_run` detects runner binary and uses it with `F3D_CONFIG` env var. Falls back to compiled binary path.
- **Pipeline builder**: New 6-step wizard page in webapp (`/pipeline`) — geometry → solver → physics → boundaries → run → results. Stepper navigation with solver-aware forms.
- **Dash board overhaul**: 4 status cards (FreeCAD, OpenFOAM/Docker, FluidX3D/GPU, Files). Quick action grid (8 links). Fetches `/api/v1/health` for live status.
- **`/api/v1/health` endpoint**: Returns FreeCAD status, Docker/OpenFOAM availability, FluidX3D path, compiler, uptime. No dependencies required.
- **OpenAI-compatible NL2FOAM**: `cfd_nl2foam` now accepts `api_url` + `api_key` params for any `/v1/chat/completions` endpoint (GPT-4, Claude API, any OpenAI-compatible).
- **STL auto-wire**: `cfd_fluidx3d_setup` auto-discovers STL geometry from matching OpenFOAM case via `of_case_name` parameter. 4-level discovery cascade.
- **STL viewer on FluidX3D page**: Reuses existing Three.js viewer component to show meshes after setup.
- **`GET /api/v1/case-files/{case}/{file}`**: Serves STL/VTK files from case directories.
- **`docs/flow-visualization.md`**: Guide covering FluidX3D interactive graphics mode (keyboard controls, visualization modes, ffmpeg video), ParaView, vtk.js.
- **`docs/status.md`**: Comprehensive status/todo document covering all 37 tools, current state, in-progress items, and roadmap.
- **CFD test suite**: `tests/test_cfd_configs.py` — 56 tests validating blockMeshDict, physics configs, boundary fields, FluidX3D C++ generation, and NL2FOAM schema.
- **`docs/install.md` rewritten**: 9 prerequisites with install/verify steps (FreeCAD, Python, Node, Docker, FluidX3D, g++, PrusaSlicer, Ollama, bootstrap).
- **README hero rewritten**: Human-readable categories (mechanical parts, architecture, fluid simulation, 3D printing, marketplace, ML). "Two ways to use this" section (AI agents vs humans). Scripting examples. See-also section linking QCad/Blender/Unity/Inkscape/GIMP MCPs.

### Changed
- Tool count: 30 → 37 (added FluidX3D prebuilt, 7th tool)
- `_find_prebuilt` priority: env var → runner binary → compiled binary
- Dashboard now fetches `/api/v1/health` instead of just `/api/v1/status`
- Sidebar: 12 nav items (added CFD, FluidX3D, Pipeline)
- CORS: allow_origins explicit list for Tauri WebView compatibility

### Fixed
- CHANGELOG encoding issues (tab/em-dash corruption in Tauri CORS section)

## [0.5.0] — 2026-05-15

### Added

- **CFD / OpenFOAM integration**: 10 new MCP tools for the complete Geometry-Mesh-Simulation-Analysis pipeline — `cfd_status`, `cfd_create_domain`, `cfd_configure_physics`, `cfd_set_boundary`, `cfd_build_case`, `cfd_run_solver`, `cfd_read_results`, `cfd_parametric_study`, `cfd_nl2foam`, `cfd_sample_for_pinns`. All in `src/freecad_mcp/tools/cfd.py` (1430 lines), following the same dual-mode pattern as BIM tools (TCP bridge + subprocess fallback).
- **Parametric domain creation**: `cfd_create_domain` generates fluid domains (channel, pipe, box, nozzle, custom STEP) in FreeCAD and exports blockMeshDict for structured hex meshing.
- **Physics auto-configuration**: `cfd_configure_physics` generates all OpenFOAM dictionaries (controlDict, fvSchemes, fvSolution, transportProperties, turbulenceProperties) with laminar/kEpsilon/kOmegaSST models. Built-in fluid property reference (water, air, oil, glycerin).
- **Boundary condition management**: `cfd_set_boundary` generates per-patch field files (U, p, k, omega, nut) with 14 supported BC types.
- **Case validation**: `cfd_build_case` checks OpenFOAM case completeness and reports missing files.
- **Docker-based solver execution**: `cfd_run_solver` executes OpenFOAM steps (blockMesh, checkMesh, simpleFoam/pisoFoam/pimpleFoam, decomposePar, reconstructPar) via `docker run` with automatic Windows path conversion.
- **Results parsing**: `cfd_read_results` extracts time directories, force coefficients, solver residuals, convergence status.
- **Parametric design sweeps**: `cfd_parametric_study` duplicates a base case across parameter variations — supports both config-only mode and full execution mode.
- **NL2FOAM**: `cfd_nl2foam` converts plain-language fluid dynamics descriptions into executable OpenFOAM cases via Ollama LLM.
- **PINN point cloud sampling**: `cfd_sample_for_pinns` exports coordinate point clouds for PINN training. Supports CSV, JSON, NumPy (.npz) formats.
- **CFD webapp workspace**: `CfdPage.tsx` (490 lines) with 10-tab interface.
- **Comprehensive CFD documentation**: `docs/cfd-guide.md` with architecture diagrams, parameter tables, fluid properties, BC reference, workflow examples, troubleshooting, benchmarks.
- Sidebar updated with CFD nav item. Help page extended with CFD tools tab. README updated.
- MCP tools count: 20 → 30.

## [0.4.0] — 2026-05-14

### Added

- **BIM/Arch workbench tools**: 9 new MCP tools wrapping FreeCAD's Arch workbench — `bim_create_wall`, `bim_create_slab`, `bim_create_column`, `bim_create_window`, `bim_create_door`, `bim_create_roof`, `bim_export_ifc`, `bim_import_ifc`, `bim_status`. All create parametric .fcstd documents with dual-mode execution (TCP bridge + subprocess fallback).
- **IFC exchange**: `bim_export_ifc` exports .fcstd to .ifc. `bim_import_ifc` imports .ifc files from architects.
- **Modular tool architecture**: BIM tools in `tools/bim.py` with `register_bim_tools()` factory pattern. `tools/__init__.py` portmanteau re-exports.
- **BIM bridge commands**: 8 JSON-RPC methods in `fc_bridge.py` for BIM operations.
- **REST proxy**: `/api/v1/control/tool` dispatches all 9 BIM tools.

## [0.3.0] — 2026-05-12

### Added
- Printables search fix (GraphQL update), marketplace download UX, Settings page, no duplicate FreeCAD GUI, Help page (9 tabs), Thingiverse/GrabCAD marketplace support, STL Viewer (Three.js), marketplace categories, Prefab marketplace card, G-code column, marketplace proxy endpoints, marketplace MCP tools.

## [0.2.0] — 2026-05-12

### Added
- PrusaSlicer integration (`slicer_status`, `slice_stl`), FreeCAD GUI launch (`freecad_gui`), TCP Bridge architecture (`fc_bridge.py`), G-code output directory.

## [0.1.0] — 2026-05-07

### Added
- Initial release: FastMCP 3.2 SSE transport on port 10944. Vite/React dashboard on port 10945 (8 pages). MCP tools: `freecad_status`, `step_to_stl`, `model_info`, `create_shape`. REST API: status, upload, download, files, control/tool. Ollama chat integration. SSDP fleet discovery.
