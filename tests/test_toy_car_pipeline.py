"""Tests for elaborate toy car pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from freecad_mcp.model_ops import script_toy_car
from freecad_mcp.toy_car_build import (
    blender_build_and_export_script,
    freecad_sports_car_shape_block,
    load_blender_sports_car_script,
)


class TestToyCarBuild:
    def test_load_blender_sports_car_script(self):
        script = load_blender_sports_car_script()
        if script is None:
            pytest.skip("blender-mcp vehicles.json not found on this machine")
        assert "SportsCar" in script or "Car_Body" in script
        assert "Car_Wheel" in script

    def test_blender_export_script_contains_join_and_stl(self):
        if load_blender_sports_car_script() is None:
            pytest.skip("blender-mcp vehicles.json not found on this machine")
        script = blender_build_and_export_script(
            export_stl="D:/Temp/sports_car.stl",
            body_length_mm=120,
        )
        assert "export_mesh.stl" in script
        assert "object.join" in script
        assert "global_scale" in script

    def test_freecad_shape_block_uses_torus_and_arches(self):
        block = freecad_sports_car_shape_block()
        assert "Part.makeTorus" in block
        assert "car_shape.cut(arch)" in block
        assert "spoiler" in block.lower()

    def test_parametric_script_exports_elaborate_car(self):
        script = script_toy_car(
            body_length_mm=120,
            body_width_mm=60,
            body_height_mm=35,
            wheel_radius_mm=12,
            wheelbase_mm=70,
            export_stl="D:/Temp/toy.stl",
            style="sports",
        )
        assert "Part.makeTorus" in script
        assert "car_source" in script or "parametric" in script
        assert "Mesh.export" in script


def test_resolve_auto_falls_back_when_blender_down(monkeypatch, tmp_path):
    import asyncio

    from freecad_mcp import toy_car_pipeline as pipeline

    export_stl = str(tmp_path / "car.stl")

    async def fake_blender(*_args, **_kwargs):
        return {"success": False, "error": "blender down"}

    async def fake_market(*_args, **_kwargs):
        return {"success": False, "error": "no results"}

    monkeypatch.setattr(pipeline, "build_toy_car_via_blender", fake_blender)
    monkeypatch.setattr(pipeline, "build_toy_car_via_marketplace", fake_market)

    result = asyncio.run(
        pipeline.resolve_toy_car_auto(
            export_stl,
            body_length_mm=120,
            marketplace_query="toy car",
            marketplace_search=lambda **_: {},
            marketplace_download=lambda **_: {},
        )
    )
    assert result["success"] is False
    assert result["car_source"] == "auto"


def test_marketplace_copy_success(tmp_path):
    import asyncio

    from freecad_mcp import toy_car_pipeline as pipeline

    src = tmp_path / "uploaded.stl"
    src.write_bytes(b"solid test")
    export_stl = str(tmp_path / "out" / "car.stl")

    async def fake_search(**_kwargs):
        return {
            "success": True,
            "results": [
                {
                    "id": "99",
                    "title": "Mini Car",
                    "file_url": "https://example.com/car.stl",
                }
            ],
        }

    async def fake_download(**_kwargs):
        return {"success": True, "path": str(src)}

    result = asyncio.run(
        pipeline.build_toy_car_via_marketplace(
            export_stl,
            query="toy car",
            marketplace_search=fake_search,
            marketplace_download=fake_download,
        )
    )
    assert result["success"] is True
    assert Path(export_stl).is_file()
