"""Tests for bridge execution mode resolution."""

from __future__ import annotations

from freecad_mcp.tools.bridge_tools import resolve_execution_mode


def test_resolve_auto_prefers_bridge_when_tcp():
    state = {"bridge_mode": "tcp", "execution_mode": "auto"}
    assert resolve_execution_mode(state) == "hands_in"


def test_resolve_auto_falls_back_to_subprocess():
    state = {"bridge_mode": "none", "execution_mode": "auto"}
    assert resolve_execution_mode(state) == "hands_off"


def test_resolve_explicit_hands_in():
    state = {"bridge_mode": "none", "execution_mode": "hands_in"}
    assert resolve_execution_mode(state, "hands_in") == "hands_in"
