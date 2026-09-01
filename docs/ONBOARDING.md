# Onboarding — freecad-mcp

## What this is for

FreeCAD MCP exposes parametric CAD, BIM/IFC, OpenFOAM+FluidX3D CFD, and CalculiX FEM as MCP tools + REST + web dashboard. First run needs FreeCAD + (optionally) PrusaSlicer + FluidX3D/OpenFOAM. This doc gets a first-timer from zero to `http://localhost:10945` and an NSIS install.

## Cost and accounts

| Question | Answer |
|----------|--------|
| Do I need an account? | No for local CAD/CFD. Optional: Printables/Thingiverse/GrabCAD for marketplace search (free accounts, API keys optional). |
| Free tier? | All local — FreeCAD 1.1.1, PrusaSlicer, FluidX3D (OpenCL) are free. OpenFOAM via Docker free. |
| Credit card required? | No. |
| Ongoing cost? | None locally. Optional cloud LLM (Ollama local is free). |
| Who bills? | No billing for core. |

## Prerequisites outside this repo

- **FreeCAD 1.1.1** — `winget install FreeCAD.FreeCAD` or extract `FreeCAD_1.1.1-Windows-x86_64-py311` to `D:\Dev\repos\FreeCAD\...` (set `FREECAD_PATH` if non-default).
- **Python 3.12+** + `uv` (`pip install uv` or `winget install --id=astral-sh.uv`).
- **Node 22** (`winget install OpenJS.NodeJS.LTS`) + `npm` (for `webapp/`).
- **Rust + Tauri CLI** (only for `just tauri-build`): `rustup` + `cargo install tauri-cli` or `npm i -D @tauri-apps/cli` (repo vendors it).
- Optional: **PrusaSlicer 2.8.1**, **FluidX3D** (`FLUIDX3D_PATH`), **Docker** (OpenFOAM), **Ollama** `:11434` for local LLM.

## First-timer setup

1. `just bootstrap` — `uv sync --all-extras` + `pre-commit install` + `webapp npm install` (needs `bun`? repo uses `npm`, `package-lock.json` present).
2. `start.ps1` (or `fleet-start.config.ps1` via `mcp-central-docs\scripts\Invoke-FleetWebappStart.ps1`) — clears port 10944/10945 zombies, starts `freecad_mcp.server:app` on 10944, Vite on 10945, opens browser. Or `just serve` for backend only.
3. Open `http://localhost:10945` — Dashboard hero → KPIs → Chat → Tools. Big red **Onboarding** cue under hero (`data-testid="onboarding-cue"`) is visible until FreeCAD is detected (status dot green). MOCK KPIs (MOCK badge, names like Joe Mocky) show until onboarding succeeds, then clear.
4. Verify: `curl http://localhost:10944/api/v1/status` → `{"freecad_ok": true}`. `just fleet-e2e-offline` for CI-safe chain smoke.
5. NSIS: `just tauri-build` (needs Rust) → `native/target/release/bundle/nsis/FreeCAD MCP_0.6.0_x64-setup.exe` (30 MB). Install hooks kill `freecad-mcp-backend.exe` pre-install.

## Pitfalls

- **FreeCAD not found** — set `$env:FREECAD_PATH="C:\...\FreeCAD.exe"` and `Test-Path $env:FREECAD_PATH`. Bridge falls back to `FreeCADCmd` subprocess if GUI not connected.
- **Port 10944 busy** — `native/src/backend.rs::free_port` kills via `taskkill` + `Get-NetTCPConnection` 240s poll; but `start.ps1` also clears. If TIME_WAIT persists, wait 60s or `Get-NetTCPConnection -LocalPort 10944 | % { taskkill /F /PID $_.OwningProcess }`.
- **Tauri stdio hijack** — `FREECAD_TAURI=1` forces `run_server.py` + `server.py:main()` to `--mode http` + `isatty()->False` (Gate J). Do not run `--mode stdio` from Tauri.
- **Vite chunk 1.5 MB** — expected (three.js + recharts). Warning is non-blocking.
- **src-tauri twin** — removed in v0.6.0; canonical is `native/` (0.6.0). Do not recreate `src-tauri/`.

## Sanity check

- `curl http://localhost:10944/api/v1/diagnostics` → `tool_count` 50+, `freecad_ok` true.
- Webapp Dashboard green dot, Chat page `ollama`/`lm_studio` auto-detect via `GET /api/llm/discover`, Zustand store `webapp/src/store/llm.ts` persists `llm_provider`/`llm_model` in localStorage.

## Declared doubles

- Webapp MOCK KPIs until onboarding — declared, badge `MOCK`, cleared after `freecad_ok`. No undeclared fakes.
