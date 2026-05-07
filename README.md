# freecad-mcp — FreeCAD MCP Server

**FastMCP 3.2** — CAD operations via MCP tools and REST API. Converts STEP→STL, reads model info, creates basic geometry. Backed by FreeCAD's OCCT CAD kernel.

| Item | Details |
|------|---------|
| **Repo** | `D:\Dev\repos\freecad-mcp` |
| **Ports** | Backend **10944** (FastAPI + MCP SSE), Dashboard **10945** (Vite) |
| **Start** | `webapp\start.ps1` (or `just serve` + `just web`) |
| **Depends on** | FreeCAD 1.1.1+ (`FreeCADCmd.exe` on PATH or `FREECAD_PATH` env var) |

## Tools

| Tool | Description |
|------|-------------|
| `freecad_status` | Check FreeCAD availability and version |
| `step_to_stl` | Convert STEP/STP file to STL mesh |
| `model_info` | Return object count, solids, volume, bounding box |
| `create_shape` | Create box/cylinder/sphere/cone and export as STL |

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/status` | GET | Server and FreeCAD status |
| `/api/v1/upload` | POST | Upload STEP/STL file |
| `/api/v1/download/{name}` | GET | Download processed STL |
| `/api/v1/files` | GET | List uploads and outputs |

## Usage

```powershell
# Upload a STEP file
curl -X POST -F "file=@model.step" http://localhost:10944/api/v1/upload

# Convert via MCP tool
curl -X POST http://localhost:10944/api/v1/control/tool \
  -H "Content-Type: application/json" \
  -d '{"tool":"step_to_stl","arguments":{"file_name":"model.step","output_name":"model.stl"}}'

# Download result
curl -O http://localhost:10944/api/v1/download/model.stl
```

## MCP Client Config

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
