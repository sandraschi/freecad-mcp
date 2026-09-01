#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start qcad + freecad backends and run live fleet chain smoke.
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$QcadPort = 10966
$FreecadPort = 10944

function Test-PortListen([int]$Port) {
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Wait-Health([string]$Url, [int]$Seconds = 45) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -eq 200) { return $true }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    return $false
}

Write-Host "=== Live fleet chain runner ===" -ForegroundColor Cyan

$qcadJob = $null
$freecadJob = $null

try {
    if (-not (Test-PortListen $QcadPort)) {
        Write-Host "-> Starting qcad-mcp on :$QcadPort" -ForegroundColor Yellow
        $qcadRepo = "D:\Dev\repos\qcad-mcp"
        $qcadJob = Start-Job -Name "qcad-mcp-chain" -ScriptBlock {
            Set-Location $using:qcadRepo
            $env:QCAD_MCP_WORK_DIR = "$env:TEMP\qcad_mcp_work"
            uv run python -m qcad_mcp.server --mode dual --port $using:QcadPort
        }
    }

    if (-not (Test-PortListen $FreecadPort)) {
        Write-Host "-> Starting freecad-mcp on :$FreecadPort" -ForegroundColor Yellow
        $freecadJob = Start-Job -Name "freecad-mcp-chain" -ScriptBlock {
            Set-Location $using:Root
            $env:FREECAD_MCP_WORK_DIR = "$env:TEMP\freecad_mcp_work"
            uv run python -m freecad_mcp.server --mode dual --port $using:FreecadPort
        }
    }

    if (-not (Wait-Health "http://127.0.0.1:$QcadPort/api/v1/health")) {
        throw "qcad-mcp did not become healthy on port $QcadPort"
    }
    if (-not (Wait-Health "http://127.0.0.1:$FreecadPort/api/v1/health")) {
        throw "freecad-mcp did not become healthy on port $FreecadPort"
    }

    Set-Location $Root
    $args = @("scripts/fleet_e2e_smoke.py", "--live-chain", "--strict")
    if ($env:FREECAD_LIVE_CHAIN_GPU -eq "1") {
        $args += "--live-chain-gpu"
    }
    uv run python @args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    foreach ($job in @($qcadJob, $freecadJob)) {
        if ($job) {
            Stop-Job -Job $job -ErrorAction SilentlyContinue
            Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
        }
    }
}
