# freecad-mcp — Agent Guide

## Overview
FreeCAD MCP server — Parametric 3D CAD modeling, 2D TechDraw drafting, 2D constraint sketching, multi-part STEP assemblies, generative topology optimization, CFD (OpenFOAM CPU + FluidX3D GPU), and CalculiX FEM structural stress analysis via 50+ MCP tools and REST API.

## Core Capabilities for Fleet Agents

| Capability | Core MCP Tools | Output Formats | Fleet Handoff Targets |
|:---|:---|:---|:---|
| **Parametric CAD & Extrusion** | `freecad_model` (`sketch`), `create_shape` | STEP, STL, FCStd | `qcad-mcp`, `prusa-slicer-mcp` |
| **2D Engineering Blueprints** | `freecad_model` (`techdraw`) | SVG, PDF | `mcp-central-docs` |
| **Multi-Part STEP Assemblies** | `freecad_model` (`assembly`, `inspect_assembly`) | STEP, STL, Tree JSON | `robotics-mcp` (URDF) |
| **Generative Weight Reduction** | `freecad_model` (`generative`) | STEP, Volume JSON | `robotics-mcp`, `prusa-slicer-mcp` |
| **Heuristic Edge Filleting** | `freecad_model` (`heuristic_fillet`) | STEP | Manufacturing pipelines |
| **Architectural BIM / IFC** | `bim_create_wall`, `bim_export_ifc` | IFC, FCStd | Architecture workflows |
| **OpenFOAM CFD (CPU)** | `cfd_create_domain`, `cfd_snappy_mesh`, `cfd_configure_physics`, `cfd_post_process` | OpenFOAM case, Cd/Cl JSON | `openfoam-mcp` |
| **Fluid-Structure Interaction (FSI)** | `cfd_map_loads_to_fem` | CalculiX INP, Stress MPa | `freecad-mcp` (FEM) |
| **FluidX3D GPU LBM CFD** | `cfd_fluidx3d_setup`, `cfd_fluidx3d_export_for_render` | VTK, OBJ Streamlines, WebM | `godot-mcp`, `resonite-mcp` (VR) |
| **CalculiX Structural FEM** | `fem_create_analysis`, `run_fem_analysis` | Von Mises Stress MPa, INP | Engineering validation |

## Standards & Patterns
- **FastMCP 3.4+ Portmanteau Pattern**: Portmanteau tool `freecad_model` maps `execution_mode` ("hands_off" or "hands_in") to underlying operational modules in `src/freecad_mcp/model_ops.py`.
- **Annotation Constants**: Every `@mcp.tool()` explicitly includes `annotations=READ_ONLY` or `annotations=MUTATING`.
- **Dual Execution Architecture**: Prefers live FreeCAD TCP bridge (port 10946) for full B-Rep tree access; automatically falls back to headless `FreeCADCmd` subprocess if GUI is not connected.
- **REST Control Endpoint**: `POST http://localhost:10944/api/v1/control/tool` with payload `{"tool": "...", "arguments": {...}}`.

## Key Files & Structure
- `src/freecad_mcp/server.py` — MCP server entrypoint and REST dispatch table.
- `src/freecad_mcp/model_ops.py` — Script generator backend for CAD extensions (TechDraw, Sketcher, Assemblies, Generative, Filleting, Introspection).
- `src/freecad_mcp/tools/model_tools.py` — Portmanteau MCP tool definition (`freecad_model`).
- `src/freecad_mcp/tools/cfd.py` — OpenFOAM CFD tools (`blockMesh`, `snappyHexMesh`, physics, post-proc, FSI).
- `src/freecad_mcp/tools/fluidx3d.py` — GPU LBM CFD tools and rendering export manifest.
- `src/freecad_mcp/tools/bim.py` — BIM architectural design & IFC import/export.
- `src/freecad_mcp/tools/fem.py` — CalculiX structural FEM analysis tools.
- `webapp/` — React 19 + Vite + Tailwind CSS dark-mode web application (port 10945).
- `docs/` — Technical guides (`cfd-guide.md`, `mcp-tools.md`, `architecture.md`, `fleet-pipeline.md`).
