# Handover — freecad-mcp (2026-09-01)

## State — SHIPPED, proven
- **NSIS `FreeCAD MCP_0.6.0_x64-setup.exe` 30.2 MB** — CUA smoke **11/11 PASS** (Kill→Install→Launch healthy attempt 5→Feature 200→Diagnostics 200→Uninstall 0). Backend 27.6 MB, frontend Vite 1.50 MB (manualChunks react/vendor), `cargo check` 0, `tsc` 0, `pytest --cov 15` 123 passed.
- **MCPB `dist/freecad-mcp-v0.6.0.mcpb` 162 KB, 85 tools, validate PASS.**
- **Gate F/G/H/J fixed**: `native/src/main.rs` spawn backend on thread + `kill+wait` on Exit; `backend.rs` `resource_dir`/`exe_dir` fallback + `free_port` 10s; `run_server.py` + `server.py::main()` isatty shim + `stdio→http` when `FREECAD_TAURI=1`; `build-sidecar.ps1` → `resources/`+`binaries/`; `src-tauri/` twin removed.
- **Sweep**: `AGENTS/docs/manifest/justfile`, `.gitignore` (`build/`,`cua-reports/`,`data/`,`*.obj`,`*.bak*`), zustand store, CONFIGURATION/ONBOARDING docs, vite manualChunks, renovate/coverage, glama 85 tools, mcpb fresh-stage.
- Pushed through `1b860058` (`.assess-fix-timestamp` 82/100 SOTA). MCD project page synced `99799171`.

## Files this session
`native/src/main.rs`, `native/src/backend.rs`, `run_server.py`, `src/freecad_mcp/server.py`, `native/build-sidecar.ps1`, `native/package.json`, `webapp/vite.config.ts`, `webapp/src/store/llm.ts`, `pyproject.toml`, `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, `.gitattributes`, `docs/CONFIGURATION.md`, `docs/ONBOARDING.md`, `glama.json`, `mcpb/*`, `reports/assess-2026-09-01.md`.

## Residual (deferred)
- `llms-full.txt`/`docs/mcp-tools.md` auto-regen (generator `freecad_mcp.utils.llms_txt` not found — manual sync still pending).
- 88-file fleet-wide `sota` drift (mcpb/webapp/src) not all swept — next `assfix` chunk to ≥80 SOTA verified.
