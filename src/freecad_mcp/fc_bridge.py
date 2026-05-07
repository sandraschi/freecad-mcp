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

PORT = int(os.environ.get("FC_BRIDGE_PORT", "10946"))
FreeCAD.Console.PrintMessage(f"FreeCAD Bridge starting on port {PORT}...\n")

# Ensure GUI is ready
FreeCADGui.showMainWindow(True)


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
                            "bbox": {"xmin": bb.XMin, "ymin": bb.YMin, "zmin": bb.ZMin, "xmax": bb.XMax, "ymax": bb.YMax, "zmax": bb.ZMax},
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
                                    infos.append({
                                        "name": o.Label,
                                        "solids": len(s.Solids),
                                        "volume": round(s.Volume, 3) if s.Volume else 0,
                                        "bbox": {"xmin": bb.XMin, "ymin": bb.YMin, "zmin": bb.ZMin, "xmax": bb.XMax, "ymax": bb.YMax, "zmax": bb.ZMax},
                                    })
                            except Exception:
                                pass
                        result["data"] = {"objects": infos, "total": len(infos)}
                        FreeCAD.closeDocument(doc.Name)

                elif method == "create_shape":
                    stl_path = params["path"]
                    st = params.get("shape_type", "box")
                    p = params.get("params", {})
                    import Part

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
