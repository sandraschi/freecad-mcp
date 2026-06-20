# freecad-mcp — MCP Server Capabilities

FreeCAD MCP exposes FreeCAD 3D modeling, BIM/architecture design, CFD fluid simulation (OpenFOAM CPU + FluidX3D GPU), and 3D printing workflows through 38 MCP tools. The server runs FreeCAD as a headless geometry engine via TCP bridge or subprocess, generates OpenFOAM case directories for Docker-based execution, and compiles FluidX3D GPU binaries via OpenCL.

## Architecture

The server operates in three modes: stdio (Claude Desktop), HTTP/SSE (Cursor, any MCP client), or dual transport. FreeCAD geometry operations go through a TCP bridge (FreeCAD.exe with fc_bridge.py on port 10946) with subprocess fallback (FreeCADCmd.exe). CFD tools generate OpenFOAM dictionary files at `work_dir/cfd_cases/` and execute solvers via Docker (openfoam/openfoam10-paraview56). FluidX3D GPU tools generate C++ setup files + config.json at `work_dir/fluidx3d_cases/` and compile/run via g++/MSVC + OpenCL. The web dashboard runs on port 10945. REST API and MCP SSE transport share port 10944.

## Tools by Domain

### Mechanical CAD (7 tools)

**freecad_status**: Check FreeCAD executable availability and version. Returns bridge_mode (tcp/subprocess/none), freecad_ok boolean, version string. Call this first before any CAD operation. No parameters.

**step_to_stl**: Convert STEP or STP assembly file to STL mesh. Parameters: file_name (str, required — STEP file in uploads), output_name (str, default "output.stl"). Uses TCP bridge for AP214 assemblies with full object extraction, falls back to subprocess for simple STEP. Returns objects count and file size.

**model_info**: Read CAD file metadata without converting. Parameters: file_name (str, required). Returns object list with solids count, volume, bounding box for STEP. Returns vertex/facet count for STL.

**create_shape**: Create geometric primitive (box, cylinder, sphere, cone) and export as STL. Parameters: shape_type (str: box/cylinder/sphere/cone), params (dict with width/height/depth for box, radius/height for cylinder/sphere/cone). All dimensions in millimetres.

**slicer_status**: Check PrusaSlicer availability and version. No parameters. Returns available bool, version string, profiles_dir.

**slice_stl**: Slice STL file to G-code for 3D printing. Parameters: file_name (str, required), printer_profile (str, default "Prusa MK4"), filament_profile (str, default "PLA"), quality (str, default "0.20mm SPEED"), output_name (str, optional). Returns file size and path.

**freecad_gui**: Launch the FreeCAD desktop GUI application, optionally opening a file. Parameters: file_name (str, optional). Returns process PID.

### BIM / Architecture (9 tools)

**bim_status**: Check Arch workbench and IFC module availability. No parameters. Returns bim_available bool and bridge_mode.

**bim_create_wall**: Create parametric architectural wall. Parameters: length_mm, width_mm (thickness), height_mm, placement_x/y/z, rotation_z. All dimensions in mm. Outputs .fcstd file.

**bim_create_slab**: Create floor slab structure element. Parameters: width_mm, length_mm, thickness_mm, placement_x/y/z. Outputs .fcstd.

**bim_create_column**: Create structural column with profile selection. Parameters: profile_type (rectangular/circular/h_section), width_mm, depth_mm, height_mm, placement_x/y/z. Outputs .fcstd.

**bim_create_window**: Create window hosted in auto-generated wall. Parameters: window_type (fixed/casement/sliding/awning), width_mm, height_mm, sill_height_mm, placement_x/y/z, rotation_z. Outputs .fcstd.

**bim_create_door**: Create door hosted in auto-generated wall. Parameters: door_type (simple/glass/sliding_glass), width_mm, height_mm, placement_x/y/z, rotation_z. Outputs .fcstd.

**bim_create_roof**: Create sloped or flat roof. Parameters: width_mm, length_mm, angle_deg (0=flat, max 75), thickness_mm, placement_x/y/z. Outputs .fcstd.

**bim_export_ifc**: Export FCStd document to IFC format. Parameters: file_name (source .fcstd), output_name (target .ifc). IFC is the open BIM exchange standard.

**bim_import_ifc**: Import IFC file and convert to FCStd. Parameters: file_name (source .ifc), output_name (target .fcstd).

### CFD / OpenFOAM (10 tools)

**cfd_status**: Check Docker availability and OpenFOAM image presence. Returns docker_available, docker_exe, openfoam_image, bridge_mode.

**cfd_create_domain**: Create parametric fluid domain in FreeCAD and generate OpenFOAM case skeleton. Parameters: domain_type (channel/pipe/box/nozzle/custom), length_m, width_m, height_m, inlet_radius_m, outlet_radius_m (nozzle), mesh_cells, case_name, step_file (custom). Generates blockMeshDict, STEP geometry.

**cfd_configure_physics**: Generate all OpenFOAM physics dictionaries. Parameters: case_name, solver (simpleFoam/pisoFoam/pimpleFoam), flow_type (laminar/kEpsilon/kOmegaSST), fluid_nu, fluid_density, inlet_velocity, end_time, delta_t, write_interval. Generates controlDict, fvSchemes, fvSolution, transportProperties, turbulenceProperties.

**cfd_set_boundary**: Configure per-patch boundary condition field files. Parameters: case_name, patch_name (inlet/outlet/walls), field_name (U/p/k/omega/nut), bc_type (fixedValue/zeroGradient/inletOutlet/noSlip/slip/symmetry/empty + 7 more), value (OpenFOAM syntax string like "uniform (1 0 0)"). Generates field file in 0/ directory.

**cfd_build_case**: Validate OpenFOAM case completeness. Parameters: case_name. Returns files present, files missing, ready boolean.

**cfd_run_solver**: Execute OpenFOAM solver steps via Docker. Parameters: case_name, steps (comma-separated: blockMesh,checkMesh,simpleFoam/pisoFoam/pimpleFoam,decomposePar,reconstructPar), parallel (bool), n_cores (int). Mounts case directory in Docker container. Returns steps_completed, log, exit_codes.

**cfd_read_results**: Parse simulation results from completed case. Parameters: case_name. Returns time directories list, force coefficients from postProcessing/forces/, final residuals for each solved field, convergence boolean.

**cfd_parametric_study**: Run parameter sweep across design variable. Parameters: case_name (base), parameter (inlet_velocity/length/width/height/fluid_nu/angle), values (JSON array like "[0.5, 1.0, 2.0]"), run (bool). Creates suffixed cases (_0, _1, ...) with varied parameter.

**cfd_nl2foam**: Convert natural language description to executable OpenFOAM case via LLM. Parameters: description (string), case_name, model (Ollama model name), api_url (optional OpenAI-compatible endpoint), api_key (optional). Sends CFD problem description to LLM, parses structured JSON response, creates complete case.

**cfd_sample_for_pinns**: Export coordinate point clouds from CFD domain for PINN training. Parameters: case_name, n_boundary, n_interior, output_format (csv/json/numpy). Samples boundary and interior points from domain geometry. Compatible with NVIDIA Modulus, DeepXDE, PyTorch Geometric.

### FluidX3D GPU CFD (7 tools)

**cfd_fluidx3d_status**: Check FluidX3D clone and C++ compiler availability. Returns fluidx3d_path, compiler, ready boolean.

**cfd_fluidx3d_setup**: Generate FluidX3D C++ setup file and config.json for GPU simulation. Parameters: case_name, domain_type (channel/pipe/box/stl), resolution_x/y/z (grid cells), length_m, velocity_ms, viscosity_m2s, density_kgm3, time_steps, write_interval, stl_file, of_case_name, profile_shape, symmetry_axis, non_newtonian, free_surface, thermal, outlet_type, mode_2d. Supports STL auto-discovery from matching OpenFOAM case.

**cfd_fluidx3d_compile**: Compile FluidX3D setup against FluidX3D source via g++ or MSVC. Parameters: case_name, opencl_lib (optional hint). Copies setup.cpp to FluidX3D src/, compiles with -O3.

**cfd_fluidx3d_run**: Execute compiled FluidX3D binary on GPU via OpenCL. Parameters: case_name, gpu_device (index or name substring), timeout_s. Uses runner binary (reads config.json) if available, falls back to compiled binary. Returns exit code, output, runtime, VTK file list.

**cfd_fluidx3d_results**: Parse FluidX3D simulation results from run log. Parameters: case_name. Returns forces history (STEP lines), final_forces (Fx/Fy/Fz), MLUPS throughput, time steps completed, completion status.

**cfd_fluidx3d_explain**: Explain flow physics for a configured case. Parameters: case_name. Returns Reynolds number estimate, flow regime (creeping/laminar/transitional/turbulent), Darcy friction factor guidance, LBM solver notes.

**cfd_fluidx3d_prebuilt**: Check for pre-compiled FluidX3D runner binary. No parameters. Checks FLUIDX3D_BINARY env var, case bin/, runner build output.

### Model Marketplaces (3 tools)

**marketplace_search**: Search Printables (GraphQL), Thingiverse (REST), or GrabCAD (REST) for CAD models. Parameters: source, query, category (optional), page. Returns title, author, thumbnail, download/like counts.

**marketplace_download**: Download model from marketplace into uploads directory. Parameters: source, model_id, file_url, filename. Auto-extracts ZIP archives from Thingiverse.

**marketplace_categories**: List available categories for a marketplace source. Parameters: source. Returns 15-17 categories per source.

### Prefab UI (1 tool)

**show_marketplace_card**: Display marketplace search results as a rich Prefab UI card in supporting MCP clients. Parameters: source, query, category. Renders up to 6 results with thumbnails and stats.

## Environment Variables

FREECAD_PATH (default: auto-detected from D:\Dev\repos\FreeCAD\FreeCAD_1.1.1-Windows-x86_64-py311\bin\FreeCAD.exe). FC_BRIDGE_PORT (default: 10946). FREECAD_MCP_WORK_DIR (default: %TEMP%\freecad_mcp_work). PRUSA_SLICER_PATH (default: portable 2.8.1). FLUIDX3D_PATH (auto-detected from common locations). FLUIDX3D_BINARY (for pre-built runner). THINGIVERSE_API_KEY, GRABCAD_API_KEY. OpenFOAM runs via Docker (openfoam/openfoam10-paraview56 image).

## REST API

GET /api/v1/status — server health. GET /api/v1/health — full health (FreeCAD, Docker, FluidX3D, compiler, uptime). POST /api/v1/upload — upload CAD file. GET /api/v1/download/{name} — download processed file. GET /api/v1/files — list uploads/outputs/gcodes. POST /api/v1/control/tool — execute any MCP tool. GET /api/v1/case-files/{case}/{file} — serve STL/VTK from case dirs. GET/POST marketplace endpoints. GET/PUT /api/v1/settings — LLM and marketplace API keys. POST /api/v1/chat — Ollama CAD expert chat.

## Data Sources

FreeCAD geometry files: uploads/ and outputs/ directories under work_dir. CFD cases: work_dir/cfd_cases/ and work_dir/fluidx3d_cases/. Depot: work_dir/uploads/ and work_dir/outputs/ for CAD files and results. PrusaSlicer G-code: work_dir/gcode/. Logs: ring buffer in memory (2000 line, SSE stream at /api/v1/logs/stream).

## Quality Standards

All 38 tools annotated with READ_ONLY or MUTATING via @mcp.tool(annotations=...). Parameters use Annotated[str, Field(description=...)] SOTA pattern. Dual-path execution (TCP bridge then subprocess fallback) for all geometry operations. All dimensions in millimetres. All output files are served via GET /api/v1/download/{name}.
