set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]
import 'scripts/just/fleet.just'

export NAME := "FreeCAD MCP"
export DESC := "CAD operations via MCP tools and REST API"
export VER  := "0.5.1"
export PORT := "10944"
export HOST := "0.0.0.0"

# --- Project Configuration ---

# Open the interactive recipe dashboard in the browser
default:
    @just --list

# --- Lifecycle ---

# Synchronise all dependencies and dev extras
bootstrap:
    uv sync --all-extras
    Set-Location '{{justfile_directory()}}\webapp'
    cmd /c npm install

# Workspace sanitisation
clean:
    if (Test-Path -Path "__pycache__") { Remove-Item -Recurse -Force "__pycache__" }; \
    if (Test-Path -Path "**/__pycache__") { Get-ChildItem -Path "." -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force }; \
    if (Test-Path -Path ".pytest_cache") { Remove-Item -Recurse -Force ".pytest_cache" }; \
    if (Test-Path -Path "htmlcov") { Remove-Item -Recurse -Force "htmlcov" }

# Complete project re-initialisation
setup: clean bootstrap
    Write-Host "FreeCAD MCP ready." -ForegroundColor Green

# --- Operation ---

# Start the FreeCAD MCP server (Unified Gateway, dual mode)
serve mode="dual" port=PORT:
    uv run python -m freecad_mcp.server --mode {{mode}} --port {{port}}

# Start in stdio mode (for MCP clients)
stdio:
    uv run python -m freecad_mcp.server --mode stdio

# Start the Vite dashboard
web:
    Set-Location '{{justfile_directory()}}\webapp'
    cmd /c npm run dev

# --- Development ---

# Start server with auto-reload
dev port=PORT:
    uv run uvicorn freecad_mcp.server:app --reload --port {{port}} --host {{HOST}}

# --- Quality ---

# Execute linting (ruff + biome + tsc)
lint:
    uv run ruff check src/
    Set-Location '{{justfile_directory()}}\webapp'
    npx @biomejs/biome ci .
    npx tsc --noEmit

# Execute auto-fixes and formatting
fix:
    uv run ruff check src/ --fix
    uv run ruff format src/
    Set-Location '{{justfile_directory()}}\webapp'
    npx @biomejs/biome check --write .

# Fast quality check (lint + tests)
check: lint test

# --- Testing ---

# Run the complete test suite
test:
    uv run pytest

# Fleet E2E smoke (offline config chain for CI)
fleet-e2e-offline:
    uv run python scripts/fleet_e2e_smoke.py --offline --strict

# FluidX3D GPU integration (local: FLUIDX3D_PATH + compiler + OpenCL)
fleet-e2e-integration:
    uv run python scripts/fleet_e2e_smoke.py --integration --strict

# Bootstrap FluidX3D clone + verify compiler/GPU
bootstrap-fluidx3d:
    powershell.exe -NoProfile -File '{{justfile_directory()}}\scripts\bootstrap_fluidx3d.ps1'

# Live HTTP chain with auto-start backends
fleet-e2e-chain-run:
    powershell.exe -NoProfile -File '{{justfile_directory()}}\scripts\run_live_chain.ps1'

# Fleet E2E smoke (HTTP probe when qcad + freecad running)
fleet-e2e:
    uv run python scripts/fleet_e2e_smoke.py --strict

# Live HTTP chain: qcad plan_extrude -> freecad FluidX3D setup
fleet-e2e-chain:
    uv run python scripts/fleet_e2e_smoke.py --live-chain --strict

# Live chain + GPU compile/run (slow)
fleet-e2e-chain-gpu:
    uv run python scripts/fleet_e2e_smoke.py --live-chain --live-chain-gpu --strict

# Pytest including integration marker
test-integration:
    uv run pytest -m integration

# Install ParaView for professional CFD visualization (optional, ~500 MB)
install-paraview:
    winget install Kitware.ParaView

# Run all verification gates (lint + typecheck + tests)
gates-green:
    uv run ruff check src/ --quiet
    uv run ruff format src/ --check --quiet
    Set-Location '{{justfile_directory()}}\webapp'
    npx tsc --noEmit --quiet
    uv run pytest --quiet -x

# Run cert gates
certify: gates-green

e2e:
    powershell.exe -NoProfile -NoProfile -ExecutionPolicy Bypass -File "D:\Dev\repos\mcp-central-docs\scripts\playwright-audit.ps1" -RepoPath "{{justfile_directory()}}"

# Register this MCP server with a client (stdio)
install-mcp:
    uv run python -m freecad_mcp.server --mode stdio

# Regenerate LLM documentation files (llms.txt)
llms-txt:
    uv run python -m freecad_mcp.utils.llms_txt

# --- Diagnostics ---

# Check FreeCAD status
health:
    curl http://localhost:10944/api/v1/status

# --- Native  Tauri ---

tauri-sidecar:
    powershell.exe -NoProfile -File '{{justfile_directory()}}\native\build-sidecar.ps1'

tauri-build:
    $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"; & '{{justfile_directory()}}\native\build.ps1'

tauri-dev:
    powershell.exe -NoProfile -File '{{justfile_directory()}}\native\ensure-sidecar-stub.ps1'
    Set-Location '{{justfile_directory()}}\native'
    $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
    npm install
    npx @tauri-apps/cli dev

build-native: tauri-build

build-native-debug:
    powershell.exe -NoProfile -File '{{justfile_directory()}}\native\ensure-sidecar-stub.ps1'
    Set-Location '{{justfile_directory()}}\native'
    $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
    npx @tauri-apps/cli build --debug



# Bootstrap: install dev deps + pre-commit hook
