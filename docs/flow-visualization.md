# Flow Visualization Guide

How to inspect, render, and post-process CFD results from FluidX3D and OpenFOAM simulations.

## 1. FluidX3D Interactive Graphics Mode

FluidX3D includes a built-in real-time GPU renderer for live visualization during simulation.
This is **the** live visualizer — no external tools needed for interactive inspection.

### Enabling

Edit `defines.hpp` (or `src/defines.hpp` in the FluidX3D source tree) and add:

```cpp
#define INTERACTIVE_GRAPHICS
```

When `cfd_fluidx3d_setup` generates `defines.hpp`, add `INTERACTIVE_GRAPHICS` to the
extensions list. Recompile with `cfd_fluidx3d_compile` after enabling.

### Visualization Modes

Press number keys during the running simulation to switch between modes:

| Key | Mode | What It Shows |
|-----|------|---------------|
| `2` | Velocity field | Colored by velocity magnitude, arrows on lattice cells |
| `3` | Streamlines | Advected tracer lines following the velocity field |
| `4` | Q-criterion | Vorticity iso-surfaces (vortex tubes, wake structures) |
| `5` | Free surface | Fluid interface (for multiphase / free-surface flows) |

### Keyboard Controls

| Key | Action |
|-----|--------|
| `P` | Start / pause simulation |
| `H` | Toggle help overlay |
| `F` | Toggle fullscreen |
| `Mouse drag` | Rotate camera |
| `Scroll` | Zoom |
| `Right-click drag` | Pan |
| `1` | Reset to default view |

### Recording Video

With `INTERACTIVE_GRAPHICS` enabled, FluidX3D renders frames to the GPU window.
Capture to video using ffmpeg screen recording:

**Windows:**
```powershell
ffmpeg -f gdigrab -framerate 30 -i desktop -vf "crop=1920:1080:0:0" output.mp4
```

**Linux:**
```bash
ffmpeg -f x11grab -framerate 30 -video_size 1920x1080 -i :0.0 output.mp4
```

Replace the crop/size values with the FluidX3D window dimensions.

> **Note:** `INTERACTIVE_GRAPHICS` adds a small per-frame overhead from GPU rendering.
> For maximum throughput benchmarking, disable it.

---

## 2. ParaView

[ParaView](https://www.paraview.org/) is the standard desktop post-processor for VTK-based CFD.

### Loading Files

#### From FluidX3D

FluidX3D writes VTK files to the binary's export directory (e.g. `bin/export/`).
These are ASCII VTK format with cell data arrays for velocity (`u.x`, `u.y`, `u.z`),
density (`rho`), and flags.

1. Launch ParaView
2. **File → Open** → navigate to the `.vtk` files
3. Select multiple files for a time series (Ctrl+A)
4. Click **Apply** in the Properties panel

#### From OpenFOAM

Use the built-in OpenFOAM reader:

1. **File → Open** → navigate to your OpenFOAM case directory
2. Select `case.foam` (or create an empty file named `case.foam`)
3. Click **Apply**

Alternatively, run `foamToVTK` first to convert OpenFOAM data to VTK, then load as above.

### Common Visualizations

| Technique | How To |
|-----------|--------|
| **Slice** | Filter → Alphabetical → Slice. Cut plane through domain to show scalar/vector fields. |
| **Streamlines** | Filter → Alphabetical → Stream Tracer. Seeds from line, plane, or point source. |
| **Contour** | Filter → Alphabetical → Contour. Iso-surface of a scalar (e.g. Q-criterion, pressure). |
| **Volume rendering** | Representation → Volume. GPU-accelerated volumetric rendering of scalar fields. |
| **Glyphs** | Filter → Alphabetical → Glyph. Arrows/spheres showing vector direction and magnitude. |
| **Calculator** | Filter → Alphabetical → Calculator. Custom derived fields (e.g. `mag(u.x*iHat + u.y*jHat)`). |

### Animations

1. **View → Animation View** to open the animation panel
2. Set the number of frames and time step correspondence
3. **File → Save Animation** to export as AVI, OGV, or image sequence

### Data Extraction

- **Plot Over Line**: Filter → Alphabetical → Plot Over Line. Extract 1D profiles.
- **Plot Selection Over Time**: Plot a point/cell value across a time series.
- **Save Data**: File → Save Data. Export as CSV, VTK, or other formats.

### Vorticity & Q-Criterion

To replicate FluidX3D's Q-criterion view in ParaView:

1. Apply **Gradient** filter to the velocity field
2. Apply **Calculator** filter with formula:

```
Q = -0.5 * (dU_dx^2 + dV_dy^2 + dW_dz^2 + 2*dU_dy*dV_dx + 2*dU_dz*dW_dx + 2*dV_dz*dW_dy)
```

3. Apply **Contour** on Q, set isovalue to a small positive number (e.g. 0.01)
4. Color by `u` magnitude

---

## 3. vtk.js

[vtk.js](https://kitware.github.io/vtk-js/) is Kitware's in-browser VTK renderer.
It enables browser-based 3D visualization without installing ParaView.

**Use cases**: embedding CFD results in web dashboards, lightweight sharing.

Documentation: <https://kitware.github.io/vtk-js/docs/>

### Quick Example

```javascript
import vtkGenericRenderWindow from 'vtk.js/Sources/Rendering/Misc/GenericRenderWindow';
import vtkXMLPolyDataReader from 'vtk.js/Sources/IO/XML/XMLPolyDataReader';

const reader = vtkXMLPolyDataReader.newInstance();
reader.setUrl('http://localhost:10944/api/v1/case-files/pipe_gpu/u_00100.vtk');
reader.then(() => {
  // Render in container
});
```

vtk.js supports `.vtk` (legacy ASCII), `.vtp` (XML polydata), `.vti` (XML image data),
and `.vtu` (XML unstructured grid) — all relevant to FluidX3D and OpenFOAM output.

---

## 4. Summary

| Tool | Use Case | Strengths |
|------|----------|-----------|
| **FluidX3D INTERACTIVE_GRAPHICS** | Live simulation monitoring | Zero-latency GPU rendering, velocity streamlines, Q-criterion, free surfaces. No file I/O. |
| **ParaView** | Detailed post-processing | Full pipeline: slices, contours, streamlines, volume rendering, animations, data export. |
| **vtk.js** | Web embedding | Browser-native, no install. Good for dashboards and sharing. |

**FluidX3D's interactive mode is the live visualizer.** Use it while the simulation runs.
Use ParaView for publication-quality post-processing after the run completes.
