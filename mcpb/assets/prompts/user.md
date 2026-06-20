# freecad-mcp — User Guide

FreeCAD MCP exposes FreeCAD 3D modeling, architecture/BIM design, CFD fluid simulation (OpenFOAM CPU + FluidX3D GPU), FEM structural analysis, and 3D printing workflows through 38+ MCP tools. The server runs FreeCAD as a headless geometry engine via TCP bridge (FreeCAD.exe + fc_bridge.py on port 10946) with subprocess fallback (FreeCADCmd.exe).

## Quick Start

### Prerequisites

| Component | Required | Purpose |
|-----------|----------|---------|
| FreeCAD 1.1.1+ | Yes | CAD kernel for all geometry operations |
| Python 3.12+ + uv | Yes | FastMCP server runtime |
| Node.js 18+ | Yes | Vite web dashboard (port 10945) |
| Docker Desktop | For OpenFOAM | Container runtime for CPU CFD |
| FluidX3D + g++ | For GPU CFD | OpenCL Lattice-Boltzmann solver |
| PrusaSlicer 2.8+ | For 3D printing | G-code generation from STL |

### Install FreeCAD

Download from [FreeCAD 1.1.1+ releases](https://github.com/FreeCAD/FreeCAD/releases). Set the path:

```powershell
$env:FREECAD_PATH = "D:\Dev\repos\FreeCAD\FreeCAD_1.1.1-Windows-x86_64-py311\bin\FreeCAD.exe"
```

Verify:
```powershell
& "$env:FREECAD_PATH" --version
```

### Install Python Dependencies

```powershell
uv sync --all-extras
```

### Install Docker (OpenFOAM)

```powershell
docker pull openfoam/openfoam10-paraview56
```

### Install FluidX3D (GPU CFD)

```powershell
git clone https://github.com/ProjectPhysX/FluidX3D.git D:\Dev\repos\FluidX3D
```

### Start the Server

```powershell
start.ps1
```

Or separately:
```powershell
just serve     # backend on 10944
just web       # frontend on 10945
just stdio     # MCP stdio mode (no webapp)
```

### Configure MCP Client (Cursor / Claude Desktop)

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

### Verify Installation

```python
await freecad_status()
# {"success": true, "freecad_ok": true, "version": "FreeCAD 1.1.1 ..."}

await cfd_status()
# {"success": true, "docker_available": true, "openfoam_image": true}

await cfd_fluidx3d_status()
# {"success": true, "fluidx3d_path": "D:/Dev/repos/FluidX3D", "compiler": "g++", "ready": true}
```

### Port Layout

| Port | Service |
|------|---------|
| 10944 | FastAPI + FastMCP SSE / REST API |
| 10945 | Vite web dashboard |
| 10946 | FreeCAD TCP Bridge (fc_bridge.py) |

---

## Tutorial 1: Convert a STEP File to STL for 3D Printing

Upload a STEP assembly and produce an STL mesh ready for slicing or printing.

```python
# Step 1: Upload the STEP file
# POST /api/v1/upload with multipart file "raspbot_v2_step.STEP"

# Step 2: Check FreeCAD is available
await freecad_status()
# {"success": true, "freecad_ok": true, "version": "FreeCAD 1.1.1 ..."}

# Step 3: Convert STEP to STL
await step_to_stl(file_name="raspbot_v2_step.STEP", output_name="boomy.stl")
# {"success": true, "output": "boomy.stl", "data": {"objects": 42, "size_kb": 1532.4}}

# Step 4: Inspect the resulting mesh
await model_info(file_name="boomy.stl")
# {"success": true, "data": {"type": "mesh", "vertices": 123456, "facets": 41152}}

# Step 5: Check PrusaSlicer is available
await slicer_status()
# {"success": true, "available": true, "version": "PrusaSlicer-2.8.1+win64"}

# Step 6: Slice to G-code
await slice_stl(file_name="boomy.stl", printer_profile="Prusa MK4", filament_profile="PLA", quality="0.20mm SPEED")
# The G-code is downloadable from GET /api/v1/download/boomy.gcode
```

The STL is served from `GET /api/v1/download/boomy.stl` and the G-code from `GET /api/v1/download/boomy.gcode`.

---

## Tutorial 2: Design a Room with Walls and a Window

Create a parametric BIM room by placing walls and a window with a single tool call.

```python
# Step 1: Check BIM availability
await bim_status()
# {"success": true, "bim_available": true, "bridge_mode": "tcp", "workbench": "Arch (BIM)"}

# Step 2: Create a 6m exterior wall
await bim_create_wall(
    length_mm=6000, width_mm=240, height_mm=3000,
    placement_x=0, placement_y=0, placement_z=0,
    output_name="exterior_wall.fcstd"
)
# {"success": true, "output": "exterior_wall.fcstd", "data": {"label": "Wall", "length": 6000, "width": 240, "height": 3000}}

# Step 3: Add a casement window in the wall
# The window auto-generates its hosting wall and cuts the opening
await bim_create_window(
    window_type="casement", width_mm=1200, height_mm=1500,
    sill_height_mm=850, placement_x=2000, output_name="room_window.fcstd"
)
# {"success": true, "output": "room_window.fcstd", "data": {"label": "Window", "width": 1200, "height": 1500}}

# Step 4: Add a door on the opposite wall
await bim_create_door(
    door_type="simple", width_mm=900, height_mm=2100,
    placement_x=4000, rotation_z=90, output_name="room_door.fcstd"
)

# Step 5: Export the building to IFC format
await bim_export_ifc(file_name="room_window.fcstd", output_name="room_building.ifc")
# {"success": true, "output": "room_building.ifc", "data": {"path": "...", "size_kb": 12.3, "objects": 3}}
```

---

## Tutorial 3: Run a Laminar Pipe Flow Simulation (OpenFOAM)

Complete end-to-end CFD simulation of laminar water flow through a pipe.

```python
# Step 1: Check the CFD pipeline
await cfd_status()
# {"success": true, "docker_available": true, "openfoam_image": true, "bridge_mode": "tcp"}

# Step 2: Create a pipe domain (0.5m long, 20mm radius, 50k cells)
await cfd_create_domain(
    domain_type="pipe",
    length_m=0.5, inlet_radius_m=0.02,
    mesh_cells=50000,
    case_name="pipe_study"
)
# {"success": true, "case_name": "pipe_study", "data": {"domain_type": "pipe", "dimensions_m": [0.5, 0.04, 0.04], "mesh_cells": 48000}}

# Step 3: Configure physics (water, laminar, Re=100)
await cfd_configure_physics(
    case_name="pipe_study",
    solver="simpleFoam",
    flow_type="laminar",
    fluid_nu=1e-6, fluid_density=1000,
    inlet_velocity=0.005,  # Re = U*D/nu = 0.005*0.04/1e-6 = 200
    end_time=2000
)
# {"success": true, "case_name": "pipe_study", "data": {"solver": "simpleFoam", "flow_type": "laminar", "Re_estimate": 200.0}}

# Step 4: Set boundary conditions
await cfd_set_boundary(case_name="pipe_study", patch_name="inlet", field_name="U", bc_type="fixedValue", value="uniform (0.005 0 0)")
await cfd_set_boundary(case_name="pipe_study", patch_name="outlet", field_name="p", bc_type="fixedValue", value="uniform 0")
await cfd_set_boundary(case_name="pipe_study", patch_name="walls", field_name="U", bc_type="noSlip", value="uniform (0 0 0)")

# Step 5: Validate case completeness
await cfd_build_case(case_name="pipe_study")
# {"success": true, "data": {"files": [...], "missing": [], "ready": true}}

# Step 6: Run the solver
await cfd_run_solver(case_name="pipe_study", steps="blockMesh,checkMesh,simpleFoam")
# {"success": true, "data": {"steps_completed": ["blockMesh", "checkMesh", "simpleFoam"], "exit_codes": {...}}}

# Step 7: Read results
await cfd_read_results(case_name="pipe_study")
# {"success": true, "data": {"times": ["0", "100", "200"], "forces": {...}, "final_residuals": {"p": 3.2e-6, "Ux": 8.1e-7}, "converged": true}}
```

---

## Tutorial 4: Describe a CFD Problem and Get an OpenFOAM Config (NL2FOAM)

Use natural language to describe a fluid dynamics problem and have the LLM generate the full OpenFOAM case configuration.

```python
# Using Ollama (default, local LLM)
await cfd_nl2foam(
    description="Incompressible laminar flow through a 1m long, 0.1m diameter pipe at Re=500. Water at 20C. Inlet velocity 0.005 m/s. Calculate pressure drop.",
    case_name="pipe_nl_500",
    model="gemma3:1b"
)
# {"success": true, "case_name": "pipe_nl_500",
#  "data": {"solver": "simpleFoam", "flow_type": "laminar",
#           "mesh": {"nx": 100, "ny": 20, "nz": 20},
#           "bc": {"inlet": {"velocity": [0.005, 0, 0]}, ...},
#           "reasoning": "Laminar pipe flow at Re=500 ..."}}

# Turbulent airfoil with more detail
await cfd_nl2foam(
    description="Turbulent air flow over NACA 0012 at 10 degrees angle of attack, chord 0.5m, Re=1e6, standard air at sea level. kOmegaSST model. Calculate lift and drag coefficients.",
    case_name="naca0012_nl",
    model="gemma3:1b"
)

# Natural convection in a cavity
await cfd_nl2foam(
    description="Natural convection in a 0.5m x 0.5m square cavity. Left wall at 310K, right wall at 290K, top and bottom adiabatic. Air, Ra=1e6. Steady-state laminar.",
    case_name="cavity_nl"
)
```

The LLM generates blockMeshDict, boundary conditions, physics models, and solver settings as structured JSON. The case is then created by calling `cfd_create_domain` and `cfd_configure_physics` internally.

---

## Tutorial 5: Run a GPU-Accelerated Channel Flow (FluidX3D)

Use the RTX 4090 (or any GPU via OpenCL) for native Lattice-Boltzmann CFD at hundreds of millions of cells.

```python
# Step 1: Check FluidX3D and compiler availability
await cfd_fluidx3d_status()
# {"success": true, "fluidx3d_path": "D:/Dev/repos/FluidX3D", "compiler": "g++", "ready": true}

# Step 2: Check for pre-built binary (skip compile)
await cfd_fluidx3d_prebuilt()
# {"success": true, "prebuilt_path": "D:/Dev/.../fluidx3d-runner.exe"}

# Step 3: Generate the setup (512x128x128 grid, water, Re=10000)
await cfd_fluidx3d_setup(
    case_name="channel_gpu",
    domain_type="channel",
    resolution_x=512, resolution_y=128, resolution_z=128,
    length_m=1.0, velocity_ms=0.01, viscosity_m2s=1e-6,
    density_kgm3=1000,
    time_steps=50000, write_interval=1000
)
# {"success": true, "case_name": "channel_gpu", "data": {"setup_file": "...", "resolution": "512x128x128", "cells": 8388608}}

# Step 4: Compile (if no pre-built binary)
await cfd_fluidx3d_compile(case_name="channel_gpu")
# {"success": true, "data": {"binary": "...", "compile_time_s": 4.2}}

# Step 5: Run on GPU
await cfd_fluidx3d_run(case_name="channel_gpu", gpu_device="0", timeout_s=3600)
# {"success": true, "case_name": "channel_gpu", "data": {"exit_code": 0, "runtime_s": 234.5, "vtk_files": [...]}}

# Step 6: Read forces and throughput
await cfd_fluidx3d_results(case_name="channel_gpu")
# {"success": true, "data": {"forces": [...], "mlups": 234.5, "completed": true, "time_steps_completed": 50000}}
```

On an RTX 4090 (24 GB VRAM), a 512x128x128 grid runs at ~200 time steps per second with ~134 million cells.

---

## Tutorial 6: Search and Import a Model from Printables

Find CAD models from community repositories and bring them into FreeCAD.

```python
# Step 1: Search Printables for robot chassis models
await marketplace_search(source="printables", query="robot chassis")
# {"success": true, "source": "printables", "total": 230, "results": [
#   {"id": "123456", "title": "Robot Chassis v2", "author": "maker42",
#    "downloads": 1520, "likes": 87, "image_url": "...", ...}
# ]}

# Step 2: Search Thingiverse with category filter
await marketplace_search(source="thingiverse", query="gear", category="Tools")
# {"success": true, "source": "thingiverse", "results": [...]}

# Step 3: List available categories first
await marketplace_categories(source="printables")
# {"success": true, "source": "printables", "categories": [{"id": "3D-Printing", "label": "3D Printing"}, ...]}

# Step 4: Download the model
await marketplace_download(
    source="printables",
    model_id="123456",
    file_url="https://www.printables.com/model/123456/download",
    filename="chassis.stl"
)
# {"success": true, "filename": "chassis.stl", "size_bytes": 2456789, "extracted": null}

# Step 5: Inspect the downloaded model
await model_info(file_name="chassis.stl")
# For Thingiverse ZIP files, STL/STEP files are auto-extracted

# Step 6: Slice and print
await slice_stl(file_name="chassis.stl", quality="0.15mm QUALITY", output_name="chassis.gcode")
```

Sources supported: Printables (GraphQL, no auth), Thingiverse (REST, ZIP auto-extract), GrabCAD (REST, engineering parts).

---

## Tutorial 7: Generate Training Data for a Neural Network (PINN)

Export point clouds from CFD domain geometry for Physics-Informed Neural Network training with frameworks like NVIDIA Modulus, DeepXDE, or PyTorch Geometric.

```python
# Step 1: Create a pipe flow domain (must exist first)
await cfd_create_domain(
    domain_type="pipe", length_m=0.5, inlet_radius_m=0.02,
    mesh_cells=50000, case_name="pinn_pipe"
)

# Step 2: Configure physics
await cfd_configure_physics(
    case_name="pinn_pipe", flow_type="laminar",
    fluid_nu=1e-6, inlet_velocity=0.005
)
await cfd_set_boundary(case_name="pinn_pipe", patch_name="inlet", field_name="U", bc_type="fixedValue", value="uniform (0.005 0 0)")
await cfd_set_boundary(case_name="pinn_pipe", patch_name="outlet", field_name="p", bc_type="fixedValue", value="uniform 0")
await cfd_set_boundary(case_name="pinn_pipe", patch_name="walls", field_name="U", bc_type="noSlip", value="uniform (0 0 0)")

# Step 3: Sample point clouds for PINN training
await cfd_sample_for_pinns(
    case_name="pinn_pipe",
    n_boundary=5000,
    n_interior=20000,
    output_format="csv"
)
# {"success": true, "case_name": "pinn_pipe", "data": {"n_boundary": 4998, "n_interior": 20000, "output_file": "...", "format": "csv"}}

# Step 4: Export as NumPy for PyTorch/TensorFlow
await cfd_sample_for_pinns(
    case_name="pinn_pipe",
    n_boundary=10000,
    n_interior=50000,
    output_format="numpy"
)
# Output pinn_points.npz with keys: coords (float32), regions (int8)
```

The CSV file has columns x, y, z, region. The NPZ file has arrays coords (Nx3 float32) and regions (Nx int8: 0=interior, 1=boundary).

---

## Tutorial 8: Parametric Sweep Across Reynolds Numbers

Run a design-of-experiments parametric sweep to study how flow changes with velocity.

```python
# Step 1: Create base pipe case
await cfd_create_domain(
    domain_type="pipe", length_m=2.0, inlet_radius_m=0.05,
    mesh_cells=150000, case_name="reynolds_sweep"
)

# Step 2: Configure turbulent physics (air, kOmegaSST)
await cfd_configure_physics(
    case_name="reynolds_sweep",
    solver="simpleFoam", flow_type="kOmegaSST",
    fluid_nu=1.5e-5, fluid_density=1.225,
    inlet_velocity=3.0,  # Re = U*D/nu = 3*0.1/1.5e-5 = 20000
    end_time=3000
)

# Step 3: Set boundary conditions
await cfd_set_boundary(case_name="reynolds_sweep", patch_name="inlet", field_name="U", bc_type="fixedValue", value="uniform (3 0 0)")
await cfd_set_boundary(case_name="reynolds_sweep", patch_name="inlet", field_name="k", bc_type="fixedValue", value="uniform 0.03375")
await cfd_set_boundary(case_name="reynolds_sweep", patch_name="inlet", field_name="omega", bc_type="fixedValue", value="uniform 14.6")
await cfd_set_boundary(case_name="reynolds_sweep", patch_name="outlet", field_name="p", bc_type="fixedValue", value="uniform 0")
await cfd_set_boundary(case_name="reynolds_sweep", patch_name="walls", field_name="U", bc_type="noSlip", value="uniform (0 0 0)")

# Step 4: Sweep 5 velocities (Re = 5000 to 80000)
await cfd_parametric_study(
    case_name="reynolds_sweep",
    parameter="inlet_velocity",
    values="[0.75, 1.5, 3.0, 6.0, 12.0]",
    run=True
)
# Creates cases: reynolds_sweep_0, reynolds_sweep_1, ... reynolds_sweep_4

# Step 5: Collect results from each variant
results = []
for i in range(5):
    result = await cfd_read_results(case_name=f"reynolds_sweep_{i}")
    results.append(result["data"])
# Compare pressure drop vs Reynolds number
```

Other sweeps: geometry (length, width, height), fluid properties (fluid_nu), angle of attack.

---

## Tutorial 9: Export a Building Model to IFC

Create a complete BIM building with walls, slab, roof and export to IFC for exchange with architects.

```python
# Step 1: Create the ground floor slab
await bim_create_slab(
    width_mm=8000, length_mm=10000, thickness_mm=250,
    placement_z=0,
    output_name="ground_slab.fcstd"
)

# Step 2: Create four exterior walls
await bim_create_wall(length_mm=8000, width_mm=240, height_mm=3000, rotation_z=0, output_name="wall_north.fcstd")
await bim_create_wall(length_mm=10000, width_mm=240, height_mm=3000, placement_x=8000, rotation_z=90, output_name="wall_east.fcstd")
await bim_create_wall(length_mm=8000, width_mm=240, height_mm=3000, placement_x=8000, placement_y=10000, rotation_z=180, output_name="wall_south.fcstd")
await bim_create_wall(length_mm=10000, width_mm=240, height_mm=3000, placement_y=10000, rotation_z=270, output_name="wall_west.fcstd")

# Step 3: Add columns at corners
await bim_create_column(profile_type="rectangular", width_mm=300, depth_mm=300, height_mm=3000, output_name="column_corner1.fcstd")
await bim_create_column(profile_type="circular", width_mm=400, depth_mm=400, height_mm=3000, placement_x=8000, output_name="column_corner2.fcstd")

# Step 4: Add windows
await bim_create_window(window_type="casement", width_mm=1200, height_mm=1500, sill_height_mm=850, output_name="window1.fcstd")
await bim_create_window(window_type="sliding", width_mm=2000, height_mm=1200, placement_x=3000, output_name="window2.fcstd")

# Step 5: Create the roof
await bim_create_roof(
    width_mm=8500, length_mm=10500, angle_deg=30, thickness_mm=120,
    placement_z=3000,
    output_name="roof.fcstd"
)

# Step 6: Export everything to IFC
# Note: IFC export requires a single FCStd file containing all elements.
# To combine, reopen and save the building model as a single file first.
await bim_export_ifc(file_name="building.fcstd", output_name="building.ifc")
# {"success": true, "output": "building.ifc", "data": {"path": "...", "size_kb": 85.2, "objects": 12}}
```

IFC (Industry Foundation Classes) is the open BIM exchange standard. The exported .ifc file contains parametric building elements with material, type, and relationship data.

---

## Tutorial 10: Explain Flow Physics from Simulation Data

Interpret the flow physics from completed FluidX3D simulation results without opening ParaView.

```python
# Step 1: Set up and run a simulation first
await cfd_fluidx3d_setup(
    case_name="physics_explain",
    domain_type="channel",
    resolution_x=256, resolution_y=64, resolution_z=64,
    length_m=1.0, velocity_ms=0.01, viscosity_m2s=1e-6,
    time_steps=20000
)
await cfd_fluidx3d_compile(case_name="physics_explain")
await cfd_fluidx3d_run(case_name="physics_explain", timeout_s=1800)

# Step 2: Get the physics explanation
await cfd_fluidx3d_explain(case_name="physics_explain")
# {"success": true, "case_name": "physics_explain", "data": {
#   "summary": "Channel flow at Re=10000 with D_h=0.1m. The flow is transitional/turbulent...",
#   "Re": 10000.0,
#   "regime": "transitional to turbulent (Re > 4000 for pipe flow)",
#   "solver_notes": "Smagorinsky-Lilly subgrid turbulence model active..."
# }}

# Step 3: Read the actual results
await cfd_fluidx3d_results(case_name="physics_explain")
# {"success": true, "data": {"forces": [...], "mlups": 450.2, "completed": true}}
```

The explain tool computes Reynolds number from the stored config, classifies the flow regime (creeping/laminar/transitional/turbulent), estimates Darcy friction factor, and explains what the LBM solver is computing.

---

## Tutorial 11: Use OpenAI API for NL2FOAM Instead of Ollama

Configure the NL2FOAM tool to use GPT-4o, DeepSeek, or any OpenAI-compatible API instead of the default Ollama instance.

```python
# Using OpenAI API directly
await cfd_nl2foam(
    description="Laminar flow through a 90-degree elbow pipe bend. Pipe diameter 50mm, bend radius 75mm. Water at 20C, Re=50000. kOmegaSST. Calculate pressure loss coefficient K.",
    case_name="elbow_nl",
    api_url="https://api.openai.com",
    api_key="sk-your-api-key-here",
    model="gpt-4o"
)

# Using DeepSeek API
await cfd_nl2foam(
    description="External aerodynamic flow over a NACA 0012 airfoil. Chord 1m, angle of attack 10 degrees, Re=3e6, Ma=0.2. Standard air. kOmegaSST. Calculate Cl and Cd.",
    case_name="airfoil_nl_deepseek",
    api_url="https://api.deepseek.com",
    api_key="sk-deepseek-key",
    model="deepseek-chat"
)

# Using local LM Studio with OpenAI-compatible server
await cfd_nl2foam(
    description="Microchannel flow, D_h=200um, water, Re=100, laminar, calculate pressure drop.",
    case_name="microchannel_nl",
    api_url="http://localhost:1234/v1",
    api_key="not-needed",
    model="local-model"
)

# Mixed approach: Ollama for simple cases, API for complex
await cfd_nl2foam(
    description="Simple pipe flow, Re=500, D=0.1m, L=1m",
    case_name="quick_pipe"
)
```

The api_url and api_key persist for the session after the first call, so subsequent calls can omit them.

---

## Tutorial 12: Check the Health of Your Pipeline

Run a comprehensive diagnostic of the entire FreeCAD + CFD pipeline before starting work.

```python
# Step 1: Check FreeCAD availability
await freecad_status()
# {"success": true, "freecad_ok": true, "version": "FreeCAD 1.1.1 ...", "bridge_mode": "tcp"}

# Step 2: Check BIM/Arch workbench
await bim_status()
# {"success": true, "bim_available": true, "bridge_mode": "tcp"}

# Step 3: Check FEM workbench and CalculiX
await fem_status()
# {"success": true, "fem_available": true, "bridge_mode": "tcp", "solver": "CalculiX (ccx)"}

# Step 4: Check Docker/OpenFOAM pipeline
await cfd_status()
# {"success": true, "docker_available": true, "openfoam_image": true, "bridge_mode": "tcp"}

# Step 5: Check FluidX3D GPU pipeline
await cfd_fluidx3d_status()
# {"success": true, "fluidx3d_path": "D:/Dev/repos/FluidX3D", "compiler": "g++", "ready": true}

# Step 6: Check PrusaSlicer
await slicer_status()
# {"success": true, "available": true, "version": "PrusaSlicer-2.8.1+win64"}

# Step 7: Check marketplace connectivity
await marketplace_categories(source="printables")
# {"success": true, "source": "printables", "categories": [...]}

# Step 8: View the full health endpoint
# GET http://localhost:10944/api/v1/health
# Returns: freecad_ok, docker_available, openfoam_image, fluidx3d_path,
#          compiler, bridge_mode, uptime_seconds
```

The web dashboard at http://localhost:10945 shows live status cards for all components.

---

## Additional Tutorial: Run an End-to-End FEM Structural Analysis

Analyze a cantilever beam under load using the full CalculiX pipeline.

```python
# Step 1: Check FEM availability
await fem_status()
# {"success": true, "fem_available": true, "bridge_mode": "tcp", "solver": "CalculiX (ccx)"}

# Step 2: Upload a STEP beam file or create a test shape
await create_shape(shape_type="box", params={"width": 50, "height": 30, "depth": 200}, output_name="beam_shape.stl")

# Step 3: Create the FEM analysis container
await fem_create_analysis(file_name="beam_shape.stl", analysis_name="CantileverAnalysis", output_name="beam_fem.fcstd")
# {"success": true, "output": "beam_fem.fcstd", "data": {"analysis_name": "CantileverAnalysis", "objects": [...]}}

# Step 4: Assign steel material
await fem_set_material(file_name="beam_fem.fcstd", material="steel")

# Step 5: Apply boundary conditions (fixed one end, force on the other)
await fem_set_constraint(file_name="beam_fem.fcstd", constraints=[
    {"type": "fixed", "face_name": "Face1"},
    {"type": "force", "face_name": "Face6", "fy": -5000},
])

# Step 6: Generate mesh with 10mm elements
await fem_mesh(file_name="beam_fem.fcstd", max_size_mm=10, second_order=True)
# {"success": true, "data": {"nodes": 15234, "elements": 8912, "element_size_mm": 10.0, "element_order": 2}}

# Step 7: Run the solver
await fem_run(file_name="beam_fem.fcstd")
# {"success": true, "data": {"solver": "CalculiX ccx", "exit_code": 0, "result_files": [...], "working_dir": "..."}}

# Step 8: Read results
await fem_read_results(file_name="beam_fem.fcstd")
# {"success": true, "data": {"max_von_mises_MPa": 187.3, "max_displacement_mm": 2.45,
#   "max_principal_MPa": 201.1, "min_principal_MPa": -15.2, "nodes": 15234}}

# Or use the convenience tool (end-to-end in one call):
await run_fem_analysis(
    file_name="beam.step",
    material="steel",
    constraints=[
        {"type": "fixed", "face_name": "Face1"},
        {"type": "force", "face_name": "Face6", "fy": -5000},
    ],
    mesh_size_mm=10,
)
# Returns safety factor = 1.65, max stress = 145.3 MPa, max displacement = 0.89 mm
```

Available material presets: steel (E=210GPa), stainless (193GPa), aluminum (70GPa), titanium (110GPa), concrete (25GPa), wood (12GPa), brass (100GPa), copper (117GPa), nylon (3GPa), carbon_fiber (150GPa).

---

## Additional Tutorial: Use the Persistent CAD Depot

The depot stores CAD files with metadata across server restarts.

```python
# Save a primitive directly to the depot
await cad_create(shape_type="cylinder", params={"radius": 5, "height": 20},
    output_name="pin.stl", description="Cylindrical pin for linkage assembly",
    tags=["pin", "linkage", "prototype"])

# List all depot files with metadata
await cad_depot()
# {"success": true, "data": {"files": [{"name": "pin.stl", "size_kb": 4.2,
#   "meta": {"description": "Cylindrical pin...", "tags": ["pin", "linkage"], "shape_type": "cylinder"}}]}}

# Upload via REST to depot
# POST /api/v1/depot/upload with multipart file
# PUT /api/v1/depot/pin.stl with {"description": "Updated pin", "tags": ["v2"]}
# DELETE /api/v1/depot/pin.stl
# GET /api/v1/depot/pin.stl (download)
```

---

## Additional Tutorial: Fleet Pipeline from qcad-mcp to FluidX3D

Chain 2D floor plans (qcad-mcp) through STL extrusion to CFD simulation (freecad-mcp) to VR visualization (godot-mcp/resonite-mcp).

```python
# Step 1: [In qcad-mcp] Extrude a floor plan to STL
# await plan_extrude(dxf_name="office.dxf", height_mm=2800, output_name="office_walls.stl")

# Step 2: [In freecad-mcp] Import the STL mesh
# POST /api/v1/upload with office_walls.stl
await model_info(file_name="office_walls.stl")
# {"success": true, "data": {"type": "mesh", "vertices": 50000, "facets": 100000}}

# Step 3: Convert mesh to solid B-Rep (requires TCP bridge)
await mesh_to_solid(file_name="office_walls.stl", output_name="office_solid.fcstd")

# Step 4: Set up GPU-accelerated CFD around the geometry
await cfd_fluidx3d_setup(
    case_name="office_flow_gpu",
    domain_type="stl",
    stl_file="office_walls.stl",
    resolution_x=512, resolution_y=256, resolution_z=256,
    velocity_ms=1.0, viscosity_m2s=1.5e-5,
    time_steps=100000
)

# Step 5: Run on GPU
await cfd_fluidx3d_compile(case_name="office_flow_gpu")
await cfd_fluidx3d_run(case_name="office_flow_gpu")

# Step 6: Export streamlines for VR visualization
await cfd_fluidx3d_export_for_render(
    case_name="office_flow_gpu",
    n_streamlines=40,
    export_csv=True
)
# {"success": true, "data": {"streamline_obj": "...", "csv_file": "..."}}

# The OBJ streamlines can be imported into Godot or Resonite for immersive flow visualization
```

---

## Additional Tutorial: Material Selection for FEA

Compare different materials for a bracket under 2kN load to find the optimal tradeoff between strength, weight, and cost.

```python
# Run the same analysis with three materials and compare results
import json

constraints = [{"type": "fixed", "face_name": "Face1"}, {"type": "force", "face_name": "Face6", "fy": -2000}]

for material in ["steel", "aluminum", "carbon_fiber"]:
    result = await run_fem_analysis(
        file_name="bracket.step",
        material=material,
        constraints=constraints,
        mesh_size_mm=5,
    )
    data = result["data"]
    print(f"{material}: stress={data['max_von_mises_MPa']:.1f} MPa, "
          f"disp={data['max_displacement_mm']:.3f} mm, "
          f"safety={data['safety_factor']:.2f}")

# steel:      145.3 MPa, 0.89 mm, SF=1.65
# aluminum:   148.1 MPa, 2.65 mm, SF=1.62
# carbon_fiber: 140.2 MPa, 0.95 mm, SF=5.71
```

---

## REST API Reference

```
GET /api/v1/status
# {"service": "freecad-mcp", "freecad_ok": true, "freecad_version": "FreeCAD 1.1.1"}
```

```
GET /api/v1/health
# {"status": "ok", "freecad_ok": true, "docker_available": true, "openfoam_image": true,
#  "fluidx3d_path": "D:/Dev/repos/FluidX3D", "compiler": "g++", "uptime_seconds": 3600.0}
```

### File Management

```
POST /api/v1/upload
# Content-Type: multipart/form-data
# file: <STEP/STL binary>
# {"success": true, "filename": "part.step", "size_bytes": 123456}
```

```
GET /api/v1/download/{filename}
# Returns the file binary (STL, G-code, IFC, FCStd)
```

```
GET /api/v1/files
# {"uploads": [{"name": "...", "size_kb": ...}], "outputs": [...], "gcodes": [...]}
```

### Depot CRUD (Persistent Storage)

```
GET /api/v1/depot
# {"files": [{"name": "part.step", "size_kb": 120.5, "meta": {...}}]}
```

```
GET /api/v1/depot/{name}
GET /api/v1/depot/{name}?download=true
# Returns file binary or depot listing
```

```
PUT /api/v1/depot/{name}
# {"name": "newname.stl", "description": "Updated part", "tags": ["bracket", "prototype"]}
# {"success": true, "filename": "newname.stl"}
```

```
DELETE /api/v1/depot/{name}
# {"success": true, "filename": "part.step"}
```

```
POST /api/v1/depot/create
# {"shape_type": "cylinder", "params": {"radius": 5, "height": 20}, "description": "Test part"}
# {"success": true, "filename": "shape.stl"}
```

```
POST /api/v1/depot/upload
# Same as /api/v1/upload but saves to persistent depot
```

### Tool Execution

```
POST /api/v1/control/tool
# {"tool": "step_to_stl", "arguments": {"file_name": "part.step", "output_name": "part.stl"}}
# {"success": true, "output": "part.stl", "data": {...}}
```

### CFD Case Files

```
GET /api/v1/case-files/{case_name}/{filename}
# Serves STL/VTK from case directories
```

```
GET /api/v1/case-files/pipe_study/geometry.step
GET /api/v1/case-files/channel_gpu/u_00100.vtk
```

### Marketplace

```
GET /api/v1/marketplace/search?source=printables&query=robot+chassis&limit=20&page=1
```

```
POST /api/v1/marketplace/download
# {"source": "printables", "model_id": "123456", "file_url": "...", "filename": "model.stl"}
```

### Settings

```
GET /api/v1/settings
# {"ollama_url": "http://192.168.1.11:11434", "model": "gemma3:1b", "api_url": ""}
```

```
PUT /api/v1/settings
# {"ollama_url": "http://localhost:11434", "model": "qwen2.5:14b"}
```

### AI Chat

```
POST /api/v1/chat
# {"messages": [{"role": "user", "content": "What material for a 500N bracket?"}], "provider": "ollama", "model": "gemma3:1b"}
# {"response": "For a 500N load, aluminum 6061..."}
```

### Logs

```
GET /api/v1/logs/stream
# SSE event stream of server logs (last 2000 lines)
# data: 2026-06-20 10:00:00 - freecad-mcp - INFO - Bridge connected
```

---

## Troubleshooting

### FreeCAD

| Symptom | Cause | Fix |
|---------|-------|-----|
| "FreeCAD not found" | FREECAD_PATH wrong | Set env var to correct FreeCAD.exe or FreeCADCmd.exe |
| Bridge timeout | FreeCAD GUI not starting | Launch FreeCAD manually first, then start server |
| Subprocess fallback active | FreeCADCmd.exe only | Install full FreeCAD GUI for AP214 STEP support |
| "STEP import failed" | Bad STEP file | Verify file in uploads/ directory |
| "Bridge not connected" | Port 10946 in use | Kill zombie FreeCAD processes |

### Docker / OpenFOAM

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Docker not available" | Docker Desktop not running | Start Docker Desktop; check `docker info` |
| "OpenFOAM image not found" | Image not pulled | `docker pull openfoam/openfoam10-paraview56` |
| blockMesh fails | Wrong vertex ordering | Check hex block follows right-hand rule |
| Solver diverges | Bad boundary conditions | Reduce inlet velocity, check BC consistency |
| "Mount fails" | Windows path format | Server auto-converts; ensure case dir is on local drive |

### FluidX3D / GPU

| Symptom | Cause | Fix |
|---------|-------|-----|
| "FluidX3D not found" | FLUIDX3D_PATH missing | Clone to default path or set env var |
| "Compiler not found" | g++ or MSVC not installed | Install MinGW-w64 or VS Build Tools |
| Compile fails | Missing OpenCL headers | Install GPU driver with OpenCL support |
| GPU not detected | Old driver | Update GPU driver; check clinfo |
| "OpenCL error -45" | GPU busy | Close GPU-intensive apps (browser, games) |
| Low MLUPS | Suboptimal grid | Adjust resolution for GPU memory |
| "No GPU devices" | No OpenCL runtime | Install Intel/AMD/NVIDIA OpenCL driver |

### PrusaSlicer

| Symptom | Cause | Fix |
|---------|-------|-----|
| "PrusaSlicer not found" | PRUSA_SLICER_PATH missing | Set env var to prusa-slicer.exe |
| Slicing fails | Non-manifold STL | Repair mesh with model_info check |
| Wrong printer profile | Profile name typo | Check available profiles in config |

### NL2FOAM

| Symptom | Cause | Fix |
|---------|-------|-----|
| Ollama not reachable | Ollama not running | Start Ollama; check `ollama list` |
| "Invalid JSON" | LLM hallucination | Retry with more specific description |
| Unphysical parameters | Bad model | Use larger model or provide explicit values |
| API not found | Invalid api_url | Check URL includes `/v1` path correctly |

### General

| Symptom | Cause | Fix |
|---------|-------|-----|
| Port conflict | Another process on 10944 | Kill zombie processes |
| Webapp blank | Frontend not built | Run `just web` or `cd webapp && npm run build` |
| SSE not connecting | Wrong transport config | Use `"transport": "sse"` in MCP config |
| CORS errors | Origin not allowed | Add your client origin to CORS config |

---

## FAQ

**What ports does freecad-mcp use?**
10944 (FastAPI + MCP SSE + REST API), 10945 (Vite web dashboard), 10946 (FreeCAD TCP bridge). All within the fleet reserved range 10700-11500.

**What if I don't have Docker?**
You can still generate OpenFOAM case directories with `cfd_create_domain`, `cfd_configure_physics`, and `cfd_set_boundary`. The case will be ready to run on any machine with OpenFOAM. Just skip `cfd_run_solver` and run the case manually.

**Can I use another LLM besides Ollama?**
Yes. NL2FOAM supports any OpenAI-compatible API via the `api_url` parameter. Use GPT-4o, DeepSeek, Claude API, or local LM Studio. Set the url and key per-call or via settings.

**Does it work on Mac?**
Yes. FreeCAD runs on macOS (via FreeCADCmd). FluidX3D runs on Apple Silicon GPU via OpenCL. Docker Desktop is available for macOS. For FluidX3D on Mac with 128GB unified memory, you can run grids up to ~1500^3 (3.4 billion cells).

**Can I use this without FreeCAD installed?**
CAD tools require FreeCAD. CFD tools (cfd_create_domain through cfd_read_results) require FreeCAD for geometry generation plus Docker for solver execution. FluidX3D tools require a FluidX3D clone and C++ compiler. You can run NL2FOAM (cfd_nl2foam) with just an LLM endpoint.

**How do I get help for a specific tool?**
The server registers a `freecad_expert` prompt via `@mcp.prompt()`. Call `freecad_expert(topic="cfd")` to get tool guidance. The web dashboard also has an 11-tab Help page.

**Can I use the REST API from scripts?**
Yes. All MCP tools are exposed via `POST /api/v1/control/tool`. File upload/download uses standard REST endpoints. Example:
```
curl -X POST http://localhost:10944/api/v1/control/tool \
  -H "Content-Type: application/json" \
  -d '{"tool": "freecad_status", "arguments": {}}'
```

**What if I get a "bridge not connected" error?**
The server auto-launches the FreeCAD bridge on startup. If it fails, start FreeCAD GUI manually (it will connect to the existing instance), then restart the server. The subprocess fallback still works for basic operations.

**Can I run multiple FluidX3D simulations simultaneously?**
Each GPU can run one FluidX3D instance. On multi-GPU systems, set `gpu_device` to select specific devices (e.g., "RTX 4090", "Arc A770", or index "1").

**How do I clean up old CFD cases?**
Case directories are in `%TEMP%\freecad_mcp_work\cfd_cases\` and `%TEMP%\freecad_mcp_work\fluidx3d_cases\`. Delete individual directories or clear the entire work dir.

**Is there a way to verify the mesh quality before running?**
Yes. Use `cfd_run_solver(case_name="...", steps="blockMesh,checkMesh")` to run mesh generation and validation without the solver. checkMesh reports skewness, aspect ratio, non-orthogonality, and negative volumes.
