# FreeCAD MCP Expert

## Overview
FreeCAD MCP is a FastMCP 3.4+ server providing 46+ CAD/CAM/CAE tools. It operates
through a TCP bridge to FreeCAD GUI or via FreeCADCmd subprocess fallback.

## Tools by Category

### Core CAD
- `freecad_status` — Check FreeCAD availability and version
- `step_to_stl` — Convert STEP/STP assemblies to STL mesh
- `model_info` — Read CAD file metadata (objects, solids, bounding box, volume)
- `create_shape` — Generate geometric primitives (box, cylinder, sphere, cone) and export STL
- `freecad_gui` — Launch FreeCAD GUI, optionally opening a file

### BIM (Building Information Modeling)
- `bim_create_wall`, `bim_create_slab`, `bim_create_column`, `bim_create_window`, `bim_create_door`, `bim_create_roof`
- `bim_export_ifc`, `bim_import_ifc`
- `bim_status`, `mesh_to_solid`

### CFD (OpenFOAM Pipeline)
- `cfd_status`, `cfd_create_domain`, `cfd_configure_physics`, `cfd_set_boundary`
- `cfd_build_case`, `cfd_run_solver`, `cfd_read_results`
- `cfd_parametric_study`, `cfd_nl2foam`, `cfd_sample_for_pinns`

### FluidX3D (GPU CFD)
- `cfd_fluidx3d_status`, `cfd_fluidx3d_prebuilt`, `cfd_fluidx3d_setup`
- `cfd_fluidx3d_compile`, `cfd_fluidx3d_run`, `cfd_fluidx3d_results`, `cfd_fluidx3d_explain`

### FEM (Structural Analysis)
- `fem_status`, `fem_create_analysis`, `fem_set_material`, `fem_set_constraint`
- `fem_mesh`, `fem_run`, `fem_read_results`, `run_fem_analysis`

### Slicing & 3D Printing
- `slicer_status`, `slice_stl` — PrusaSlicer G-code generation

### Marketplace
- `marketplace_search`, `marketplace_download`, `marketplace_categories`
- Prefab card: `show_marketplace_card`

## Best Practices
1. Start with `freecad_status()` to confirm FreeCAD is reachable
2. Upload files via `POST /api/v1/upload` REST endpoint
3. Use `cad_depot` for persistent file storage across sessions
4. For CFD: build case with `cfd_create_domain` → configure physics → set boundaries → build → run → read results
5. Bridge mode (TCP) is preferred over subprocess for complex operations

## Configuration
- `FREECAD_PATH` — Path to FreeCAD executable
- `PRUSA_SLICER_PATH` — Optional path to PrusaSlicer
- `FREECAD_MCP_WORK_DIR` — Working directory for temp files (default: %TEMP%\\freecad_mcp_work)
- REST API at `127.0.0.1:10944`, webapp at `127.0.0.1:10945`
