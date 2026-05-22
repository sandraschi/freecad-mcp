#!/usr/bin/env pwsh
$ErrorActionPreference = "Stop"
$iconDir = Join-Path (Split-Path -Parent $PSScriptRoot) "native\icons"
New-Item -ItemType Directory -Path $iconDir -Force | Out-Null
$out = Join-Path $iconDir "icon.png"

Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap 512, 512
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.Clear([System.Drawing.Color]::FromArgb(255, 32, 40, 56))
$brush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 120, 180, 255))
$font = New-Object System.Drawing.Font("Segoe UI", 180, [System.Drawing.FontStyle]::Bold)
$g.DrawString("F", $font, $brush, 140, 88)
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
$brush.Dispose()
Write-Host "Wrote $out" -ForegroundColor Green
