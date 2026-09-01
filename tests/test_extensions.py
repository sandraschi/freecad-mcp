"""Unit tests for FreeCAD MCP extension operations: techdraw, sketch, assembly, generative, heuristic_fillet, inspect_assembly."""

from freecad_mcp.model_ops import (
    script_create_assembly,
    script_create_sketch,
    script_create_techdraw,
    script_generative_optimize,
    script_heuristic_fillet,
    script_inspect_assembly,
)


def test_script_create_techdraw():
    script = script_create_techdraw(
        file_name="bracket.stl",
        output_svg="blueprint.svg",
        scale=1.5,
    )
    assert "TechDraw::DrawPage" in script
    assert "ViewFront" in script
    assert "ViewIso" in script
    assert "blueprint.svg" in script


def test_script_create_sketch():
    script = script_create_sketch(
        sketch_type="rectangle_with_hole",
        width_mm=80.0,
        height_mm=50.0,
        hole_diameter_mm=16.0,
        extrude_height_mm=20.0,
        plane="XY",
        export_stl="sketch_bracket.stl",
    )
    assert "Sketcher::SketchObject" in script
    assert "addConstraint" in script
    assert "Part::Extrusion" in script
    assert "sketch_bracket.stl" in script


def test_script_create_assembly():
    components = [
        {"file_name": "bolt.stl", "x": 0, "y": 0, "z": 0, "label": "Bolt"},
        {"file_name": "nut.stl", "x": 0, "y": 0, "z": 20, "label": "Nut"},
    ]
    script = script_create_assembly(
        components=components,
        output_step="assembly.step",
        output_stl="assembly.stl",
    )
    assert "AssemblyDoc" in script
    assert "comp_details" in script
    assert "assembly.step" in script


def test_script_generative_optimize():
    script = script_generative_optimize(
        file_name="bracket.stl",
        target_reduction_pct=40.0,
        wall_thickness_mm=3.5,
        output_stl="opt_bracket.stl",
    )
    assert "reduction_factor" in script
    assert "orig_shape.cut" in script
    assert "opt_bracket.stl" in script


def test_script_heuristic_fillet():
    script = script_heuristic_fillet(
        file_name="bracket.stl",
        radius_mm=2.5,
        edge_filter="all_vertical",
        output_stl="filleted_bracket.stl",
    )
    assert "all_vertical" in script
    assert "makeFillet" in script
    assert "filleted_bracket.stl" in script


def test_script_inspect_assembly():
    script = script_inspect_assembly(
        file_path="complex_assembly.step",
    )
    assert "assembly_tree" in script
    assert "total_assembly_volume_mm3" in script
