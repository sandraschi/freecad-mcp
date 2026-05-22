#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "=== freecad-mcp sidecar build ===" -ForegroundColor Cyan

Push-Location $Root
try {
    $pi = uv run pyinstaller --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "-> Installing PyInstaller..." -ForegroundColor Yellow
        uv pip install pyinstaller
    } else {
        Write-Host "-> PyInstaller: $pi" -ForegroundColor Gray
    }

    Remove-Item -Recurse -Force "$Root\build\freecad-mcp-backend" -ErrorAction SilentlyContinue
    Remove-Item -Force "$Root\dist\freecad-mcp-backend.exe" -ErrorAction SilentlyContinue

    Write-Host "-> Running PyInstaller..." -ForegroundColor Yellow
    uv run pyinstaller freecad-mcp-backend.spec --clean --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)" }

    $triple = "x86_64-pc-windows-msvc"
    $src = "$Root\dist\freecad-mcp-backend.exe"
    $dstDir = "$Root\native\binaries"
    $dst = "$dstDir\freecad-mcp-backend-$triple.exe"

    if (-not (Test-Path $src)) { throw "Build output not found: $src" }

    New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    Copy-Item $src $dst -Force

    $sizeMB = [math]::Round((Get-Item $dst).Length / 1MB, 1)
    Write-Host "=== Sidecar ready ===" -ForegroundColor Green
    Write-Host "  $dst ($sizeMB MB)" -ForegroundColor Cyan
} finally {
    Pop-Location
}
