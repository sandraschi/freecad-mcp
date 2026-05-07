set windows-shell := ["pwsh.exe", "-NoLogo", "-Command"]

export NAME := "FreeCAD MCP"
export DESC := "CAD operations via MCP"
export VER  := "0.1.0"
export PORT := "10944"
export HOST := "0.0.0.0"

# Show dashboard
default:
    Write-Host " [{{NAME}}] {{DESC}} v{{VER}}" -ForegroundColor Cyan

# Bootstrap dependencies
bootstrap:
    uv sync --all-extras
    Set-Location '{{justfile_directory()}}\webapp'
    cmd /c npm install

# Start server (dual mode: REST + MCP)
serve:
    uv run python -m freecad_mcp.server --mode dual --port {{PORT}}

# Start webapp dev server
web:
    Set-Location '{{justfile_directory()}}\webapp'
    cmd /c npm run dev

# Lint
lint:
    uv run ruff check src/

# Test
test:
    uv run pytest
