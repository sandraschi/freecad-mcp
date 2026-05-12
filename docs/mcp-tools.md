# MCP Tools

All 12 tools registered via `@mcp.tool()` in `src/freecad_mcp/server.py`. 7 for CAD/slicing, 3 for marketplace, 1 Prefab card, 1 app tool.

## Tool Manifest

| Tool | Annotation | Description |
|:---|:---|:---|
| `freecad_status` | READ_ONLY | FreeCAD availability + version check |
| `step_to_stl` | MUTATING | Convert STEP/STP → STL mesh |
| `model_info` | READ_ONLY | Object count, solids, volume, bounding box |
| `create_shape` | MUTATING | Box, cylinder, sphere, cone → STL |
| `slicer_status` | READ_ONLY | PrusaSlicer availability + version |
| `slice_stl` | MUTATING | Slice STL → G-code for 3D printing |
| `freecad_gui` | MUTATING | Launch FreeCAD desktop application |
| `marketplace_search` | READ_ONLY | Search Printables, Thingiverse, GrabCAD |
| `marketplace_download` | MUTATING | Download model → uploads directory |
| `marketplace_categories` | READ_ONLY | List categories for a marketplace source |
| `show_marketplace_card` | PREFAB | Rich card view of marketplace results |

---

## freecad_status

Check if FreeCAD is reachable. Call this first before any CAD operation.

```python
await freecad_status()
# {"success": true, "freecad_ok": true, "version": "FreeCAD 1.1.1 ...", "work_dir": "..."}
```

Returns `bridge_mode` in the server state: `"tcp"` (GUI bridge active) or `"subprocess"` (headless fallback).

---

## step_to_stl

Convert a STEP assembly to an STL mesh. Upload the file first via `POST /api/v1/upload`.

```python
await step_to_stl(file_name="raspbot_v2_step.STEP", output_name="boomy.stl")
# {"success": true, "output": "boomy.stl", "data": {"objects": 42, "size_kb": 1532.4}}
```

- Uses TCP bridge for AP214 assemblies (full object extraction)
- Falls back to `FreeCADCmd` subprocess for simple STEP
- Returns number of objects converted and output file size

---

## model_info

Read metadata from a CAD file without converting it.

```python
# STEP assembly
await model_info(file_name="raspbot_v2_step.STEP")
# {"success": true, "data": {"objects": [{"name": "Chassis", "solids": 1, "volume": 450.3, "bbox": {...}}], "total": 42}}

# STL mesh
await model_info(file_name="boomy.stl")
# {"success": true, "data": {"type": "mesh", "vertices": 123456, "facets": 41152, "bbox": {...}}}
```

---

## create_shape

Create a geometric primitive and export as STL. All dimensions in millimetres.

```python
# Box
await create_shape(shape_type="box", params={"width": 20, "height": 10, "depth": 5})

# Cylinder
await create_shape(shape_type="cylinder", params={"radius": 5, "height": 20}, output_name="tube.stl")

# Sphere
await create_shape(shape_type="sphere", params={"radius": 10})

# Cone
await create_shape(shape_type="cone", params={"radius": 5, "height": 15})
```

Output is downloadable via `GET /api/v1/download/{output_name}`.

---

## slicer_status

Check PrusaSlicer availability.

```python
await slicer_status()
# {"success": true, "available": true, "version": "PrusaSlicer-2.8.1+win64", "profiles_dir": "..."}
```

Requires `PRUSA_SLICER_PATH` env var or the default portable path.

---

## slice_stl

Generate G-code from an STL file for 3D printing.

```python
# Default settings (Prusa MK4, PLA, 0.20mm SPEED)
await slice_stl(file_name="bracket.stl")

# Custom profiles
await slice_stl(
    file_name="bracket.stl",
    printer_profile="Prusa MK4",
    filament_profile="PETG",
    quality="0.15mm QUALITY",
    output_name="bracket_petg.gcode",
)
```

The G-code file is served from `GET /api/v1/download/{output_name}`.

---

## freecad_gui

Launch the full FreeCAD desktop application.

```python
# Just open FreeCAD
await freecad_gui()

# Open a specific file
await freecad_gui(file_name="tfmini_bracket_final.stl")
```

Runs as a separate process. Returns immediately. Does not connect to the bridge — use the bridge launched at server startup for tool operations.

---

## marketplace_search

Search Printables, Thingiverse, or GrabCAD for CAD models.

```python
# Basic search
await marketplace_search(source="printables", query="robot chassis")
# {"success": true, "source": "printables", "total": 230, "results": [...]}

# With category filter
await marketplace_search(source="thingiverse", query="gear", category="Tools")
```

Results contain: id, title, summary, author, download/like counts, thumbnail URL, model URL, and download URL.

---

## marketplace_download

Download a marketplace model into the uploads directory.

```python
await marketplace_download(
    source="printables",
    model_id="123456",
    file_url="https://www.printables.com/model/123456/download",
    filename="chassis.stl",
)
# {"success": true, "filename": "chassis.stl", "size_bytes": 2456789, "extracted": null}
```

Thingiverse ZIP files are auto-extracted — all STL and STEP files inside the ZIP are saved to uploads.

---

## marketplace_categories

List available categories for a marketplace source.

```python
await marketplace_categories(source="printables")
# {"success": true, "source": "printables", "categories": [{"id": "3D-Printing", "label": "3D Printing"}, ...]}
```

Categories differ per source (15-17 each). Use the id in marketplace_search's `category` param.

---

## show_marketplace_card (Prefab)

Rich Prefab UI card showing marketplace search results in supporting MCP clients (Claude Desktop, Cursor).

```python
await show_marketplace_card(source="printables", query="robot chassis")
await show_marketplace_card(source="thingiverse", query="gear", category="Tools")
```

Shows up to 6 results with thumbnails, stats, and marketplace links. Renders as an interactive card in the chat rather than raw JSON.
