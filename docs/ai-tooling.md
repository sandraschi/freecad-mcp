# AI Tooling

## Ollama Chat (CAD Expert)

The webapp includes a chat page (`/chat`) that connects to an Ollama instance for AI-assisted CAD reasoning. The server proxies chat requests to Ollama's `/api/chat` endpoint.

**Default config:**
- URL: `http://192.168.1.11:11434`
- Model: `gemma3:1b`

**Settings page** (`/settings`) lets you change the Ollama URL and model at runtime.

### Chat Endpoint

```
POST /api/v1/chat
{
  "messages": [{"role": "user", "content": "What's the volume of this part?"}],
  "system": "You are a CAD expert. Answer concisely.",
  "provider": "ollama",
  "model": "gemma3:1b"
}
```

The system prompt defaults to "You are a CAD expert." and can be overridden per request.

## Agentic Workflows

Since FreeCAD MCP is a FastMCP 3.2 server, any MCP client (Claude Desktop, Cursor, OpenCode) can chain tool calls agentically:

```
1. freecad_status()          → confirm FreeCAD is up
2. step_to_stl("part.STEP")  → convert to mesh
3. model_info("part.stl")    → inspect dimensions
4. slice_stl("part.stl")     → generate G-code
```

### Sampling (SEP-1577)

FastMCP 3.2 supports `ctx.sample()` for LLM-guided multi-step workflows. Future updates will add a `freecad_agentic_workflow` tool that uses sampling to:
- Suggest optimal slice settings based on model geometry
- Recommend support structures for overhangs
- Detect printability issues (wall thickness, manifold errors)

## Integration with Fleet AI

The server broadcasts SSDP discovery beacons so fleet orchestrators (meta-mcp, hermes-agent) can auto-discover it. Other fleet servers can call FreeCAD tools via `/api/v1/control/tool`:

```json
POST /api/v1/control/tool
{"tool": "step_to_stl", "arguments": {"file_name": "part.step", "output_name": "part.stl"}}
```
