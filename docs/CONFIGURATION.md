# Configuration — freecad-mcp

Ports: **10944** backend (FastAPI+FastMCP SSE), **10945** frontend (Vite), **10946** FreeCAD bridge TCP. Registry: `mcp-central-docs/operations/WEBAPP_PORTS.md`.

## Environment

| Var | Default | Purpose |
|-----|---------|---------|
| `FREECAD_PATH` | `D:\Dev\repos\FreeCAD\...\FreeCAD.exe` | FreeCAD binary for bridge/subprocess |
| `FREECAD_MCP_WORK_DIR` | `%TEMP%\freecad_mcp_work` | uploads/output/fluidx3d_cases |
| `FREECAD_MCP_DEPOT` | `%LOCALAPPDATA%\freecad-mcp\depot` | Persistent CAD depot |
| `FC_BRIDGE_PORT` | `10946` | TCP bridge |
| `MCP_PORT`/`PORT` | `10944` | Backend HTTP port (Tauri sets `MCP_PORT`) |
| `MCP_HOST` | `127.0.0.1` | Bind host (Tauri) |
| `FREECAD_TAURI` | `1` in Tauri | Forces HTTP, isatty shim (Gate J) |
| `PRUSA_SLICER_PATH` | `PrusaSlicer-2.8.1\prusa-slicer.exe` | Slicer binary |
| `THINGIVERSE_API_KEY` / `GRABCAD_API_KEY` | — | Marketplace auth |

## Tauri

`native/tauri.conf.json` bundles `resources/freecad-mcp-backend.exe` + `resources/.env.example`, `targets:["nsis"]`, `capabilities/default.json` (`core:default`, `shell:allow-open`, `fs:default`, `process:default`), hooks `windows/hooks.nsh`.

## Frontend

`webapp/` Vite 5.4 + React 19 + Tailwind + Zustand (`store/llm.ts`), `VITE_API_BASE=http://127.0.0.1:10944` for Tauri prod, proxy `/api`→10944 in dev.

## Fleet Start

`fleet-start.config.ps1`: `HealthPath /api/v1/status`, `UvicornTarget freecad_mcp.server:app`, `WebRoot webapp`, `BackendPort 10944`/`FrontendPort 10945`.

## MCP Tools

50+ tools via `freecad_model` portmanteau + `cfd_*`, `fem_*`, `fluidx3d_*`, `bim_*`, `marketplace_*`. See `docs/mcp-tools.md` and `llms-full.txt`.
