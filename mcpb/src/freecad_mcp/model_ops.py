"""FreeCAD modeling helpers — subprocess script generation for Hands-Off mode."""

from __future__ import annotations

import json
import re
from typing import Any

_BLOCKED_SCRIPT_PATTERNS = (
    r"\bimport\b",
    r"\b__\w+__\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bopen\s*\(",
    r"\bos\.system\b",
    r"\bsubprocess\b",
)


def validate_bridge_script(script: str) -> tuple[bool, str]:
    """Reject scripts that try imports or arbitrary file/exec access."""
    if not script or not script.strip():
        return False, "Script is empty"
    if len(script) > 12000:
        return False, "Script exceeds 12000 character limit"
    for pattern in _BLOCKED_SCRIPT_PATTERNS:
        if re.search(pattern, script):
            return False, f"Script blocked by safety rule: {pattern}"
    return True, ""


def script_create_primitive(
    *,
    primitive_type: str,
    params: dict[str, Any],
    label: str,
    document_label: str,
    placement: dict[str, float] | None,
    export_stl: str | None,
) -> str:
    """Generate FreeCADCmd script that creates one primitive Part::Feature."""
    p = params or {}
    placement = placement or {}
    px = placement.get("x", 0.0)
    py = placement.get("y", 0.0)
    pz = placement.get("z", 0.0)
    rx = placement.get("rx", 0.0)
    ry = placement.get("ry", 0.0)
    rz = placement.get("rz", 0.0)

    if primitive_type == "box":
        shape_expr = f"Part.makeBox({p.get('width', 10)}, {p.get('height', 10)}, {p.get('depth', 10)})"
    elif primitive_type == "cylinder":
        shape_expr = (
            f"Part.makeCylinder({p.get('radius', 5)}, {p.get('height', 20)}, "
            f"FreeCAD.Vector({p.get('x', 0)}, {p.get('y', 0)}, {p.get('z', 0)}))"
        )
    elif primitive_type == "sphere":
        shape_expr = f"Part.makeSphere({p.get('radius', 10)})"
    elif primitive_type == "cone":
        shape_expr = f"Part.makeCone({p.get('radius', 5)}, {p.get('radius2', 0)}, {p.get('height', 15)})"
    else:
        raise ValueError(f"Unknown primitive_type: {primitive_type}")

    export_block = ""
    if export_stl:
        export_block = f"""
import Mesh
Mesh.export([obj], r"{export_stl}")
payload["export_stl"] = r"{export_stl}"
payload["size_kb"] = round(os.path.getsize(r"{export_stl}") / 1024, 1)
"""

    return f"""
import FreeCAD, Part, json, os
doc = FreeCAD.newDocument({json.dumps(document_label)})
obj = doc.addObject("Part::Feature", {json.dumps(label)})
obj.Shape = {shape_expr}
obj.Placement = FreeCAD.Placement(
    FreeCAD.Vector({px}, {py}, {pz}),
    FreeCAD.Rotation({rx}, {ry}, {rz}),
)
doc.recompute()
payload = {{
    "document": doc.Name,
    "object": obj.Name,
    "label": obj.Label,
    "volume_mm3": round(float(obj.Shape.Volume), 3),
}}
{export_block}
print(json.dumps({{"success": True, "data": payload}}))
FreeCAD.closeDocument(doc.Name)
"""


def script_boolean(
    *,
    operation: str,
    parts: list[dict[str, Any]],
    result_label: str,
    document_label: str,
    export_stl: str | None,
) -> str:
    """Fuse/cut/common multiple primitive specs in a fresh document."""
    if operation not in {"fuse", "cut", "common"}:
        raise ValueError(f"Unsupported boolean operation: {operation}")
    if len(parts) < 2:
        raise ValueError("Boolean operations require at least two parts")

    export_block = ""
    if export_stl:
        export_block = f"""
import Mesh
Mesh.export([result], r"{export_stl}")
payload["export_stl"] = r"{export_stl}"
payload["size_kb"] = round(os.path.getsize(r"{export_stl}") / 1024, 1)
"""

    parts_json = json.dumps(parts)
    return f"""
import FreeCAD, Part, json, os
doc = FreeCAD.newDocument({json.dumps(document_label)})
parts = {parts_json}
shapes = []
for i, spec in enumerate(parts):
    obj = doc.addObject("Part::Feature", f"Input{{i}}")
    ptype = spec.get("primitive_type", "box")
    p = spec.get("params", {{}})
    if ptype == "box":
        obj.Shape = Part.makeBox(p.get("width", 10), p.get("height", 10), p.get("depth", 10))
    elif ptype == "cylinder":
        obj.Shape = Part.makeCylinder(p.get("radius", 5), p.get("height", 20))
    elif ptype == "sphere":
        obj.Shape = Part.makeSphere(p.get("radius", 10))
    else:
        raise ValueError("unsupported primitive in boolean spec")
    pl = spec.get("placement", {{}})
    obj.Placement = FreeCAD.Placement(
        FreeCAD.Vector(pl.get("x", 0), pl.get("y", 0), pl.get("z", 0)),
        FreeCAD.Rotation(pl.get("rx", 0), pl.get("ry", 0), pl.get("rz", 0)),
    )
    shapes.append(obj)
doc.recompute()
base = shapes[0].Shape
for obj in shapes[1:]:
    if {json.dumps(operation)} == "fuse":
        base = base.fuse(obj.Shape)
    elif {json.dumps(operation)} == "cut":
        base = base.cut(obj.Shape)
    else:
        base = base.common(obj.Shape)
result = doc.addObject("Part::Feature", {json.dumps(result_label)})
result.Shape = base
doc.recompute()
payload = {{
    "document": doc.Name,
    "object": result.Name,
    "label": result.Label,
    "volume_mm3": round(float(result.Shape.Volume), 3),
    "operation": {json.dumps(operation)},
}}
{export_block}
print(json.dumps({{"success": True, "data": payload}}))
FreeCAD.closeDocument(doc.Name)
"""


def script_toy_car(
    *,
    body_length_mm: float,
    body_width_mm: float,
    body_height_mm: float,
    wheel_radius_mm: float,
    wheelbase_mm: float,
    export_stl: str,
    document_label: str = "ToyCar",
    style: str = "sports",
) -> str:
    """Build an elaborate sports-toy car from Part solids and export STL."""
    from freecad_mcp.toy_car_build import freecad_sports_car_shape_block

    shape_block = freecad_sports_car_shape_block()
    return f"""
import FreeCAD, Part, Mesh, json, os
doc = FreeCAD.newDocument({json.dumps(document_label)})

L = {body_length_mm}
W = {body_width_mm}
H = {body_height_mm}
wheel_r = {wheel_radius_mm}
wheelbase = {wheelbase_mm}
{shape_block}

result = doc.addObject("Part::Feature", "ToyCar")
result.Shape = car_shape
doc.recompute()
Mesh.export([result], r"{export_stl}")
payload = {{
    "document": doc.Name,
    "object": result.Name,
    "label": result.Label,
    "volume_mm3": round(float(result.Shape.Volume), 3),
    "export_stl": r"{export_stl}",
    "size_kb": round(os.path.getsize(r"{export_stl}") / 1024, 1),
    "wheels": 4,
    "style": {json.dumps(style)},
    "car_source": "parametric",
}}
print(json.dumps({{"success": True, "data": payload}}))
FreeCAD.closeDocument(doc.Name)
"""
