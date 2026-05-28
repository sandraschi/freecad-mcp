#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Ensure Tauri externalBin sidecar exists (stub for cargo check / dev until build-sidecar).
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$triple = "x86_64-pc-windows-msvc"
$dstDir = "$PSScriptRoot\binaries"
$dst = "$dstDir\freecad-mcp-backend-$triple.exe"
$built = "$Root\dist\freecad-mcp-backend.exe"

if (Test-Path $dst) {
    Write-Host "Sidecar present: $dst" -ForegroundColor Gray
    exit 0
}

New-Item -ItemType Directory -Path $dstDir -Force | Out-Null

if (Test-Path $built) {
    Copy-Item $built $dst -Force
    Write-Host "Copied PyInstaller sidecar -> $dst" -ForegroundColor Green
    exit 0
}

Copy-Item "$env:SystemRoot\System32\cmd.exe" $dst -Force
Write-Warning "Stub sidecar only (cmd.exe copy). Run: just tauri-sidecar"
