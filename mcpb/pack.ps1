#Requires -Version 5.1
# Shim: kept because the vendored scripts/just/fleet.just recipe invokes
# mcpb/pack.ps1. The canonical pipeline lives in
# mcp-central-docs/scripts/fleet-mcpb-pack.ps1 (via scripts/mcpb-pack.ps1), so
# fixes there apply fleet-wide instead of drifting in this copy.
$shim = Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts\mcpb-pack.ps1'
if (-not (Test-Path $shim)) { throw "Fleet pack shim missing: $shim" }
& $shim
exit $LASTEXITCODE
