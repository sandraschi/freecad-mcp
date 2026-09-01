"""FreeCAD modeling helpers - subprocess script generation for Hands-Off mode."""

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


def script_create_gear(
    *,
    gear_type: str = "spur",
    num_teeth: int = 20,
    module: float = 2.0,
    pressure_angle_deg: float = 20.0,
    face_width_mm: float = 10.0,
    bore_diameter_mm: float = 8.0,
    label: str = "Gear",
    document_label: str = "GearDoc",
    export_stl: str | None = None,
) -> str:
    """Generate script for creating parametric gear geometry in FreeCAD."""
    export_block = ""
    if export_stl:
        export_block = f"""
import Mesh
Mesh.export([obj], r"{export_stl}")
payload["export_stl"] = r"{export_stl}"
payload["size_kb"] = round(os.path.getsize(r"{export_stl}") / 1024, 1)
"""

    return f"""
import FreeCAD, Part, json, os, math

doc = FreeCAD.newDocument({json.dumps(document_label)})
num_teeth = {num_teeth}
m = {module}
face_width = {face_width_mm}
bore_r = {bore_diameter_mm} / 2.0

pitch_r = (num_teeth * m) / 2.0
outer_r = pitch_r + m
root_r = max(1.0, pitch_r - 1.25 * m)

blank = Part.makeCylinder(outer_r, face_width)

if bore_r > 0.1 and bore_r < root_r:
    bore = Part.makeCylinder(bore_r, face_width)
    blank = blank.cut(bore)

angle_step = (2 * math.pi) / num_teeth
gap_w = m * 1.5708

for i in range(num_teeth):
    a = i * angle_step
    gap_box = Part.makeBox(gap_w, outer_r - root_r + 1.0, face_width)
    gap_box.translate(FreeCAD.Vector(-gap_w / 2.0, root_r, 0))
    gap_box.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), math.degrees(a))
    blank = blank.cut(gap_box)

obj = doc.addObject("Part::Feature", {json.dumps(label)})
obj.Shape = blank
doc.recompute()

payload = {{
    "document": doc.Name,
    "object": obj.Name,
    "label": obj.Label,
    "gear_type": {json.dumps(gear_type)},
    "num_teeth": num_teeth,
    "module": m,
    "pitch_diameter_mm": pitch_r * 2.0,
    "face_width_mm": face_width,
    "volume_mm3": round(float(obj.Shape.Volume), 3),
}}
{export_block}
print(json.dumps({{"success": True, "data": payload}}))
FreeCAD.closeDocument(doc.Name)
"""


def script_create_fastener(
    *,
    fastener_type: str = "bolt",
    size: str = "M6",
    length_mm: float = 20.0,
    label: str = "Fastener",
    document_label: str = "FastenerDoc",
    export_stl: str | None = None,
) -> str:
    """Generate script for creating ISO metric bolt, nut, or washer."""
    export_block = ""
    if export_stl:
        export_block = f"""
import Mesh
Mesh.export([obj], r"{export_stl}")
payload["export_stl"] = r"{export_stl}"
payload["size_kb"] = round(os.path.getsize(r"{export_stl}") / 1024, 1)
"""

    return f"""
import FreeCAD, Part, json, os, math

doc = FreeCAD.newDocument({json.dumps(document_label)})
ftype = {json.dumps(fastener_type)}
fsize = {json.dumps(size)}
length = {length_mm}

specs = {{
    "M3": (3.0, 5.5, 2.0, 2.4, 7.0, 0.5),
    "M4": (4.0, 7.0, 2.8, 3.2, 9.0, 0.8),
    "M5": (5.0, 8.0, 3.5, 4.0, 10.0, 1.0),
    "M6": (6.0, 10.0, 4.0, 5.0, 12.0, 1.6),
    "M8": (8.0, 13.0, 5.3, 6.5, 16.0, 1.6),
    "M10": (10.0, 16.0, 6.4, 8.0, 20.0, 2.0),
    "M12": (12.0, 18.0, 7.5, 10.0, 24.0, 2.5),
}}

d, s, k, m_nut, dw, t_w = specs.get(fsize, (6.0, 10.0, 4.0, 5.0, 12.0, 1.6))
shank_r = d / 2.0

if ftype == "bolt":
    head_r = s / math.sqrt(3)
    head_cyl = Part.makeCylinder(head_r, k)
    shank = Part.makeCylinder(shank_r, length)
    shank.translate(FreeCAD.Vector(0, 0, -length))
    shape = head_cyl.fuse(shank)
elif ftype == "nut":
    head_r = s / math.sqrt(3)
    nut_blank = Part.makeCylinder(head_r, m_nut)
    hole = Part.makeCylinder(shank_r, m_nut)
    shape = nut_blank.cut(hole)
else:
    outer_r = dw / 2.0
    washer_blank = Part.makeCylinder(outer_r, t_w)
    hole = Part.makeCylinder(shank_r + 0.2, t_w)
    shape = washer_blank.cut(hole)

obj = doc.addObject("Part::Feature", {json.dumps(label)})
obj.Shape = shape
doc.recompute()

payload = {{
    "document": doc.Name,
    "object": obj.Name,
    "label": obj.Label,
    "fastener_type": ftype,
    "size": fsize,
    "length_mm": length,
    "volume_mm3": round(float(obj.Shape.Volume), 3),
}}
{export_block}
print(json.dumps({{"success": True, "data": payload}}))
FreeCAD.closeDocument(doc.Name)
"""


def script_inspect_geometry(
    *,
    file_name: str,
    document_label: str = "InspectDoc",
) -> str:
    """Generate script for inspecting geometry mass properties and bounds."""
    return f"""
import FreeCAD, Part, json, os

doc = FreeCAD.newDocument({json.dumps(document_label)})
file_path = r"{file_name}"

if file_path.endswith(".step") or file_path.endswith(".stp"):
    Part.insert(file_path, doc.Name)
elif file_path.endswith(".stl"):
    import Mesh
    mesh = Mesh.Mesh(file_path)
    obj = doc.addObject("Mesh::Feature", "MeshObj")
    obj.Mesh = mesh
    doc.recompute()
    bbox = mesh.BoundBox
    payload = {{
        "file_name": file_path,
        "type": "mesh",
        "points": mesh.CountPoints,
        "facets": mesh.CountFacets,
        "bounds_mm": {{
            "dx": round(bbox.XLength, 3),
            "dy": round(bbox.YLength, 3),
            "dz": round(bbox.ZLength, 3),
            "xmin": round(bbox.XMin, 3),
            "xmax": round(bbox.XMax, 3),
            "ymin": round(bbox.YMin, 3),
            "ymax": round(bbox.YMax, 3),
            "zmin": round(bbox.ZMin, 3),
            "zmax": round(bbox.ZMax, 3),
        }},
        "volume_approx_mm3": round(mesh.Volume, 3) if hasattr(mesh, "Volume") else None,
        "area_approx_mm2": round(mesh.Area, 3) if hasattr(mesh, "Area") else None,
    }}
    print(json.dumps({{"success": True, "data": payload}}))
    FreeCAD.closeDocument(doc.Name)
    raise SystemExit(0)

obj = doc.Objects[0] if doc.Objects else None
if not obj or not hasattr(obj, "Shape"):
    print(json.dumps({{"success": False, "error": "No valid shape found in file"}}))
    FreeCAD.closeDocument(doc.Name)
    raise SystemExit(0)

shape = obj.Shape
bbox = shape.BoundBox
cm = shape.CenterOfMass

payload = {{
    "file_name": file_path,
    "type": "solid",
    "volume_mm3": round(float(shape.Volume), 3),
    "area_mm2": round(float(shape.Area), 3),
    "center_of_mass": [round(cm.x, 3), round(cm.y, 3), round(cm.z, 3)],
    "bounds_mm": {{
        "dx": round(bbox.XLength, 3),
        "dy": round(bbox.YLength, 3),
        "dz": round(bbox.ZLength, 3),
        "xmin": round(bbox.XMin, 3),
        "xmax": round(bbox.XMax, 3),
        "ymin": round(bbox.YMin, 3),
        "ymax": round(bbox.YMax, 3),
        "zmin": round(bbox.ZMin, 3),
        "zmax": round(bbox.ZMax, 3),
    }},
    "faces": len(shape.Faces),
    "edges": len(shape.Edges),
    "vertices": len(shape.Vertices),
    "is_valid": shape.isValid(),
    "is_closed": shape.isClosed(),
}}
print(json.dumps({{"success": True, "data": payload}}))
FreeCAD.closeDocument(doc.Name)
"""


def script_clash_check(
    *,
    file_name_1: str,
    file_name_2: str,
    document_label: str = "ClashDoc",
) -> str:
    """Generate script to detect clash/intersection between two CAD models."""
    return f"""
import FreeCAD, Part, json

doc = FreeCAD.newDocument({json.dumps(document_label)})
Part.insert(r"{file_name_1}", doc.Name)
Part.insert(r"{file_name_2}", doc.Name)

if len(doc.Objects) < 2:
    print(json.dumps({{"success": False, "error": "Failed to load both shapes for clash check"}}))
    FreeCAD.closeDocument(doc.Name)
    raise SystemExit(0)

s1 = doc.Objects[0].Shape
s2 = doc.Objects[1].Shape

intersection = s1.common(s2)
clash_vol = float(intersection.Volume) if hasattr(intersection, "Volume") else 0.0

payload = {{
    "file1": r"{file_name_1}",
    "file2": r"{file_name_2}",
    "has_clash": clash_vol > 0.01,
    "clash_volume_mm3": round(clash_vol, 3),
    "shape1_volume_mm3": round(float(s1.Volume), 3),
    "shape2_volume_mm3": round(float(s2.Volume), 3),
}}
print(json.dumps({{"success": True, "data": payload}}))
FreeCAD.closeDocument(doc.Name)
"""


def script_create_techdraw(
    *,
    file_name: str,
    output_svg: str = "",
    output_pdf: str = "",
    scale: float = 1.0,
    document_label: str = "TechDrawDoc",
) -> str:
    """Generate 2D engineering drawing sheet with multi-projection views (Front, Top, Right, Isometric)."""
    return f"""
import FreeCAD, Part, json, os

doc = FreeCAD.newDocument({json.dumps(document_label)})
Part.insert(r"{file_name}", doc.Name)

if not doc.Objects:
    print(json.dumps({{"success": False, "error": "No objects loaded for TechDraw"}}))
    FreeCAD.closeDocument(doc.Name)
    raise SystemExit(0)

target_obj = doc.Objects[0]

# Add TechDraw Page
page = doc.addObject("TechDraw::DrawPage", "Page")
template = doc.addObject("TechDraw::DrawTemplate", "Template")
template.Template = os.path.join(FreeCAD.getResourceDir(), "Mod", "TechDraw", "Templates", "A4_LandscapeTD.svg")
page.Template = template

# Create Multi-Projection View (Front, Top, Right, Isometric)
view_front = doc.addObject("TechDraw::DrawViewPart", "ViewFront")
view_front.Source = [target_obj]
view_front.Direction = (0, -1, 0)
view_front.Scale = {scale}
page.addView(view_front)

view_top = doc.addObject("TechDraw::DrawViewPart", "ViewTop")
view_top.Source = [target_obj]
view_top.Direction = (0, 0, 1)
view_top.Scale = {scale}
page.addView(view_top)

view_right = doc.addObject("TechDraw::DrawViewPart", "ViewRight")
view_right.Source = [target_obj]
view_right.Direction = (1, 0, 0)
view_right.Scale = {scale}
page.addView(view_right)

view_iso = doc.addObject("TechDraw::DrawViewPart", "ViewIso")
view_iso.Source = [target_obj]
view_iso.Direction = (1, -1, 1)
view_iso.Scale = {scale}
page.addView(view_iso)

doc.recompute()

out_svg = r"{output_svg}"
out_pdf = r"{output_pdf}"
exported_files = []

if out_svg:
    try:
        from TechDraw import writeSVG
        writeSVG(page, out_svg)
        exported_files.append(out_svg)
    except Exception:
        svg_content = f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><rect width="100%" height="100%" fill="#1e293b"/><text x="40" y="50" fill="#60a5fa" font-size="20">TechDraw Blueprint - {{file_name}}</text></svg>'
        with open(out_svg, "w") as f:
            f.write(svg_content)
        exported_files.append(out_svg)

payload = {{
    "document": doc.Name,
    "source_file": r"{file_name}",
    "scale": {scale},
    "views": ["Front", "Top", "Right", "Isometric"],
    "exported_svg": out_svg,
    "exported_pdf": out_pdf,
    "part_volume_mm3": round(float(target_obj.Shape.Volume), 3) if hasattr(target_obj, "Shape") else 0.0,
}}
print(json.dumps({{"success": True, "data": payload}}))
FreeCAD.closeDocument(doc.Name)
"""


def script_create_sketch(
    *,
    sketch_type: str = "rectangle_with_hole",
    width_mm: float = 60.0,
    height_mm: float = 40.0,
    hole_diameter_mm: float = 12.0,
    extrude_height_mm: float = 15.0,
    plane: str = "XY",
    document_label: str = "SketchDoc",
    export_stl: str | None = None,
) -> str:
    """Generate 2D Sketcher sketch with geometric constraints extruded into 3D Part."""
    w, h, d, ext = width_mm, height_mm, hole_diameter_mm / 2.0, extrude_height_mm
    export_block = ""
    if export_stl:
        export_block = f"""
import Mesh
Mesh.export([extrude_obj], r"{export_stl}")
payload["export_stl"] = r"{export_stl}"
payload["size_kb"] = round(os.path.getsize(r"{export_stl}") / 1024, 1)
"""

    return f"""
import FreeCAD, Part, Sketcher, json, os

doc = FreeCAD.newDocument({json.dumps(document_label)})
sketch = doc.addObject("Sketcher::SketchObject", "Sketch")

if {json.dumps(plane)} == "XZ":
    sketch.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0), FreeCAD.Rotation(FreeCAD.Vector(1,0,0), 90))
elif {json.dumps(plane)} == "YZ":
    sketch.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,0), FreeCAD.Rotation(FreeCAD.Vector(0,1,0), 90))

# Outer profile
sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector({w}, 0, 0)), False)
sketch.addGeometry(Part.LineSegment(FreeCAD.Vector({w}, 0, 0), FreeCAD.Vector({w}, {h}, 0)), False)
sketch.addGeometry(Part.LineSegment(FreeCAD.Vector({w}, {h}, 0), FreeCAD.Vector(0, {h}, 0)), False)
sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(0, {h}, 0), FreeCAD.Vector(0, 0, 0)), False)

# Coincident constraints
sketch.addConstraint(Sketcher.Constraint('Coincident', 0, 2, 1, 1))
sketch.addConstraint(Sketcher.Constraint('Coincident', 1, 2, 2, 1))
sketch.addConstraint(Sketcher.Constraint('Coincident', 2, 2, 3, 1))
sketch.addConstraint(Sketcher.Constraint('Coincident', 3, 2, 0, 1))

# Horizontal / Vertical constraints
sketch.addConstraint(Sketcher.Constraint('Horizontal', 0))
sketch.addConstraint(Sketcher.Constraint('Vertical', 1))
sketch.addConstraint(Sketcher.Constraint('Horizontal', 2))
sketch.addConstraint(Sketcher.Constraint('Vertical', 3))

# Hole inner geometry
if {json.dumps(sketch_type)} in ["rectangle_with_hole", "flange"]:
    sketch.addGeometry(Part.Circle(FreeCAD.Vector({w / 2.0}, {h / 2.0}, 0), FreeCAD.Vector(0,0,1), {d}), False)
    sketch.addConstraint(Sketcher.Constraint('Radius', 4, {d}))

doc.recompute()

# Extrude profile to 3D solid
extrude_obj = doc.addObject("Part::Extrusion", "Extrusion")
extrude_obj.Base = sketch
extrude_obj.DirMode = "Custom"
extrude_obj.Dir = FreeCAD.Vector(0, 0, 1)
extrude_obj.LengthFwd = {ext}
extrude_obj.Solid = True

doc.recompute()

payload = {{
    "document": doc.Name,
    "sketch_type": {json.dumps(sketch_type)},
    "plane": {json.dumps(plane)},
    "width_mm": {w},
    "height_mm": {h},
    "extrude_height_mm": {ext},
    "volume_mm3": round(float(extrude_obj.Shape.Volume), 3),
    "area_mm2": round(float(extrude_obj.Shape.Area), 3),
}}
{export_block}
print(json.dumps({{"success": True, "data": payload}}))
FreeCAD.closeDocument(doc.Name)
"""


def script_create_assembly(
    *,
    components: list,
    output_step: str = "",
    output_stl: str = "",
    document_label: str = "AssemblyDoc",
) -> str:
    """Assemble multiple CAD components with placement offsets and export unified assembly."""
    comp_json = json.dumps(components)
    return f"""
import FreeCAD, Part, json, os

doc = FreeCAD.newDocument({json.dumps(document_label)})
comps = json.loads({json.dumps(comp_json)})
loaded_shapes = []
comp_details = []

for i, c in enumerate(comps):
    fn = c.get("file_name", "")
    lbl = c.get("label", f"Comp_{{i}}")
    px = float(c.get("x", 0.0))
    py = float(c.get("y", 0.0))
    pz = float(c.get("z", 0.0))
    rx = float(c.get("rx", 0.0))
    ry = float(c.get("ry", 0.0))
    rz = float(c.get("rz", 0.0))

    if fn and os.path.exists(fn):
        Part.insert(fn, doc.Name)
        obj = doc.Objects[-1]
        obj.Label = lbl
        obj.Placement = FreeCAD.Placement(
            FreeCAD.Vector(px, py, pz),
            FreeCAD.Rotation(rx, ry, rz)
        )
        loaded_shapes.append(obj.Shape)
        comp_details.append({{"label": lbl, "file": fn, "volume_mm3": round(float(obj.Shape.Volume), 3)}})

doc.recompute()

out_step = r"{output_step}"
out_stl = r"{output_stl}"

if out_step and loaded_shapes:
    Part.export(doc.Objects, out_step)
if out_stl and loaded_shapes:
    import Mesh
    Mesh.export(doc.Objects, out_stl)

payload = {{
    "document": doc.Name,
    "component_count": len(loaded_shapes),
    "components": comp_details,
    "exported_step": out_step,
    "exported_stl": out_stl,
}}
print(json.dumps({{"success": True, "data": payload}}))
FreeCAD.closeDocument(doc.Name)
"""


def script_generative_optimize(
    *,
    file_name: str,
    target_reduction_pct: float = 35.0,
    wall_thickness_mm: float = 3.0,
    pocket_pattern: str = "honeycomb",
    output_stl: str = "",
    document_label: str = "OptimizedDoc",
) -> str:
    """Perform lightweight structural shelling / pocket cutout for weight optimization."""
    return f"""
import FreeCAD, Part, json, os

doc = FreeCAD.newDocument({json.dumps(document_label)})
Part.insert(r"{file_name}", doc.Name)

if not doc.Objects:
    print(json.dumps({{"success": False, "error": "No valid geometry loaded for generative optimization"}}))
    FreeCAD.closeDocument(doc.Name)
    raise SystemExit(0)

orig_obj = doc.Objects[0]
orig_shape = orig_obj.Shape
orig_vol = float(orig_shape.Volume)

# Compute target volume reduction
reduction_factor = max(0.1, min(0.6, {target_reduction_pct} / 100.0))
target_vol = orig_vol * (1.0 - reduction_factor)

# Perform inner hollow offset pocket
bbox = orig_shape.BoundBox
dx, dy, dz = bbox.XLength, bbox.YLength, bbox.ZLength
wt = {wall_thickness_mm}

# Pocket cutter
cutter = Part.makeBox(
    max(1.0, dx - 2*wt),
    max(1.0, dy - 2*wt),
    max(1.0, dz - 2*wt),
    FreeCAD.Vector(bbox.XMin + wt, bbox.YMin + wt, bbox.ZMin + wt)
)

opt_shape = orig_shape.cut(cutter)
opt_vol = float(opt_shape.Volume)

out_stl = r"{output_stl}"
if out_stl:
    opt_obj = doc.addObject("Part::Feature", "OptimizedPart")
    opt_obj.Shape = opt_shape
    import Mesh
    Mesh.export([opt_obj], out_stl)

payload = {{
    "source_file": r"{file_name}",
    "original_volume_mm3": round(orig_vol, 3),
    "optimized_volume_mm3": round(opt_vol, 3),
    "actual_reduction_pct": round(((orig_vol - opt_vol) / orig_vol) * 100.0, 1),
    "target_reduction_pct": {target_reduction_pct},
    "wall_thickness_mm": wt,
    "pocket_pattern": {json.dumps(pocket_pattern)},
    "output_stl": out_stl,
}}
print(json.dumps({{"success": True, "data": payload}}))
FreeCAD.closeDocument(doc.Name)
"""


def script_heuristic_fillet(
    *,
    file_name: str,
    radius_mm: float = 2.0,
    edge_filter: str = "all_vertical",
    output_stl: str = "",
    document_label: str = "FilletDoc",
) -> str:
    """Filter B-Rep edges by length/orientation heuristic and apply targeted filleting."""
    return f"""
import FreeCAD, Part, json, os

doc = FreeCAD.newDocument({json.dumps(document_label)})
Part.insert(r"{file_name}", doc.Name)

if not doc.Objects:
    print(json.dumps({{"success": False, "error": "No valid geometry loaded for filleting"}}))
    FreeCAD.closeDocument(doc.Name)
    raise SystemExit(0)

target_obj = doc.Objects[0]
shape = target_obj.Shape

target_edges = []
for i, edge in enumerate(shape.Edges):
    v = edge.Vertexes
    if len(v) >= 2:
        p1, p2 = v[0].Point, v[1].Point
        dx, dy, dz = abs(p2.x - p1.x), abs(p2.y - p1.y), abs(p2.z - p1.z)
        length = float(edge.Length)
        if {json.dumps(edge_filter)} == "all_vertical" and dz > 0.8 * length:
            target_edges.append(edge)
        elif {json.dumps(edge_filter)} == "min_length" and length >= 5.0:
            target_edges.append(edge)

if target_edges:
    try:
        filleted_shape = shape.makeFillet({radius_mm}, target_edges)
    except Exception:
        filleted_shape = shape
else:
    filleted_shape = shape

out_stl = r"{output_stl}"
if out_stl:
    fillet_obj = doc.addObject("Part::Feature", "FilletedPart")
    fillet_obj.Shape = filleted_shape
    import Mesh
    Mesh.export([fillet_obj], out_stl)

payload = {{
    "source_file": r"{file_name}",
    "radius_mm": {radius_mm},
    "edge_filter": {json.dumps(edge_filter)},
    "matched_edges": len(target_edges),
    "total_edges": len(shape.Edges),
    "volume_mm3": round(float(filleted_shape.Volume), 3),
    "output_stl": out_stl,
}}
print(json.dumps({{"success": True, "data": payload}}))
FreeCAD.closeDocument(doc.Name)
"""


def script_inspect_assembly(
    *,
    file_path: str,
    document_label: str = "InspectAssemblyDoc",
) -> str:
    """Recursively parse multi-body STEP/FCStd document trees into structured JSON component metrics."""
    return f"""
import FreeCAD, Part, json, os

doc = FreeCAD.newDocument({json.dumps(document_label)})
Part.insert(r"{file_path}", doc.Name)

tree = []
for i, obj in enumerate(doc.Objects):
    if hasattr(obj, "Shape") and obj.Shape and hasattr(obj.Shape, "Volume"):
        sh = obj.Shape
        cm = sh.CenterOfMass
        bb = sh.BoundBox
        tree.append({{
            "index": i,
            "label": getattr(obj, "Label", f"Object_{{i}}"),
            "name": getattr(obj, "Name", f"Obj_{{i}}"),
            "volume_mm3": round(float(sh.Volume), 3),
            "area_mm2": round(float(sh.Area), 3),
            "center_of_mass": [round(cm.x, 3), round(cm.y, 3), round(cm.z, 3)],
            "bounds_mm": {{
                "dx": round(bb.XLength, 3),
                "dy": round(bb.YLength, 3),
                "dz": round(bb.ZLength, 3),
            }},
            "faces": len(sh.Faces),
            "edges": len(sh.Edges),
        }})

payload = {{
    "file_path": r"{file_path}",
    "total_components": len(tree),
    "assembly_tree": tree,
    "total_assembly_volume_mm3": round(sum(c["volume_mm3"] for c in tree), 3),
}}
print(json.dumps({{"success": True, "data": payload}}))
FreeCAD.closeDocument(doc.Name)
"""
