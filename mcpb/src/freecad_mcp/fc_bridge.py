"""
FreeCAD TCP bridge - runs inside FreeCAD GUI as a startup macro.
Listens on a TCP socket for JSON commands, executes them using FreeCAD's
full API (including Import/Part/Mesh), and returns JSON responses.

Started automatically by the freecad-mcp server via:
  FreeCAD.exe fc_bridge.py
"""

import base64
import json
import os
import socketserver
import tempfile

import FreeCAD
import FreeCADGui
import Import
import Mesh
import Part

# BIM module imports - available inside FreeCAD GUI
try:
    import Arch
    import Draft

    _BIM_READY = True
except ImportError:
    _BIM_READY = False

PORT = int(os.environ.get("FC_BRIDGE_PORT", "10946"))
FreeCAD.Console.PrintMessage(f"FreeCAD Bridge starting on port {PORT}...\n")


def _get_doc(params: dict):
    name = params.get("document")
    if name:
        return FreeCAD.getDocument(name)
    if FreeCAD.ActiveDocument is None:
        return FreeCAD.newDocument(params.get("document_label", "MCP_Model"))
    return FreeCAD.ActiveDocument


def _object_info(obj) -> dict:
    info = {"name": obj.Name, "label": obj.Label, "type": obj.TypeId}
    try:
        if hasattr(obj, "Shape") and obj.Shape:
            bb = obj.Shape.BoundBox
            info["solids"] = len(obj.Shape.Solids)
            info["volume_mm3"] = round(float(obj.Shape.Volume), 3) if obj.Shape.Volume else 0.0
            info["bbox"] = {
                "xmin": bb.XMin,
                "ymin": bb.YMin,
                "zmin": bb.ZMin,
                "xmax": bb.XMax,
                "ymax": bb.YMax,
                "zmax": bb.ZMax,
            }
    except Exception:
        pass
    return info


def _make_primitive_shape(primitive_type: str, params: dict):
    p = params or {}
    if primitive_type == "box":
        return Part.makeBox(p.get("width", 10), p.get("height", 10), p.get("depth", 10))
    if primitive_type == "cylinder":
        return Part.makeCylinder(
            p.get("radius", 5),
            p.get("height", 20),
            FreeCAD.Vector(p.get("x", 0), p.get("y", 0), p.get("z", 0)),
        )
    if primitive_type == "sphere":
        return Part.makeSphere(p.get("radius", 10))
    if primitive_type == "cone":
        return Part.makeCone(p.get("radius", 5), p.get("radius2", 0), p.get("height", 15))
    raise ValueError(f"Unknown primitive_type: {primitive_type}")


def _apply_placement(obj, placement: dict | None):
    placement = placement or {}
    obj.Placement = FreeCAD.Placement(
        FreeCAD.Vector(placement.get("x", 0), placement.get("y", 0), placement.get("z", 0)),
        FreeCAD.Rotation(
            placement.get("rx", 0),
            placement.get("ry", 0),
            placement.get("rz", 0),
        ),
    )


def _place_shape(shape, x, y, z):
    shape.translate(FreeCAD.Vector(x, y, z))
    return shape


def _build_sports_car_shape(body_length, body_width, body_height, wheel_radius, wheelbase):
    """Elaborate sports-toy car solid - chassis, cabin, arches, torus wheels."""
    l_val = float(body_length)
    w_val = float(body_width)
    h_val = float(body_height)
    wheel_r = float(wheel_radius)
    wheelbase_val = float(wheelbase)
    ground = wheel_r

    chassis_h = h_val * 0.52
    car_shape = _place_shape(Part.makeBox(l_val, w_val, chassis_h), 0, 0, ground)

    cabin_l = l_val * 0.44
    cabin_w = w_val * 0.72
    cabin_h = h_val * 0.58
    cabin = _place_shape(Part.makeBox(cabin_l, cabin_w, cabin_h), l_val * 0.24, -cabin_w / 2, ground + chassis_h * 0.82)
    car_shape = car_shape.fuse(cabin)

    bonnet = _place_shape(
        Part.makeBox(l_val * 0.36, w_val * 0.86, h_val * 0.18), 0, -w_val * 0.43, ground + chassis_h * 0.62
    )
    nose = _place_shape(
        Part.makeBox(l_val * 0.14, w_val * 0.68, h_val * 0.28), 0, -w_val * 0.34, ground + chassis_h * 0.72
    )
    car_shape = car_shape.fuse(bonnet).fuse(nose)

    spoiler_mount = _place_shape(
        Part.makeBox(l_val * 0.035, w_val * 0.10, h_val * 0.32),
        l_val * 0.84,
        -w_val * 0.05,
        ground + chassis_h + cabin_h * 0.35,
    )
    spoiler_wing = _place_shape(
        Part.makeBox(l_val * 0.06, w_val * 0.52, h_val * 0.09),
        l_val * 0.82,
        -w_val * 0.26,
        ground + chassis_h + cabin_h * 0.72,
    )
    car_shape = car_shape.fuse(spoiler_mount).fuse(spoiler_wing)

    grille = _place_shape(
        Part.makeBox(l_val * 0.025, w_val * 0.55, h_val * 0.12),
        l_val * 0.01,
        -w_val * 0.275,
        ground + chassis_h * 0.35,
    )
    car_shape = car_shape.cut(grille)

    for hy in (-w_val * 0.30, w_val * 0.30):
        hl = Part.makeSphere(wheel_r * 0.32)
        hl.translate(FreeCAD.Vector(l_val * 0.025, hy, ground + chassis_h * 0.42))
        car_shape = car_shape.fuse(hl)

    for hy in (-w_val * 0.28, w_val * 0.28):
        tl = Part.makeSphere(wheel_r * 0.22)
        tl.translate(FreeCAD.Vector(l_val * 0.93, hy, ground + chassis_h * 0.38))
        car_shape = car_shape.fuse(tl)

    front_bumper = _place_shape(
        Part.makeBox(l_val * 0.07, w_val * 0.94, h_val * 0.14),
        0,
        -w_val * 0.47,
        ground + wheel_r * 0.35,
    )
    rear_bumper = _place_shape(
        Part.makeBox(l_val * 0.07, w_val * 0.94, h_val * 0.12),
        l_val * 0.93,
        -w_val * 0.47,
        ground + wheel_r * 0.32,
    )
    car_shape = car_shape.fuse(front_bumper).fuse(rear_bumper)

    wheel_y = w_val * 0.48
    wheel_positions = [
        (wheelbase_val * 0.5, wheel_y, ground),
        (wheelbase_val * 0.5, -wheel_y, ground),
        (l_val - wheelbase_val * 0.5, wheel_y, ground),
        (l_val - wheelbase_val * 0.5, -wheel_y, ground),
    ]
    for wx, wy, wz in wheel_positions:
        arch = Part.makeSphere(wheel_r * 1.12)
        arch.translate(FreeCAD.Vector(wx, wy, wz + wheel_r * 0.55))
        car_shape = car_shape.cut(arch)

        tire = Part.makeTorus(
            wheel_r,
            wheel_r * 0.34,
            FreeCAD.Vector(wx, wy, wz + wheel_r),
            FreeCAD.Vector(0, 1, 0),
        )
        hub = Part.makeCylinder(
            wheel_r * 0.55,
            wheel_r * 0.22,
            FreeCAD.Vector(wx, wy - wheel_r * 0.11, wz + wheel_r),
            FreeCAD.Vector(0, 1, 0),
        )
        car_shape = car_shape.fuse(tire).fuse(hub)

    return car_shape


def _build_toy_car(doc, params: dict):
    body_length = float(params.get("body_length_mm", 120))
    body_width = float(params.get("body_width_mm", 60))
    body_height = float(params.get("body_height_mm", 35))
    wheel_radius = float(params.get("wheel_radius_mm", 12))
    wheelbase = float(params.get("wheelbase_mm", 70))

    car_shape = _build_sports_car_shape(body_length, body_width, body_height, wheel_radius, wheelbase)
    result = doc.addObject("Part::Feature", "ToyCar")
    result.Shape = car_shape
    doc.recompute()
    return result


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

                elif method == "list_objects":
                    doc = _get_doc(params)
                    doc.recompute()
                    result["data"] = {
                        "document": doc.Name,
                        "objects": [_object_info(o) for o in doc.Objects],
                        "count": len(doc.Objects),
                    }

                elif method == "screenshot_view":
                    width = int(params.get("width", 1280))
                    height = int(params.get("height", 720))
                    output_path = params.get("path") or os.path.join(
                        tempfile.gettempdir(),
                        "freecad_mcp_view.png",
                    )
                    view = FreeCADGui.activeDocument().activeView()
                    if view is None:
                        raise RuntimeError("No active 3D view - open FreeCAD GUI with a document")
                    view.saveImage(output_path, width, height)
                    with open(output_path, "rb") as img_file:
                        encoded = base64.b64encode(img_file.read()).decode("ascii")
                    result["data"] = {
                        "path": output_path,
                        "width": width,
                        "height": height,
                        "base64_png": encoded,
                        "size_kb": round(os.path.getsize(output_path) / 1024, 1),
                    }

                elif method == "execute_script":
                    script = params.get("script", "")
                    if not script.strip():
                        raise ValueError("script is empty")
                    doc = _get_doc(params)
                    local_ns = {
                        "FreeCAD": FreeCAD,
                        "App": FreeCAD,
                        "Part": Part,
                        "Mesh": Mesh,
                        "doc": doc,
                        "FreeCADGui": FreeCADGui,
                    }
                    exec(script, {"__builtins__": {}}, local_ns)  # noqa: S102
                    doc.recompute()
                    result["data"] = {
                        "document": doc.Name,
                        "objects": [_object_info(o) for o in doc.Objects],
                    }

                elif method == "new_document":
                    label = params.get("document_label", "MCP_Model")
                    doc = FreeCAD.newDocument(label)
                    result["data"] = {"document": doc.Name, "label": label}

                elif method == "add_primitive":
                    doc = _get_doc(params)
                    label = params.get("label", "Part")
                    obj = doc.addObject("Part::Feature", label)
                    obj.Shape = _make_primitive_shape(params.get("primitive_type", "box"), params.get("params", {}))
                    _apply_placement(obj, params.get("placement"))
                    doc.recompute()
                    result["data"] = _object_info(obj) | {"document": doc.Name}

                elif method == "model_boolean":
                    doc = _get_doc(params)
                    operation = params.get("operation", "fuse")
                    names = params.get("object_names", [])
                    if len(names) < 2:
                        raise ValueError("model_boolean requires at least two object_names")
                    objs = [doc.getObject(n) for n in names]
                    if any(o is None for o in objs):
                        raise ValueError("One or more object_names not found in document")
                    base = objs[0].Shape
                    for obj in objs[1:]:
                        if operation == "fuse":
                            base = base.fuse(obj.Shape)
                        elif operation == "cut":
                            base = base.cut(obj.Shape)
                        elif operation == "common":
                            base = base.common(obj.Shape)
                        else:
                            raise ValueError(f"Unknown boolean operation: {operation}")
                    result_label = params.get("result_label", "Boolean")
                    out = doc.addObject("Part::Feature", result_label)
                    out.Shape = base
                    doc.recompute()
                    result["data"] = _object_info(out) | {"document": doc.Name, "operation": operation}

                elif method == "model_mirror":
                    doc = _get_doc(params)
                    name = params["object_name"]
                    src = doc.getObject(name)
                    if src is None:
                        raise ValueError(f"Object not found: {name}")
                    plane = params.get("plane", "yz")
                    if plane == "xy":
                        mirrored = src.Shape.mirror(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1))
                    elif plane == "xz":
                        mirrored = src.Shape.mirror(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0))
                    else:
                        mirrored = src.Shape.mirror(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(1, 0, 0))
                    out = doc.addObject("Part::Feature", params.get("result_label", f"{name}_Mirror"))
                    out.Shape = mirrored
                    doc.recompute()
                    result["data"] = _object_info(out) | {"document": doc.Name, "plane": plane}

                elif method == "model_extrude":
                    doc = _get_doc(params)
                    name = params["object_name"]
                    src = doc.getObject(name)
                    if src is None:
                        raise ValueError(f"Object not found: {name}")
                    vector = params.get("vector", [0, 0, 10])
                    extruded = src.Shape.extrude(FreeCAD.Vector(vector[0], vector[1], vector[2]))
                    out = doc.addObject("Part::Feature", params.get("result_label", f"{name}_Extrude"))
                    out.Shape = extruded
                    doc.recompute()
                    result["data"] = _object_info(out) | {"document": doc.Name}

                elif method == "model_fillet":
                    doc = _get_doc(params)
                    name = params["object_name"]
                    src = doc.getObject(name)
                    if src is None:
                        raise ValueError(f"Object not found: {name}")
                    radius = float(params.get("radius_mm", 2.0))
                    filleted = src.Shape.makeFillet(radius, src.Shape.Edges)
                    out = doc.addObject("Part::Feature", params.get("result_label", f"{name}_Fillet"))
                    out.Shape = filleted
                    doc.recompute()
                    result["data"] = _object_info(out) | {"document": doc.Name, "radius_mm": radius}

                elif method == "model_transform":
                    doc = _get_doc(params)
                    name = params["object_name"]
                    obj = doc.getObject(name)
                    if obj is None:
                        raise ValueError(f"Object not found: {name}")
                    pl = params.get("placement", {})
                    _apply_placement(obj, pl)
                    doc.recompute()
                    result["data"] = _object_info(obj) | {"document": doc.Name}

                elif method == "export_fcstd":
                    doc = _get_doc(params)
                    path = params["path"]
                    doc.saveAs(path)
                    result["data"] = {
                        "path": path,
                        "document": doc.Name,
                        "objects": len(doc.Objects),
                        "size_kb": round(os.path.getsize(path) / 1024, 1),
                    }

                elif method == "export_stl_objects":
                    doc = _get_doc(params)
                    names = params.get("object_names", [])
                    stl_path = params["path"]
                    objs = (
                        [doc.getObject(n) for n in names] if names else [o for o in doc.Objects if hasattr(o, "Shape")]
                    )
                    objs = [o for o in objs if o is not None]
                    if not objs:
                        raise ValueError("No exportable objects found")
                    Mesh.export(objs, stl_path)
                    result["data"] = {
                        "path": stl_path,
                        "objects": [o.Name for o in objs],
                        "size_kb": round(os.path.getsize(stl_path) / 1024, 1),
                    }

                elif method == "toy_car":
                    doc = _get_doc(params)
                    car = _build_toy_car(doc, params)
                    export_path = params.get("export_stl")
                    data = _object_info(car) | {"document": doc.Name, "wheels": 4}
                    if export_path:
                        Mesh.export([car], export_path)
                        data["export_stl"] = export_path
                        data["size_kb"] = round(os.path.getsize(export_path) / 1024, 1)
                    fcstd_path = params.get("export_fcstd")
                    if fcstd_path:
                        doc.saveAs(fcstd_path)
                        data["export_fcstd"] = fcstd_path
                    result["data"] = data

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
