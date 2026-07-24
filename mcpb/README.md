# freecad-mcp (MCPB Bundle)

FreeCAD MCP server — CAD operations via MCP tools and REST API

## Usage

Add to \claude_desktop_config.json\:
\\\json
{
  "mcpServers": {
    "freecad-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "\D:\Dev\repos", "python", "-m", "freecad_mcp"],
      "env": { "PYTHONPATH": "\D:\Dev\repos/src" }
    }
  }
}
\\\

## Tools

- **step_to_stl**: step_to_stl
- **bim_create_wall**: bim_create_wall
- **freecad_bridge**: freecad_bridge
- **cfd_create_domain**: cfd_create_domain
- **cad_create**: cad_create
- **fem_create_analysis**: fem_create_analysis
- **cfd_fluidx3d_setup**: cfd_fluidx3d_setup
- **freecad_model**: freecad_model

## Requirements

- Python 3.12+
- uv
