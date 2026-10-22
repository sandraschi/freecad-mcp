#Requires -Version 5.1
<#
.SYNOPSIS
  Guarantee a working FreeCAD MCP bridge before the backend/webapp start.

.DESCRIPTION
  Called by fleet-start.config.ps1 via PreStartScript. It:
    1. Pings the bridge (TCP connect alone is NOT enough - a hung GUI-thread
       pump accepts connections and never answers).
    2. If FreeCAD is not running, launches it with fc_bridge.py and waits.
    3. If FreeCAD is running with a hung bridge, offers a graceful restart
       (CloseMainWindow, so FreeCAD can prompt to save) or aborts.
  It never launches a second FreeCAD while one is running.

.EXIT CODES
  0  bridge answered pong
  1  freecad executable/script missing
  2  bridge did not become ready in time
  3  FreeCAD running, bridge hung, and -NoRestart was passed
  4  FreeCAD could not be closed for the restart

.PARAMETER CheckOnly
  Report state and exit; never launch, close or restart anything.

.PARAMETER NoRestart
  Do not touch a running FreeCAD (the old refuse behaviour). Default is to
  recover: graceful close first, force close if it will not exit, then relaunch.
#>
[CmdletBinding()]
param(
    [int]$Port = 11968,
    [int]$TimeoutSec = 90,
    [string]$RepoRoot = '',
    [string]$FreeCadPath = '',
    [switch]$NoRestart,
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
if (-not $RepoRoot) { $RepoRoot = Split-Path -Parent $PSScriptRoot }
$BridgeScript = Join-Path $RepoRoot 'src\freecad_mcp\fc_bridge.py'

function Write-Step([string]$Text, [string]$Color = 'Gray') {
    Write-Host "[bridge] $Text" -ForegroundColor $Color
}

function Test-BridgePing {
    param([int]$PortNumber, [int]$TimeoutMs = 4000)

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $iar = $client.BeginConnect('127.0.0.1', $PortNumber, $null, $null)
        if (-not $iar.AsyncWaitHandle.WaitOne($TimeoutMs)) { return $false }
        $client.EndConnect($iar)

        $stream = $client.GetStream()
        $stream.ReadTimeout = $TimeoutMs
        $stream.WriteTimeout = $TimeoutMs
        $payload = '{"id":1,"method":"ping","params":{}}' + "`n"
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush()

        $buffer = New-Object byte[] 4096
        $builder = New-Object System.Text.StringBuilder
        $deadline = (Get-Date).AddMilliseconds($TimeoutMs)
        while ((Get-Date) -lt $deadline) {
            if ($stream.DataAvailable) {
                $read = $stream.Read($buffer, 0, $buffer.Length)
                if ($read -le 0) { break }
                [void]$builder.Append([System.Text.Encoding]::UTF8.GetString($buffer, 0, $read))
                if ($builder.ToString().Contains("`n")) { break }
            }
            Start-Sleep -Milliseconds 50
        }

        $text = $builder.ToString().Trim()
        if (-not $text) { return $false }
        $response = $text | ConvertFrom-Json
        return ($response.data -eq 'pong')
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Get-FreeCadGuiProcesses {
    @(Get-Process -Name FreeCAD -ErrorAction SilentlyContinue)
}

function Resolve-FreeCadExe {
    if ($FreeCadPath -and (Test-Path -LiteralPath $FreeCadPath)) { return $FreeCadPath }
    if ($env:FREECAD_PATH -and (Test-Path -LiteralPath $env:FREECAD_PATH)) { return $env:FREECAD_PATH }

    $envFile = Join-Path $RepoRoot '.env'
    if (Test-Path -LiteralPath $envFile) {
        $line = Get-Content -LiteralPath $envFile | Where-Object { $_ -match '^\s*FREECAD_PATH\s*=' } | Select-Object -First 1
        if ($line) {
            $candidate = ($line -replace '^\s*FREECAD_PATH\s*=\s*', '').Trim().Trim('"').Trim("'")
            if (Test-Path -LiteralPath $candidate) { return $candidate }
        }
    }

    $patterns = @()
    if ($env:ProgramFiles) { $patterns += (Join-Path $env:ProgramFiles 'FreeCAD*\bin\FreeCAD.exe') }
    if (${env:ProgramFiles(x86)}) { $patterns += (Join-Path ${env:ProgramFiles(x86)} 'FreeCAD*\bin\FreeCAD.exe') }
    if ($env:LOCALAPPDATA) { $patterns += (Join-Path $env:LOCALAPPDATA 'Programs\FreeCAD*\bin\FreeCAD.exe') }
    $patterns += 'D:\Dev\repos\FreeCAD\*\bin\FreeCAD.exe'
    foreach ($pattern in $patterns) {
        if (-not $pattern) { continue }
        $found = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    return $null
}

function Start-BridgedFreeCad([string]$Exe) {
    $env:FC_BRIDGE_PORT = "$Port"
    Write-Step "starting FreeCAD with the bridge: $Exe" 'Cyan'
    Start-Process -FilePath $Exe -ArgumentList @("`"$BridgeScript`"") | Out-Null
}

function Wait-BridgeReady {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-BridgePing -PortNumber $Port) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Update-BackendBridgeState {
    # If the backend is already running (reused), make it connect now instead of
    # waiting for a restart.
    $backendPort = $env:FLEET_BACKEND_PORT
    if (-not $backendPort) { return }
    try {
        $body = @{ tool = 'freecad_bridge'; arguments = @{ operation = 'ensure_gui' } } | ConvertTo-Json -Depth 4
        Invoke-RestMethod -Uri "http://127.0.0.1:$backendPort/api/v1/control/tool" -Method Post `
            -ContentType 'application/json' -Body $body -TimeoutSec 15 | Out-Null
    } catch {
        Write-Step "backend on :$backendPort not reachable yet (it will connect at startup)" 'DarkGray'
    }
}

# --- main -------------------------------------------------------------------
$gui = Get-FreeCadGuiProcesses
$ping = Test-BridgePing -PortNumber $Port

if ($ping) {
    Write-Step "bridge on 127.0.0.1:$Port answered pong" 'Green'
    if (-not $CheckOnly) { Update-BackendBridgeState }
    exit 0
}

if ($CheckOnly) {
    if ($gui.Count -gt 0) {
        Write-Step "FreeCAD is running, but the bridge on :$Port does not answer (hung pump)" 'Yellow'
        exit 3
    }
    Write-Step "FreeCAD is not running; bridge on :$Port is down" 'Yellow'
    exit 4
}

$exe = Resolve-FreeCadExe
if (-not $exe) {
    Write-Step 'FreeCAD executable not found. Set FREECAD_PATH in .env or the environment.' 'Red'
    exit 1
}
if (-not (Test-Path -LiteralPath $BridgeScript)) {
    Write-Step "bridge script missing: $BridgeScript" 'Red'
    exit 1
}

if ($gui.Count -eq 0) {
    Start-BridgedFreeCad -Exe $exe
} else {
    Write-Step "FreeCAD is running but the bridge on :$Port is not responding - restarting it." 'Yellow'
    if ($NoRestart) {
        Write-Step '-NoRestart was passed; leaving FreeCAD untouched. Close it manually and re-run.' 'Red'
        exit 3
    }

    Write-Step 'closing FreeCAD (save prompts may appear)...' 'Cyan'
    foreach ($proc in $gui) { [void]$proc.CloseMainWindow() }
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
        if ((Get-FreeCadGuiProcesses).Count -eq 0) { break }
        Start-Sleep -Seconds 1
    }
    if ((Get-FreeCadGuiProcesses).Count -gt 0) {
        Write-Step 'FreeCAD did not close in 20s; forcing it. Unsaved changes in that instance are lost.' 'Red'
        foreach ($proc in Get-FreeCadGuiProcesses) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Seconds 3
    }
    if ((Get-FreeCadGuiProcesses).Count -gt 0) {
        Write-Step 'could not terminate FreeCAD. Close it manually, then re-run.' 'Red'
        exit 4
    }
    Start-Sleep -Seconds 2
    Start-BridgedFreeCad -Exe $exe
}

Write-Step "waiting up to ${TimeoutSec}s for the bridge..." 'Gray'
if (-not (Wait-BridgeReady)) {
    Write-Step 'first launch did not answer; retrying once.' 'Yellow'
    foreach ($proc in Get-FreeCadGuiProcesses) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3
    Start-BridgedFreeCad -Exe $exe
    if (-not (Wait-BridgeReady)) {
        Write-Step "bridge did not answer on :$Port within ${TimeoutSec}s after two launches." 'Red'
        exit 2
    }
}

Write-Step "bridge ready on 127.0.0.1:$Port" 'Green'
Update-BackendBridgeState
exit 0
