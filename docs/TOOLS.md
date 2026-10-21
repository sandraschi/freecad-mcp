# Tools

The server exposes 59 MCP tools. `llms-full.txt` is the generated reference with
annotations; this page is the short map.

## Naming

- `freecad_*` - bridge / process control and the parametric modeling portmanteau.
- `cfd_*` - OpenFOAM and FluidX3D.
- `fem_*` - CalculiX structural analysis.
- `bim_*` - IFC / architectural primitives.
- `depot_*` / `cad_*` - persistent CAD file store.
- `marketplace_*` - Printables / Thingiverse / GrabCAD search and download.

## Core CAD

| Tool | Purpose |
|------|---------|
| `freecad_status` | FreeCAD install/version probe and bridge mode |
| `freecad_bridge` | Start/stop the in-FreeCAD TCP bridge (port 11968) |
| `freecad_gui` | Launch the desktop app, optionally opening a file |
| `freecad_model` | Portmanteau: `create_primitive`, `gear`, `fastener`, `inspect`, `clash_check`, `techdraw`, `sketch`, `assembly`, `inspect_assembly`, `generative`, `heuristic_fillet`, `fuse`, `cut`, `common`, `mirror`, `extrude`, `fillet`, `transform`, `export`, `toy_car` |
| `freecad_design_loop` | Sampling-assisted iterative design |
| `create_shape` | Primitive to STL shortcut |
| `step_to_stl` | STEP/STP assembly to STL |
| `model_info` | Object count, solids, volume, bounding box |
| `mesh_to_solid` | Mesh repair / conversion |
| `slice_stl` / `slicer_status` | PrusaSlicer G-code |

## BIM

`bim_create_wall`, `bim_create_slab`, `bim_create_column`, `bim_create_window`,
`bim_create_door`, `bim_create_roof`, `bim_export_ifc`, `bim_import_ifc`,
`bim_status`.

## CFD (OpenFOAM)

`cfd_status`, `cfd_create_domain`, `cfd_configure_physics`, `cfd_set_boundary`,
`cfd_build_case`, `cfd_snappy_mesh`, `cfd_run_solver`, `cfd_read_results`,
`cfd_post_process`, `cfd_parametric_study`, `cfd_map_loads_to_fem` (FSI),
`cfd_nl2foam`, `cfd_sample_for_pinns`.

## CFD (FluidX3D, GPU LBM)

`cfd_fluidx3d_status`, `cfd_fluidx3d_prebuilt`, `cfd_fluidx3d_setup`,
`cfd_fluidx3d_compile`, `cfd_fluidx3d_run`, `cfd_fluidx3d_results`,
`cfd_fluidx3d_explain`, `cfd_fluidx3d_export_for_render`, `cfd_fluidx3d_render`,
`cfd_fluidx3d_parametric_sweep`, `cfd_fluidx3d_train_surrogate`,
`cfd_surrogate_predict`.

## FEM (CalculiX)

`fem_status`, `fem_create_analysis`, `fem_set_material`, `fem_set_constraint`,
`fem_mesh`, `fem_run`, `fem_read_results`, `run_fem_analysis`.

## Depot and marketplace

`cad_depot`, `cad_create`, `depot_list`, `depot_get`, `depot_rename`,
`depot_delete`, `depot_create`, `depot_upload`, `marketplace_search`,
`marketplace_categories`, `marketplace_download`, `show_marketplace_card`.

## Skills, status and control

`list_skills`, `get_skill`, `get_status`, `health_check`, `list_files`,
`upload_file`, `download_file`, `serve_case_file`, `execute_tool`,
`stream_logs`, `diagnostics`, `capabilities`, `shutdown`, `llm_discover`,
`get_settings`, `update_settings`, `chat_completion`, `get_help`.

## Return shape

Most tools return a dict with `success`, `message` and a domain payload. Errors
carry `error` and usually a recovery hint. Portmanteau tools take an
`operation` (or `execution_mode` + operation) parameter - read the tool
docstring for the accepted values.

## REST equivalents

Every route is also reachable over HTTP on port 10944. The control route
`POST /api/v1/control/tool` with `{"tool": "...", "arguments": {...}}` dispatches
any MCP tool, which is what the webapp uses.
