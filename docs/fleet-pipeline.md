# Fleet pipeline — qcad-mcp to freecad-mcp to downstream viz

Last updated: 2026-05-28

freecad-mcp side of the CAD fleet CFD pipeline. Complements [qcad-mcp/docs/freecad-pipeline.md](https://github.com/sandraschi/qcad-mcp/blob/main/docs/freecad-pipeline.md).

## End-to-end chain

```text
qcad-mcp (10966)
  plan_agentic / plan_extrude
    -> STL in CAD depot
freecad-mcp (10944)
  mesh_to_solid (optional B-Rep)
  cfd_create_domain / cfd_fluidx3d_setup
    -> OpenFOAM case OR FluidX3D setup.cpp
  cfd_run_solver (Docker) OR cfd_fluidx3d_run (GPU)
    -> VTK / CSV / force logs
  cfd_fluidx3d_export_for_render
    -> OBJ streamlines + CSV for VR/robotics
resonite-mcp / godot-mcp / robotics-mcp
  import meshes + field overlays
```

## Ports

| Service | MCP / API | Web UI |
|---------|-----------|--------|
| qcad-mcp | 10966 | 10967 |
| freecad-mcp | 10944 | 10945 |

## Tool sequence (CFD path)

### 1. 2D plan from qcad-mcp

```python
# qcad-mcp — extrude floor plan to STL
await plan_extrude(dxf_name="office.dxf", height_mm=2800, output_name="office_walls.stl")
```

### 2. Import to FreeCAD (optional solid)

Requires FreeCAD TCP bridge (GUI mode):

```python
await mesh_to_solid(file_name="office_walls.stl", output_name="office_solid.fcstd")
```

### 3. OpenFOAM (CPU / Docker)

```python
await cfd_create_domain(domain_type="channel", case_name="office_flow", length_m=10.0)
await cfd_configure_physics(case_name="office_flow", flow_type="incompressible", turbulence="kEpsilon")
await cfd_set_boundary(case_name="office_flow", patch="inlet", bc_type="fixedValue", field="U", value="(1 0 0)")
await cfd_build_case(case_name="office_flow")
await cfd_run_solver(case_name="office_flow")
await cfd_read_results(case_name="office_flow")
```

Or natural language:

```python
await cfd_nl2foam(
    case_name="office_flow",
    description="Air at 2 m/s through a 10 m channel, k-epsilon turbulence, Re ~ 100k",
)
```

### 4. FluidX3D (GPU — RTX 4090)

```python
await cfd_fluidx3d_status()
await cfd_fluidx3d_prebuilt()  # skip compile when FLUIDX3D_BINARY is set
await cfd_fluidx3d_setup(case_name="office_gpu", domain_type="stl", stl_file="office_walls.stl")
await cfd_fluidx3d_compile(case_name="office_gpu")
await cfd_fluidx3d_run(case_name="office_gpu")
await cfd_fluidx3d_results(case_name="office_gpu")
await cfd_fluidx3d_export_for_render(case_name="office_gpu", export_csv=True)
```

### 5. Downstream handoff

Export artifacts from `fluidx3d_cases/<case>/` or OpenFOAM `postProcessing/`:

- **VTK** — field volume data
- **OBJ streamlines** — lightweight mesh for Resonite / Godot
- **CSV** — robotics digital-twin telemetry

## Fleet E2E smoke

Offline (CI — no Docker/GPU):

```powershell
cd D:\Dev\repos\freecad-mcp
uv run python scripts/fleet_e2e_smoke.py --offline --strict
```

HTTP (local fleet):

```powershell
# Terminal A: just serve (freecad) + qcad start
uv run python scripts/fleet_e2e_smoke.py --strict
```

## Competitive moat

No commercial MCP product chains **2D DXF -> 3D CFD (OpenFOAM + GPU LBM) -> social VR / robotics** in one local fleet. See [CAD_FLEET_COMPETITIVE.md](https://github.com/sandraschi/mcp-central-docs/blob/master/projects/CAD_FLEET_COMPETITIVE.md).

## References

- [cfd-guide.md](cfd-guide.md)
- [openfoam.md](openfoam.md)
- [flow-visualization.md](flow-visualization.md)
- [mcp-tools.md](mcp-tools.md)
