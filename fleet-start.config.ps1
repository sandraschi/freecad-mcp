# Per-repo fleet start config for freecad-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'freecad-mcp'
    BackendPort  = 10944
    FrontendPort = 10945
    HealthPath   = '/api/v1/status'
    WebRoot      = 'webapp'
    # Guarantee a responsive FreeCAD bridge before the backend starts.
    # Launches one bridged FreeCAD when none is running; refuses to start a
    # second instance; offers a graceful restart when the bridge is hung.
    PreStartScript   = 'scripts\ensure-bridge.ps1'
    PreStartRequired = $true
    Backend = @{
        Kind          = 'uvicorn'
        UvicornTarget = 'freecad_mcp.server:app'
        SyncExtras    = @('dev')
        SyncOnStart  = $true
        Env           = @{ WEB_PORT = '10944'; FC_BRIDGE_PORT = '11968'; FLUIDX3D_PATH = 'D:\Dev\repos\external\FluidX3D' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
