# Per-repo fleet start config for freecad-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'freecad-mcp'
    BackendPort  = 10944
    FrontendPort = 10945
    HealthPath   = '/api/v1/status'
    WebRoot      = 'D:\Dev\repos\freecad-mcp\webapp'
    Backend = @{
        Kind          = 'uvicorn'
        UvicornTarget = 'freecad_mcp.server:app'
        SyncExtras    = @('dev')
        Env           = @{ WEB_PORT = '10944' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
