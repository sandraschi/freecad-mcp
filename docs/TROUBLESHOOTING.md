# Troubleshooting

Symptom-first. Check the backend log first: `GET /api/v1/logs/stream` or the
Logs page in the webapp.

## FreeCAD is "not found"

The server looks for FreeCAD in this order:

1. `FREECAD_PATH` environment variable.
2. Common install locations (`C:\Program Files\FreeCAD\bin\FreeCAD.exe`, then
   fleet-local candidate paths).

Fix: set `FREECAD_PATH` to `FreeCADCmd.exe` (headless) or `FreeCAD.exe` in
`.env`, then restart. Verify with `freecad_status`.

## Bridge mode is "subprocess" but I want "tcp"

Hands-In mode needs the in-FreeCAD bridge:

1. Open the FreeCAD GUI.
2. Call `freecad_bridge` with the start operation (or run the bridge macro).
3. `freecad_status` should report `bridge_mode: tcp` and port 11968 listening.

If the port is occupied by a stale bridge, stop the FreeCAD process, then
restart the bridge. Do not kill the bridge child from a shell while FreeCAD is
still running.

## Dashboard says "Connecting..." forever

- Backend not up: `curl http://127.0.0.1:10944/api/v1/status`.
- Wrong host: the dashboard now calls same-origin `/api/...`; only the Tauri
  WebView uses an absolute loopback URL. If you set `VITE_API_BASE`, make sure
  it points at a host the browser can reach (LAN name / Tailscale DNS).
- Port squatter: `Get-NetTCPConnection -LocalPort 10944 -State Listen`.

## OpenFOAM tools fail with Docker errors

`api/v1/health` reports `docker_available`. If false, start Docker Desktop.
If the image is missing, pull it:

```powershell
docker pull openfoam/openfoam10-paraview56
```

Long cases: the solver call is synchronous and can exceed a client timeout -
run it with a large timeout, or use the demos page which polls status.

## FluidX3D

- `cfd_fluidx3d_status` reports whether `FLUIDX3D_PATH`, a prebuilt binary, a
  compiler and an OpenCL device were found.
- No GPU device: install the vendor OpenCL runtime (NVIDIA driver is enough).
- Compile errors: FluidX3D needs a C++17 compiler on PATH. `just
  bootstrap-fluidx3d` clones the source and checks the toolchain.
- The optional PyTorch surrogate needs `torch`; without it
  `cfd_fluidx3d_train_surrogate` returns a clear error instead of training.

## Tests fail on a machine without FreeCAD

Expected. FreeCAD integration tests are behind the `integration` marker and are
deselected by default (`addopts = "-m 'not integration'"`). Run them only where
FreeCAD and the GPU toolchain exist:

```powershell
just test-integration
```

## MCPB bundle will not start

- The manifest must not contain `${PWD}` - Claude Desktop does not expand it.
  Use `${__dirname}`.
- `mcp_config` must start the stdio server, not the HTTP sidecar.
- Run the fleet audit:

```powershell
pwsh D:\Dev\repos\mcp-central-docs\scripts\audit-mcpb-bundles.ps1 -Repo freecad-mcp
```

## Port conflicts

Registered ports: 10944 (backend), 10945 (frontend), 11968 (FreeCAD bridge).
If another process owns one, stop it - do not silently move the port without
updating `mcp-central-docs/operations/WEBAPP_PORTS.md` and
`fleet-start.config.ps1`.
