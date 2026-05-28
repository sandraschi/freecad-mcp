set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

export NAME := "FreeCAD MCP"
export DESC := "CAD operations via MCP tools and REST API"
export VER  := "0.5.0"
export PORT := "10944"
export HOST := "0.0.0.0"

# ── Project Configuration ─────────────────────────────────────────────────────

# Open the interactive recipe dashboard in the browser
default:
    @pwsh.exe -NoProfile -ExecutionPolicy Bypass -File ../mcp-central-docs/scripts/just-dashboard.ps1 -Path .

# ── Lifecycle ─────────────────────────────────────────────────────────────────

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

# ── Operation ─────────────────────────────────────────────────────────────────

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

# ── Development ───────────────────────────────────────────────────────────────

# Start server with auto-reload
dev port=PORT:
    uv run uvicorn freecad_mcp.server:app --reload --port {{port}} --host {{HOST}}

# ── Quality ───────────────────────────────────────────────────────────────────

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

# ── Testing ───────────────────────────────────────────────────────────────────

# Run the complete test suite
test:
    uv run pytest

# Fleet E2E smoke (offline config chain for CI)
fleet-e2e-offline:
    uv run python scripts/fleet_e2e_smoke.py --offline --strict

# Fleet E2E smoke (HTTP probe when qcad + freecad running)
fleet-e2e:
    uv run python scripts/fleet_e2e_smoke.py --strict

e2e:
    pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File "D:\Dev\repos\mcp-central-docs\scripts\playwright-audit.ps1" -RepoPath "{{justfile_directory()}}"

# ── Diagnostics ───────────────────────────────────────────────────────────────

# Check FreeCAD status
health:
    curl http://localhost:10944/api/v1/status

# ── Native (Tauri) ────────────────────────────────────────────────────────────

tauri-sidecar:
    pwsh -NoLogo -File '{{justfile_directory()}}\native\build-sidecar.ps1'

tauri-build:
    Set-Location '{{justfile_directory()}}\native'
    $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
    .\build.ps1

tauri-dev:
    pwsh -NoLogo -File '{{justfile_directory()}}\native\ensure-sidecar-stub.ps1'
    Set-Location '{{justfile_directory()}}\native'
    $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
    npm install
    npx @tauri-apps/cli dev

build-native: tauri-build

build-native-debug:
    pwsh -NoLogo -File '{{justfile_directory()}}\native\ensure-sidecar-stub.ps1'
    Set-Location '{{justfile_directory()}}\native'
    $env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
    npx @tauri-apps/cli build --debug
