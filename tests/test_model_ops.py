"""Tests for FreeCAD model_ops script generation."""

from __future__ import annotations

from freecad_mcp.model_ops import (
    script_boolean,
    script_create_primitive,
    script_toy_car,
    validate_bridge_script,
)


class TestValidateBridgeScript:
    def test_allows_simple_part_usage(self):
        ok, reason = validate_bridge_script("obj.Shape = Part.makeBox(1,2,3)")
        assert ok is True
        assert reason == ""

    def test_blocks_import(self):
        ok, reason = validate_bridge_script("import os")
        assert ok is False
        assert "import" in reason


class TestModelScripts:
    def test_create_primitive_contains_main_symbols(self):
        script = script_create_primitive(
            primitive_type="box",
            params={"width": 10, "height": 20, "depth": 30},
            label="Body",
            document_label="Car",
            placement={"x": 1, "y": 2, "z": 3},
            export_stl="D:/Temp/body.stl",
        )
        assert "Part.makeBox" in script
        assert "ToyCar" not in script
        assert "Body" in script
        assert "json.dumps" in script

    def test_boolean_script_uses_operation(self):
        script = script_boolean(
            operation="fuse",
            parts=[
                {"primitive_type": "box", "params": {"width": 1, "height": 1, "depth": 1}},
                {"primitive_type": "cylinder", "params": {"radius": 2, "height": 3}},
            ],
            result_label="Merged",
            document_label="BoolDoc",
            export_stl=None,
        )
        assert '"fuse"' in script
        assert "Merged" in script

    def test_toy_car_script_exports_stl(self):
        script = script_toy_car(
            body_length_mm=120,
            body_width_mm=60,
            body_height_mm=35,
            wheel_radius_mm=12,
            wheelbase_mm=70,
            export_stl="D:/Temp/toy.stl",
        )
        assert "ToyCar" in script
        assert "Part.makeTorus" in script
        assert "Mesh.export" in script
