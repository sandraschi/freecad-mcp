# Build Log — freecad-mcp

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
