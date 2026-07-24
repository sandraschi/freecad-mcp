# FreeCAD MCP

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://biomejs.dev"><img src="https://img.shields.io/badge/Linted_with-Biome-60a5fa?style=flat-square&logo=biome&logoColor=white" alt="Biome"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>

## Two ways to use this

This project exposes FreeCAD as a server that two different kinds of users talk to:

| | Who | How | What for |
|:---|:---|:---|:---|
| **MCP server** (port 10944) | **AI agents** — Claude Desktop, Cursor, Continue, any MCP client | Your AI assistant calls tools like `step_to_stl()` or `cfd_run_solver()` directly. You type "convert this STEP file and slice it for my printer" and it does the whole chain. | Hands-free CAD work. Agentic loops: the AI iterates design → simulate → analyze → refine without you touching the GUI. |
| **Web dashboard** (port 10945) | **Humans** — you, in a browser | A dark-mode React app with pages for converting files, browsing models, configuring fluid simulations, chatting with an LLM about CAD, viewing logs, and changing settings. | Point-and-click workflow. Upload a file, click Convert, download the STL. Fill in a form, click Run, see simulation results. |

Both talk to the same FreeCAD backend. An AI agent can prepare a simulation case, and you can inspect the results in the web dashboard — or vice versa.

## Scripting & automation

Everything the AI agents and the web dashboard call goes through the same REST API at `http://localhost:10944/api/v1/`. You can script against it directly from Python, curl, or any HTTP client:

```python
import requests

# Ask the AI assistant to convert a file — same API the webapp uses
r = requests.post("http://localhost:10944/api/v1/control/tool", json={
    "tool": "step_to_stl",
    "arguments": {"file_name": "bracket.step", "output_name": "bracket.stl"}
})
print(r.json())  # {"success": True, "output": "bracket.stl", ...}

# Or run a parametric study across 10 different geometries
for length in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.5, 10.0]:
    requests.post("http://localhost:10944/api/v1/control/tool", json={
        "tool": "cfd_create_domain",
        "arguments": {"domain_type": "channel", "length_m": length, "case_name": f"study_{length}m"}
    })
```

This is how you build headless pipelines: generate 100 geometry variants in a loop, run simulations on each, collect results, train a surrogate model. No GUI needed — FreeCAD runs in the background as a geometry engine.

## What can I do with this?

FreeCAD is a free professional CAD modeler (like SolidWorks but open-source). Through the API, you can:

| Category | What you can do |
|:---|:---|
| **Mechanical parts** | Convert STEP files to 3D-printable STL meshes. Create boxes, cylinders, spheres, cones by describing them. Inspect part volumes and bounding boxes. All managed through the persistent CAD file depot with full CRUD. |
| **Architecture & construction** | Create walls, floor slabs, columns (rectangular or steel H-sections), windows, doors, and sloped roofs — all in millimeters. Export to `.ifc` files that architects and structural engineers can open. Import `.ifc` files from other design tools. *This is called BIM (Building Information Modeling) — 3D building design where every element knows what it is (a wall, a door, a load-bearing column), not just a shape. FreeCAD's Arch workbench handles this. QCAD is a 2D drafting tool — different domain.* |
| **Fluid simulation** | Model pipes, channels, and nozzles. Run airflow or water-flow simulations through OpenFOAM (the same tool Formula 1 teams use). Or run GPU-accelerated simulations with FluidX3D — uses your graphics card instead of the CPU. Describe a flow problem in plain English and let an LLM write the solver config. |
| **Structural analysis (FEM)** | Run finite element analysis with CalculiX: stress, strain, displacement, safety factor. 10 material presets (steel, aluminum, titanium, carbon fiber...), automatic meshing via Gmsh, and an end-to-end `run_fem_analysis` convenience tool. Same tool Formula 1 teams use for chassis and wing analysis. |
| **3D printing** | Slice STL files into G-code for your printer. Configurable profiles for different printers, filaments, and layer heights. |
| **Model marketplace** | Search Printables, Thingiverse, and GrabCAD for ready-made parts. Import them directly into your workspace. |
| **Machine learning** | Export point clouds from fluid domains to train neural networks that replace slow physics simulations. Generate datasets by running parameter sweeps automatically. |

| | |
|--:|--|
| **Example use cases** | "What's inside this STEP file?" — "Convert this assembly to 3D-printable STL" — "Design a room with two windows and a door" — "Simulate water flow through this pipe at 2 m/s" — "Find me a gear on Printables and slice it for my MK4" — "Train a neural network to predict airflow instead of running the full simulation every time" — "Browse my persistent CAD depot, create a test bracket, rename and tag it" |
| **What it connects to** | FreeCAD 1.1.1+ (the CAD engine), OpenFOAM 10 via Docker (fluid simulation), FluidX3D via OpenCL (GPU-accelerated simulation), PrusaSlicer 2.8+ (3D printing), Ollama (local LLM), Printables / Thingiverse / GrabCAD (model search) |
| **Ports** | **10944** = MCP server (AI agents), **10945** = web dashboard (humans), **10946** = FreeCAD bridge (internal) |
| **Start** | `just bootstrap` then `start.ps1` |

## Documentation Index

| Guide | Content |
| :--- | :--- |
| **[Installation](docs/install.md)** | Prerequisites, FreeCAD setup, PrusaSlicer, `just bootstrap` |
| **[Architecture](docs/architecture.md)** | TCP bridge, subprocess fallback, port layout, file pipeline |
| **[MCP Tools](docs/mcp-tools.md)** | All 46 tools with examples: geometry conversion, architecture (walls/floors/roofs/IFC), structural FEM (CalculiX stress/strain), fluid simulation (OpenFOAM + FluidX3D), 3D printing, marketplace search, LLM assistance, and **CAD file depot** with persistent storage + full CRUD |
| **[Fleet CFD pipeline](docs/fleet-pipeline.md)** | qcad DXF → freecad OpenFOAM/FluidX3D → resonite/godot/robotics handoff |
| **[Fluid simulation guide](docs/cfd-guide.md)** | Full walkthrough: creating domains, configuring physics, setting boundary conditions, running solvers, reading results, parametric sweeps, natural language config, and exporting data for neural network training |
| **[Flow visualization & render guide](docs/flow-visualization.md)** | What FluidX3D produces (VTK, OBJ, WebM, PNG, CSV). How to turn it into video, game engine assets, or VR visuals. Glossary of terms (VTK, OBJ, streamlines, LBM, MLUPS, heatmaps). Integration with Unity3D, Godot, Blender, Resonite. |
| **[OpenFOAM & GPU solvers](docs/openfoam.md)** | Solver reference, turbulence model guide, GPU acceleration options (FluidX3D on RTX 4090 and Apple Silicon), Mac vs PC comparison |
| **[AI Tooling](docs/ai-tooling.md)** | Ollama chat, agentic CAD reasoning, sampling workflows |
| **[About FreeCAD](docs/about-freecad.md)** | History, community, Python scripting, 300+ workbenches, vs SolidWorks/Fusion |
| **[Marketplace](docs/marketplace.md)** | Searching and importing models from Printables, Thingiverse, GrabCAD |
| **[Webapp README](webapp/README.md)** | Dashboard frontend: pages, viewer, proxy, development |

## Quick Start

```powershell
just bootstrap   # uv sync + npm install
start.ps1        # kills zombies, starts backend + frontend, opens browser
```

## MCP Client Config

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

## Quality

- **Python**: [Ruff](https://astral.sh/ruff) linter + formatter (zero-config, sub-millisecond)
- **Frontend**: [Biome](https://biomejs.dev/) linter + formatter
- **Task runner**: [`just`](https://github.com/casey/just) — `just lint`, `just fix`, `just dev`, `just tauri-build`
- **Native desktop**: Tauri 2.0 + PyInstaller sidecar — `just tauri-build` (ports 10944/10945)
- **AI protocol**: FastMCP 3.2 with SSE transport

## See also — other construction & design tools in the fleet

| Repo | What it does |
|:---|:---|
| [**QCad MCP**](https://github.com/sandraschi/qcad-mcp) | 2D technical drafting — floor plans, schematics, blueprints |
| [**Blender MCP**](https://github.com/sandraschi/blender-mcp) | 3D modeling, animation, rendering, sculpting |
| [**Unity3D MCP**](https://github.com/sandraschi/unity3d-mcp) | Game engine, real-time 3D, physics, VR/AR |
| [**Inkscape MCP**](https://github.com/sandraschi/inkscape-mcp) | Vector graphics — logos, illustrations, SVGs |
| [**GIMP MCP**](https://github.com/sandraschi/gimp-mcp) | Raster image editing — photos, textures, pixel art |

Each follows the same pattern: MCP server for AI agents + web dashboard for humans, sharing a common API.

## CFD fleet moat

Only fleet repo with **OpenFOAM + GPU FluidX3D + NL2FOAM + PINN sampling + VTK/OBJ export** for downstream Resonite/Godot/robotics handoff. Competitive analysis: [mcp-central-docs/projects/CAD_FLEET_COMPETITIVE.md](https://github.com/sandraschi/mcp-central-docs/blob/master/projects/CAD_FLEET_COMPETITIVE.md). Pipeline: [docs/fleet-pipeline.md](docs/fleet-pipeline.md).

```powershell
just fleet-e2e-offline   # CI-safe config chain smoke
just fleet-e2e-integration   # GPU FluidX3D setup->compile->run (local)
just fleet-e2e-chain     # qcad extrude -> freecad setup (HTTP)
```

## License

MIT — see [LICENSE](LICENSE).
