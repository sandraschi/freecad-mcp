# FreeCAD MCP

[![FastMCP Version](https://img.shields.io/badge/FastMCP-3.2.0-blue?style=flat-square&logo=python&logoColor=white)](https://github.com/sandraschi/fastmcp)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Linted with Biome](https://img.shields.io/badge/Linted_with-Biome-60a5fa?style=flat-square&logo=biome&logoColor=white)](https://biomejs.dev/)
[![Built with Just](https://img.shields.io/badge/Built_with-Just-000000?style=flat-square&logo=gnu-bash&logoColor=white)](https://github.com/casey/just)

## What can I do with this?

FreeCAD is a free professional CAD modeler (like SolidWorks but open-source). This project lets your AI assistant control it — through a chat interface, a web dashboard, or automated scripts. No need to open FreeCAD yourself.

| Category | What you can do |
|:---|:---|
| **Mechanical parts** | Convert STEP files to 3D-printable STL meshes. Create boxes, cylinders, spheres, cones by describing them. Inspect part volumes and bounding boxes. |
| **Architecture & construction** | Create walls, floor slabs, columns (rectangular or steel H-sections), windows, doors, and sloped roofs — all in millimeters. Export to `.ifc` files that architects and structural engineers can open. Import `.ifc` files from other design tools. *This is called BIM (Building Information Modeling) — 3D building design where every element knows what it is (a wall, a door, a load-bearing column), not just a shape. FreeCAD's Arch workbench handles this. QCAD is a 2D drafting tool — different domain.* |
| **Fluid simulation** | Model pipes, channels, and nozzles. Run airflow or water-flow simulations through OpenFOAM (the same tool Formula 1 teams use). Or run GPU-accelerated simulations with FluidX3D — uses your graphics card instead of the CPU. Describe a flow problem in plain English and let an LLM write the solver config. |
| **3D printing** | Slice STL files into G-code for your printer. Configurable profiles for different printers, filaments, and layer heights. |
| **Model marketplace** | Search Printables, Thingiverse, and GrabCAD for ready-made parts. Import them directly into your workspace. |
| **Machine learning** | Export point clouds from fluid domains to train neural networks that replace slow physics simulations. Generate datasets by running parameter sweeps automatically. |

| | |
|--:|--|
| **Example use cases** | "What's inside this STEP file?" — "Convert this assembly to 3D-printable STL" — "Design a room with two windows and a door" — "Simulate water flow through this pipe at 2 m/s" — "Find me a gear on Printables and slice it for my MK4" — "Train a neural network to predict airflow instead of running the full simulation every time" |
| **What it talks to** | FreeCAD 1.1.1+ (mechanical/architectural CAD), OpenFOAM 10 via Docker (fluid simulation), FluidX3D (GPU-accelerated simulation), PrusaSlicer 2.8+ (3D printing), Ollama (local LLM for natural language → config), Printables / Thingiverse / GrabCAD (model search) |
| **Network ports** | Web dashboard on **10945**, API + AI tools on **10944**, FreeCAD bridge on **10946** |
| **Start** | `just bootstrap` then `start.ps1` |

## Documentation Index

| Guide | Content |
| :--- | :--- |
| **[Installation](docs/install.md)** | Prerequisites, FreeCAD setup, PrusaSlicer, `just bootstrap` |
| **[Architecture](docs/architecture.md)** | TCP bridge, subprocess fallback, port layout, file pipeline |
| **[MCP Tools](docs/mcp-tools.md)** | All 36 tools with examples: geometry conversion, architecture (walls/floors/roofs/IFC), fluid simulation (OpenFOAM + FluidX3D), 3D printing, marketplace search, LLM assistance |
| **[Fluid simulation guide](docs/cfd-guide.md)** | Full walkthrough: creating domains, configuring physics, setting boundary conditions, running solvers, reading results, parametric sweeps, natural language config, and exporting data for neural network training |
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
- **Task runner**: [`just`](https://github.com/casey/just) — `just lint`, `just fix`, `just dev`
- **AI protocol**: FastMCP 3.2 with SSE transport

## License

MIT — see [LICENSE](LICENSE).
