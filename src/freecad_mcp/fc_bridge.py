"""
FreeCAD TCP bridge — runs inside FreeCAD GUI as a startup macro.
Listens on a TCP socket for JSON commands, executes them using FreeCAD's
full API (including Import/Part/Mesh), and returns JSON responses.

Started automatically by the freecad-mcp server via:
  FreeCAD.exe fc_bridge.py
"""

import json
import os
import socketserver

import FreeCAD
import FreeCADGui
import Import
import Mesh
import Part

# BIM module imports — available inside FreeCAD GUI
try:
    import Arch
    import Draft

    _BIM_READY = True
except ImportError:
    _BIM_READY = False

PORT = int(os.environ.get("FC_BRIDGE_PORT", "10946"))
FreeCAD.Console.PrintMessage(f"FreeCAD Bridge starting on port {PORT}...\n")

# Ensure GUI is ready
try:
    FreeCADGui.showMainWindow()
except Exception:
    try:
        FreeCADGui.showMainWindow(True)
    except Exception:
        FreeCAD.Console.PrintMessage("GUI showMainWindow not available, continuing anyway\n")


class BridgeHandler(socketserver.StreamRequestHandler):
    """Handles one JSON command over TCP."""

    def handle(self):
        try:
            data = self.rfile.readline()
            if not data:
                return
            req = json.loads(data.decode("utf-8"))
            req_id = req.get("id", 0)
            method = req.get("method", "")
            params = req.get("params", {})
            result = {"id": req_id, "success": True}

            try:
                if method == "ping":
                    result["data"] = "pong"

                elif method == "status":
                    result["data"] = {
                        "freecad_version": FreeCAD.Version,
                        "documents": len(FreeCAD.listDocuments()),
                    }

                elif method == "open":
                    path = params["path"]
                    name = params.get("name", "Document")
                    doc = FreeCAD.openDocument(path)
                    if doc is None:
                        doc = FreeCAD.newDocument(name)
                        Import.insert(path, name)
                    doc.recompute()
                    objs = [
                        {
                            "name": o.Label,
                            "type": o.TypeId,
                            "solids": len(o.Shape.Solids) if hasattr(o, "Shape") and o.Shape else 0,
                        }
                        for o in doc.Objects
                    ]
                    result["data"] = {"document": doc.Name, "objects": objs}

                elif method == "export_stl":
                    doc_name = params.get("document", FreeCAD.ActiveDocument.Name)
                    stl_path = params["path"]
                    doc = FreeCAD.getDocument(doc_name)
                    Mesh.export(doc.Objects, stl_path)
                    sz = os.path.getsize(stl_path)
                    result["data"] = {"size_bytes": sz, "size_kb": round(sz / 1024, 1)}

                elif method == "model_info":
                    path = params["path"]
                    if path.lower().endswith(".stl"):
                        mesh = Mesh.Mesh(path)
                        bb = mesh.BoundBox
                        result["data"] = {
                            "type": "mesh",
                            "vertices": len(mesh.Points),
                            "facets": mesh.CountFacets,
                            "bbox": {
                                "xmin": bb.XMin,
                                "ymin": bb.YMin,
                                "zmin": bb.ZMin,
                                "xmax": bb.XMax,
                                "ymax": bb.YMax,
                                "zmax": bb.ZMax,
                            },
                        }
                    else:
                        doc = FreeCAD.openDocument(path)
                        doc.recompute()
                        infos = []
                        for o in doc.Objects:
                            try:
                                s = o.Shape
                                if s and s.Solids:
                                    bb = s.BoundingBox
                                    infos.append(
                                        {
                                            "name": o.Label,
                                            "solids": len(s.Solids),
                                            "volume": round(s.Volume, 3) if s.Volume else 0,
                                            "bbox": {
                                                "xmin": bb.XMin,
                                                "ymin": bb.YMin,
                                                "zmin": bb.ZMin,
                                                "xmax": bb.XMax,
                                                "ymax": bb.YMax,
                                                "zmax": bb.ZMax,
                                            },
                                        }
                                    )
                            except Exception:
                                pass
                        result["data"] = {"objects": infos, "total": len(infos)}
                        FreeCAD.closeDocument(doc.Name)

                elif method == "create_shape":
                    stl_path = params["path"]
                    st = params.get("shape_type", "box")
                    p = params.get("params", {})

                    if st == "box":
                        s = Part.makeBox(p.get("width", 10), p.get("height", 10), p.get("depth", 10))
                    elif st == "cylinder":
                        s = Part.makeCylinder(p.get("radius", 5), p.get("height", 20))
                    elif st == "sphere":
                        s = Part.makeSphere(p.get("radius", 10))
                    elif st == "cone":
                        s = Part.makeCone(p.get("radius", 5), 0, p.get("height", 15))
                    else:
                        raise ValueError(f"Unknown shape: {st}")
                    m = Mesh.Mesh(s)
                    m.write(stl_path)
                    sz = os.path.getsize(stl_path)
                    result["data"] = {"size_bytes": sz, "size_kb": round(sz / 1024, 1)}

                elif method == "bim_create_wall":
                    params = params  # shadow from outer scope
                    doc = FreeCAD.newDocument("BIM_Wall")
                    try:
                        p1 = FreeCAD.Vector(0, 0, 0)
                        p2 = FreeCAD.Vector(params["length"], 0, 0)
                        line = Draft.makeLine(p1, p2)
                        wall = Arch.makeWall(line, width=params["width"], height=params["height"])
                        wall.Label = "Wall"
                        wall.Placement = FreeCAD.Placement(
                            FreeCAD.Vector(params["x"], params["y"], params["z"]),
                            FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), params.get("rotation_z", 0)),
                        )
                        doc.recompute()
                        doc.saveAs(params["path"])
                        doc.recompute()
                        result["data"] = {
                            "label": wall.Label,
                            "length": params["length"],
                            "width": params["width"],
                            "height": params["height"],
                            "path": params["path"],
                        }
                    finally:
                        FreeCAD.closeDocument(doc.Name)

                elif method == "bim_create_slab":
                    doc = FreeCAD.newDocument("BIM_Slab")
                    try:
                        box = Part.makeBox(params["width"], params["length"], params["thickness"])
                        slab = Arch.makeStructure(box)
                        slab.Label = "Slab"
                        slab.IfcType = "Slab"
                        slab.Placement = FreeCAD.Placement(
                            FreeCAD.Vector(params["x"], params["y"], params["z"]),
                            FreeCAD.Rotation(),
                        )
                        doc.recompute()
                        doc.saveAs(params["path"])
                        doc.recompute()
                        result["data"] = {
                            "label": slab.Label,
                            "width": params["width"],
                            "length": params["length"],
                            "thickness": params["thickness"],
                            "path": params["path"],
                        }
                    finally:
                        FreeCAD.closeDocument(doc.Name)

                elif method == "bim_create_column":
                    doc = FreeCAD.newDocument("BIM_Column")
                    try:
                        profile = params["profile"]
                        w = params["width"]
                        d = params["depth"]
                        h = params["height"]
                        if profile == "circular":
                            s = Part.makeCylinder(w / 2, h)
                        elif profile == "h_section":
                            wb = Part.makeBox(w, d, h)
                            s1 = Part.makeBox(d, w * 0.25, h)
                            s2 = Part.makeBox(w * 0.5, d * 0.3, h)
                            s = wb.fuse(s1).fuse(s2)
                        else:
                            s = Part.makeBox(w, d, h)
                        col = Arch.makeStructure(s)
                        col.Label = "Column"
                        col.IfcType = "Column"
                        col.Placement = FreeCAD.Placement(
                            FreeCAD.Vector(params["x"], params["y"], params["z"]),
                            FreeCAD.Rotation(),
                        )
                        doc.recompute()
                        doc.saveAs(params["path"])
                        doc.recompute()
                        result["data"] = {
                            "label": col.Label,
                            "profile": profile,
                            "width": w,
                            "depth": d,
                            "height": h,
                            "path": params["path"],
                        }
                    finally:
                        FreeCAD.closeDocument(doc.Name)

                elif method == "bim_create_window":
                    doc = FreeCAD.newDocument("BIM_Window")
                    try:
                        ww = params["width"]
                        wh = params["height"]
                        wall_len = ww + 2000
                        p1 = FreeCAD.Vector(0, 0, 0)
                        p2 = FreeCAD.Vector(wall_len, 0, 0)
                        host_line = Draft.makeLine(p1, p2)
                        host_wall = Arch.makeWall(host_line, width=200, height=wh + params["sill_height"] + 400)
                        host_wall.Label = "HostWall"
                        host_wall.Placement = FreeCAD.Placement(
                            FreeCAD.Vector(params["x"], params["y"], params["z"]),
                            FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), params.get("rotation_z", 0)),
                        )
                        win = Arch.makeWindow(None, width=ww, height=wh)
                        win.Label = "Window"
                        win.Placement = FreeCAD.Placement(
                            FreeCAD.Vector(wall_len / 2 - ww / 2, params["sill_height"], 0),
                            FreeCAD.Rotation(),
                        )
                        if hasattr(win, "Hosts"):
                            win.Hosts = [host_wall]
                        doc.recompute()
                        doc.saveAs(params["path"])
                        doc.recompute()
                        result["data"] = {
                            "label": win.Label,
                            "window_type": params.get("window_type", "fixed"),
                            "width": ww,
                            "height": wh,
                            "path": params["path"],
                        }
                    finally:
                        FreeCAD.closeDocument(doc.Name)

                elif method == "bim_create_door":
                    doc = FreeCAD.newDocument("BIM_Door")
                    try:
                        dw = params["width"]
                        dh = params["height"]
                        wall_len = dw + 2000
                        p1 = FreeCAD.Vector(0, 0, 0)
                        p2 = FreeCAD.Vector(wall_len, 0, 0)
                        host_line = Draft.makeLine(p1, p2)
                        host_wall = Arch.makeWall(host_line, width=200, height=dh + 400)
                        host_wall.Label = "HostWall"
                        host_wall.Placement = FreeCAD.Placement(
                            FreeCAD.Vector(params["x"], params["y"], params["z"]),
                            FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), params.get("rotation_z", 0)),
                        )
                        door = Arch.makeWindow(None, width=dw, height=dh)
                        door.Label = "Door"
                        door.Placement = FreeCAD.Placement(
                            FreeCAD.Vector(wall_len / 2 - dw / 2, 0, 0),
                            FreeCAD.Rotation(),
                        )
                        if hasattr(door, "Hosts"):
                            door.Hosts = [host_wall]
                        doc.recompute()
                        doc.saveAs(params["path"])
                        doc.recompute()
                        result["data"] = {
                            "label": door.Label,
                            "door_type": params.get("door_type", "simple"),
                            "width": dw,
                            "height": dh,
                            "path": params["path"],
                        }
                    finally:
                        FreeCAD.closeDocument(doc.Name)

                elif method == "bim_create_roof":
                    doc = FreeCAD.newDocument("BIM_Roof")
                    try:
                        face = Part.makePlane(params["width"], params["length"])
                        roof = Arch.makeRoof(face, angle=params["angle"], thickness=params["thickness"])
                        roof.Label = "Roof"
                        roof.Placement = FreeCAD.Placement(
                            FreeCAD.Vector(params["x"], params["y"], params["z"]),
                            FreeCAD.Rotation(),
                        )
                        doc.recompute()
                        doc.saveAs(params["path"])
                        doc.recompute()
                        result["data"] = {
                            "label": roof.Label,
                            "width": params["width"],
                            "length": params["length"],
                            "angle": params["angle"],
                            "thickness": params["thickness"],
                            "path": params["path"],
                        }
                    finally:
                        FreeCAD.closeDocument(doc.Name)

                elif method == "bim_export_ifc":
                    doc = FreeCAD.openDocument(params["src"])
                    try:
                        Import.export(doc.Objects, params["dst"])
                        sz = os.path.getsize(params["dst"])
                        result["data"] = {
                            "path": params["dst"],
                            "size_kb": round(sz / 1024, 1),
                            "objects": len(doc.Objects),
                        }
                    finally:
                        FreeCAD.closeDocument(doc.Name)

                elif method == "bim_import_ifc":
                    doc = FreeCAD.newDocument("IFC_Import")
                    try:
                        Import.insert(params["src"], doc.Name)
                        doc.recompute()
                        doc.saveAs(params["dst"])
                        doc.recompute()
                        names = [o.Label for o in doc.Objects]
                        result["data"] = {
                            "path": params["dst"],
                            "objects": len(doc.Objects),
                            "object_names": names[:50],
                        }
                    finally:
                        FreeCAD.closeDocument(doc.Name)

                elif method == "mesh_to_solid":
                    import MeshPart
                    stl_path = params["path"]
                    output_path = params.get("output_path", stl_path.replace(".stl", "_solid.FCStd"))
                    doc = FreeCAD.newDocument("MeshToSolid")
                    try:
                        mesh = Mesh.Mesh(stl_path)
                        if mesh.CountPoints == 0:
                            result["success"] = False
                            result["error"] = "Empty mesh"
                        else:
                            shape = MeshPart.meshFromShape(mesh)
                            solid = Part.makeSolid(shape)
                            if solid.isValid():
                                obj = doc.addObject("Part::Feature", "Solid")
                                obj.Shape = solid
                                doc.recompute()
                                doc.saveAs(output_path)
                                result["success"] = True
                                result["data"] = {
                                    "output": output_path,
                                    "vertices": mesh.CountPoints,
                                    "facets": mesh.CountFacets,
                                    "volume_mm3": round(solid.Volume, 1),
                                }
                            else:
                                result["success"] = False
                                result["error"] = "Could not create valid solid from mesh"
                    finally:
                        FreeCAD.closeDocument(doc.Name)

                else:
                    result["success"] = False
                    result["error"] = f"Unknown method: {method}"

            except Exception as e:
                result["success"] = False
                result["error"] = str(e)
                FreeCAD.Console.PrintError(f"Bridge error: {e}\n")

            response = json.dumps(result) + "\n"
            self.wfile.write(response.encode("utf-8"))

        except Exception as e:
            FreeCAD.Console.PrintError(f"Bridge handler fatal: {e}\n")


class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    server = ThreadedServer(("127.0.0.1", PORT), BridgeHandler)
    FreeCAD.Console.PrintMessage(f"Bridge listening on 127.0.0.1:{PORT}\n")
    server.serve_forever()
