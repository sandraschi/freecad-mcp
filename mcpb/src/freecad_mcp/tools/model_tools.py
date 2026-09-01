"""FreeCAD modeling portmanteau - primitives, booleans, toy car preset."""

from __future__ import annotations

import logging
import os
from typing import Annotated, Any

from pydantic import Field

from freecad_mcp.model_ops import (
    script_boolean,
    script_clash_check,
    script_create_assembly,
    script_create_fastener,
    script_create_gear,
    script_create_primitive,
    script_create_sketch,
    script_create_techdraw,
    script_generative_optimize,
    script_heuristic_fillet,
    script_inspect_assembly,
    script_inspect_geometry,
    script_toy_car,
)
from freecad_mcp.tools.bridge_tools import resolve_execution_mode
from freecad_mcp.toy_car_pipeline import (
    build_toy_car_via_blender,
    build_toy_car_via_marketplace,
    resolve_toy_car_auto,
)

logger = logging.getLogger("freecad-mcp.model")

_READ_ONLY = {"readonly": True}
_MUTATING = {"mutating": True}


def register_model_tools(
    mcp,
    state: dict,
    bridge_send,
    run_freecad,
    output_dir: str,
    build_result,
    marketplace_search=None,
    marketplace_download=None,
):
    """Register freecad_model portmanteau tool."""

    async def _run_script(script: str, timeout: int = 120) -> dict[str, Any]:
        out, err, code = await run_freecad(script, timeout=timeout)
        return build_result("freecad_model", out, err, code)

    @mcp.tool(annotations=_MUTATING)
    async def freecad_model(
        operation: Annotated[
            str,
            Field(
                description=(
                    "Operation: create_primitive, gear, fastener, inspect, clash_check, fuse, cut, common, mirror, extrude, "
                    "fillet, transform, export, toy_car"
                ),
            ),
        ] = "create_primitive",
        execution_mode: Annotated[str, Field(description="auto, hands_in, or hands_off.")] = "auto",
        primitive_type: Annotated[str, Field(description="box, cylinder, sphere, cone.")] = "box",
        params: Annotated[
            dict | None,
            Field(default=None, description="Primitive dimensions (mm)."),
        ] = None,
        label: Annotated[str, Field(description="Object label/name.")] = "Part",
        document: Annotated[str, Field(description="Existing document name (Hands-In).")] = "",
        document_label: Annotated[str, Field(description="New document label.")] = "MCP_Model",
        placement: Annotated[
            dict | None,
            Field(default=None, description="Placement dict: x,y,z,rx,ry,rz in mm/deg."),
        ] = None,
        object_name: Annotated[str, Field(description="Source object name for unary ops.")] = "",
        object_names: Annotated[
            list[str] | None,
            Field(default=None, description="Object names for boolean ops (Hands-In)."),
        ] = None,
        parts: Annotated[
            list[dict] | None,
            Field(default=None, description="Primitive specs for Hands-Off boolean ops."),
        ] = None,
        result_label: Annotated[str, Field(description="Output object label.")] = "Result",
        plane: Annotated[str, Field(description="Mirror plane: xy, xz, yz.")] = "yz",
        vector: Annotated[
            list[float] | None,
            Field(default=None, description="Extrude vector [x,y,z] mm."),
        ] = None,
        radius_mm: Annotated[float, Field(description="Fillet radius mm.", ge=0.1)] = 2.0,
        output_name: Annotated[str, Field(description="Output STL/FCStd filename.")] = "",
        export_format: Annotated[str, Field(description="stl or fcstd.")] = "stl",
        body_length_mm: Annotated[float, Field(description="Toy car body length.", ge=20)] = 120.0,
        body_width_mm: Annotated[float, Field(description="Toy car body width.", ge=20)] = 60.0,
        body_height_mm: Annotated[float, Field(description="Toy car body height.", ge=10)] = 35.0,
        wheel_radius_mm: Annotated[float, Field(description="Toy car wheel radius.", ge=3)] = 12.0,
        wheelbase_mm: Annotated[float, Field(description="Toy car wheelbase.", ge=10)] = 70.0,
        car_source: Annotated[
            str,
            Field(description="auto, blender, marketplace, or parametric (FreeCAD sculpt)."),
        ] = "auto",
        marketplace_query: Annotated[
            str,
            Field(description="Marketplace search when car_source is auto or marketplace."),
        ] = "toy car sports car stl",
        car_style: Annotated[str, Field(description="Car style hint (sports).")] = "sports",
        gear_type: Annotated[str, Field(description="Gear type: spur or helical.")] = "spur",
        num_teeth: Annotated[int, Field(description="Gear tooth count.", ge=4)] = 20,
        module: Annotated[float, Field(description="Gear module mm.", ge=0.5)] = 2.0,
        pressure_angle_deg: Annotated[float, Field(description="Gear pressure angle deg.")] = 20.0,
        face_width_mm: Annotated[float, Field(description="Gear face width mm.", ge=1.0)] = 10.0,
        bore_diameter_mm: Annotated[float, Field(description="Gear center bore diameter mm.", ge=0.0)] = 8.0,
        fastener_type: Annotated[str, Field(description="Fastener type: bolt, nut, washer.")] = "bolt",
        size: Annotated[str, Field(description="Fastener size: M3, M4, M5, M6, M8, M10, M12.")] = "M6",
        length_mm: Annotated[float, Field(description="Fastener length mm.", ge=1.0)] = 20.0,
        file_name: Annotated[str, Field(description="Input file name for inspect, clash_check, techdraw, etc.")] = "",
        file_name_2: Annotated[str, Field(description="Second file name for clash_check.")] = "",
        components: Annotated[
            list[dict] | None,
            Field(default=None, description="Component placement list for assembly operation."),
        ] = None,
        sketch_type: Annotated[
            str, Field(description="Sketch profile type: rectangle_with_hole, slot, flange.")
        ] = "rectangle_with_hole",
        width_mm: Annotated[float, Field(description="Sketch width mm.", ge=1.0)] = 60.0,
        height_mm: Annotated[float, Field(description="Sketch height mm.", ge=1.0)] = 40.0,
        hole_diameter_mm: Annotated[float, Field(description="Sketch hole diameter mm.", ge=0.0)] = 12.0,
        extrude_height_mm: Annotated[float, Field(description="Sketch extrude height mm.", ge=0.1)] = 15.0,
        target_reduction_pct: Annotated[
            float, Field(description="Generative weight reduction target %.", ge=5.0, le=75.0)
        ] = 35.0,
        wall_thickness_mm: Annotated[float, Field(description="Generative wall thickness mm.", ge=0.5)] = 3.0,
        edge_filter: Annotated[
            str, Field(description="Fillet edge filter: all_vertical, min_length.")
        ] = "all_vertical",
        scale: Annotated[float, Field(description="TechDraw blueprint view scale.", ge=0.01)] = 1.0,
    ) -> dict[str, Any]:
        """Parametric FreeCAD modeling for agentic CAD workflows.

        Supports Hands-In (live GUI bridge) and Hands-Off (FreeCADCmd subprocess).
        Operations: create_primitive, gear, fastener, inspect, clash_check, techdraw, sketch,
        assembly, generative, heuristic_fillet, inspect_assembly, fuse, cut, common, mirror, extrude, fillet, transform, export, toy_car.
        """
        op = operation.strip().lower()
        mode = resolve_execution_mode(state, execution_mode or None)
        bridge_params: dict[str, Any] = {"document_label": document_label}
        if document:
            bridge_params["document"] = document

        stl_name = output_name or {
            "toy_car": "toy_car.stl",
            "create_primitive": f"{label.lower()}.stl",
        }.get(op, "model_export.stl")
        if export_format == "fcstd" and not stl_name.lower().endswith(".fcstd"):
            stl_name = stl_name.rsplit(".", 1)[0] + ".FCStd"
        export_path = os.path.join(output_dir, stl_name)

        if op == "create_primitive":
            if mode == "hands_in" and state.get("bridge_mode") == "tcp":
                resp = await bridge_send(
                    "add_primitive",
                    {
                        **bridge_params,
                        "primitive_type": primitive_type,
                        "params": params or {},
                        "label": label,
                        "placement": placement or {},
                    },
                    timeout=60,
                )
                if resp.get("success") and output_name:
                    obj_name = (resp.get("data") or {}).get("name")
                    if obj_name:
                        stl_resp = await bridge_send(
                            "export_stl_objects",
                            {**bridge_params, "object_names": [obj_name], "path": export_path},
                            timeout=60,
                        )
                        if stl_resp.get("success"):
                            resp["data"] = {**(resp.get("data") or {}), **(stl_resp.get("data") or {})}
                            resp["output"] = stl_name
                return {**resp, "effective_mode": mode, "operation": op}

            script = script_create_primitive(
                primitive_type=primitive_type,
                params=params or {},
                label=label,
                document_label=document_label,
                placement=placement,
                export_stl=export_path if output_name else None,
            )
            result = await _run_script(script)
            if result.get("success"):
                result["output"] = stl_name if output_name else None
            result["effective_mode"] = mode
            result["operation"] = op
            return result

        if op == "gear":
            script = script_create_gear(
                gear_type=gear_type,
                num_teeth=num_teeth,
                module=module,
                pressure_angle_deg=pressure_angle_deg,
                face_width_mm=face_width_mm,
                bore_diameter_mm=bore_diameter_mm,
                label=label or "Gear",
                document_label=document_label or "GearDoc",
                export_stl=export_path if output_name else None,
            )
            res = await _run_script(script)
            if res.get("success") and output_name:
                res["output"] = stl_name
            res["effective_mode"] = mode
            res["operation"] = op
            return res

        if op == "fastener":
            script = script_create_fastener(
                fastener_type=fastener_type,
                size=size,
                length_mm=length_mm,
                label=label or "Fastener",
                document_label=document_label or "FastenerDoc",
                export_stl=export_path if output_name else None,
            )
            res = await _run_script(script)
            if res.get("success") and output_name:
                res["output"] = stl_name
            res["effective_mode"] = mode
            res["operation"] = op
            return res

        if op == "inspect":
            target = file_name or output_name
            script = script_inspect_geometry(file_name=target, document_label=document_label or "InspectDoc")
            res = await _run_script(script)
            res["effective_mode"] = mode
            res["operation"] = op
            return res

        if op == "clash_check":
            script = script_clash_check(
                file_name_1=file_name,
                file_name_2=file_name_2,
                document_label=document_label or "ClashDoc",
            )
            res = await _run_script(script)
            res["effective_mode"] = mode
            res["operation"] = op
            return res

        if op == "techdraw":
            svg_out = os.path.join(output_dir, output_name or "blueprint.svg")
            pdf_out = os.path.join(output_dir, output_name.rsplit(".", 1)[0] + ".pdf") if output_name else ""
            script = script_create_techdraw(
                file_name=file_name,
                output_svg=svg_out,
                output_pdf=pdf_out,
                scale=scale,
                document_label=document_label or "TechDrawDoc",
            )
            res = await _run_script(script)
            res["output"] = os.path.basename(svg_out)
            res["effective_mode"] = mode
            res["operation"] = op
            return res

        if op == "sketch":
            script = script_create_sketch(
                sketch_type=sketch_type,
                width_mm=width_mm,
                height_mm=height_mm,
                hole_diameter_mm=hole_diameter_mm,
                extrude_height_mm=extrude_height_mm,
                plane=plane or "XY",
                document_label=document_label or "SketchDoc",
                export_stl=export_path if output_name else None,
            )
            res = await _run_script(script)
            if res.get("success") and output_name:
                res["output"] = stl_name
            res["effective_mode"] = mode
            res["operation"] = op
            return res

        if op == "assembly":
            step_out = os.path.join(output_dir, output_name or "assembly.step")
            script = script_create_assembly(
                components=components or [],
                output_step=step_out,
                output_stl=export_path if output_name else "",
                document_label=document_label or "AssemblyDoc",
            )
            res = await _run_script(script)
            res["output"] = os.path.basename(step_out)
            res["effective_mode"] = mode
            res["operation"] = op
            return res

        if op == "generative":
            script = script_generative_optimize(
                file_name=file_name,
                target_reduction_pct=target_reduction_pct,
                wall_thickness_mm=wall_thickness_mm,
                output_stl=export_path if output_name else "",
                document_label=document_label or "OptimizedDoc",
            )
            res = await _run_script(script)
            if res.get("success") and output_name:
                res["output"] = stl_name
            res["effective_mode"] = mode
            res["operation"] = op
            return res

        if op == "heuristic_fillet":
            script = script_heuristic_fillet(
                file_name=file_name,
                radius_mm=radius_mm,
                edge_filter=edge_filter,
                output_stl=export_path if output_name else "",
                document_label=document_label or "FilletDoc",
            )
            res = await _run_script(script)
            if res.get("success") and output_name:
                res["output"] = stl_name
            res["effective_mode"] = mode
            res["operation"] = op
            return res

        if op == "inspect_assembly":
            script = script_inspect_assembly(file_path=file_name, document_label=document_label or "InspectAssemblyDoc")
            res = await _run_script(script)
            res["effective_mode"] = mode
            res["operation"] = op
            return res

        if op in {"fuse", "cut", "common"}:
            if mode == "hands_in" and state.get("bridge_mode") == "tcp":
                names = object_names or []
                resp = await bridge_send(
                    "model_boolean",
                    {
                        **bridge_params,
                        "operation": op,
                        "object_names": names,
                        "result_label": result_label,
                    },
                    timeout=120,
                )
                if resp.get("success") and output_name:
                    obj_name = (resp.get("data") or {}).get("name")
                    if obj_name:
                        stl_resp = await bridge_send(
                            "export_stl_objects",
                            {**bridge_params, "object_names": [obj_name], "path": export_path},
                            timeout=60,
                        )
                        if stl_resp.get("success"):
                            resp["data"] = {**(resp.get("data") or {}), **(stl_resp.get("data") or {})}
                            resp["output"] = stl_name
                return {**resp, "effective_mode": mode, "operation": op}

            if not parts or len(parts) < 2:
                return {
                    "success": False,
                    "error": "Hands-Off boolean ops require parts: list of {primitive_type, params, placement}",
                    "effective_mode": mode,
                }
            script = script_boolean(
                operation=op,
                parts=parts,
                result_label=result_label,
                document_label=document_label,
                export_stl=export_path if output_name else None,
            )
            result = await _run_script(script, timeout=180)
            if result.get("success") and output_name:
                result["output"] = stl_name
            result["effective_mode"] = mode
            result["operation"] = op
            return result

        if op == "mirror":
            if mode != "hands_in" or state.get("bridge_mode") != "tcp":
                return {"success": False, "error": "mirror requires Hands-In bridge mode", "effective_mode": mode}
            if not object_name:
                return {"success": False, "error": "object_name required for mirror"}
            resp = await bridge_send(
                "model_mirror",
                {**bridge_params, "object_name": object_name, "plane": plane, "result_label": result_label},
                timeout=60,
            )
            return {**resp, "effective_mode": mode, "operation": op}

        if op == "extrude":
            if mode != "hands_in" or state.get("bridge_mode") != "tcp":
                return {"success": False, "error": "extrude requires Hands-In bridge mode", "effective_mode": mode}
            if not object_name:
                return {"success": False, "error": "object_name required for extrude"}
            vec = vector or [0, 0, 10]
            resp = await bridge_send(
                "model_extrude",
                {
                    **bridge_params,
                    "object_name": object_name,
                    "vector": vec,
                    "result_label": result_label,
                },
                timeout=60,
            )
            return {**resp, "effective_mode": mode, "operation": op}

        if op == "fillet":
            if mode != "hands_in" or state.get("bridge_mode") != "tcp":
                return {"success": False, "error": "fillet requires Hands-In bridge mode", "effective_mode": mode}
            if not object_name:
                return {"success": False, "error": "object_name required for fillet"}
            resp = await bridge_send(
                "model_fillet",
                {
                    **bridge_params,
                    "object_name": object_name,
                    "radius_mm": radius_mm,
                    "result_label": result_label,
                },
                timeout=60,
            )
            return {**resp, "effective_mode": mode, "operation": op}

        if op == "transform":
            if mode != "hands_in" or state.get("bridge_mode") != "tcp":
                return {"success": False, "error": "transform requires Hands-In bridge mode", "effective_mode": mode}
            if not object_name:
                return {"success": False, "error": "object_name required for transform"}
            resp = await bridge_send(
                "model_transform",
                {**bridge_params, "object_name": object_name, "placement": placement or {}},
                timeout=60,
            )
            return {**resp, "effective_mode": mode, "operation": op}

        if op == "export":
            if mode != "hands_in" or state.get("bridge_mode") != "tcp":
                return {"success": False, "error": "export requires Hands-In bridge mode", "effective_mode": mode}
            if export_format == "fcstd":
                resp = await bridge_send("export_fcstd", {**bridge_params, "path": export_path}, timeout=60)
            else:
                names = object_names or []
                resp = await bridge_send(
                    "export_stl_objects",
                    {**bridge_params, "object_names": names, "path": export_path},
                    timeout=60,
                )
            if resp.get("success"):
                resp["output"] = stl_name
            return {**resp, "effective_mode": mode, "operation": op}

        if op == "toy_car":
            fcstd_path = os.path.join(output_dir, stl_name.replace(".stl", ".FCStd"))
            source = (car_source or "auto").strip().lower()
            if source not in ("auto", "blender", "marketplace", "parametric"):
                return {
                    "success": False,
                    "error": f"Unknown car_source: {car_source}",
                    "effective_mode": mode,
                    "operation": op,
                }

            if source == "auto":
                auto_result = await resolve_toy_car_auto(
                    export_path,
                    body_length_mm=body_length_mm,
                    marketplace_query=marketplace_query,
                    marketplace_search=marketplace_search,
                    marketplace_download=marketplace_download,
                )
                if auto_result.get("success"):
                    auto_result["output"] = stl_name
                    auto_result["effective_mode"] = mode
                    auto_result["operation"] = op
                    return auto_result

            elif source == "blender":
                blender_result = await build_toy_car_via_blender(
                    export_path,
                    body_length_mm=body_length_mm,
                )
                if blender_result.get("success"):
                    blender_result["output"] = stl_name
                    blender_result["effective_mode"] = mode
                    blender_result["operation"] = op
                    return blender_result
                blender_result["effective_mode"] = mode
                blender_result["operation"] = op
                return blender_result

            elif source == "marketplace":
                if not marketplace_search or not marketplace_download:
                    return {
                        "success": False,
                        "error": "marketplace tools unavailable",
                        "effective_mode": mode,
                        "operation": op,
                    }
                market_result = await build_toy_car_via_marketplace(
                    export_path,
                    query=marketplace_query,
                    marketplace_search=marketplace_search,
                    marketplace_download=marketplace_download,
                )
                if market_result.get("success"):
                    market_result["output"] = stl_name
                market_result["effective_mode"] = mode
                market_result["operation"] = op
                return market_result

            if mode == "hands_in" and state.get("bridge_mode") == "tcp":
                resp = await bridge_send(
                    "toy_car",
                    {
                        **bridge_params,
                        "body_length_mm": body_length_mm,
                        "body_width_mm": body_width_mm,
                        "body_height_mm": body_height_mm,
                        "wheel_radius_mm": wheel_radius_mm,
                        "wheelbase_mm": wheelbase_mm,
                        "export_stl": export_path,
                        "export_fcstd": fcstd_path,
                    },
                    timeout=180,
                )
                if resp.get("success"):
                    resp["output"] = stl_name
                    resp["car_source"] = "parametric"
                    resp["style"] = car_style
                return {**resp, "effective_mode": mode, "operation": op}

            script = script_toy_car(
                body_length_mm=body_length_mm,
                body_width_mm=body_width_mm,
                body_height_mm=body_height_mm,
                wheel_radius_mm=wheel_radius_mm,
                wheelbase_mm=wheelbase_mm,
                export_stl=export_path,
                document_label=document_label,
                style=car_style,
            )
            result = await _run_script(script, timeout=180)
            if result.get("success"):
                result["output"] = stl_name
                result["car_source"] = "parametric"
                result["style"] = car_style
            result["effective_mode"] = mode
            result["operation"] = op
            return result

        return {"success": False, "error": f"Unknown operation: {operation}", "effective_mode": mode}

    return {"freecad_model": freecad_model}
