# Build Log — freecad-mcp

## 2026-09-01 — v0.6.0

**Build type:** NSIS (Tauri 2.11.2) — gate-clean
**Backend:** PyInstaller 6.21.0, 27.6 MB (D:\Dev\repos\freecad-mcp\dist\freecad-mcp-backend.exe)
**Frontend:** Vite 5.4.21, React, 1.50 MB JS (1498.54 kB) + 33.29 kB CSS, tsc --noEmit PASS
**Installer:** NSIS, 30.2 MB (30236084 bytes)
**Rust:** native/Cargo.toml 0.6.0 + native/package.json 0.6.0 + native/tauri.conf.json 0.6.0 aligned; cargo check PASS

### Artifacts

| Artifact | Path | Size |
|----------|------|------|
| Backend exe | `dist/freecad-mcp-backend.exe` | 27.6 MB |
| Backend (resources) | `native/resources/freecad-mcp-backend.exe` | 27.6 MB |
| Backend (dev) | `native/binaries/freecad-mcp-backend-x86_64-pc-windows-msvc.exe` | 27.6 MB |
| Web dist | `webapp/dist/` | 1.53 MB |
| NSIS | `native/target/release/bundle/nsis/FreeCAD MCP_0.6.0_x64-setup.exe` | 30.2 MB |
| NSIS (staged) | `dist/FreeCAD MCP_0.6.0_x64-setup.exe` | 30.2 MB |

### Gate A–J audit (this build)

- **F (Spawn):** Fixed — `native/src/main.rs` now delegates to `backend::spawn_backend` which resolves via `BaseDirectory::Resource` (`freecad-mcp-backend.exe` + `resources/freecad-mcp-backend.exe`), sets `MCP_PORT=10944`, `MCP_HOST=127.0.0.1`, `FREECAD_TAURI=1`, `CREATE_NO_WINDOW`, logs to `app_log_dir/backend-spawn.log`, does `free_port` kill + 240s poll + TCP health check (30×2s).
- **G (Lifecycle):** Fixed — spawn synchronously in `setup()` (no `async_runtime::spawn`), `RunEvent::Exit` does `kill + wait`. `BackendProcess(Mutex<Option<Child>>)` correctly managed.
- **H (Sidecar):** Fixed — `native/build.ps1` embeds to `resources/` + `binaries/`; `native/build-sidecar.ps1` now copies to both `native/binaries/` and `native/resources/`.
- **I (NSIS hooks):** Pass — `native/tauri.conf.json` `installerHooks: "./windows/hooks.nsh"` + `windows/hooks.nsh` `KillFleetSidecars` (taskkill + nsis_tauri_utils::KillProcessCurrentUser/KillProcess + Sleep 2000) for PREINSTALL/PREUNINSTALL.
- **J (Stdio hijack):** Fixed — `run_server.py` shims `isatty()->False` when `FREECAD_TAURI`/`FREECAD_MCP_TAURI=1`, forces `--mode http` on `127.0.0.1:10944` even if `MCP_PORT` unset; `src/freecad_mcp/server.py::main()` does same shim + forces `stdio->http` when Tauri env set so sidecar never hijacks stdout.

### Changes since v0.5.1
- Aligned `native/package.json` 0.1.0 → 0.6.0 to match Cargo/tauri.conf
- Removed duplicate `start_backend` inline spawn in `native/src/main.rs`; now thin wrapper over `backend::spawn_backend`
- Gate J isatty shim + Tauri guard in both entry points
- `native/build-sidecar.ps1` now stages to `resources/` as required for bundle

### Regressions
- Vite chunk size warning persists (1.50 MB vendor bundle >500 kB) — not blocking
- Dual Tauri trees remain (`native/` canonical 0.6.0 vs `src-tauri/` stale 0.1.0) — build uses `native/`, but `src-tauri/` should be removed or synced to avoid confusion

### Fixes applied this build
- Patched `native/src/main.rs`, `run_server.py`, `src/freecad_mcp/server.py`, `native/build-sidecar.ps1`, `native/package.json` (backups `*.20250901_000000.bak`)
- Rebuilt Vite with `VITE_API_BASE=http://127.0.0.1:10944`, PyInstaller --clean, embedded to resources/binaries, `tauri build --bundles nsis` via `.\node_modules\.bin\tauri.cmd`

## 2026-07-24 — v0.5.1

**Build type:** MCPB + NSIS (Tauri 2.0)
**Backend:** PyInstaller 6.21.0, 26.2 MB
**Frontend:** Vite 5.4.21, React, 1.47 MB JS + 28 KB CSS
**Installer:** NSIS, 28.8 MB

### Artifacts

| Artifact | Path | Size |
|----------|------|------|
| MCPB | `dist/freecad-mcp-v0.5.1.mcpb` | 130 KB |
| NSIS | `native/target/release/bundle/nsis/FreeCAD MCP_0.5.1_x64-setup.exe` | 28.8 MB |

### Changes since last build
- Agentic Design Loop: `freecad_design_loop` tool using ctx.sample()
- FluidX3D Parametric Sweeps: `cfd_fluidx3d_parametric_sweep`
- Live WebSocket dashboard: `WS /api/v1/fluidx3d/ws/{case}`
- Neural Surrogate: `cfd_fluidx3d_train_surrogate` + `cfd_surrogate_predict`
- VITE_API_BASE for Tauri production API routing
- CORS: unconditional Tailscale/LAN regex

### Regressions
- Rust dead-code warnings in `backend.rs` (pre-existing, not from this build)
- PyInstaller requires pyinstaller installed in `.venv` (not global tool)
- Vite chunk size warning (1.47 MB vendor bundle)

### Fixes applied
- Added pyinstaller to `.venv` dev dependencies in build.ps1
- Removed duplicate justfile recipes conflicting with fleet.just
