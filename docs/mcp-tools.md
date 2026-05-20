# MCP Tools

All 44 (37+7 FEM) tools registered via `@mcp.tool()` in `src/freecad_mcp/server.py`, `src/freecad_mcp/tools/bim.py`, `src/freecad_mcp/tools/cfd.py`, `src/freecad_mcp/tools/fem.py`, and `src/freecad_mcp/tools/fluidx3d.py`. 7 for CAD/slicing, 9 for BIM/Arch, 10 for CFD/OpenFOAM, 8 for FEM/structural (CalculiX), 7 for FluidX3D GPU, 3 for marketplace, 1 Prefab card.

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
| `bim_status` | READ_ONLY | BIM/Arch workbench availability check |
| `bim_create_wall` | MUTATING | Parametric architectural wall → FCStd |
| `bim_create_slab` | MUTATING | Floor slab (structural element) → FCStd |
| `bim_create_column` | MUTATING | Column (rect., circular, H-section) → FCStd |
| `bim_create_window` | MUTATING | Window hosted in auto-generated wall → FCStd |
| `bim_create_door` | MUTATING | Door hosted in auto-generated wall → FCStd |
| `bim_create_roof` | MUTATING | Sloped or flat roof → FCStd |
| `bim_export_ifc` | MUTATING | Export FCStd document → IFC format |
| `bim_import_ifc` | MUTATING | Import IFC file → FCStd document |
| `marketplace_search` | READ_ONLY | Search Printables, Thingiverse, GrabCAD |
| `marketplace_download` | MUTATING | Download model → uploads directory |
| `marketplace_categories` | READ_ONLY | List categories for a marketplace source |
| `show_marketplace_card` | PREFAB | Rich card view of marketplace results |
| `cfd_status` | READ_ONLY | Docker/OpenFOAM availability check |
| `cfd_create_domain` | MUTATING | Parametric fluid domain → STEP + blockMeshDict |
| `cfd_configure_physics` | MUTATING | Solver/physics/fluid property config → OpenFOAM dicts |
| `cfd_set_boundary` | MUTATING | Per-patch boundary condition field files |
| `cfd_build_case` | READ_ONLY | Validate OpenFOAM case completeness |
| `cfd_run_solver` | MUTATING | Execute OpenFOAM solver via Docker |
| `cfd_read_results` | READ_ONLY | Parse forces, residuals, time directories |
| `cfd_parametric_study` | MUTATING | Parameter sweep for design optimization |
| `cfd_nl2foam` | MUTATING | Natural language → OpenFOAM config via LLM |
| `cfd_sample_for_pinns` | MUTATING | Export point clouds for PINN/GNN training |
| `fem_status` | READ_ONLY | FEM workbench and CalculiX availability |
| `fem_create_analysis` | MUTATING | Create structural analysis container on 3D model |
| `fem_set_material` | MUTATING | Assign material (10 presets) with E, nu, density, yield |
| `fem_set_constraint` | MUTATING | Apply fixed supports, forces, pressure to named faces |
| `fem_mesh` | MUTATING | Generate finite element mesh via Gmsh (tetra4/tetra10) |
| `fem_run` | MUTATING | Write .inp file and run CalculiX ccx solver |
| `fem_read_results` | READ_ONLY | Parse von Mises stress, displacement, principal stresses |
| `run_fem_analysis` | MUTATING | End-to-end FEM: create → material → constraints → mesh → solve → results |
| `cfd_fluidx3d_status` | READ_ONLY | Check FluidX3D + compiler availability |
| `cfd_fluidx3d_setup` | MUTATING | Generate FluidX3D C++ setup.cpp for GPU CFD |
| `cfd_fluidx3d_compile` | MUTATING | Compile setup.cpp → GPU binary via g++/MSVC |
| `cfd_fluidx3d_run` | MUTATING | Execute FluidX3D simulation on GPU via OpenCL |
| `cfd_fluidx3d_results` | READ_ONLY | Parse forces, MLUPS throughput, completion status |
| `cfd_fluidx3d_explain` | READ_ONLY | Explain flow physics: Reynolds number, regime, solver notes |

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

---

## BIM/Arch Tools

All 9 BIM tools live in `src/freecad_mcp/tools/bim.py` and are registered on the FastMCP instance via `register_bim_tools()`. They wrap FreeCAD's Arch workbench (Draft, Arch, Part modules) for parametric building element creation and IFC exchange.

All dimensions in millimetres. Output files are FreeCAD `.fcstd` documents saved to the outputs directory.

### bim_status

Check BIM/Arch workbench availability.

```python
await bim_status()
# {"success": true, "bim_available": true, "bridge_mode": "tcp", "workbench": "Arch (BIM)"}
```

BIM tools require the FreeCAD bridge (TCP mode) or subprocess mode. Use `freecad_status` first.

---

### bim_create_wall

Create a parametric architectural wall via `Arch.makeWall()`.

```python
# Standard interior wall
await bim_create_wall(length_mm=6000, width_mm=240, height_mm=3000, output_name="exterior_wall.fcstd")
# {"success": true, "output": "exterior_wall.fcstd", "data": {"label": "Wall", "length": 6000, "width": 240, "height": 3000, "path": "..."}}

# Rotated wall at specific position
await bim_create_wall(length_mm=3000, width_mm=120, height_mm=2600, placement_x=5000, rotation_z=90)
```

Parameters: `length_mm`, `width_mm` (thickness), `height_mm`, `placement_x/y/z`, `rotation_z` (degrees), `output_name`.

---

### bim_create_slab

Create a floor slab as a structural BIM element.

```python
# Ground floor slab
await bim_create_slab(width_mm=6000, length_mm=8000, thickness_mm=250, output_name="ground_floor.fcstd")
# {"success": true, "output": "ground_floor.fcstd", "data": {"label": "Slab", "width": 6000, "length": 8000, "thickness": 250, "path": "..."}}
```

Parameters: `width_mm` (X-axis), `length_mm` (Y-axis), `thickness_mm`, `placement_x/y/z`, `output_name`.

---

### bim_create_column

Create a structural column with selectable profile.

```python
# Rectangular column
await bim_create_column(profile_type="rectangular", width_mm=300, depth_mm=300, height_mm=3500)

# Circular column
await bim_create_column(profile_type="circular", width_mm=400, depth_mm=400, height_mm=4000, placement_x=6000)
```

Profile types: `rectangular`, `circular`, `h_section`. Parameters: `profile_type`, `width_mm`, `depth_mm`, `height_mm`, `placement_x/y/z`, `output_name`.

---

### bim_create_window

Create a window hosted in an auto-generated wall.

```python
# Casement window
await bim_create_window(window_type="casement", width_mm=1200, height_mm=1500, sill_height_mm=850)

# Sliding window at offset position
await bim_create_window(window_type="sliding", width_mm=2000, height_mm=1200, placement_x=3000)
```

Window types: `fixed`, `casement`, `sliding`, `awning`. Parameters: `window_type`, `width_mm`, `height_mm`, `sill_height_mm`, `placement_x/y/z`, `rotation_z`, `output_name`.

A hosting wall is auto-generated to hold the window. The window auto-cuts its opening.

---

### bim_create_door

Create a door hosted in an auto-generated wall.

```python
# Simple interior door
await bim_create_door(door_type="simple", width_mm=900, height_mm=2100)

# Glass door
await bim_create_door(door_type="glass", width_mm=1000, height_mm=2200, placement_x=5000, rotation_z=90)
```

Door types: `simple`, `glass`, `sliding_glass`. Parameters: `door_type`, `width_mm`, `height_mm`, `placement_x/y/z`, `rotation_z`, `output_name`.

A hosting wall is auto-generated. The door auto-cuts its opening.

---

### bim_create_roof

Create a sloped or flat roof.

```python
# Pitched roof (30 degrees)
await bim_create_roof(width_mm=8000, length_mm=10000, angle_deg=30, thickness_mm=120)

# Flat roof
await bim_create_roof(width_mm=6000, length_mm=6000, angle_deg=0, placement_z=3000, output_name="flat_roof.fcstd")
```

Parameters: `width_mm` (span direction), `length_mm` (ridge direction), `angle_deg` (0 = flat, max 75), `thickness_mm`, `placement_x/y/z`, `output_name`.

---

### bim_export_ifc

Export a FreeCAD `.fcstd` document to IFC (Industry Foundation Classes) format.

```python
await bim_export_ifc(file_name="my_building.fcstd", output_name="my_building.ifc")
# {"success": true, "output": "my_building.ifc", "data": {"path": "...", "size_kb": 45.2, "objects": 12}}
```

The source `.fcstd` must be in the uploads or outputs directory. IFC files contain parametric BIM data (material, type, relationships) intact.

---

### bim_import_ifc

Import an IFC file from an architect and convert to FreeCAD `.fcstd` format.

```python
await bim_import_ifc(file_name="architect_model.ifc", output_name="imported_building.fcstd")
# {"success": true, "output": "imported_building.fcstd", "data": {"path": "...", "objects": 47, "object_names": [...]}}
```

Supports IFC files containing walls, slabs, columns, windows, doors, and other BIM elements. Auto-detects IFC format via FreeCAD's `Import.insert()`.

```python
await show_marketplace_card(source="printables", query="robot chassis")
await show_marketplace_card(source="thingiverse", query="gear", category="Tools")
```

Shows up to 6 results with thumbnails, stats, and marketplace links. Renders as an interactive card in the chat rather than raw JSON.

---

## CFD / OpenFOAM Tools

All 10 CFD tools live in `src/freecad_mcp/tools/cfd.py` and wrap the FreeCAD → OpenFOAM geometry-mesh-simulation-analysis pipeline. They require Docker with the OpenFOAM image for execution, but can generate ready-to-run case directories without Docker.

### cfd_status

Check Docker, OpenFOAM image, and FreeCAD bridge availability.

```python
await cfd_status()
# {"success": true, "docker_available": true, "docker_exe": "docker", "openfoam_image": true, "bridge_mode": "tcp", "cfd_case_dir": "..."}
```

---

### cfd_create_domain

Create a parametric fluid domain geometry in FreeCAD and generate an OpenFOAM case skeleton with blockMeshDict.

```python
# Rectangular channel
await cfd_create_domain(domain_type="channel", length_m=1.0, width_m=0.1, height_m=0.05, mesh_cells=20000, case_name="channel_flow")

# Cylindrical pipe
await cfd_create_domain(domain_type="pipe", length_m=0.5, inlet_radius_m=0.02, mesh_cells=50000, case_name="pipe_study")

# Custom STEP geometry
await cfd_create_domain(domain_type="custom", step_file="my_valve.step", mesh_cells=100000, case_name="valve_cfd")
```

Domain types: `channel`, `pipe`, `box`, `nozzle`, `custom`. Output: STEP file + `constant/polyMesh/blockMeshDict`.

---

### cfd_configure_physics

Generate OpenFOAM physics dictionaries: controlDict, fvSchemes, fvSolution, transportProperties, turbulenceProperties.

```python
# Laminar water flow
await cfd_configure_physics(case_name="channel_flow", solver="simpleFoam", flow_type="laminar", fluid_nu=1e-6, inlet_velocity=0.1)

# Turbulent air flow (kOmegaSST)
await cfd_configure_physics(case_name="pipe_study", solver="simpleFoam", flow_type="kOmegaSST", fluid_nu=1.5e-5, fluid_density=1.225, inlet_velocity=10.0)
```

Solvers: `simpleFoam`, `pisoFoam`, `pimpleFoam`. Flow types: `laminar`, `kEpsilon`, `kOmegaSST`.

---

### cfd_set_boundary

Configure per-patch field boundary conditions (U, p, k, omega, nut).

```python
# Inlet velocity
await cfd_set_boundary(case_name="pipe_study", patch_name="inlet", field_name="U", bc_type="fixedValue", value="uniform (1 0 0)")

# Outlet pressure
await cfd_set_boundary(case_name="pipe_study", patch_name="outlet", field_name="p", bc_type="fixedValue", value="uniform 0")

# No-slip walls
await cfd_set_boundary(case_name="pipe_study", patch_name="walls", field_name="U", bc_type="noSlip", value="uniform (0 0 0)")
```

---

### cfd_build_case

Validate that all required OpenFOAM files are present.

```python
await cfd_build_case(case_name="pipe_study")
# {"success": true, "data": {"files": [...], "missing": [...], "ready": true}}
```

---

### cfd_run_solver

Execute OpenFOAM solver steps inside a Docker container.

```python
# Standard run
await cfd_run_solver(case_name="pipe_study")

# Custom steps
await cfd_run_solver(case_name="pipe_study", steps="blockMesh,simpleFoam")

# Parallel execution
await cfd_run_solver(case_name="large_case", steps="blockMesh,decomposePar,simpleFoam,reconstructPar", parallel=True, n_cores=8)
```

Requires: `docker pull openfoam/openfoam10-paraview56`

---

### cfd_read_results

Parse simulation results: time directories, forces, residuals, convergence check.

```python
await cfd_read_results(case_name="pipe_study")
# {"success": true, "data": {"times": ["0", "100", "200"], "forces": {...}, "final_residuals": {"p": 3.2e-6, "Ux": 8.1e-7}, "converged": true}}
```

---

### cfd_parametric_study

Run a parameter sweep varying one design variable across multiple cases.

```python
# Velocity sweep (generate only)
await cfd_parametric_study(case_name="pipe_base", parameter="inlet_velocity", values="[0.5, 1.0, 2.0, 5.0]", run=False)

# Geometry sweep with execution
await cfd_parametric_study(case_name="nozzle_base", parameter="length", values="[0.3, 0.5, 0.8]", run=True)
```

Useful for design optimization and generating training datasets for ML surrogate models.

---

### cfd_nl2foam

Convert a natural language fluid dynamics description into an executable OpenFOAM case using the configured Ollama LLM.

```python
# Laminar pipe flow
await cfd_nl2foam(description="Laminar pipe flow, Re=500, D=0.1m, L=1m, inlet velocity 0.005 m/s", case_name="pipe_nl")

# Turbulent airfoil
await cfd_nl2foam(description="Turbulent air flow over NACA 0012 at 10 deg AoA, Re=1e6, standard air")
```

The LLM outputs structured JSON validated against OpenFOAM conventions.

---

### cfd_sample_for_pinns

Export coordinate point clouds from CFD domain geometry for PINN/GNN training (NVIDIA Modulus, PyTorch Geometric, DeepXDE).

```python
# CSV export
await cfd_sample_for_pinns(case_name="pipe_study", n_boundary=5000, n_interior=20000)

# NumPy export for ML frameworks
await cfd_sample_for_pinns(case_name="airfoil_cfd", n_boundary=10000, n_interior=50000, output_format="numpy")
```

Output: CSV/JSON/NPZ with columns x, y, z, region (boundary/interior).

---

## FEM / Structural Analysis Tools

All 8 FEM tools live in `src/freecad_mcp/tools/fem.py` and provide a complete structural FEA pipeline: create analysis container → set material properties → apply boundary conditions → generate mesh → solve with CalculiX → read results. A convenience `run_fem_analysis` tool chains the entire pipeline automatically.

Requires: FreeCAD FEM workbench + CalculiX ccx solver (bundled with FreeCAD on Windows).

### fem_status

Check FEM workbench and CalculiX solver availability.

```python
await fem_status()
# {"success": true, "fem_available": true, "bridge_mode": "tcp", "solver": "CalculiX (ccx)"}
```

---

### fem_create_analysis

Create a structural analysis container on a 3D model (STEP/FCStd).

```python
await fem_create_analysis(file_name="beam.step", analysis_name="BeamStatic")
# {"success": true, "output": "beam_fem.fcstd", "data": {"analysis_name": "BeamStatic", "objects": [...]}}
```

Sets up `FemAnalysis` container + `FemSolverCalculixCxxtools` solver with working directory in `fem_output/`.

---

### fem_set_material

Assign material properties to the FEM analysis. 10 built-in presets.

```python
# Structural steel (default)
await fem_set_material(file_name="beam_fem.fcstd", material="steel")

# Aluminum with custom elastic modulus
await fem_set_material(file_name="bracket_fem.fcstd", material="aluminum", E_mpa=69000)

# Custom material with full overrides
await fem_set_material(file_name="beam_fem.fcstd", material="steel", E_mpa=200000, nu=0.28, density_kgm3=7850, yield_mpa=350)
```

| Material | E (MPa) | nu | Density (kg/m³) | Yield (MPa) |
|:---|:---|:---|:---|:---|
| steel | 210,000 | 0.30 | 7,800 | 250 |
| stainless | 193,000 | 0.29 | 8,000 | 275 |
| aluminum | 70,000 | 0.33 | 2,700 | 240 |
| titanium | 110,000 | 0.34 | 4,420 | 880 |
| concrete | 25,000 | 0.20 | 2,400 | 30 |
| wood | 12,000 | 0.35 | 600 | 40 |
| brass | 100,000 | 0.35 | 8,500 | 200 |
| copper | 117,000 | 0.36 | 8,960 | 210 |
| nylon | 3,000 | 0.39 | 1,150 | 75 |
| carbon_fiber | 150,000 | 0.30 | 1,600 | 800 |

---

### fem_set_constraint

Apply boundary conditions: fixed supports, force loads, pressure loads.

```python
# Cantilever: fixed at one end, force on the other
await fem_set_constraint(file_name="beam_fem.fcstd", constraints=[
    {"type": "fixed", "face_name": "Face1"},
    {"type": "force", "face_name": "Face6", "fy": -5000},
])

# Pressure vessel: internal pressure
await fem_set_constraint(file_name="tank_fem.fcstd", constraints=[
    {"type": "fixed", "face_name": "Face2"},
    {"type": "pressure", "face_name": "Face3", "value": 2.5},
])
```

Constraint types: `fixed` (clamped), `force` (fx/fy/fz in N), `pressure` (value in MPa). Face names follow FreeCAD convention (Face1, Face2, etc.). Constraints are automatically linked to the analysis container.

---

### fem_mesh

Generate a finite element mesh using Gmsh. Supports first-order (tetra4) and second-order (tetra10) elements.

```python
# Default mesh (50mm elements, second-order)
await fem_mesh(file_name="beam_fem.fcstd")

# Fine mesh for bending analysis
await fem_mesh(file_name="beam_fem.fcstd", max_size_mm=10, min_size_mm=2, second_order=True)
# {"success": true, "data": {"nodes": 15234, "elements": 8912, "element_size_mm": 10.0, "element_order": 2}}
```

Second-order elements (tetra10) strongly recommended for bending-dominated problems — they avoid shear locking that plagues linear tets. The mesh is automatically linked to the analysis container.

---

### fem_run

Write the CalculiX input file (.inp) and execute the ccx solver.

```python
# Standard solve (5 min timeout)
await fem_run(file_name="beam_fem.fcstd")

# Large model with extended timeout
await fem_run(file_name="large_assembly_fem.fcstd", timeout_s=1200)
# {"success": true, "data": {"solver": "CalculiX ccx", "exit_code": 0, "result_files": ["beam_fem.frd", "beam_fem.dat", "beam_fem.inp"]}}
```

Requires all previous steps (analysis, material, constraints, mesh). Generates .frd (result) and .dat (log) files in `fem_output/`.

---

### fem_read_results

Parse CalculiX result files to extract key metrics.

```python
await fem_read_results(file_name="beam_fem.fcstd")
# {"success": true, "data": {
#   "max_von_mises_MPa": 187.3,
#   "max_displacement_mm": 2.45,
#   "max_principal_MPa": 201.1,
#   "min_principal_MPa": -15.2,
#   "nodes": 15234
# }}
```

Parses the .frd binary result file for von Mises stress, displacement magnitude, and principal stresses. Reads the full file (not truncated).

---

### run_fem_analysis

End-to-end convenience tool. Chains the entire pipeline and returns actionable results with safety factor.

```python
# Cantilever beam: steel, 5000N tip load
await run_fem_analysis(
    file_name="beam.step",
    material="steel",
    constraints=[
        {"type": "fixed", "face_name": "Face1"},
        {"type": "force", "face_name": "Face6", "fy": -5000},
    ],
    mesh_size_mm=10,
)

# Shorthand: just constrain one face, force on opposite face
await run_fem_analysis(
    file_name="bracket.step",
    material="aluminum",
    force_N=2000,
    mesh_size_mm=5,
)
# {"success": true,
#  "message": "FEM complete. Max von Mises stress: 145.30 MPa (yield: 240 MPa, safety factor: 1.65). Max displacement: 0.8912 mm. Mesh: 28450 nodes, 15200 elements.",
#  "data": {"max_von_mises_MPa": 145.3, "max_displacement_mm": 0.8912, "yield_MPa": 240, "safety_factor": 1.65, ...}}
```

This mirrors neka-nat/freecad-mcp's `run_fem_analysis` with added material presets, safety factor calculation, and mesh statistics. The `force_N` shorthand auto-applies a fixed constraint on Face1 and a downward (-Y) force on Face6.

---

## FluidX3D GPU CFD Tools

All 6 FluidX3D tools live in `src/freecad_mcp/tools/fluidx3d.py` and provide native GPU CFD via ProjectPhysX/FluidX3D (OpenCL — all GPU vendors). Generate C++, compile via g++/MSVC, run on GPU, parse forces/throughput.

Requires: `git clone https://github.com/ProjectPhysX/FluidX3D.git` + a C++ compiler.

### cfd_fluidx3d_status

Check FluidX3D installation and compiler availability.

```python
await cfd_fluidx3d_status()
# {"success": true, "fluidx3d_path": "D:/Dev/repos/FluidX3D", "compiler": "g++", "ready": true}
```

---

### cfd_fluidx3d_setup

Generate a C++ setup.cpp and defines.hpp for GPU simulation. Domain types: channel, pipe, box, stl.

```python
# Channel flow — 512×128×128 grid, water at Re=10000
await cfd_fluidx3d_setup(
    case_name="channel_gpu",
    domain_type="channel",
    resolution_x=512, resolution_y=128, resolution_z=128,
    length_m=1.0, velocity_ms=0.01, viscosity_m2s=1e-6,
    time_steps=50000
)

# STL geometry import
await cfd_fluidx3d_setup(
    case_name="airfoil_gpu",
    domain_type="stl", stl_file="naca0012.stl",
    resolution_x=768, resolution_y=256, resolution_z=256,
    time_steps=100000
)
```

---

### cfd_fluidx3d_compile

Compile the generated setup.cpp into a GPU executable. Copies into FluidX3D source tree, runs g++ or MSVC.

```python
await cfd_fluidx3d_compile(case_name="channel_gpu")
# {"success": true, "data": {"binary": ".../bin/fluidx3d_channel_gpu.exe", "compile_time_s": 4.2}}
```

---

### cfd_fluidx3d_run

Execute the compiled binary on the GPU via OpenCL. Captures stdout for force/residual parsing.

```python
# Run on fastest GPU (device 0)
await cfd_fluidx3d_run(case_name="channel_gpu")

# Select specific GPU
await cfd_fluidx3d_run(case_name="channel_gpu", gpu_device=1, timeout_s=7200)
```

VTK output files are written for ParaView post-processing.

---

### cfd_fluidx3d_results

Parse simulation results: forces history, final forces, MLUPS throughput, completion status.

```python
await cfd_fluidx3d_results(case_name="channel_gpu")
# {"success": true, "data": {"forces": [...], "mlups": 234.5, "completed": true, "time_steps_completed": 50000}}
```

---

### cfd_fluidx3d_explain

Explain the flow physics: Reynolds number, regime (creeping/laminar/transitional/turbulent), expected behaviour, solver notes.

```python
await cfd_fluidx3d_explain(case_name="channel_gpu")
# {"success": true, "data": {"Re": 10000.0, "regime": "turbulent...", "summary": "..."}}  ```
