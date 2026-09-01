# freecad-mcp (MCPB Bundle)

FreeCAD 3D CAD automation: headless documents and export, plus CFD via FluidX3D/OpenFOAM

## Usage

Add to \claude_desktop_config.json\:
\\\json
{
  "mcpServers": {
    "freecad-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "\D:\Dev\repos\freecad-mcp", "python", "-m", "freecad_mcp"],
      "env": { "PYTHONPATH": "\D:\Dev\repos\freecad-mcp/src" }
    }
  }
}
\\\

## Tools

- **freecad_status**: freecad_status
- **step_to_stl**: step_to_stl
- **model_info**: model_info
- **create_shape**: create_shape
- **slicer_status**: slicer_status
- **slice_stl**: slice_stl
- **freecad_gui**: freecad_gui
- **freecad_design_loop**: freecad_design_loop
- **marketplace_search**: marketplace_search
- **marketplace_download**: marketplace_download
- **marketplace_categories**: marketplace_categories
- **show_marketplace_card**: show_marketplace_card
- **list_skills**: List available skill names.
- **get_skill**: Return the raw SKILL.md content for a skill.
- **get_status**: FreeCAD MCP server status.
- **health_check**: Return server health: FreeCAD status, Docker, uptime.
- **upload_file**: Upload a STEP/STL file for processing.
- **download_file**: Download a processed STL, G-code, IFC, or FCStd file.
- **serve_case_file**: Serve a file from a FluidX3D case directory.
- **list_files**: List uploaded and output files including G-code, IFC, and FCStd.
- **depot_list**: depot_list
- **depot_get**: depot_get
- **depot_rename**: depot_rename
- **depot_delete**: depot_delete
- **depot_create**: depot_create
- **depot_upload**: depot_upload
- **execute_tool**: Execute an MCP tool via REST (for webapp convenience).
- **stream_logs**: SSE log stream.
- **categories_endpoint**: List categories for a marketplace source.
- **search_endpoint**: Search a marketplace for CAD models.
- **download_endpoint**: Download a model from a marketplace URL into the uploads directory.
- **diagnostics**: Return server diagnostics for CUA smoke test.
- **capabilities**: List server capabilities.
- **shutdown**: Gracefully shut down the server.
- **llm_discover**: Discover local LLM providers (Ollama, LM Studio, vLLM).      Returns detected providers and avail...
- **get_settings**: Get LLM and marketplace settings.
- **update_settings**: Update LLM or marketplace settings.
- **chat_completion**: Chat with CAD expert via Ollama.
- **bim_create_wall**: bim_create_wall
- **bim_create_slab**: bim_create_slab
- **bim_create_column**: bim_create_column
- **bim_create_window**: bim_create_window
- **bim_create_door**: bim_create_door
- **bim_create_roof**: bim_create_roof
- **bim_export_ifc**: bim_export_ifc
- **bim_import_ifc**: bim_import_ifc
- **mesh_to_solid**: mesh_to_solid
- **bim_status**: bim_status
- **freecad_bridge**: freecad_bridge
- **cfd_status**: cfd_status
- **cfd_create_domain**: cfd_create_domain
- **cfd_configure_physics**: cfd_configure_physics
- **cfd_set_boundary**: cfd_set_boundary
- **cfd_build_case**: cfd_build_case
- **cfd_run_solver**: cfd_run_solver
- **cfd_read_results**: cfd_read_results
- **cfd_parametric_study**: cfd_parametric_study
- **cfd_nl2foam**: cfd_nl2foam
- **cfd_sample_for_pinns**: cfd_sample_for_pinns
- **cfd_snappy_mesh**: cfd_snappy_mesh
- **cfd_post_process**: cfd_post_process
- **cfd_map_loads_to_fem**: cfd_map_loads_to_fem
- **cad_depot**: cad_depot
- **cad_create**: cad_create
- **fem_status**: fem_status
- **fem_create_analysis**: fem_create_analysis
- **fem_set_material**: fem_set_material
- **fem_set_constraint**: fem_set_constraint
- **fem_mesh**: fem_mesh
- **fem_run**: fem_run
- **fem_read_results**: fem_read_results
- **run_fem_analysis**: run_fem_analysis
- **cfd_fluidx3d_status**: cfd_fluidx3d_status
- **cfd_fluidx3d_prebuilt**: cfd_fluidx3d_prebuilt
- **cfd_fluidx3d_setup**: cfd_fluidx3d_setup
- **cfd_fluidx3d_compile**: cfd_fluidx3d_compile
- **cfd_fluidx3d_run**: cfd_fluidx3d_run
- **cfd_fluidx3d_results**: cfd_fluidx3d_results
- **cfd_fluidx3d_explain**: cfd_fluidx3d_explain
- **cfd_fluidx3d_export_for_render**: cfd_fluidx3d_export_for_render
- **cfd_fluidx3d_render**: cfd_fluidx3d_render
- **cfd_fluidx3d_parametric_sweep**: cfd_fluidx3d_parametric_sweep
- **cfd_fluidx3d_train_surrogate**: cfd_fluidx3d_train_surrogate
- **cfd_surrogate_predict**: cfd_surrogate_predict
- **freecad_model**: freecad_model

## Requirements

- Python 3.12+
- uv
