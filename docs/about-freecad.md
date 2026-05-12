# About FreeCAD

## What is FreeCAD?

FreeCAD is a **free and open-source parametric 3D CAD modeler** built on the OpenCASCADE (OCCT) geometry kernel. It's the Blender of the CAD world — community-driven, Python-scriptable, and extensible via workbenches.

Started in 2002 by Jürgen Riegel, it has grown into a mature platform with 300+ community workbenches, FEM analysis, CAM/CNC toolpaths, BIM/architecture, and robot simulation.

## History & Community

| Year | Milestone |
|:---|:---|
| 2002 | Jürgen Riegel starts FreeCAD as a Qt/OpenCASCADE project |
| 2007 | First public release (0.1) |
| 2012 | Part Design workbench, sketcher solver |
| 2015 | Assembly2 workbench, Path/CAM workbench |
| 2018 | Qt5 port, TechDraw workbench |
| 2022 | Topological naming fix (realthunder's LinkStage3 fork) |
| 2024 | FreeCAD 1.0 — "production ready" milestone |
| 2025 | FreeCAD 1.1 — improved STEP AP214 support, Ondsel merger |

**Community size:** 150+ core contributors, 70k+ GitHub stars across org, ~2M downloads per release.

**Key resources:**
- [freecad.org](https://freecad.org) — official site
- [forum.freecad.org](https://forum.freecad.org) — 300k+ posts, the primary community hub
- [wiki.freecad.org](https://wiki.freecad.org) — comprehensive documentation
- [github.com/FreeCAD/FreeCAD](https://github.com/FreeCAD/FreeCAD) — source

## Python Scripting

FreeCAD's entire API is accessible from Python. The console inside FreeCAD is a live REPL into the OCCT kernel.

### Core Modules

```python
import FreeCAD      # Application object, document management
import Part         # Topology: makeBox, makeCylinder, fuse, cut, fillet
import Mesh         # Tessellated mesh export/import (STL)
import Sketcher     # 2D constraint solver
import Draft        # 2D drafting
import Fem          # Finite element analysis
import Path         # CAM toolpath generation
import TechDraw     # Technical drawing sheets
import Import       # STEP/IGES/STL import
```

### Example: Script a bracket

```python
import Part, Mesh

# Create base plate
base = Part.makeBox(50, 40, 5)

# Add a mounting boss
boss = Part.makeCylinder(5, 15, Part.Vector(10, 10, 5))
hole = Part.makeCylinder(3, 15, Part.Vector(10, 10, 5))

# Boolean operations
bracket = base.fuse(boss).cut(hole)

# Fillet edges
edges = []
for e in bracket.Edges:
    if abs(e.Length - 5 * 3.14159) < 1:  # top edge of cylinder
        edges.append(e)
bracket = bracket.makeFillet(1.0, edges)

# Export STL
Mesh.Mesh(bracket).write("bracket.stl")
```

### FreeCAD as a Python Library

FreeCAD can be imported without the GUI:

```python
# FreeCADCmd.exe script.py
import FreeCAD
import Part

doc = FreeCAD.newDocument("MyPart")
box = doc.addObject("Part::Box", "Box")
box.Width = 20
box.Height = 10
box.Length = 5
doc.recompute()

# Export
import Mesh
Mesh.export([box], "output.stl")
```

This is exactly how the MCP server's subprocess fallback works — it pipes Python scripts to `FreeCADCmd.exe` and parses JSON from stdout.

## Workbenches

FreeCAD's extension system. Workbenches are Python packages that add domain-specific tools and UI.

### Built-in Workbenches (shipped with FreeCAD)

| Workbench | Domain |
|:---|:---|
| **Part** | CSG primitives, booleans, sweeps |
| **Part Design** | Feature-based parametric modeling (sketch → pad → pocket) |
| **Sketcher** | 2D constraint solver (lines, arcs, dimensions, constraints) |
| **Draft** | 2D CAD (lines, polylines, dimensions, snap-to-grid) |
| **Mesh** | Mesh import/repair/analysis |
| **TechDraw** | Technical drawing sheets, dimensions, annotations |
| **FEM** | Finite element analysis (CalculiX solver, stress/strain) |
| **Path** | CAM/CNC toolpaths (milling, drilling, lathe) |
| **BIM** | Building Information Modeling (IFC, walls, slabs, windows) |
| **Spreadsheet** | Parametric tables driving model dimensions |
| **Robot** | 6-axis robot simulation (KUKA, ABB kinematics) |
| **Assembly** | Assembly constraints (joints, mates) — new in 1.0 |

### Notable Community Workbenches

| Workbench | Purpose |
|:---|:---|
| **Fasteners** | ISO/DIN standard screws, nuts, washers |
| **SheetMetal** | Sheet metal unfolding, bends, reliefs |
| **Gears** | Involute gears, sprockets, timing belts |
| **A2plus** | Assembly with kinematic constraints |
| **Curves** | Freeform curves and surfaces (Gordon, sweep on 2 rails) |
| **Curved Shapes** | Arrays of curved panels (furniture, boats) |
| **Assembly4** | LCS-based assembly with variables |
| **Rocket** | Model rocket design with stability analysis |
| **CfdOF** | OpenFOAM CFD integration |
| **KiCadStepUp** | PCB ↔ FreeCAD bridge for enclosure design |
| **LCInterlocking** | Laser-cut interlocking parts |

## Comparison: FreeCAD vs Professional CAD

| Aspect | FreeCAD | SolidWorks | Fusion 360 | AutoCAD |
|:---|:---|:---|:---|:---|
| **License** | Free (LGPL) | $4,000+/year | $680/year | $2,000+/year |
| **Parametric** | Yes (sketcher + Part Design) | Yes | Yes | Limited |
| **Assembly** | New in 1.0 (evolving) | Mature | Mature | N/A |
| **FEM** | Built-in (CalculiX) | Built-in (Simulation) | Built-in (cloud) | No |
| **CAM** | Built-in (Path workbench) | CAMWorks add-on | Built-in | No |
| **Python API** | Full — everything scriptable | Limited (VBA macros) | Limited (Python add-in) | Limited (AutoLISP) |
| **File Format** | FCStd (zip of B-Rep) | SLDPRT (proprietary) | F3D (proprietary) | DWG (proprietary) |
| **Topological Naming** | Fixed in 1.0 | Yes (robust) | Yes | N/A |
| **Cloud** | No (self-hosted) | 3DEXPERIENCE | Yes (forced cloud) | BIM 360 |
| **STEP Support** | Good (AP203, AP214 in 1.1) | Excellent | Good | Limited |
| **Learning Curve** | Moderate | Steep | Gentle | Steep |

**When FreeCAD wins:**
- You need scriptable, automated CAD pipelines (our MCP server wouldn't exist without FreeCAD's Python API)
- Budget is zero and you want no vendor lock-in
- You're building tools that generate or process CAD files programmatically
- You need FEM or CAM without paying for add-ons

**When pro CAD wins:**
- Large assemblies (1000+ parts) — SolidWorks/Fusion handle this better
- Production manufacturing with GD&T, tolerancing, and PLM integration
- You need certified simulation results (NAFEMS-validated solvers)
- Collaborative multi-user editing (Fusion has better cloud sharing)

## FreeCAD in the Fleet

This MCP server turns FreeCAD into an AI-accessible service. Other fleet repos can:
- Convert STEP assemblies from robotics projects (yahboom-mcp)
- Generate STL files for 3D printing pipelines (any repo with PrusaSlicer)
- Inspect model geometry before fabrication
- Batch-convert parts libraries

The key insight: FreeCAD's Python API means **every CAD operation can be an MCP tool**. The 7 tools here are a starting point — the API surface is effectively unlimited.
