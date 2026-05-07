# Handover — freecad-mcp

**Session**: 2026-05-07
**Operator**: Sandra
**Status**: Fleet-standard SOTA webapp + TCP bridge

---

## Running Services

| Service | Port | Status | Notes |
|---------|------|--------|-------|
| FastAPI + FastMCP | **10944** | Starts with `just serve` | Dual mode (stdio + HTTP) |
| Vite webapp | **10945** | Starts with `just web` | Fleet-standard SPA |
| FreeCAD Bridge | **10946** (TCP) | Launched by server lifespan | FreeCAD GUI window with bridge script |

---

## Key Files

| File | Purpose |
|------|---------|
| `src/freecad_mcp/server.py` | FastMCP 3.2 server — all tools + REST endpoints |
| `src/freecad_mcp/fc_bridge.py` | TCP bridge script run inside FreeCAD GUI |
| `src/freecad_mcp/__init__.py` | Portmanteau |
| `webapp/src/` | 8-page SOTA webapp |

## TCP Bridge

The server starts FreeCAD.exe with `fc_bridge.py` on lifespan startup. The bridge listens on TCP port 10946. Server sends JSON commands:
- `open` — import STEP/STP file (uses `FreeCAD.openDocument` + GUI pipeline, AP214 works)
- `export_stl` — export current document as STL
- `model_info` — return object/solid/volume data
- `create_shape` — box, cylinder, sphere, cone

Fallback: if bridge fails, server uses `FreeCADCmd.exe` subprocess (limited — can't handle AP214 assemblies).

## AP214 STEP Limitation

The Raspbot V2 STEP file (`Raspbot-V2.STEP`) is an AP214 automotive assembly. FreeCAD's console mode (`FreeCADCmd`) returns 0 solids. The **TCP bridge** fixes this by running FreeCAD GUI mode, which has the full Import pipeline.

To convert: open FreeCAD GUI → File → Open → select STEP → Ctrl+A → File → Export → STL.

## Webapp Pages

| Page | Purpose |
|------|---------|
| Dashboard | FreeCAD status, file counts, quick actions |
| Convert | Upload STEP → download STL |
| Models | Browse files, inspect metadata |
| CAD Expert | Chat with Ollama CAD specialist |
| Apps | Tool launcher |
| Logs | Live SSE stream with filter/export |
| Settings | Ollama URL + model config |
| Help | FreeCAD docs, workbenches, formats |

## Next Actions

- Start the server: `just serve` then `just web`
- Fix `create_shape` output path escaping (was using incorrect Mesh.export syntax, now Mesh.Mesh + .write — untested)
- QCAD MCP: start from `qcad-mcp/ARCHITECTURE.md`
