"""FreeCAD STEP-to-STL export: open STEP, export all solids as STL."""

import os
import sys

fc_bin = r"D:\Dev\repos\FreeCAD\FreeCAD_1.1.1-Windows-x86_64-py311\bin"
sys.path = [p for p in sys.path if "freecad" not in p.lower()]
sys.path.insert(0, fc_bin)
os.chdir(fc_bin)

import FreeCAD
import Mesh

STEP = r"C:\Users\sandr\AppData\Local\Temp\raspbot_v2_step.STEP"
OUT = r"D:\Dev\repos\yahboom-mcp\webapp\public\assets\meshes"
os.makedirs(OUT, exist_ok=True)

print("Opening STEP file...", flush=True)
doc = FreeCAD.openDocument(STEP)
doc.recompute()
objs = doc.Objects
print(f"Objects: {len(objs)}", flush=True)

for i, obj in enumerate(objs):
    name = obj.Label or f"part_{i:02d}"
    safe = "".join(c for c in name if c.isalnum() or c in "_-").strip() or f"part_{i:02d}"
    path = os.path.join(OUT, f"boomy_{i:02d}_{safe}.stl")
    try:
        shapes = [obj] if not hasattr(obj, "Shape") or obj.Shape.isNull() else [obj]
        Mesh.export(shapes, path)
        sz = os.path.getsize(path) / 1024
        print(f"  [{i}] {name} — {sz:.0f} KB", flush=True)
    except Exception as e:
        print(f"  [{i}] {name} — {e}", flush=True)

FreeCAD.closeDocument(doc.Name)
print("Done.", flush=True)
