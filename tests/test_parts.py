"""Unit tests for parametric gear, fastener, inspect, and clash check script generators."""

import pytest
from freecad_mcp.model_ops import (
    script_clash_check,
    script_create_fastener,
    script_create_gear,
    script_inspect_geometry,
)


def test_script_create_gear():
    script = script_create_gear(
        gear_type="spur",
        num_teeth=18,
        module=2.5,
        face_width_mm=12.0,
        bore_diameter_mm=6.0,
        export_stl="test_gear.stl",
    )
    assert "num_teeth = 18" in script
    assert "m = 2.5" in script
    assert "pitch_r = (num_teeth * m) / 2.0" in script
    assert "test_gear.stl" in script
    assert "Part.makeCylinder" in script


def test_script_create_fastener_bolt():
    script = script_create_fastener(
        fastener_type="bolt",
        size="M8",
        length_mm=30.0,
        export_stl="test_bolt.stl",
    )
    assert 'ftype = "bolt"' in script
    assert 'fsize = "M8"' in script
    assert "length = 30.0" in script
    assert "test_bolt.stl" in script


def test_script_create_fastener_nut_and_washer():
    nut_script = script_create_fastener(fastener_type="nut", size="M6")
    assert 'ftype = "nut"' in nut_script
    assert "shape = nut_blank.cut(hole)" in nut_script


    washer_script = script_create_fastener(fastener_type="washer", size="M5")
    assert 'ftype = "washer"' in washer_script
    assert "washer_blank.cut(hole)" in washer_script


def test_script_inspect_geometry():
    script = script_inspect_geometry(file_name="sample_bracket.step")
    assert "sample_bracket.step" in script
    assert "CenterOfMass" in script
    assert "volume_mm3" in script
    assert "bounds_mm" in script


def test_script_clash_check():
    script = script_clash_check(file_name_1="partA.step", file_name_2="partB.step")
    assert "partA.step" in script
    assert "partB.step" in script
    assert "has_clash" in script
    assert "clash_volume_mm3" in script
