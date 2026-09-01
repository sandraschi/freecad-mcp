#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Bootstrap FluidX3D for freecad-mcp GPU integration on Windows.
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$F3dPath = if ($env:FLUIDX3D_PATH) { $env:FLUIDX3D_PATH } else { "D:\Dev\repos\FluidX3D" }

Write-Host "=== FluidX3D bootstrap ===" -ForegroundColor Cyan

if (-not (Test-Path $F3dPath)) {
    Write-Host "-> Cloning FluidX3D to $F3dPath ..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path (Split-Path $F3dPath) -Force | Out-Null
    git clone --depth 1 https://github.com/ProjectPhysX/FluidX3D.git $F3dPath
}

$checks = @(
    @{ Name = "FluidX3D src"; Path = Join-Path $F3dPath "src" },
    @{ Name = "OpenCL.lib"; Path = Join-Path $F3dPath "src\OpenCL\lib\OpenCL.lib" }
)

foreach ($check in $checks) {
    if (Test-Path $check.Path) {
        Write-Host "  OK  $($check.Name)" -ForegroundColor Green
    } else {
        Write-Host "  FAIL $($check.Name): $($check.Path)" -ForegroundColor Red
        exit 1
    }
}

Set-Location $Root
$status = uv run python -c @"
from freecad_mcp.tools.fluidx3d import _find_compiler, _find_fluidx3d, _query_gpu_devices
print('fluidx3d_path=', _find_fluidx3d())
print('compiler=', _find_compiler())
gpus = _query_gpu_devices()
print('gpu_count=', len(gpus))
for g in gpus[:3]:
    print(' gpu=', g.get('device'))
"@

Write-Host $status
Write-Host "=== Bootstrap complete ===" -ForegroundColor Green
Write-Host "Run: just fleet-e2e-integration" -ForegroundColor Cyan
