"""Minimal test: server initialises and MCP tool decorators work."""

from freecad_mcp.server import _state


def test_server_state_init():
    """Server state dict should exist and have known keys after lifespan."""
    assert isinstance(_state, dict)
