# Development

How to work on freecad-mcp itself (not how to use the tools - see `TOOLS.md`).

## Prerequisites

- Windows 11, PowerShell 7 for interactive work and PowerShell 5.1 for scripts.
- `uv` on PATH (`C:\Users\<you>\.local\bin\uv.exe` in the fleet image).
- Node 22 for the webapp (`webapp/`), npm lockfile committed.
- FreeCAD 1.x installed for Hands-In/Hands-Off CAD work. Optional: Docker
  (OpenFOAM), a C++ compiler + OpenCL (FluidX3D), CalculiX (FEM).

## Setup

```powershell
uv sync --all-extras
Set-Location webapp; npm install
just bootstrap        # same, plus pre-commit install
```

## Layout

| Path | Contents |
|------|----------|
| `src/freecad_mcp/server.py` | FastAPI app, REST routes, FastMCP bridge, most CAD tools |
| `src/freecad_mcp/tools/` | Portmanteau tool modules: `model_tools`, `cfd`, `fluidx3d`, `bim`, `fem`, `depot`, `bridge_tools` |
| `src/freecad_mcp/model_ops.py` | FreeCAD script generators used by Hands-Off mode |
| `src/freecad_mcp/fc_bridge.py` | TCP bridge that runs *inside* FreeCAD; imports FreeCAD modules |
| `src/freecad_mcp/utils/` | Optional integrations (VTK renderer, torch surrogate, fleet HTTP) |
| `webapp/` | React 19 + Vite + Tailwind dashboard (port 10945) |
| `mcpb/` | Claude Desktop bundle: manifest, prompts, vendored pack pipeline |
| `native/` | Tauri 2 shell and NSIS build |

## Gates

```powershell
uv run ruff check src/
uv run ruff format src/ --check
uv run pyright src/            # known debt, see below
uv run pytest                  # 123 tests, coverage floor 15%
Set-Location webapp; npx tsc --noEmit
Set-Location webapp; npx @biomejs/biome ci .
just gates-green               # ruff + tsc + pytest
just ci                        # ruff + biome + pyright + tsc + pytest
```

`pyright src/` currently reports errors from three sources: optional third-party
imports that are not in the venv (FreeCAD, PySide, torch, PIL), `ctx.sample()`
return-value typing in `server.py`, and private `FastMCP._tool_manager` access in
the diagnostics endpoints. Treat it as a dedicated typing task; do not make the
gate "pass" by widening ignore rules.

## Running

```powershell
just serve            # server.py --mode dual --port 10944
just stdio            # stdio transport for MCP clients
just web              # Vite dev server on 10945
.\start.ps1           # fleet launcher (reads fleet-start.config.ps1)
```

The fleet launcher uses `Kind='uvicorn'` with `freecad_mcp.server:app` and probes
`/api/v1/status`. Run `start.ps1 -BackendOnly` and check that endpoint after any
change to the app factory or routes.

## Adding a tool

1. Put the implementation in the matching `src/freecad_mcp/tools/*.py` module.
2. Register with `@mcp.tool(annotations=READ_ONLY or MUTATING)`.
3. Docstring must include a summary, `## Return Format`, and `## Examples`.
4. Return a dict with `success`, `message` and the domain payload.
5. Add the name to `llms-full.txt`, `glama.json` and `mcpb/manifest.json`.
6. Add a test under `tests/` - at minimum the dry-run / validation path.

## Packaging

`just mcpb-pack` calls `scripts/mcpb-pack.ps1`, which delegates to the fleet
pipeline (`mcp-central-docs/scripts/fleet-mcpb-pack.ps1`). That pipeline wipes
and recopies `src/` to `mcpb/src/` before packing; never edit `mcpb/src/` by hand.
Manifest variables may only use `${__dirname}`, `${HOME}`, `${user_config.*}` etc.
`${PWD}` is not expanded by Claude Desktop.
