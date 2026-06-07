param(
    [switch]$Headless,
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$NoBrowser
)

$WebPort = 10945
$ApiPort = 10944
$ProjectRoot = $PSScriptRoot
$SrcDir = Join-Path $ProjectRoot "src"

$FleetStartPath = Join-Path $ProjectRoot "scripts\FleetStartMode.ps1"
if (-not (Test-Path -LiteralPath $FleetStartPath)) {
    Write-Host "ERROR: Missing vendored launcher helper: $FleetStartPath" -ForegroundColor Red
    exit 1
}
. $FleetStartPath
$FleetStart = Initialize-FleetStartMode @PSBoundParameters
Enter-FleetHeadlessConsole -Headless:$Headless -BackendOnly:$BackendOnly
Stop-FleetPortSquatters -Ports @($WebPort, $ApiPort) -Label "freecad-mcp"

$env:FREECAD_MCP_WORK_DIR = "$env:TEMP\freecad_mcp_work"
Set-Location $ProjectRoot
uv sync --project $ProjectRoot
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: uv sync failed for freecad-mcp." -ForegroundColor Red
    exit 1
}

$backendCmd = "Set-Location '$ProjectRoot'; uv run --project '$ProjectRoot' python -m freecad_mcp.server --mode http --host 127.0.0.1 --port $ApiPort"
Write-Host "Starting FreeCAD MCP backend on port $ApiPort ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Normal", "-Command", $backendCmd

$healthUrl = "http://127.0.0.1:$ApiPort/api/v1/status"
$attempt = 0
while ($attempt -lt 40) {
    try {
        $null = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        Write-Host "Backend ready at $healthUrl" -ForegroundColor Green
        break
    } catch {
        Start-Sleep -Seconds 2
        $attempt++
    }
}

if (-not $FleetStart.RunFrontend) {
    while ($true) { Start-Sleep -Seconds 60 }
}

Push-Location (Join-Path $ProjectRoot "webapp")
if (-not (Test-Path "node_modules")) { npm install }
Write-Host "Starting Vite frontend on port $WebPort ..." -ForegroundColor Green
npm run dev -- --port $WebPort --host 127.0.0.1 --strictPort

