# Flow Visualization Guide

What FluidX3D simulations produce and how to turn them into something you can see,
animate, and drop into game engines or creative pipelines.

---

## 1. What FluidX3D Produces

When `cfd_fluidx3d_run` finishes, these files are in the case directory:

| Format | Extension | What it is | Can you see it? |
|--------|-----------|------------|-----------------|
| **VTK** | `.vtk` | Simulation field data — velocity vectors and density at every cell in the 3D grid | Not directly. Needs ParaView or our render pipeline. |
| **OBJ** | `.obj` | 3D geometry (streamlines = flow path curves, or STL geometry). Standard format for every 3D tool. | Yes — open in Blender, Unity, Godot, Windows 3D Viewer. |
| **WebM** | `.webm` | Heatmap video — 2D slice animation of velocity magnitude, color-coded. | Yes — any browser, video player. |
| **PNG** | `.png` | Single heatmap frame — velocity magnitude slice as a static image. | Yes — any image viewer. |
| **CSV** | `.csv` | Velocity point cloud data for custom analysis or ML training. | In a spreadsheet. |
| **JSON** | `.json` | Simulation config, force history, MLUPS throughput. | As text. |
| **Log** | `.log` | Raw solver stdout — STEP/FORCE/DONE lines parsed by results tool. | As text in any editor. |

### What each format is for

**VTK (Visualization Toolkit)** — The raw scientific output. Contains a 3D grid where
every cell has a velocity vector (Ux, Uy, Uz in m/s) and a density value. ParaView
opens these directly. For everyone else, use our render pipeline (section 3) to
convert to video or 3D geometry.

**OBJ (Wavefront OBJ)** — The standard 3D geometry format supported by every 3D tool
since 1985. Our `cfd_fluidx3d_export_for_render` tool generates **streamlines** —
curves that follow the flow path, like putting dye in water and tracing where it goes.
Each streamline is a polyline (connected line segments) with vertex positions in
real-world meters.

**WebM (Video)** — Our `cfd_fluidx3d_render` tool reads VTK velocity fields,
renders each time step as a colored heatmap (blue=slow, red=fast), and stitches
them into a WebM video. Playable in any browser, embeddable in webapps.

**CSV (Comma-Separated Values)** — Velocity point cloud: x, y, z coordinates with
vx, vy, vz velocity components. Use this for training neural networks (PINNs),
importing into data analysis tools, or custom shader effects.

---

## 2. OBJ Streamlines: Game Engine & VR Pipeline

The OBJ streamlines from `cfd_fluidx3d_export_for_render` are the primary bridge
from CFD into creative tools. A streamline is just a 3D curve — the same kind of
object a 3D artist would model as a path.

### Into Unity3D

```text
1. Copy {case_name}_streamlines.obj from the case directory
2. Unity: Assets → Import New Asset → select the .obj file
3. The streamlines appear as 3D curves in world space
4. Add a Line Renderer component or Tube shader to make them visible
5. Animate: iterate opacity/color over time for flow visualization
```

Unity imports OBJ natively — no plugin needed. The streamlines are in real-world
meters, so they match the domain geometry exactly. Use the Line Renderer with
a custom gradient (blue→cyan→yellow→red) mapped to velocity magnitude.

**VR use case:** Place the streamlines in a VR scene. The user walks through the
flow field, seeing the paths the fluid takes around objects. For Resonite, import
the OBJ as a `MeshRenderer` slot and apply a metallic/transparent material.

### Into Godot

```text
1. Copy .obj file to project's assets/ folder
2. Godot auto-imports it as a Mesh resource
3. Add a MeshInstance3D node, assign the OBJ mesh
4. Material → StandardMaterial3D → set Emission + Transparency
5. Animate with a shader or script for pulsing flow visualization
```

Godot 4 has native OBJ import. For animated flow, attach a script that sweeps
a color along the streamline vertices using a custom shader material.

### Into Blender (for rendering / video)

```text
1. File → Import → Wavefront (.obj)
2. The streamlines appear as curve objects
3. Add a Bevel modifier to give them visible thickness
4. Add an Emission shader with a color ramp
5. Render with Cycles/Eevee for production video
```

Blender is the intermediate step if you want production-quality renders of CFD
results: lighting, reflections, motion blur, compositing.

### Into Resonite (VR social platform)

Resonite imports OBJ via the `MeshRenderer` component. Place the streamlines in a
world, add a `PBS_Metallic` material with emissive color, and users can walk
through the flow field in VR. The fleet uses this for "inhabit the simulation" —
engineers experience the flow around their designs at 1:1 scale.

---

## 3. Video Render Pipeline (Automatic)

`cfd_fluidx3d_render` converts VTK velocity fields into a WebM heatmap animation.
No manual steps:

```python
# One call — produces a WebM video of velocity magnitude over time
await cfd_fluidx3d_render(case_name="pipe_gpu", fps=10)
# Returns: {"success": true, "video_path": "...", "frame_count": 24, "duration_s": 2.4}
```

The video shows:
- XY mid-plane slice through the domain
- Velocity magnitude as a color heatmap (blue = slow → cyan → green → yellow → red = fast)
- A colorbar legend with min/max values
- Frame counter labels
- One frame per VTK time step

**Requirements:** Pillow (PNG rendering) + ffmpeg (video encoding).
Install: `pip install Pillow` and `winget install ffmpeg` or `choco install ffmpeg`.

### Fallback: single PNG frame

If ffmpeg is not available, the tool renders a single PNG of the final time step
instead of a video.

### Serving in the webapp

Rendered videos are served at:
```
GET /api/v1/case-files/{case_name}/{case_name}_simulation.webm
GET /api/v1/case-files/{case_name}/{case_name}_result.png
```

The FluidX3D page in the web dashboard has a **Video** tab with an HTML5 video
player that auto-loads the rendered video.

---

## 4. ParaView — "CFD to the Max"

[ParaView](https://www.paraview.org/) is an open-source scientific visualization
workstation (500 MB). Think "Photoshop for CFD data." **You don't need it** —
our `cfd_fluidx3d_render` already produces video and PNG from VTK files, and
`cfd_fluidx3d_export_for_render` produces OBJ streamlines for game engines.

But for power users who want full control, ParaView adds:

| You want to... | Built-in `cfd_fluidx3d_render` | ParaView |
|----------------|--------------------------------|----------|
| See a heatmap video | ✅ One-click `cfd_fluidx3d_render` | Manual setup |
| Slice at any angle | ❌ Only XY mid-plane | ✅ Any plane, any position, animated sweep |
| Streamlines from arbitrary seed points | ❌ Fixed inlet seeds | ✅ Seeds from line, plane, point — any location |
| Vortex / Q-criterion iso-surfaces | ❌ Not available | ✅ Contour filter on calculated Q field |
| Volume rendering (3D semi-transparent) | ❌ 2D slice only | ✅ GPU volume rendering, rotate in real-time |
| Probe values at exact coordinates | ❌ Not available | ✅ Plot Over Line, Plot Over Time |
| Compare multiple simulations side-by-side | ❌ One case at a time | ✅ Open multiple VTK files, link views |
| Export publication-quality renders | ❌ 800x600 PNG max | ✅ Up to 8K, transparent background, annotation |
| Script automation (pvpython) | ❌ Not available | ✅ Full Python scripting for batch rendering |

### Auto-install (optional)

```powershell
# One command — 500 MB download
winget install Kitware.ParaView
```

After install, VTK files are double-clickable from the case directory:

### Vorticity & Q-Criterion (example ParaView workflow)

To replicate FluidX3D's Q-criterion view:
1. **File → Open** → select `.vtk` files (Ctrl+A for time series) → **Apply**
2. Filter → **Gradient** on velocity field
3. Filter → **Calculator**: `Q = -0.5 * (dU_dx^2 + dV_dy^2 + dW_dz^2 + 2*dU_dy*dV_dx + 2*dU_dz*dW_dx + 2*dV_dz*dW_dy)`
4. Filter → **Contour** on Q at isovalue 0.01 (positive = vortex)
5. Color by velocity magnitude
6. **File → Save Animation** for video export

### Loading FluidX3D VTK files

```text
1. Open ParaView
2. File → Open → navigate to %TEMP%\fluidx3d\bin\export\ or case directory
3. Select all .vtk files → Open
4. Click Apply in the Properties panel
5. ParaView auto-detects the structured grid and velocity fields
```

---

## 5. vtk.js (Browser 3D)

[vtk.js](https://kitware.github.io/vtk-js/) renders VTK data directly in the browser.
Useful for embedding 3D flow visualization in webapps:

```javascript
import vtkGenericRenderWindow from 'vtk.js/Sources/Rendering/Misc/GenericRenderWindow';
import vtkXMLPolyDataReader from 'vtk.js/Sources/IO/XML/XMLPolyDataReader';

const reader = vtkXMLPolyDataReader.newInstance();
reader.setUrl('http://localhost:10944/api/v1/case-files/pipe_gpu/u_00100.vtk');
```

Requires building vtk.js into the webapp bundle — not currently integrated.

---

## 6. Glossary

| Term | Meaning | Plain English |
|------|---------|---------------|
| **VTK** | Visualization Toolkit format | A file format for 3D scientific data (velocity, pressure, temperature on a grid). Think "the raw simulation output." Cannot be viewed as an image — needs a renderer. |
| **OBJ** | Wavefront OBJ format | A file format for 3D geometry (vertices, edges, faces). Every 3D tool since the 1980s opens OBJ — Blender, Unity, Godot, Maya, 3ds Max. |
| **Streamline** | A curve traced through a velocity field | Follow the path a particle would take through the flow. Like dye in water. The `export_for_render` tool generates these as OBJ files. |
| **WebM** | Web Media video format | Open video format (VP9 codec). Plays in every browser. Our render pipeline produces this from VTK time series. |
| **Heatmap** | Color-coded data visualization | A 2D image where color represents value. Blue = slow velocity, red = fast. The video render produces these as frames. |
| **LBM** | Lattice Boltzmann Method | The math FluidX3D uses to simulate fluids. Instead of solving the Navier-Stokes equations directly, LBM simulates particle distributions bouncing between grid cells. Parallelizes beautifully on GPUs. |
| **MLUPS** | Million Lattice Updates Per Second | How fast the simulation runs. Higher = faster. RTX 4090 does ~200-500 MLUPS depending on grid size. |
| **OpenCL** | Open Computing Language | The GPU programming framework FluidX3D uses. Works on NVIDIA, AMD, Intel, Apple Silicon — any GPU from any vendor. |
| **ParaView** | Professional scientific visualization | Like Photoshop for CFD data. 500 MB open-source desktop app. Optional — our render pipeline produces video/PNG/OBJ without it. Install: `winget install Kitware.ParaView` |

---

## 7. Summary: Which Output for Which Use Case

| You want to... | Use this tool | Produces | Open with... |
|----------------|---------------|----------|--------------|
| See forces, MLUPS, convergence | `cfd_fluidx3d_results` | JSON + log | Any text viewer |
| See a heatmap video of flow | `cfd_fluidx3d_render` | WebM video | Browser, video player |
| See a single frame as image | `cfd_fluidx3d_render` (no ffmpeg) | PNG image | Any image viewer |
| Import flow into a game engine | `cfd_fluidx3d_export_for_render` | OBJ streamlines | Unity, Godot, Blender, Resonite |
| Import into VR (Resonite) | `cfd_fluidx3d_export_for_render` | OBJ streamlines | Resonite MeshRenderer |
| Train a neural network | `cfd_fluidx3d_export_for_render` with `export_csv=True` | CSV point cloud | Python, PyTorch, TensorFlow |
| Professional post-processing (vortices, volume rendering, publication) | Manual: download VTK or `winget install Kitware.ParaView` | VTK files | ParaView |
| Live monitoring during sim | Enables `INTERACTIVE_GRAPHICS` | GPU window | FluidX3D built-in renderer |

All output files are served via the REST API:
- `GET /api/v1/case-files/{case_name}/{filename}` — any case file
- `GET /api/v1/download/{filename}` — uploads and outputs
