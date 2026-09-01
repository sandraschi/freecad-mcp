# FreeCAD MCP — CFD Pipeline Guide

**Computational Fluid Dynamics with FreeCAD + OpenFOAM (CPU) + FluidX3D (GPU).**

This guide covers two CFD solvers that serve different jobs:

| | OpenFOAM | FluidX3D |
|---|---|---|
| **Hardware** | CPU (Docker) — GPU is idle | GPU (OpenCL) — any vendor |
| **Mesh** | Complex (structured + unstructured) | Simple (Cartesian, voxelized STL) |
| **Turbulence** | kEpsilon, kOmegaSST, LES, DES, Spalart-Allmaras | Smagorinsky-Lilly subgrid |
| **Multiphase** | VOF, Euler-Euler, reacting | Free surface LBM |
| **Speed** | Minutes to hours per solve | Milliseconds per timestep (MLUPS) |
| **Validation** | 30+ years, industry standard | Research-grade, active development |
| **Geometry** | Any CAD | Simple channels/pipes or voxelized STL |
| **Auto-installs?** | No (needs Docker + 2GB image) | Yes (clones to %TEMP%) |
| **Output** | OpenFOAM results (forces, residuals) | Video (WebM), OBJ streamlines, PNG heatmap |

**OpenFOAM = complex physics, complex mesh, slow, CPU.**
**FluidX3D = fast iteration, simple geometry, GPU, automatic video.**

Use OpenFOAM when you need fidelity or have complex geometry. Use FluidX3D when you have a GPU and the problem fits a Cartesian grid.

---

The OpenFOAM pipeline covers: parametric CAD in FreeCAD, structured hexahedral meshing (`blockMesh`), complex CAD meshing (`snappyHexMesh`), thermal & buoyant flow solvers (`buoyantBoussinesqSimpleFoam`), solver execution through Docker, aerodynamic force coefficient post-processing ($C_d, C_l$), Fluid-Structure Interaction load mapping (CFD → CalculiX FEM), headless parametric sweeps for design optimization, LLM-driven NL2FOAM configuration, and point cloud sampling for Physics-Informed Neural Networks (PINNs).

---

## Architecture Overview

```
FreeCAD (geometry)  ──→  blockMesh / snappyHexMesh  ──→  OpenFOAM (Docker)  ──→  Results & Cd/Cl Post-Proc
       │                          │                            │                      │
       │                   cfd_configure_physics        cfd_run_solver          cfd_post_process
       │                   cfd_set_boundary            cfd_read_results        cfd_map_loads_to_fem (FSI)
       │
cfd_create_domain / cfd_snappy_mesh
       │
Parametric variations  ──→  cfd_parametric_study  ──→  Design optimization / ML datasets
       │
Natural language  ──→  cfd_nl2foam (Ollama)  ──→  Auto-generated OpenFOAM case
       │
Point clouds  ──→  cfd_sample_for_pinns  ──→  NVIDIA Modulus / PyTorch Geometric
```

All **13** CFD tools use the same dual-mode execution pattern as CAD/BIM tools:
- **TCP bridge** (primary): Full FreeCAD Python API via `fc_bridge.py`
- **Subprocess** (fallback): `FreeCADCmd.exe` with piped Python scripts

---

## Prerequisites

### Required
| Component | Version | Purpose |
|:---|:---|:---|
| FreeCAD | 1.1.1+ | Parametric geometry engine (OCCT kernel) |
| freecad-mcp | 0.5.0+ | MCP server with CFD tools |
| Docker Desktop | 24+ | Container runtime for OpenFOAM |

### Required Docker Image
```powershell
docker pull openfoam/openfoam10-paraview56
```

This is the **only** Docker image needed. The image includes:
- OpenFOAM 10 (all standard solvers: simpleFoam, pisoFoam, pimpleFoam)
- ParaView 5.6 (for optional post-processing)
- All meshing utilities: blockMesh, snappyHexMesh, checkMesh, decomposePar

### Optional (for NL2FOAM)
| Component | Purpose |
|:---|:---|
| Ollama | Local LLM for natural language → OpenFOAM config |
| `gemma3:1b` or larger | Model for config generation |

### Optional (for PINNs/ML)
| Framework | Purpose |
|:---|:---|
| PyTorch / TensorFlow | Neural network backend |
| NVIDIA Modulus | Physics-ML framework (PINN solvers) |
| DeepXDE | Lightweight PINN library |
| NumPy (server-side) | Required for `.npz` point cloud export format |

---

## Tool Reference

### 1. `cfd_status` — Pipeline Health Check

Check Docker availability, OpenFOAM image presence, and FreeCAD bridge mode.

```python
await cfd_status()
```

**Return:**
```json
{
  "success": true,
  "docker_available": true,
  "docker_exe": "docker",
  "openfoam_image": true,
  "bridge_mode": "tcp",
  "cfd_case_dir": "C:\\Users\\...\\freecad_mcp_work\\cfd_cases"
}
```

---

### 2. `cfd_create_domain` — Fluid Domain & Mesh Skeleton

Create parametric geometry in FreeCAD, export as STEP, and generate blockMeshDict.

**Parameters:**

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `domain_type` | str | `"channel"` | Geometry shape: `channel`, `pipe`, `box`, `nozzle`, `custom` |
| `length_m` | float | `1.0` | Domain length in metres |
| `width_m` | float | `0.1` | Domain width in metres |
| `height_m` | float | `0.05` | Domain height in metres |
| `inlet_radius_m` | float | `0.02` | Inlet radius for pipe/nozzle |
| `outlet_radius_m` | float | `0.01` | Outlet radius for nozzle |
| `mesh_cells` | int | `20000` | Target cell count for structured hex mesh |
| `case_name` | str | `"channel_flow"` | Case directory name |
| `step_file` | str | `""` | Existing STEP file in uploads (for `custom` type) |

**Domain types illustrated:**

| Type | Description | Use Case |
|:---|:---|:---|
| `channel` | Rectangular duct, 3D | Pipe flow, microfluidics |
| `pipe` | Cylindrical tube | Pipe networks, vascular flow |
| `box` | Generic rectangular domain | Validation cases, cavity flow |
| `nozzle` | Convergent-divergent | Rocket nozzles, Venturi meters |
| `custom` | From existing STEP file | Complex geometries, valve bodies |

**Examples:**
```python
# Laminar channel flow at Re=100
await cfd_create_domain(
    domain_type="channel",
    length_m=1.0,
    width_m=0.1,
    height_m=0.05,
    mesh_cells=50000,
    case_name="channel_re100"
)

# Turbulent pipe flow
await cfd_create_domain(
    domain_type="pipe",
    length_m=2.0,
    inlet_radius_m=0.05,
    mesh_cells=100000,
    case_name="pipe_turbulent"
)

# Custom valve geometry
await cfd_create_domain(
    domain_type="custom",
    step_file="butterfly_valve.step",
    mesh_cells=200000,
    case_name="valve_cfd"
)
```

**Generated files:**
```
cfd_cases/<case_name>/
├── geometry.step                    # FreeCAD export
├── geometry.stl                     # Mesh format
└── constant/
    └── polyMesh/
        └── blockMeshDict            # Hexahedral mesh definition
```

---

### 3. `cfd_configure_physics` — Solver & Fluid Properties

Generate all OpenFOAM physics dictionaries.

**Parameters:**

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `case_name` | str | — | Case directory name |
| `solver` | str | `"simpleFoam"` | `simpleFoam`, `pisoFoam`, `pimpleFoam` |
| `flow_type` | str | `"laminar"` | `laminar`, `kEpsilon`, `kOmegaSST` |
| `fluid_nu` | float | `1e-6` | Kinematic viscosity (m²/s). Water≈1e-6, Air≈1.5e-5 |
| `fluid_density` | float | `1000` | Density (kg/m³). Water=1000, Air=1.225 |
| `inlet_velocity` | float | `1.0` | Inlet velocity magnitude (m/s) |
| `end_time` | float | `1000` | Simulation end (iterations for steady, seconds for transient) |
| `delta_t` | float | `1.0` | Time step (ignored by steady solvers) |
| `write_interval` | int | `100` | Write results every N steps |

**Typical fluid properties:**

| Fluid | ν (m²/s) | ρ (kg/m³) | Notes |
|:---|:---|:---|:---|
| Water @ 20°C | 1.004e-6 | 998.2 | Standard lab conditions |
| Air @ 20°C | 1.516e-5 | 1.204 | Standard atmosphere |
| SAE 10W-30 Oil @ 40°C | 6.5e-5 | 865 | Hydraulic fluid |
| Glycerin @ 20°C | 1.18e-3 | 1260 | High-viscosity benchmark |
| Mercury @ 20°C | 1.15e-7 | 13546 | Liquid metal |

**Flow regime selection:**

| Flow Type | When to Use | Additional Fields |
|:---|:---|:---|
| `laminar` | Re < ~2300 in pipes, Re < ~5e5 on flat plates | None |
| `kEpsilon` | High Re industrial flows, fully turbulent | `k`, `epsilon`, `nut` |
| `kOmegaSST` | Wall-bounded flows, separation, transition | `k`, `omega`, `nut` |

**Examples:**
```python
# Water laminar flow
await cfd_configure_physics(
    case_name="channel_re100",
    solver="simpleFoam",
    flow_type="laminar",
    fluid_nu=1e-6,
    fluid_density=1000,
    inlet_velocity=0.01
)

# Air turbulent flow with kOmegaSST
await cfd_configure_physics(
    case_name="pipe_turbulent",
    solver="simpleFoam",
    flow_type="kOmegaSST",
    fluid_nu=1.5e-5,
    fluid_density=1.225,
    inlet_velocity=10.0,
    end_time=2000,
    write_interval=200
)
```

**Generated files:**
```
cfd_cases/<case_name>/
├── system/
│   ├── controlDict          # Time control, write settings, force monitors
│   ├── fvSchemes            # Discretization schemes (grad, div, laplacian)
│   └── fvSolution           # Linear solver settings, relaxation factors
├── constant/
│   ├── transportProperties  # Newtonian viscosity model
│   └── turbulenceProperties # RAS model selection (laminar/kEpsilon/kOmegaSST)
└── .cfd_config.json         # Stored config for downstream tools
```

---

### 4. `cfd_set_boundary` — Boundary Conditions

Configure per-patch field boundary conditions for each field (U, p, k, omega, nut).

**Parameters:**

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `case_name` | str | — | Case directory name |
| `patch_name` | str | `"inlet"` | Patch: `inlet`, `outlet`, `walls` |
| `field_name` | str | `"U"` | Field: `U`, `p`, `k`, `omega`, `nut`, `alphat` |
| `bc_type` | str | `"fixedValue"` | BC type (see table below) |
| `value` | str | `"uniform (0 0 0)"` | Value in OpenFOAM syntax |

**Common BC types:**

| BC Type | Description | Typical Use |
|:---|:---|:---|
| `fixedValue` | Dirichlet — specified value | Inlet velocity, outlet pressure |
| `zeroGradient` | Neumann — zero normal gradient | Outlet (velocity), symmetry |
| `inletOutlet` | Zero gradient normal inflow, fixed value on backflow | Outlet for turbulent flows |
| `noSlip` | Zero velocity at wall | Solid walls |
| `slip` | Zero normal velocity, free tangential | Symmetry plane, free surface |
| `symmetry` | Symmetry plane condition | Half-domain models |
| `empty` | 2D (no solution in this direction) | 2D simulations |

**Value syntax reference:**
```
# Scalar uniform
"uniform 0"
"uniform 101325"

# Vector uniform
"uniform (1 0 0)"        # 1 m/s in X direction
"uniform (0 0.5 0)"      # 0.5 m/s in Y direction

# Turbulence estimates
# k = 1.5 * (U * I)^2     where I ≈ 0.05 (5% turbulence intensity)
# omega = k^0.5 / (0.09^0.25 * L)   where L ≈ 0.07 * D_hydraulic
```

**Examples:**
```python
# Inlet: uniform velocity profile
await cfd_set_boundary(
    case_name="channel_re100",
    patch_name="inlet",
    field_name="U",
    bc_type="fixedValue",
    value="uniform (0.01 0 0)"
)

# Outlet: fixed pressure (zero gauge)
await cfd_set_boundary(
    case_name="channel_re100",
    patch_name="outlet",
    field_name="p",
    bc_type="fixedValue",
    value="uniform 0"
)

# Walls: no-slip
await cfd_set_boundary(
    case_name="channel_re100",
    patch_name="walls",
    field_name="U",
    bc_type="noSlip",
    value="uniform (0 0 0)"
)

# Turbulent inlet: estimated k and omega (Re=10000, L=0.1m, U=0.1m/s)
await cfd_set_boundary(
    case_name="pipe_turbulent",
    patch_name="inlet",
    field_name="k",
    bc_type="fixedValue",
    value="uniform 3.75e-05"
)
```

**Generated files:**
```
cfd_cases/<case_name>/0/
├── U          # Velocity field
├── p          # Pressure field
├── k          # Turbulent kinetic energy (turbulent only)
├── omega      # Specific dissipation rate (kOmegaSST)
└── nut        # Turbulent viscosity (turbulent only)
```

---

### 5. `cfd_build_case` — Validate Case Completeness

Check that all required OpenFOAM files are present before solving.

```python
await cfd_build_case(case_name="channel_re100")
```

**Return:**
```json
{
  "success": true,
  "case_name": "channel_re100",
  "data": {
    "files": [
      "constant/polyMesh/blockMeshDict",
      "system/controlDict",
      "system/fvSchemes",
      "system/fvSolution",
      "constant/transportProperties",
      "constant/turbulenceProperties",
      "0/U",
      "0/p"
    ],
    "missing": [],
    "ready": true
  }
}
```

If `ready` is `false`, the `missing` array lists exactly which files need to be created.

---

### 6. `cfd_run_solver` — Execute via Docker

Run OpenFOAM solver steps inside a Docker container.

**Parameters:**

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `case_name` | str | — | Case directory name |
| `steps` | str | `"blockMesh,checkMesh,simpleFoam"` | Comma-separated solver steps |
| `parallel` | bool | `false` | Use MPI parallel decomposition |
| `n_cores` | int | `4` | CPU cores for parallel run |

**Available steps:**
- `blockMesh` — Generate hexahedral mesh from blockMeshDict
- `checkMesh` — Validate mesh quality (skewness, aspect ratio, non-orthogonality)
- `simpleFoam` — Steady-state incompressible solver (SIMPLE algorithm)
- `pisoFoam` — Transient incompressible solver (PISO algorithm)
- `pimpleFoam` — Transient with large time steps (PIMPLE hybrid)
- `decomposePar` — Decompose mesh for parallel execution
- `reconstructPar` — Reconstruct parallel results
- `postProcess` — Run function objects (forces, probes, etc.)

**Examples:**
```python
# Standard run: mesh → check → solve
await cfd_run_solver(case_name="channel_re100")

# Custom steps: mesh only (dry run)
await cfd_run_solver(
    case_name="channel_re100",
    steps="blockMesh,checkMesh"
)

# Parallel execution on 8 cores
await cfd_run_solver(
    case_name="pipe_turbulent",
    steps="blockMesh,decomposePar,simpleFoam,reconstructPar",
    parallel=True,
    n_cores=8
)

# Transient simulation
await cfd_run_solver(
    case_name="vortex_street",
    steps="blockMesh,pisoFoam"
)
```

**Return:**
```json
{
  "success": true,
  "case_name": "channel_re100",
  "data": {
    "steps_completed": ["blockMesh", "checkMesh", "simpleFoam"],
    "log": "=== blockMesh (exit=0) ===\n...\n=== simpleFoam (exit=0) ===\n...\n",
    "exit_codes": {"blockMesh": 0, "checkMesh": 0, "simpleFoam": 0}
  }
}
```

**Troubleshooting:**
- Docker not found: Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
- Image not found: Run `docker pull openfoam/openfoam10-paraview56`
- `blockMesh` fails: Check blockMeshDict vertex ordering (right-hand rule for hex blocks)
- `simpleFoam` diverges: Reduce `end_time`, check BC consistency, refine mesh
- Parallel fails: Ensure `decomposeParDict` exists in `system/`

---

### 7. `cfd_read_results` — Parse Simulation Output

Extract structured results from the completed case.

```python
await cfd_read_results(case_name="channel_re100")
```

**Return:**
```json
{
  "success": true,
  "case_name": "channel_re100",
  "data": {
    "times": ["0", "100", "200", "300", "400", "500"],
    "latest_time": "500",
    "forces": {
      "forces.dat": {
        "time": 500.0,
        "pressure_x": -0.01234,
        "pressure_y": 0.0,
        "pressure_z": 0.0
      }
    },
    "final_residuals": {
      "p": 3.2e-6,
      "Ux": 8.1e-7,
      "Uy": 1.2e-8,
      "Uz": 2.3e-9
    },
    "converged": true
  }
}
```

**Interpretation:**
- `converged: true` — All residuals below 1e-4 (tight convergence)
- `forces` — Parsed from `postProcessing/forces/` — pressure forces on specified patches
- `times` — All saved time directories (time steps or iterations)
- `final_residuals` — Last residual value for each solved field (lower is better)

---

### 8. `cfd_parametric_study` — Design Optimization Sweeps

Run parameter sweeps varying one design variable across multiple cases.

**Parameters:**

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `case_name` | str | — | Base case name (variants suffixed `_0`, `_1`, ...) |
| `parameter` | str | `"inlet_velocity"` | Variable to sweep: `inlet_velocity`, `length`, `width`, `height`, `fluid_nu`, `angle` |
| `values` | str | — | JSON array of parameter values |
| `run` | bool | `false` | Execute each case (requires Docker). If false, generates configs only |

**Examples:**
```python
# Velocity sweep (4 cases, generate only)
await cfd_parametric_study(
    case_name="channel_base",
    parameter="inlet_velocity",
    values="[0.01, 0.05, 0.1, 0.5]",
    run=False
)
# Creates: channel_base_0 (v=0.01), channel_base_1 (v=0.05),
#          channel_base_2 (v=0.1),  channel_base_3 (v=0.5)

# Geometry optimization sweep with execution
await cfd_parametric_study(
    case_name="nozzle_base",
    parameter="length",
    values="[0.3, 0.5, 0.8, 1.0, 1.5]",
    run=True
)

# Viscosity sweep for Reynolds number study
await cfd_parametric_study(
    case_name="pipe_base",
    parameter="fluid_nu",
    values="[1e-6, 5e-6, 1e-5, 5e-5, 1e-4]",
    run=False
)
```

**Use cases:**
- **Design optimization**: Sweep geometry parameters, find optimal lift-to-drag ratio
- **ML dataset generation**: Generate 100s of cases for training neural surrogates
- **Sensitivity analysis**: Identify which parameters most affect results
- **Validation**: Compare against experimental data across Reynolds numbers

---

### 9. `cfd_nl2foam` — Natural Language to OpenFOAM

Convert a plain-language fluid dynamics description into an executable OpenFOAM case using the configured Ollama LLM.

**Parameters:**

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `description` | str | — | Natural language problem description |
| `case_name` | str | `"nl2foam_case"` | Target case directory name |
| `model` | str | `"gemma3:1b"` | Ollama model for config generation |

**Description guidelines — include these details:**

1. **Geometry**: Dimensions, shape, orientation
2. **Fluid**: Type (water/air/custom), temperature if relevant
3. **Flow regime**: Laminar or turbulent, Reynolds number if known
4. **Boundary conditions**: Inlet velocity/pressure, outlet type, wall condition
5. **Goals**: What you want to learn (pressure drop, lift/drag, velocity profile)

**Examples:**
```python
# Laminar pipe flow
await cfd_nl2foam(
    description="Incompressible laminar flow through a 1m long, 0.1m diameter pipe at Re=500. Water at 20°C. Inlet velocity 0.005 m/s. Calculate pressure drop.",
    case_name="pipe_nl_500"
)

# Turbulent airfoil
await cfd_nl2foam(
    description="Turbulent air flow over NACA 0012 at 10 degrees angle of attack, chord 0.5m, Re=1e6, standard air at sea level. kOmegaSST model. Calculate lift and drag coefficients.",
    case_name="naca0012_nl"
)

# Natural convection
await cfd_nl2foam(
    description="Natural convection in a 0.5m x 0.5m square cavity. Left wall at 310K, right wall at 290K, top and bottom adiabatic. Air, Ra=1e6. Steady-state laminar.",
    case_name="cavity_nl"
)

# Complex: multi-physics hint
await cfd_nl2foam(
    description="Conjugate heat transfer in a microchannel heatsink. Water coolant at 0.1 m/s inlet, 300K. Silicon substrate with 100 W/cm² heat flux on bottom. 10 parallel channels, each 200µm wide, 500µm deep, 10mm long. kOmegaSST.",
    case_name="microchannel_nl"
)
```

**What the LLM generates:**
```json
{
  "solver": "simpleFoam",
  "flow_type": "laminar",
  "fluid": {"nu": 1e-6, "density": 1000, "name": "water"},
  "inlet": {"velocity": [0.005, 0, 0], "type": "fixedValue"},
  "outlet": {"type": "zeroGradient", "pressure": 0},
  "walls": {"type": "noSlip"},
  "domain": {"lx": 1.0, "ly": 0.1, "lz": 0.1, "unit": "m"},
  "mesh": {"nx": 200, "ny": 20, "nz": 20},
  "control": {"end_time": 1000, "write_interval": 100},
  "reasoning": "Laminar pipe flow at Re=500 — well within laminar regime (<2300). ..."
}
```

**Tips for better NL2FOAM results:**
- Use precise numbers (not "about 1 meter" — say "1.0m")
- Specify the Reynolds number when possible
- Name the fluid explicitly
- State whether steady or transient
- Mention expected flow physics (separation, recirculation, etc.)

---

### 10. `cfd_sample_for_pinns` — PINN Point Cloud Export

Sample coordinate point clouds from CFD domain geometry for Physics-Informed Neural Network training.

**Parameters:**

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `case_name` | str | — | Case directory with existing geometry (STEP file) |
| `n_boundary` | int | `5000` | Number of boundary sample points (BC enforcement) |
| `n_interior` | int | `10000` | Number of interior collocation points (PDE residual) |
| `output_format` | str | `"csv"` | Output format: `csv`, `json`, `numpy` |

**Examples:**
```python
# CSV export (human-readable, universal)
await cfd_sample_for_pinns(
    case_name="pipe_study",
    n_boundary=5000,
    n_interior=20000,
    output_format="csv"
)

# NumPy export (compact, ML-ready)
await cfd_sample_for_pinns(
    case_name="airfoil_cfd",
    n_boundary=10000,
    n_interior=50000,
    output_format="numpy"
)
```

**Output format — CSV:**
```csv
x,y,z,region
0.000,0.023,0.012,boundary_xmin
0.015,0.045,0.008,interior
...
```

**Output format — NumPy (`.npz`):**
```python
import numpy as np
data = np.load("pinn_points.npz")
coords = data["coords"]    # shape: (N, 3), dtype: float32
regions = data["regions"]  # shape: (N,), dtype: int8 (0=interior, 1=boundary)
```

**Integration with ML frameworks:**

```python
# PyTorch Geometric
import torch
from torch_geometric.data import Data

coords = torch.from_numpy(np.load("pinn_points.npz")["coords"])
data = Data(pos=coords)

# NVIDIA Modulus
from modulus.domain import PointwiseBoundaryConstraint, PointwiseInteriorConstraint

# DeepXDE
import deepxde as dde
data = dde.data.TimePDE(geometry, pde, bc, num_domain=10000, num_boundary=5000)
```

---

## Complete Workflow Examples

### Example 1: Laminar Channel Flow (Navier-Stokes Validation)

```python
# Step 1: Check pipeline readiness
await cfd_status()

# Step 2: Create domain (1m × 0.1m × 0.05m channel)
await cfd_create_domain(
    domain_type="channel",
    length_m=1.0, width_m=0.1, height_m=0.05,
    mesh_cells=80000,
    case_name="channel_validation"
)

# Step 3: Configure physics (water, Re=100, steady laminar)
await cfd_configure_physics(
    case_name="channel_validation",
    solver="simpleFoam",
    flow_type="laminar",
    fluid_nu=1e-6,
    fluid_density=1000,
    inlet_velocity=0.001,     # Re = U*H/nu = 0.001*0.05/1e-6 = 50
    end_time=2000
)

# Step 4: Set boundary conditions
await cfd_set_boundary(case_name="channel_validation", patch_name="inlet", field_name="U", bc_type="fixedValue", value="uniform (0.001 0 0)")
await cfd_set_boundary(case_name="channel_validation", patch_name="outlet", field_name="p", bc_type="fixedValue", value="uniform 0")
await cfd_set_boundary(case_name="channel_validation", patch_name="walls", field_name="U", bc_type="noSlip", value="uniform (0 0 0)")

# Step 5: Validate case completeness
result = await cfd_build_case(case_name="channel_validation")
# result.data.ready should be True

# Step 6: Run solver
await cfd_run_solver(case_name="channel_validation", steps="blockMesh,checkMesh,simpleFoam")

# Step 7: Read results
results = await cfd_read_results(case_name="channel_validation")
# Check convergence, pressure drop, velocity profile
```

### Example 2: Turbulent Pipe Flow with Parametric Sweep

```python
# Step 1: Create base pipe case
await cfd_create_domain(
    domain_type="pipe",
    length_m=2.0,
    inlet_radius_m=0.05,
    mesh_cells=150000,
    case_name="pipe_base"
)

# Step 2: Configure physics (air, turbulent kOmegaSST)
await cfd_configure_physics(
    case_name="pipe_base",
    solver="simpleFoam",
    flow_type="kOmegaSST",
    fluid_nu=1.5e-5,
    fluid_density=1.225,
    inlet_velocity=3.0,      # Re = U*D/nu = 3*0.1/1.5e-5 = 20000
    end_time=3000
)

# Step 3: Set boundary conditions
await cfd_set_boundary(case_name="pipe_base", patch_name="inlet", field_name="U", bc_type="fixedValue", value="uniform (3 0 0)")
await cfd_set_boundary(case_name="pipe_base", patch_name="inlet", field_name="k", bc_type="fixedValue", value="uniform 0.03375")
await cfd_set_boundary(case_name="pipe_base", patch_name="inlet", field_name="omega", bc_type="fixedValue", value="uniform 14.6")
await cfd_set_boundary(case_name="pipe_base", patch_name="outlet", field_name="p", bc_type="fixedValue", value="uniform 0")
await cfd_set_boundary(case_name="pipe_base", patch_name="walls", field_name="U", bc_type="noSlip", value="uniform (0 0 0)")

# Step 4: Parametric study — Reynolds number sweep
await cfd_parametric_study(
    case_name="pipe_base",
    parameter="inlet_velocity",
    values="[0.75, 1.5, 3.0, 6.0, 12.0]",  # Re = 5000, 10000, 20000, 40000, 80000
    run=True
)

# Step 5: Collect results from each variant
for i in range(5):
    results = await cfd_read_results(case_name=f"pipe_base_{i}")
    # Compare pressure drop vs Re → validate Moody chart
```

### Example 3: NL2FOAM → Automated Case Setup

```python
# Describe the problem in plain language
await cfd_nl2foam(
    description="""Flow through a 90-degree elbow pipe bend.
    - Pipe diameter: 50mm, bend radius: 75mm (R/D = 1.5)
    - Water at 20°C
    - Inlet: fully developed turbulent profile at Re=50000 (U_bulk ≈ 1 m/s)
    - Outlet: atmospheric pressure
    - Goal: Calculate pressure loss coefficient K = Δp / (0.5*rho*U²)
    - kOmegaSST turbulence model""",
    case_name="elbow_bend",
    model="gemma3:1b"
)

# The LLM generates the complete config.
# Verify and validate:
await cfd_build_case(case_name="elbow_bend")

# Run
await cfd_run_solver(case_name="elbow_bend", steps="blockMesh,checkMesh,simpleFoam")

# Get pressure drop
results = await cfd_read_results(case_name="elbow_bend")
```

### Example 4: ML Dataset Generation Pipeline

```python
# Generate 100 cases for training a neural surrogate model
# Vary both Reynolds number and geometry aspect ratio

# Phase 1: Geometry sweep (10 aspect ratios)
await cfd_parametric_study(
    case_name="channel_base",
    parameter="length",
    values="[0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.5, 10.0]",
    run=False
)

# Phase 2: For each geometry, sweep Reynolds number (10 velocities)
for geo_idx in range(10):
    await cfd_parametric_study(
        case_name=f"channel_base_{geo_idx}",
        parameter="inlet_velocity",
        values="[0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]",
        run=True
    )

# Phase 3: Sample each case for PINN training
for geo_idx in range(10):
    for vel_idx in range(10):
        await cfd_sample_for_pinns(
            case_name=f"channel_base_{geo_idx}_{vel_idx}",
            n_boundary=5000,
            n_interior=20000,
            output_format="numpy"
        )
```

---

## Advanced: Adding Custom CFD Bridge Methods

For advanced meshing (snappyHexMesh, cfMesh) or in-situ post-processing, extend `fc_bridge.py` with new JSON-RPC methods:

```python
# In fc_bridge.py, add to the handle() dispatch:
elif method == "cfd_export_poly_mesh":
    import MeshPart
    obj = doc.getObject(params["object"])
    mesh = doc.addObject("Mesh::Feature", "CFD_Mesh")
    mesh.Mesh = MeshPart.meshFromShape(
        Shape=obj.Shape,
        MaxLength=params.get("max_size", 0.1),
    )
    Mesh.export([mesh], params["path"])
```

Then register the method in `cfd.py`:

```python
if state.get("bridge_mode") == "tcp":
    resp = await bridge_send("cfd_export_poly_mesh", {...}, timeout=300)
```

---

## Troubleshooting

### Docker Issues

| Symptom | Cause | Fix |
|:---|:---|:---|
| "Docker not available" | Docker Desktop not running | Start Docker Desktop; check `docker info` |
| "OpenFOAM image not found" | Image not pulled | `docker pull openfoam/openfoam10-paraview56` |
| Docker mount fails | Windows path format | Server auto-converts paths. Ensure case dir is on a local drive. |
| Container exits immediately | Invalid command | Check step names: `simpleFoam` not `simplefoam` |

### Mesh Issues

| Symptom | Cause | Fix |
|:---|:---|:---|
| blockMesh fails | Vertex ordering wrong | Hex blocks must follow right-hand rule |
| Negative volume cells | Degenerate geometry | Check dimensions; reduce mesh cell count |
| High skewness (>4) | Poor block distribution | Adjust `nx`, `ny`, `nz` for more uniform cells |
| Mesh too coarse | Not enough cells | Increase `mesh_cells` parameter |

### Solver Issues

| Symptom | Cause | Fix |
|:---|:---|:---|
| Solution diverges immediately | Bad initial conditions or BC mismatch | Check BC types; reduce inlet velocity |
| Floating point exception | Zero velocity or density | Verify fluid properties are non-zero |
| Slow convergence | Poor relaxation factors | Reduce under-relaxation (p: 0.2, U: 0.5) |
| Oscillating residuals | High-order scheme instability | Switch to `Gauss upwind` for div schemes |
| "bounding k/omega" messages | Turbulence model near wall limits | Ensure y+ appropriate for model choice |

### NL2FOAM Issues

| Symptom | Cause | Fix |
|:---|:---|:---|
| Invalid JSON response | LLM hallucination | Retry with more specific description |
| Unphysical parameters | LLM lacks fluid dynamics knowledge | Use larger model or provide explicit values |
| Missing fields | Description incomplete | List all boundaries and conditions explicitly |

---

## Performance Reference

Typical runtimes on a modern desktop (Ryzen 7 5800X, 32 GB, Docker):

| Case Size (cells) | blockMesh | simpleFoam (1000 iter) | Total |
|:---|---:|---:|---:|
| 20k | 0.5s | 8s | ~10s |
| 100k | 2s | 45s | ~50s |
| 500k | 10s | 4 min | ~5 min |
| 2M | 45s | 20 min | ~25 min |
| 10M (parallel x8) | 3 min | 25 min | ~30 min |

---

## FluidX3D Runner — GPU CFD Without Compilation

The **FluidX3D Runner** is a pre-compiled GPU CFD binary that reads all simulation parameters from a JSON file at runtime. Build once, use for any case.

### How it works

```
cfd_fluidx3d_setup → config.json + setup.cpp (both generated)
                          │
                          ▼
fluidx3d-runner.exe  ──  reads config.json at runtime
  (pre-compiled)          ├── resolution, viscosity, inlet velocity
                          ├── boundary conditions (channel/pipe/box/STL)
                          ├── time steps, write interval
                          ├── STL imports (voxelized on GPU)
                          └── force extraction, VTK export
                          │
                          ▼
                    stdout: RESULT {"success": true, forces, MLUPS, ...}
                    export/: velocity-*.vtk, density-*.vtk
```

### Benefits over compile-per-case

| Aspect | Compile path | Runner path |
|:---|:---|:---|
| Compilation needed | Every case | Once (or use pre-built binary) |
| Change resolution | Recompile | Edit config.json |
| Change BC type | Recompile | Edit config.json |
| Add STL geometry | Recompile | Edit config.json |
| Time to first results | ~5s compile + run | Run immediately |
| C++ compiler required | Yes | No (if pre-built binary) |

### Building the runner

```powershell
# Windows — auto-detects FluidX3D, compiles via g++ or MSVC
scripts/build-fluidx3d-runner.ps1

# Or via CMake
cmake -B build -S src/freecad_mcp/fluidx3d_runner/ \
  -DFLUIDX3D_SOURCE_DIR=C:/path/to/FluidX3D
cmake --build build
```

### Pre-built binary

On tagged releases (`v*`), GitHub Actions compiles the runner for:
- Windows (MSVC + g++ MinGW x86_64)
- Linux (g++ x86_64)
- macOS (clang++, ARM x86_64)

The binary auto-detects the fastest GPU via OpenCL. Set `FLUIDX3D_BINARY` env var to use a custom path.

### GPU selection

```python
# Run on fastest GPU (auto-detected)
await cfd_fluidx3d_run(case_name="pipe_gpu")
# On RTX 4090: ~770³ cells, ~456 million cells, ~60 time steps/sec

# Specify GPU by name substring
await cfd_fluidx3d_run(case_name="pipe_gpu", gpu_device="RTX 4090")
```

---

## GPU Acceleration & RTX 4090

### OpenFOAM vs FluidX3D — Which to use

| Criterion | OpenFOAM (CPU) | FluidX3D (GPU) |
|:---|:---|:---|
| Execution hardware | CPU cores (MPI) | GPU via OpenCL (any vendor) |
| RTX 4090 utilisation | None (idle during solve) | Full (D3Q19 LBM, 55 bytes/cell) |
| Max cells on 4090 (24 GB) | ~5M (CPU RAM) | ~456M (770³, FP16) |
| Max cells on Mac 128GB | ~40M | ~3.4B (1500³) |
| Solver method | Finite Volume (FVM) | Lattice-Boltzmann (LBM) |
| Turbulence models | kEpsilon, kOmegaSST, LES, DES | Smagorinsky-Lilly subgrid |
| Mesh type | Structured + unstructured + polyhedral | Cartesian grid (voxelized STL) |
| Multiphase | VOF (interFoam), Euler-Euler | Free surface (SURFACE extension) |
| 30-year legacy | Yes | No (4 years, 5k stars) |
| Setup complexity | Dictionary files (30+ year syntax) | JSON config (runner) or C++ (compile) |
| MCP tool prefix | `cfd_*` | `cfd_fluidx3d_*` |

### Neural Surrogates Workflow (Uses GPU)

The CFD pipeline is designed for a hybrid CPU/GPU workflow:

1. **CPU**: OpenFOAM generates training data (10–100 cases via `cfd_parametric_study`)
2. **CPU**: `cfd_sample_for_pinns` exports point clouds
3. **GPU (4090)**: Train a neural surrogate in PyTorch/NVIDIA Modulus — full 4090 utilisation during training
4. **GPU (4090)**: Neural surrogate replaces OpenFOAM for inference — **200x faster**, millisecond predictions

See `docs/openfoam.md` for complete GPU reference, including PINN training code and RapidCFD setup.

---

## References

- [OpenFOAM User Guide](https://www.openfoam.com/documentation/user-guide/)
- [OpenFOAM 10 Release Notes](https://www.openfoam.com/news/main-news/openfoam-v10/)
- [CfdOF Workbench for FreeCAD](https://github.com/jaheyns/CfdOF)
- [NVIDIA Modulus (Physics-ML)](https://developer.nvidia.com/modulus)
- [DeepXDE (PINN Library)](https://deepxde.readthedocs.io/)
- [PyTorch Geometric](https://pytorch-geometric.readthedocs.io/)
- [Turbulence Modeling Resource (NASA Langley)](https://turbmodels.larc.nasa.gov/)
