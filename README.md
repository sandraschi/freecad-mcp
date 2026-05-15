# FreeCAD MCP

[![FastMCP Version](https://img.shields.io/badge/FastMCP-3.2.0-blue?style=flat-square&logo=python&logoColor=white)](https://github.com/sandraschi/fastmcp)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Linted with Biome](https://img.shields.io/badge/Linted_with-Biome-60a5fa?style=flat-square&logo=biome&logoColor=white)](https://biomejs.dev/)
[![Built with Just](https://img.shields.io/badge/Built_with-Just-000000?style=flat-square&logo=gnu-bash&logoColor=white)](https://github.com/casey/just)

**CAD + BIM + CFD, through your AI assistant.** — Convert STEP assemblies, create parametric building elements (walls, slabs, columns, windows, doors, roofs), export/import IFC, run CFD simulations (OpenFOAM), generate NLP→solver configs, export point clouds for PINNs, inspect geometry, create primitives, slice for printing, and browse marketplaces — all via MCP tools and a Vite dashboard.

| | |
|--:|--|
| **You might use this if…** | You want an AI to reason about CAD files, convert formats, prepare 3D prints, or search model marketplaces without opening FreeCAD. |
| **What it connects to** | FreeCAD 1.1.1+ (OCCT kernel), OpenFOAM 10 (Docker), PrusaSlicer 2.8+, Ollama (NL2FOAM), Printables / Thingiverse / GrabCAD APIs |
| **Ports** | Backend **10944**, Dashboard **10945**, TCP Bridge **10946** |
| **Start** | `just bootstrap` then `start.ps1` |

## Documentation Index

| Guide | Content |
| :--- | :--- |
| **[Installation](docs/install.md)** | Prerequisites, FreeCAD setup, PrusaSlicer, `just bootstrap` |
| **[Architecture](docs/architecture.md)** | TCP bridge, subprocess fallback, port layout, file pipeline |
| **[MCP Tools](docs/mcp-tools.md)** | All 30 tools: CAD operations, BIM/Arch (walls, slabs, columns, IFC), CFD/OpenFOAM (domain, physics, solver, NL2FOAM, PINNs), slicing, marketplace search/download, GUI launch, Prefab card — with examples |
| **[CFD Pipeline](docs/cfd-guide.md)** | Complete CFD guide: architecture, installation, tool reference, fluid properties, boundary conditions, workflow examples, NL2FOAM, PINN sampling, troubleshooting, benchmarks |
| **[OpenFOAM & GPU](docs/openfoam.md)** | OpenFOAM fundamentals, solver/turbulence model selection, GPU acceleration (RTX 4090), RapidCFD, FluidX3D, PINN surrogate path, case directory structure, mesh quality targets |
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

## Industrial Quality Stack

- **Python (Core)**: [Ruff](https://astral.sh/ruff) for linting and formatting.
- **Webapp (UI)**: [Biome](https://biomejs.dev/) for sub-millisecond linting.
- **Protocol**: FastMCP 3.2 SSE transport with hardened stdout/stderr isolation.
- **Automation**: [Justfile](./justfile) recipes for all fleet operations (`just lint`, `just fix`, `just dev`).

## License

MIT — see [LICENSE](LICENSE).
