"""Toy car geometry helpers - Blender script loading and FreeCAD build snippets."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _repo_candidates() -> list[Path]:
    env_root = os.environ.get("BLENDER_MCP_REPO", "").strip()
    here = Path(__file__).resolve()
    return [
        Path(env_root) if env_root else Path(),
        here.parents[2].parent / "blender-mcp",
        Path("D:/Dev/repos/blender-mcp"),
    ]


def load_blender_sports_car_script() -> str | None:
    """Load the sports_car bpy script from blender-mcp vehicles.json."""
    for root in _repo_candidates():
        vehicles = root / "data" / "scripts" / "vehicles.json"
        if not vehicles.is_file():
            continue
        try:
            data = json.loads(vehicles.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for entry in data:
            if entry.get("name") == "sports_car" and entry.get("script"):
                return str(entry["script"])
    return None


def blender_build_and_export_script(*, export_stl: str, body_length_mm: float) -> str:
    """Headless Blender script: build sports car, join meshes, export STL in mm."""
    car_script = load_blender_sports_car_script()
    if not car_script:
        raise FileNotFoundError("sports_car script not found. Set BLENDER_MCP_REPO to blender-mcp checkout.")
    scale = body_length_mm / 190.0
    export_stl = export_stl.replace("\\", "/")
    return f"""
import bpy, os, math

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

{car_script}

# Join car mesh parts for a single printable solid
bpy.ops.object.select_all(action='DESELECT')
car_parts = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('Car_')]
if not car_parts:
    car_parts = [o for o in bpy.data.objects if o.type == 'MESH']
for o in car_parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = car_parts[0]
if len(car_parts) > 1:
    bpy.ops.object.join()
car = bpy.context.active_object
car.name = 'ToyCarExport'

bpy.ops.object.select_all(action='DESELECT')
car.select_set(True)
bpy.context.view_layer.objects.active = car

out_path = r"{export_stl}"
os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
bpy.ops.export_mesh.stl(
    filepath=out_path,
    use_selection=True,
    use_mesh_modifiers=True,
    global_scale={scale},
)
print("SCRIPT_DONE: exported", out_path, "scale", {scale})
"""


def freecad_sports_car_shape_block() -> str:
    """Return FreeCAD Python that assigns ``car_shape`` from dimensions L,W,H,wheel_r,wheelbase."""
    return """
def _place(shape, x, y, z):
    shape.translate(FreeCAD.Vector(x, y, z))
    return shape

L = float(L)
W = float(W)
H = float(H)
wheel_r = float(wheel_r)
wheelbase = float(wheelbase)
ground = wheel_r

chassis_h = H * 0.52
body = _place(Part.makeBox(L, W, chassis_h), 0, 0, ground)

cabin_l = L * 0.44
cabin_w = W * 0.72
cabin_h = H * 0.58
cabin = _place(Part.makeBox(cabin_l, cabin_w, cabin_h), L * 0.24, -cabin_w / 2, ground + chassis_h * 0.82)

bonnet = _place(Part.makeBox(L * 0.36, W * 0.86, H * 0.18), 0, -W * 0.43, ground + chassis_h * 0.62)

nose = _place(Part.makeBox(L * 0.14, W * 0.68, H * 0.28), 0, -W * 0.34, ground + chassis_h * 0.72)

car_shape = body.fuse(cabin).fuse(bonnet).fuse(nose)

spoiler_mount = _place(Part.makeBox(L * 0.035, W * 0.10, H * 0.32), L * 0.84, -W * 0.05, ground + chassis_h + cabin_h * 0.35)
spoiler_wing = _place(Part.makeBox(L * 0.06, W * 0.52, H * 0.09), L * 0.82, -W * 0.26, ground + chassis_h + cabin_h * 0.72)
car_shape = car_shape.fuse(spoiler_mount).fuse(spoiler_wing)

grille = _place(Part.makeBox(L * 0.025, W * 0.55, H * 0.12), L * 0.01, -W * 0.275, ground + chassis_h * 0.35)
car_shape = car_shape.cut(grille)

for hy in (-W * 0.30, W * 0.30):
    hl = Part.makeSphere(wheel_r * 0.32)
    hl.translate(FreeCAD.Vector(L * 0.025, hy, ground + chassis_h * 0.42))
    car_shape = car_shape.fuse(hl)

for hy in (-W * 0.28, W * 0.28):
    tl = Part.makeSphere(wheel_r * 0.22)
    tl.translate(FreeCAD.Vector(L * 0.93, hy, ground + chassis_h * 0.38))
    car_shape = car_shape.fuse(tl)

front_bumper = _place(Part.makeBox(L * 0.07, W * 0.94, H * 0.14), 0, -W * 0.47, ground + wheel_r * 0.35)
rear_bumper = _place(Part.makeBox(L * 0.07, W * 0.94, H * 0.12), L * 0.93, -W * 0.47, ground + wheel_r * 0.32)
car_shape = car_shape.fuse(front_bumper).fuse(rear_bumper)

wheel_y = W * 0.48
wheel_positions = [
    (wheelbase * 0.5, wheel_y, ground),
    (wheelbase * 0.5, -wheel_y, ground),
    (L - wheelbase * 0.5, wheel_y, ground),
    (L - wheelbase * 0.5, -wheel_y, ground),
]
for wx, wy, wz in wheel_positions:
    arch = Part.makeSphere(wheel_r * 1.12)
    arch.translate(FreeCAD.Vector(wx, wy, wz + wheel_r * 0.55))
    car_shape = car_shape.cut(arch)

    tire = Part.makeTorus(wheel_r, wheel_r * 0.34, FreeCAD.Vector(wx, wy, wz + wheel_r), FreeCAD.Vector(0, 1, 0))
    hub = Part.makeCylinder(wheel_r * 0.55, wheel_r * 0.22, FreeCAD.Vector(wx, wy - wheel_r * 0.11, wz + wheel_r), FreeCAD.Vector(0, 1, 0))
    car_shape = car_shape.fuse(tire).fuse(hub)
"""
