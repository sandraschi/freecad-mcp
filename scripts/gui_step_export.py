"""FreeCAD GUI-import of AP214 STEP: export all visible solids as STL."""
import sys, os, json

# Point to FreeCAD's Python libs
fc_bin = r"C:\Users\sandr\AppData\Local\Temp\freecad_extracted\FreeCAD_1.1.1-Windows-x86_64-py311\bin"
sys.path = [fc_bin] + [p for p in sys.path if "freecad" not in p.lower()]

import FreeCAD, FreeCADGui, Import, Mesh

STEP = r"C:\Users\sandr\AppData\Local\Temp\raspbot_v2_step.STEP"
OUT = r"D:\Dev\repos\yahboom-mcp\webapp\public\assets\meshes"
os.makedirs(OUT, exist_ok=True)

# Init GUI (needed for proper STEP assembly import)
FreeCADGui.setupWithoutGUI()

print("Opening STEP via GUI pipeline...", flush=True)
doc = FreeCAD.openDocument(STEP)
doc.recompute()
print(f"Objects: {len(doc.Objects)}", flush=True)

for i, obj in enumerate(doc.Objects):
    name = obj.Label or f"part_{i:02d}"
    safe = "".join(c for c in name if c.isalnum() or c in "_-").strip() or f"part_{i:02d}"
    path = os.path.join(OUT, f"boomy_{i:02d}_{safe}.stl")
    try:
        Mesh.export([obj], path)
        sz = os.path.getsize(path) / 1024
        print(f"  [{i}] {name} — {sz:.0f} KB", flush=True)
    except Exception as e:
        print(f"  [{i}] {name} — {e}", flush=True)

FreeCAD.closeDocument(doc.Name)
print("Done.", flush=True)
