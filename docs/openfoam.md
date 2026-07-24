# OpenFOAM, GPU CFD & Hardware Guide

**SOTA 2026: Running CFD on GPUs is not optional. Here are the real options.**

---

## TL;DR

| What | Answer |
|:---|:---|
| Does `cfd_run_solver` use the RTX 4090? | **No.** The standard OpenFOAM Docker image is CPU-only MPI. |
| Best free GPU CFD solver? | **[FluidX3D](https://github.com/ProjectPhysX/FluidX3D)** — 5k stars, OpenCL, runs on ANY GPU (AMD/Intel/NVIDIA/Apple Silicon), v3.7 released May 2026. |
| Does the FluidX3D Runner need a C++ compiler? | **No** if you use a pre-built binary. `cfd_fluidx3d_setup` writes `config.json` → `fluidx3d-runner.exe` reads it at runtime. Build once, run any case. |
| Should I use a Mac with 128GB RAM? | **Yes, excellent for the full pipeline.** Unified memory = massive simulation grids + large neural surrogate training. |
| Where the 4090 matters? | FluidX3D simulation, PINN/GNN surrogate training (NVIDIA Modulus/PyTorch). |

---

## 0. Why OpenFOAM Doesn't Use the GPU

This comes up constantly. OpenFOAM doesn't ignore the GPU out of neglect — it's a fundamental algorithmic mismatch:

**OpenFOAM uses the Finite Volume Method on unstructured meshes** (arbitrary polyhedral cells, tetrahedra, hexahedra, prisms). Every cell has a different number of neighbours, different face orientations, and different connectivity patterns. Computing fluxes across these faces requires indirect memory addressing — for each face, look up the left and right cell indices, then gather/scatter from those arbitrary memory locations.

GPU architectures (SIMT — Single Instruction Multiple Threads) are designed for **regular, predictable memory access**: the same operation on a contiguous array of data (matrix multiply, image convolution, LBM stencil). Unstructured FVM causes:
- **Warp divergence**: adjacent threads need different instructions for different cell types
- **Uncoalesced memory**: scattered reads instead of contiguous blocks
- **Atomic contention**: multiple threads writing to the same cell from different faces

**The linear solver step** (solving Au = b) is the one part that can be GPU-accelerated, because it's a well-studied sparse linear algebra problem. OpenFOAM v2312+ ships `module-amgx` wrapping NVIDIA AmgX for exactly this. But that's only ~30-40% of the total solve time — the flux assembly, gradient computation, and limiters remain on CPU.

**LBM (FluidX3D) maps to GPU naturally** because it's a regular stencil on a Cartesian grid — every cell applies the same collision-and-stream pattern to its 18 neighbours (D3Q19). This is a textbook GPU workload: regular memory access, no branching per cell, trivially parallel. That's why FluidX3D achieves full GPU utilisation while OpenFOAM cannot for general unstructured meshes.

**Bottom line**: If you want GPU CFD with complex geometry, the path is not "GPU OpenFOAM" — it's either:
1. **FluidX3D** (LBM, Cartesian grids, auto-voxelizes STL) — best for this server
2. **Lethe** (FEM on GPU, supports complex geometry via deal.II, CUDA)
3. **Custom OpenFOAM + module-amgx image** (DIY build, partial GPU benefit)

---

## 1. GPU-Native CFD Solvers (Free, Production-Ready)

### FluidX3D — The Gold Standard

[ProjectPhysX/FluidX3D](https://github.com/ProjectPhysX/FluidX3D) — **5,000+ stars**, 362 commits, actively maintained (v3.7, May 2026).

- **Method**: Lattice-Boltzmann (LBM), not finite-volume. Different physics model, same results for most engineering problems.
- **Hardware**: Runs on **all GPUs** via OpenCL — AMD, Intel Arc, NVIDIA, Apple Silicon M-series, even CPUs and Android ARM GPUs. Cross-vendor multi-GPU on a single machine.
- **Memory efficiency**: 55 bytes/cell vs 344 bytes/cell for traditional LBM (6x less VRAM). 19 million cells per 1 GB VRAM.
- **Performance**: On a 4090 (24 GB), the maximum grid resolution is **~770³ cells with FP16 memory compression** — that's ~456 million cells.
- **Features**: Free surfaces (VOF-like), moving boundaries, temperature/thermal convection, particles (passive + 2-way coupled), turbulence subgrid model (Smagorinsky-Lilly), force/torque computation, STL geometry import with GPU voxelization, interactive 3D visualization, video rendering, VTK export for ParaView.
- **License**: Free for non-commercial use.
- **Setup**: Write C++ setup files (like OpenFOAM dictionaries but in code). Compile with Visual Studio (Windows) or g++ (Linux/macOS). Compilation takes ~5 seconds.

```cpp
// FluidX3D setup example — incompressible pipe flow
LBM lbm(512u, 128u, 128u, nu);  // grid resolution + viscosity
// ... set boundaries, voxelize STL, run ...
lbm.run(100000u);  // 100k time steps on GPU
```

**RTX 4090 capabilities with FluidX3D:**
| Grid Resolution | VRAM Used | Cells | Typical Throughput |
|:---|---:|---:|---:|
| 256³ | ~1 GB | 16.7M | >1000 time steps/sec |
| 512³ | ~7 GB | 134M | ~200 time steps/sec |
| 770³ | ~23 GB | 456M | ~60 time steps/sec |

### Other GPU CFD Options

| Solver | Method | GPU Backend | Maturity | Best For |
|:---|:---|:---|:---|:---|
| **FluidX3D** | Lattice-Boltzmann | OpenCL (all GPUs) | Production | General-purpose, free surfaces, moving objects |
| **Lethe** | FEM Navier-Stokes | CUDA (NVIDIA) | Production | Incompressible flow, validated against OpenFOAM |
| **GPUSPH** | Smoothed Particle Hydrodynamics | CUDA | Production | Free surface, multiphase, sloshing |
| **HiFiLES** | High-order FVM (compressible) | CUDA | Active research | Supersonic, shock waves |
| **RapidCFD** | FVM (OpenFOAM 4.0 fork) | CUDA | **Dead** (repo 404) | Based on 2016 OF. No successor. Not viable. |
| **PyFR** | Flux Reconstruction | CUDA/Metal | Production | High-order, GPU-accelerated, compressible |

---

## 2. The Mac Question: 128GB Unified Memory

> "A Mac with 128GB RAM — would that be good for this type of ML?"

### Yes, excellent. Here's why:

**Apple Silicon (M-series) unified memory** means the 128GB is shared between CPU and GPU — no PCIe transfer bottleneck. For the CFD → ML surrogate pipeline, this is a major advantage:

| Workload | Mac (M3/M4 Ultra, 128GB) | RTX 4090 (24GB) | Winner |
|:---|:---|:---|:---|
| FluidX3D simulation grid size | Up to ~1500³ (~3.4B cells) | Up to ~770³ (~456M cells) | Mac (7x larger) |
| PINN training batch size | Massive (full geometry in VRAM) | Limited by 24GB VRAM | Mac |
| PINN training speed (raw TFLOPS) | ~27 TFLOPS (M3 Ultra) | ~82 TFLOPS | 4090 (3x faster) |
| GNN mesh graph size | 128GB → massive graphs | 24GB → moderate | Mac |
| LLM inference (NL2FOAM) | 128GB → 70B models at 4-bit | 24GB → 12B models | Mac |

**Conclusion**: The 4090 is **faster** for training (3x raw compute). The 128GB Mac is **capable of much larger problems** that won't fit on a 4090 at all. For the physicist's use case (large parametric studies, big PINN surrogates, GNNs on complex meshes), the Mac is the better single-machine choice. The ideal setup is both: Mac for large-grid simulation + dataset generation, 4090 for GPU CFD (FluidX3D) + fast training iterations.

### Running FluidX3D on macOS

```bash
# Install XQuartz for interactive graphics
brew install --cask xquartz

# Clone and compile
git clone https://github.com/ProjectPhysX/FluidX3D.git
cd FluidX3D
chmod +x make.sh
./make.sh
```

FluidX3D on Apple Silicon uses the GPU via OpenCL. The Metal backend for PyTorch handles PINN/GNN training on the same GPU cores.

---

## 3. Integration Path: FluidX3D in freecad-mcp

### Architecture

```
FreeCAD (geometry)      ──→  cfd_create_domain  ──→  STL export
                                                          │
                                                          ▼
                                               FluidX3D (GPU via OpenCL)
                                               - LBM simulation
                                               - Force/torque extraction
                                               - VTK export → ParaView
                                                          │
                                                          ▼
                                               cfd_sample_for_pinns
                                               cfd_parametric_study
                                                          │
                                                          ▼
                                               PyTorch / NVIDIA Modulus
                                               (PINN surrogate on GPU)
```

### What we'd add to the MCP server

```python
# New MCP tool: cfd_run_fluidx3d
await cfd_run_fluidx3d(
    case_name="pipe_study",
    solver_params={
        "resolution": [512, 128, 128],
        "viscosity": 1e-6,
        "inlet_velocity": 0.05,
        "time_steps": 100000
    },
    gpu_device=0  # Select GPU (0 = fastest available)
)

# New MCP tool: cfd_fluidx3d_results
await cfd_fluidx3d_results(
    case_name="pipe_study",
    extract=["forces", "velocity_field", "residuals"]
)
```

This would compile and run FluidX3D setups from Python-generated C++ code, parse VTK/console output, and return structured results — all GPU-accelerated, all on the 4090 or Mac GPU.

---

## 4. OpenFOAM Fundamentals

OpenFOAM (Open Source Field Operation and Manipulation) is the industry-standard **CPU** CFD toolkit. It uses the finite-volume method (FVM) and runs MPI-parallel across CPU cores.

### When to use OpenFOAM vs FluidX3D

| Criterion | OpenFOAM | FluidX3D |
|:---|:---|:---|
| Physics model | FVM (Navier-Stokes) | LBM (Navier-Stokes equivalent) |
| Solver maturity | 30+ years, battle-tested | ~4 years, rapidly maturing |
| GPU acceleration | No (CPU-only MPI) | Yes (OpenCL, all GPUs) |
| Turbulence models | kEpsilon, kOmegaSST, LES, DES, transition | Smagorinsky-Lilly subgrid |
| Multiphase | interFoam (VOF), reactingMultiphaseEulerFoam | Free surface (SURFACE extension) |
| Mesh types | Structured + unstructured + polyhedral | Cartesian grid (voxelized STL) |
| Ecosystem | CfdOF workbench, ParaView, community | Standalone, VTK export |
| RAM for 1M cells | ~700 MB | ~55 MB |

### Case Directory Structure

```
case_name/
├── 0/                      # Initial/boundary field values
│   ├── U                   # Velocity field (m/s)
│   ├── p                   # Pressure field (m²/s² = Pa/ρ)
│   ├── k                   # Turbulent kinetic energy
│   └── omega / epsilon     # Turbulence dissipation
├── constant/
│   ├── polyMesh/
│   │   └── blockMeshDict   # Structured hex mesh definition
│   ├── transportProperties # Viscosity model (Newtonian)
│   └── turbulenceProperties # RAS/LES model selection
├── system/
│   ├── controlDict         # Time control, write interval, function objects
│   ├── fvSchemes           # Spatial discretisation (gradient, divergence, Laplacian)
│   ├── fvSolution          # Linear solver settings, relaxation factors
│   └── decomposeParDict    # Parallel domain decomposition
└── postProcessing/
    └── forces/             # Force coefficient time series
```

### Solver Selection

| Solver | Type | Use Case |
|:---|:---|:---|
| `simpleFoam` | Steady incompressible | Most engineering flows, design points |
| `pisoFoam` | Transient incompressible | Vortex shedding, startup transients |
| `pimpleFoam` | Transient, large Δt | Complex geometry pseudo-transient |
| `icoFoam` | Transient laminar | Educational, simple validation |
| `buoyantSimpleFoam` | Steady compressible + buoyancy | Natural convection, HVAC |
| `interFoam` | VOF multiphase | Free surfaces, sloshing, breaking waves |
| `rhoSimpleFoam` | Steady compressible | High-speed aerodynamics |
| `reactingFoam` | Reacting + compressible | Combustion, chemical reactions |

### Turbulence Models

| Model | Type | Wall Treatment | Best For |
|:---|:---|:---|:---|
| `laminar` | None | — | Re < critical |
| `kEpsilon` | 2-equation RANS | Wall functions (y+ > 30) | High-Re, free shear, industrial |
| `kOmegaSST` | 2-equation RANS | Resolve to wall (y+ ≈ 1) | Separation, transition, wall-bounded |
| `SpalartAllmaras` | 1-equation RANS | Resolve to wall | External aero, airfoils |

---

## 5. MCP Tool → File Mapping

| MCP Tool | OpenFOAM / FluidX3D Output |
|:---|:---|
| `cfd_create_domain` | STL geometry + blockMeshDict (OpenFOAM) or STL file (FluidX3D) |
| `cfd_configure_physics` | controlDict, fvSchemes, fvSolution, transportProperties, turbulenceProperties |
| `cfd_set_boundary` | `0/U`, `0/p`, `0/k`, `0/omega`, `0/nut` |
| `cfd_build_case` | Validates all of the above |
| `cfd_run_solver` | Docker → `blockMesh`, solver → time directories, forces |
| `cfd_read_results` | Parses: time dirs, solver log, `postProcessing/forces/*.dat` |
| `cfd_parametric_study` | Duplicates case N times; runs each variant |
| `cfd_nl2foam` | LLM generates all config files from natural language |
| `cfd_sample_for_pinns` | `pinn_points.csv` / `.json` / `.npz` |
| `cfd_fluidx3d_setup` | `config.json` (runner) + `setup.cpp` + `defines.hpp` (compile) |
| `cfd_fluidx3d_run` | `config.json` → runner reads at runtime. VTK → `export/*.vtk` |
| `cfd_fluidx3d_results` | Parses: run log, `RESULT {...}` JSON, VTK count |

---

## References

- [FluidX3D](https://github.com/ProjectPhysX/FluidX3D) — Free GPU CFD (OpenCL, all vendors)
- [FluidX3D Documentation](https://github.com/ProjectPhysX/FluidX3D/blob/master/DOCUMENTATION.md) — Setup guides, sample setups, video rendering
- [Lethe](https://github.com/lethe-cfd/lethe) — GPU-accelerated FEM CFD (CUDA)
- [GPUSPH](https://github.com/GPUSPH/gpusph) — SPH on GPU (CUDA)
- [OpenFOAM v10 User Guide](https://www.openfoam.com/documentation/user-guide/)
- [NVIDIA Modulus](https://developer.nvidia.com/modulus) — Physics-ML framework (PINNs)
- [PyTorch MPS](https://pytorch.org/docs/stable/notes/mps.html) — Apple Silicon GPU training
