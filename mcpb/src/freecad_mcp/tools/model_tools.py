"""FreeCAD modeling portmanteau — primitives, booleans, toy car preset."""

from __future__ import annotations

import logging
import os
from typing import Annotated, Any

from pydantic import Field

from freecad_mcp.model_ops import (
    script_boolean,
    script_create_primitive,
    script_toy_car,
)
from freecad_mcp.tools.bridge_tools import resolve_execution_mode
from freecad_mcp.toy_car_pipeline import (
    build_toy_car_via_blender,
    build_toy_car_via_marketplace,
    resolve_toy_car_auto,
)

logger = logging.getLogger("freecad-mcp.model")

_README_ONLY = {"readonly": True}


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

    @mcp.tool()
    async def freecad_model(
        operation: Annotated[
            str,
            Field(
                description=(
                    "Operation: create_primitive, fuse, cut, common, mirror, extrude, "
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
    ) -> dict[str, Any]:
        """Parametric FreeCAD modeling for agentic CAD workflows.

        Supports Hands-In (live GUI bridge) and Hands-Off (FreeCADCmd subprocess).
        The toy_car preset builds an elaborate sports car via Blender sculpt, marketplace
        STL download, or FreeCAD parametric solids (chassis, cabin, arches, torus wheels).

        ## Examples
        await freecad_model(operation="create_primitive", primitive_type="box", params={"width": 40, "height": 20, "depth": 60})
        await freecad_model(operation="toy_car", car_source="blender", output_name="sports_car.stl")
        await freecad_model(operation="toy_car", car_source="marketplace", marketplace_query="mini sports car")
        await freecad_model(operation="fuse", object_names=["Body", "Wheel0"], execution_mode="hands_in")
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
