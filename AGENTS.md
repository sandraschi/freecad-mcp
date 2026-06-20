# freecad-mcp — Agent Guide

## Overview
FreeCAD MCP server — CAD operations via MCP tools and REST API

## Standards
- FastMCP 3.4+ portmanteau tool pattern with annotation constants — every `@mcp.tool()` includes `annotations=READ_ONLY` or `annotations=MUTATING`
- Responses: structured dicts with `success`, `message`, domain-specific fields
- Dual transport: stdio (Claude Desktop) + HTTP (`MCP_TRANSPORT=http`)
- See [mcp-central-docs](https://github.com/sandraschi/mcp-central-docs) for fleet-wide coding standards

## Key Files
- `README.md` — full documentation
- `pyproject.toml` — build config and entry points
- `CLAUDE.md` — Claude Code context (if present)

Install docs: follow mcp-central-docs/standards/AGENT_INSTALL_REFERENCE.md
