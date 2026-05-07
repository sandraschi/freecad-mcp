#!/usr/bin/env bash
# start.ps1 — FreeCAD MCP + Webapp
$WebPort = 10945
$ApiPort = 10944

# Kill any existing processes on these ports
Get-NetTCPConnection -LocalPort $ApiPort -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
Get-NetTCPConnection -LocalPort $WebPort -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
Start-Sleep -Seconds 1

# Start backend (dual mode: REST + MCP SSE)
$env:FREECAD_MCP_WORK_DIR = "$env:TEMP\freecad_mcp_work"
$job = Start-Job -Name "freecad-mcp" -ScriptBlock {
    Set-Location "$using:PWD\src"
    uv run python -m freecad_mcp.server --mode dual --port $using:ApiPort
}
Start-Sleep -Seconds 3

# Start webapp
Push-Location webapp
Start-Process cmd -ArgumentList "/c", "npm", "run", "dev"
Pop-Location

Start-Sleep -Seconds 5
Write-Host "FreeCAD MCP: http://localhost:$ApiPort/api/v1/status" -ForegroundColor Green
Write-Host "Webapp:       http://localhost:$WebPort" -ForegroundColor Green
Write-Host "MCP SSE:      http://localhost:$ApiPort/sse" -ForegroundColor Green
