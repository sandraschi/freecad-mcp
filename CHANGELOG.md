# Changelog

All notable changes to the FreeCAD MCP server and webapp.

## [0.3.0] - 2026-05-12

### Added

- **Printables search fixed**: GraphQL query updated from deprecated `search` to `searchPrints2` with correct field names (`downloadCount`, `publicUsername`). Printables search now returns real results with thumbnails, download/like counts, and author names.
- **Marketplace download UX**: "Open ↗" opens model page in browser, then an inline drop zone appears for drag-and-drop upload of downloaded files. "Import" button for sources with direct download URLs (Thingiverse with API key).
- **Settings page**: Marketplace API keys section for Thingiverse and GrabCAD tokens. Keys stored in backend state, used at runtime for search/download.
- **No duplicate FreeCAD GUI**: `_freecad_already_running()` checks for existing `FreeCAD.exe` via `tasklist` before launching bridge. Server startup now <2s instead of ~70s when FreeCAD is already open. Bridge retry reduced from 15→5 attempts.
- **Help page added**: 9 tabs: FreeCAD intro, history timeline, Python scripting, 22 workbenches, vs SolidWorks/Fusion/AutoCAD comparison, MCP tools, marketplace guide, 3D printing flow, resource links.
- **Documentation restructure**: Fleet-standard hub README with 6 linked sub-docs.
- **Webapp sub-README** (`webapp/README.md`): pages, stack, development guide.
- **Help page rewrite**: 9 tabs covering FreeCAD intro, history timeline, Python scripting with code example, 22 workbenches (built-in + community), comparison table vs SolidWorks/Fusion/AutoCAD, MCP tools manifest, marketplace guide, 3D printing flow, and resource links.
- **Thingiverse marketplace**: Search and import with auto ZIP extraction of STL/STEP files.
- **STL Viewer**: Embedded Three.js STLLoader + OrbitControls in Models page.
- **Marketplace categories**: 15-17 categories per source (Printables, Thingiverse, GrabCAD) — filter pills, fetched from new `GET /api/v1/marketplace/categories` endpoint. Active category shown in result count. Category passed as query param to each marketplace API.
- **Marketplace page**: Search with category filters, result count with category indicator.
- **Marketplace proxy endpoints**: `/api/v1/marketplace/search` and `/api/v1/marketplace/download` backend endpoints.
- **Marketplace MCP tools**: `marketplace_search`, `marketplace_download`, `marketplace_categories` — search and download models from any MCP client.
- **Prefab card**: `show_marketplace_card` (`app=True`) renders marketplace results as interactive Prefab UI cards.
- **Backend refactor**: REST and MCP tools share `_marketplace_search` / `_marketplace_download` helpers; `prefab-ui>=0.18.0` dependency added.
- **G-code column**: Models page now shows G-code files alongside uploads and outputs.

## [0.2.0] - 2026-05-12

### Added

- **PrusaSlicer integration**: `slicer_status` and `slice_stl` MCP tools for STL-to-G-code slicing with configurable printer profile, filament profile, and layer height preset.
- **FreeCAD GUI launch**: `freecad_gui` MCP tool to start the FreeCAD desktop application, optionally opening a file.
- **TCP Bridge architecture**: `fc_bridge.py` runs inside FreeCAD GUI on port 10946, providing full AP214 STEP assembly support that `FreeCADCmd.exe` console mode cannot handle. Server auto-launches the bridge in its lifespan handler.
- **G-code output directory**: `gcode/` subdirectory under work dir, served via the existing `/api/v1/download/{name}` endpoint.

### Changed

- FreeCAD detection expanded to three candidate paths (bin/FreeCAD.exe, root FreeCAD.exe, extracted portable).
- `step_to_stl` and `model_info` now prefer the TCP bridge path and fall back to subprocess.
- `create_shape` now uses the TCP bridge when available.

### Fixed

- `FreeCADCmd.exe` returning 0 solids for AP214 STEP assemblies — resolved by TCP bridge with GUI.

## [0.1.0] - 2026-05-07

### Added

- Initial release: FastMCP 3.2 server with SSE transport on port 10944.
- Vite/React dashboard on port 10945 (8 pages: Dashboard, Convert, Models, Chat, Logs, Settings, Help, Apps).
- MCP tools: `freecad_status`, `step_to_stl`, `model_info`, `create_shape`.
- REST API: `/api/v1/status`, `/api/v1/upload`, `/api/v1/download/{name}`, `/api/v1/files`, `/api/v1/control/tool`.
- Ollama chat integration (AI CAD Expert, model `gemma3:1b` on `192.168.1.11:11434`).
- SSDP fleet discovery broadcast.
