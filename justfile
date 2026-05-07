set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

export NAME := "FreeCAD MCP"
export DESC := "CAD operations via MCP tools and REST API"
export VER  := "0.1.0"
export PORT := "10944"
export HOST := "0.0.0.0"

# ── Project Configuration ─────────────────────────────────────────────────────

# Display the industrial dashboard
default:
    @$lines = Get-Content '{{justfile()}}'; \
    Write-Host " [{{NAME}}] {{DESC}} v{{VER}}" -ForegroundColor White -BackgroundColor Cyan; \
    Write-Host '' ; \
    $currentCategory = ''; \
    foreach ($line in $lines) { \
        if ($line -match '^# ── ([^─]+) ─') { \
            $currentCategory = $matches[1].Trim(); \
            Write-Host "`n  $currentCategory" -ForegroundColor Cyan; \
            Write-Host ('  ' + ('─' * 45)) -ForegroundColor Gray; \
        } elseif ($line -match '^# ([^─].+)') { \
            $desc = $matches[1].Trim(); \
            $idx = [array]::IndexOf($lines, $line); \
            if ($idx -lt $lines.Count - 1) { \
                $nextLine = $lines[$idx + 1]; \
                if ($nextLine -match '^([a-z0-9-]+):') { \
                    $recipe = $matches[1]; \
                    $pad = ' ' * [math]::Max(2, (20 - $recipe.Length)); \
                    Write-Host "    $recipe" -ForegroundColor White -NoNewline; \
                    Write-Host "$pad$desc" -ForegroundColor Gray; \
                } \
            } \
        } \
    } \
    Write-Host "`n  [Mode: DUAL | Port: {{PORT}}]" -ForegroundColor DarkGray; \
    Write-Host ''

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
serve mode=dual port=PORT:
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

# ── Diagnostics ───────────────────────────────────────────────────────────────

# Check FreeCAD status
health:
    curl http://localhost:10944/api/v1/status
