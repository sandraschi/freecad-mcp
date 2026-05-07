# FreeCAD MCP

[![FastMCP Version](https://img.shields.io/badge/FastMCP-3.2.0-blue?style=flat-square&logo=python&logoColor=white)](https://github.com/sandraschi/fastmcp)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Linted with Biome](https://img.shields.io/badge/Linted_with-Biome-60a5fa?style=flat-square&logo=biome&logoColor=white)](https://biomejs.dev/)
[![Built with Just](https://img.shields.io/badge/Built_with-Just-000000?style=flat-square&logo=gnu-bash&logoColor=white)](https://github.com/casey/just)
[![GitHub last commit](https://img.shields.io/github/last-commit/sandraschi/freecad-mcp?style=flat-square&logo=github&logoColor=white)](https://github.com/sandraschi/freecad-mcp)
[![Python version](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![FreeCAD](https://img.shields.io/badge/FreeCAD-1.1.1-094b8a?style=flat-square&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgdmlld0JveD0iMCAwIDI0IDI0Ij48cGF0aCBkPSJNMTIgMkM2LjQ4IDIgMiA2LjQ4IDIgMTJzNC40OCAxMCAxMCAxMCAxMC00LjQ4IDEwLTEwUzE3LjUyIDIgMTIgMnptMCAxOGMtNC40MSAwLTgtMy41OS04LThzMy41OS04IDgtOCA4IDMuNTkgOCA4LTMuNTkgOC04IDh6IiBmaWxsPSIjMDk0YjhhIi8+PC9zdmc+)](https://freecad.org)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

**FastMCP 3.2** — Unified Gateway: MCP (stdio/SSE) + REST + Vite dashboard.

> CAD operations via FreeCAD's OCCT kernel — STEP/STL conversion, model metadata, geometry creation.

## Summary

| Item | Details |
|------|---------|
| **Ports** | Backend **10944**, Dashboard **10945** (Vite proxies `/api` → 10944) |
| **Start** | `just serve` + `just web`, or `start.ps1` from repo root |
| **Depends on** | FreeCAD 1.1.1+ (`FreeCADCmd.exe` on PATH or `FREECAD_PATH` env var) |

## Quick Start

```powershell
just bootstrap   # install deps
just serve       # start backend
just web         # start dashboard
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `freecad_status` | Server health + FreeCAD version check |
| `step_to_stl` | Convert STEP/STP → STL mesh |
| `model_info` | Object count, solids, volume, bounding box |
| `create_shape` | Box, cylinder, sphere, cone → STL |

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/status` | GET | Health check |
| `/api/v1/upload` | POST | Upload CAD file |
| `/api/v1/download/{name}` | GET | Download STL |
| `/api/v1/files` | GET | List all files |
| `/api/v1/control/tool` | POST | Execute any MCP tool |

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

## Architecture

```
MCP Client / Webapp
    │
    ▼
FastAPI + FastMCP 3.2 (port 10944)
    │
    ▼
FreeCADCmd.exe subprocess (temp Python scripts)
    │
    ▼
OCCT CAD kernel → STL files
```

The server does NOT import FreeCAD Python modules directly (2+ GB footprint).
Instead it spawns `FreeCADCmd.exe` as a lightweight subprocess, writes Python
scripts to temp files, and parses JSON from stdout. This keeps the server slim
(~50 MB with deps) while providing full FreeCAD capabilities.
