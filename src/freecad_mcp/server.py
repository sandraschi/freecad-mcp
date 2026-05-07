"""
FastMCP 3.2 Unified Gateway for FreeCAD operations.

Architecture:
  MCP client/tool → FreeCADCmd subprocess (Python script piped to stdin) → parsed output → JSON response

The server does NOT import FreeCAD Python modules directly (too heavy, ~2 GB).
Instead it spawns FreeCADCmd.exe as a lightweight subprocess and pipes Python scripts to it.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastmcp import FastMCP
from pydantic import BaseModel, Field

logger = logging.getLogger("freecad-mcp")

# ── Config ───────────────────────────────────────────────────────────────────

FREECAD_PATH = os.environ.get(
    "FREECAD_PATH",
    os.path.join(os.environ.get("TEMP", ""), "freecad_extracted", "FreeCAD_1.1.1-Windows-x86_64-py311", "bin", "FreeCADCmd.exe"),
)
WORK_DIR = os.environ.get("FREECAD_MCP_WORK_DIR", os.path.join(os.environ.get("TEMP", ""), "freecad_mcp_work"))
os.makedirs(WORK_DIR, exist_ok=True)

UPLOAD_DIR = os.path.join(WORK_DIR, "uploads")
OUTPUT_DIR = os.path.join(WORK_DIR, "output")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Lifespan ─────────────────────────────────────────────────────────────────

_state: dict = {}


def _freecad_version() -> str:
    """Return FreeCAD version string from the executable."""
    try:
        r = subprocess.run([FREECAD_PATH, "--version"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or r.stderr.strip() or "unknown"
    except Exception as e:
        return f"error: {e}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: verify FreeCADCmd is reachable."""
    logger.info("FreeCAD MCP startup")
    if not os.path.isfile(FREECAD_PATH):
        logger.warning("FreeCADCmd not found at %s", FREECAD_PATH)
        _state["freecad_ok"] = False
        _state["freecad_version"] = None
    else:
        _state["freecad_ok"] = True
        _state["freecad_version"] = _freecad_version()
        logger.info("FreeCAD OK: %s", _state["freecad_version"])
    _state["work_dir"] = WORK_DIR
    yield


# ── FreeCAD Subprocess Runner ───────────────────────────────────────────────

_SCRIPTS_DIR = Path(__file__).parent / "scripts"
os.makedirs(_SCRIPTS_DIR, exist_ok=True)


async def _run_freecad(script: str, timeout: int = 120) -> tuple[str, str, int]:
    """Write script to temp file and run via FreeCADCmd."""
    fd, script_path = tempfile.mkstemp(suffix=".py", prefix="fc_", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("import sys\nsys.path = [p for p in sys.path if '_freecad_mcp' not in p]\n")
            f.write(script)
        proc = await asyncio.create_subprocess_exec(
            FREECAD_PATH, script_path,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
        return out, err, proc.returncode or 0
    except asyncio.TimeoutError:
        return "", "TIMEOUT", -1
    except FileNotFoundError:
        return "", f"FreeCADCmd not found at {FREECAD_PATH}", -2
    except Exception as e:
        return "", str(e), -3
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass


def _build_result(script_type: str, out: str, err: str, code: int, extra: dict | None = None) -> dict:
    """Build standardized response dict from FreeCAD output."""
    result = {"success": code == 0, "type": script_type, "exit_code": code}
    if extra:
        result.update(extra)

    # Try to extract JSON from the output (FreeCAD scripts print JSON on last line)
    lines = [l.strip() for l in out.split("\n") if l.strip()]
    for line in reversed(lines):
        try:
            data = json.loads(line)
            result["data"] = data
            break
        except (json.JSONDecodeError, ValueError):
            continue

    if err:
        result["stderr"] = err.strip()
    if out:
        result["stdout"] = out.strip()[:2000]
    return result


# ── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

mcp = FastMCP.from_fastapi(app, name="FreeCAD MCP")


# ── Pydantic models ──────────────────────────────────────────────────────────


class StepToStlRequest(BaseModel):
    """Convert a STEP file to STL."""
    file_name: str = Field(description="Filename in the uploads directory (must end with .step or .stp)")
    output_name: str = Field(default="output.stl", description="Desired output STL filename")


class CreateShapeRequest(BaseModel):
    """Create basic geometry and export to STL."""
    shape_type: str = Field(description="Shape type: box, cylinder, sphere, cone")
    params: dict = Field(default_factory=dict, description="Shape parameters: width/height/depth for box, radius/height for cylinder/sphere/cone")
    output_name: str = Field(default="shape.stl", description="Output filename")


class ToolRequest(BaseModel):
    """Execute an MCP tool via REST."""
    tool: str = Field(description="Tool name: step_to_stl, model_info, create_shape, freecad_status")
    arguments: dict = Field(default_factory=dict, description="Tool arguments as a dict")


# ── MCP Tools ───────────────────────────────────────────────────────────────


@mcp.tool(annotations={"readonly": True})
async def freecad_status() -> dict:
    """
    Check if FreeCADCmd is available and return version info.

    ## Return Format
    {"success": bool, "freecad_ok": bool, "version": str}
    """
    return {
        "success": _state.get("freecad_ok", False),
        "freecad_ok": _state.get("freecad_ok", False),
        "version": _state.get("freecad_version"),
        "work_dir": WORK_DIR,
    }


@mcp.tool()
async def step_to_stl(
    file_name: Annotated[str, Field(description="STEP filename in uploads directory (e.g. model.step)")],
    output_name: Annotated[str, Field(default="output.stl", description="Output STL filename")],
) -> dict:
    """
    Convert a STEP/STP file to STL mesh file.

    The STEP file must first be uploaded to /api/v1/upload. Then call this tool with the filename.
    Output STL is saved in the work directory and downloadable via GET /api/v1/download/{output_name}.

    ## Return Format
    {"success": bool, "output": str, "file_size_kb": float, "objects_count": int}
    """
    step_path = os.path.join(UPLOAD_DIR, file_name)
    stl_path = os.path.join(OUTPUT_DIR, output_name)

    if not os.path.isfile(step_path):
        return {"success": False, "error": f"File {file_name} not found in uploads. Upload first via POST /api/v1/upload."}

    script = (
        "import FreeCAD, Import, Mesh, json, os\n"
        f'doc = FreeCAD.newDocument("BOOMY")\n'
        f'Import.insert(r"{step_path}", doc.Name)\n'
        "doc.recompute()\n"
        "objs = [o for o in doc.Objects if hasattr(o, 'Shape') and o.Shape and o.Shape.Solids]\n"
        "if objs:\n"
        f"    Mesh.export(objs, r'{stl_path}')\n"
        f"    sz = os.path.getsize(r'{stl_path}')\n"
        '    print(json.dumps({"objects": len(objs), "size_kb": round(sz/1024, 1), "names": [o.Label for o in objs]}))\n'
        "else:\n"
        '    print(json.dumps({"objects": 0, "error": "No solids found in STEP file"}))\n'
        "FreeCAD.closeDocument(doc.Name)\n"
    )
    out, err, code = await _run_freecad(script, timeout=300)
    return _build_result("step_to_stl", out, err, code, extra={"output": output_name})


@mcp.tool(annotations={"readonly": True})
async def model_info(
    file_name: Annotated[str, Field(description="STEP or STL filename in uploads directory")],
) -> dict:
    """
    Read a CAD file and return model metadata: object count, solid count, volume, bounding box.

    ## Return Format
    {"success": bool, "objects": list, "total_solids": int}
    """
    path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.isfile(path):
        return {"success": False, "error": f"File {file_name} not found."}

    ext = Path(file_name).suffix.lower()
    if ext in (".step", ".stp"):
        script = f"""
import FreeCAD, json
doc = FreeCAD.openDocument(r"{path}")
doc.recompute()
infos = []
for o in doc.Objects:
    try:
        s = o.Shape
        if s and s.Solids:
            bb = s.BoundingBox
            infos.append({{
                "name": o.Label,
                "solids": len(s.Solids),
                "volume": round(s.Volume, 3) if s.Volume else 0,
                "bbox": {{"xmin": bb.XMin, "ymin": bb.YMin, "zmin": bb.ZMin, "xmax": bb.XMax, "ymax": bb.YMax, "zmax": bb.ZMax}}
            }})
    except: pass
print(json.dumps({{"objects": infos, "total": len(infos)}}))
FreeCAD.closeDocument(doc.Name)
"""
    elif ext == ".stl":
        script = f"""
import Mesh, json
mesh = Mesh.Mesh(r"{path}")
bb = mesh.BoundBox
print(json.dumps({{"type": "mesh", "vertices": len(mesh.Points), "facets": mesh.CountFacets, "bbox": {{"xmin": bb.XMin, "ymin": bb.YMin, "zmin": bb.ZMin, "xmax": bb.XMax, "ymax": bb.YMax, "zmax": bb.ZMax}}}}))
"""
    else:
        return {"success": False, "error": f"Unsupported format: {ext}. Use .step, .stp, or .stl."}

    out, err, code = await _run_freecad(script, timeout=120)
    return _build_result("model_info", out, err, code)


@mcp.tool()
async def create_shape(
    shape_type: Annotated[str, Field(description="Shape type: box, cylinder, sphere, cone")],
    params: Annotated[dict | None, Field(default=None, description="Parameters. For box: width, height, depth. For cylinder/sphere: radius. For cone: radius, height.")] = None,
    output_name: Annotated[str, Field(default="shape.stl", description="Output STL filename")] = "shape.stl",
) -> dict:
    """
    Create a basic geometric shape and export as STL.

    Supported shapes and parameters:
    - box: {"width": 10, "height": 10, "depth": 10}
    - cylinder: {"radius": 5, "height": 20}
    - sphere: {"radius": 10}
    - cone: {"radius": 5, "height": 15}

    ## Return Format
    {"success": bool, "output": str, "file_size_kb": float}
    """
    p = params or {}
    stl_path = os.path.join(OUTPUT_DIR, output_name)

    if shape_type == "box":
        w = p.get("width", 10)
        h = p.get("height", 10)
        d = p.get("depth", 10)
        script = f"import Part, Mesh; s = Part.makeBox({w}, {h}, {d}); m = Mesh.Mesh(s); m.write(r'{stl_path}')"
    elif shape_type == "cylinder":
        r = p.get("radius", 5)
        h = p.get("height", 20)
        script = f"import Part, Mesh; s = Part.makeCylinder({r}, {h}); m = Mesh.Mesh(s); m.write(r'{stl_path}')"
    elif shape_type == "sphere":
        r = p.get("radius", 10)
        script = f"import Part, Mesh; s = Part.makeSphere({r}); m = Mesh.Mesh(s); m.write(r'{stl_path}')"
    elif shape_type == "cone":
        r = p.get("radius", 5)
        h = p.get("height", 15)
        script = f"import Part, Mesh; s = Part.makeCone({r}, 0, {h}); m = Mesh.Mesh(s); m.write(r'{stl_path}')"
    else:
        return {"success": False, "error": f"Unknown shape: {shape_type}. Use: box, cylinder, sphere, cone."}

    script += f"\nimport os; print(os.path.getsize(r'{stl_path}'))"
    out, err, code = await _run_freecad(script, timeout=30)
    return _build_result("create_shape", out, err, code, extra={"output": output_name})


# ── REST Endpoints ────────────────────────────────────────────────────────────


@app.get("/api/v1/status")
async def get_status():
    """FreeCAD MCP server status."""
    return {
        "service": "freecad-mcp",
        "freecad_ok": _state.get("freecad_ok", False),
        "freecad_version": _state.get("freecad_version"),
        "work_dir": WORK_DIR,
    }


@app.post("/api/v1/upload")
async def upload_file(file: UploadFile):
    """Upload a STEP/STL file for processing."""
    if not file.filename:
        raise HTTPException(400, "No filename")
    ext = Path(file.filename).suffix.lower()
    if ext not in (".step", ".stp", ".stl"):
        raise HTTPException(400, f"Unsupported format: {ext}. Use .step, .stp, or .stl.")
    dest = os.path.join(UPLOAD_DIR, file.filename)
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    return {"success": True, "filename": file.filename, "size_bytes": len(content), "path": dest}


@app.get("/api/v1/download/{filename}")
async def download_file(filename: str):
    """Download a processed STL file."""
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(404, f"File {filename} not found.")
    return FileResponse(path, media_type="application/sla", filename=filename)


@app.get("/api/v1/files")
async def list_files():
    """List uploaded and output files."""
    uploads = [{"name": f, "size_kb": round(os.path.getsize(os.path.join(UPLOAD_DIR, f)) / 1024, 1)} for f in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR, f))]
    outputs = [{"name": f, "size_kb": round(os.path.getsize(os.path.join(OUTPUT_DIR, f)) / 1024, 1)} for f in os.listdir(OUTPUT_DIR) if os.path.isfile(os.path.join(OUTPUT_DIR, f))]
    return {"uploads": uploads, "outputs": outputs}


@app.post("/api/v1/control/tool")
async def execute_tool(req: ToolRequest):
    """Execute an MCP tool via REST (for webapp convenience)."""
    tool_name = req.tool
    args = req.arguments or {}

    if tool_name == "freecad_status":
        return await freecad_status()
    elif tool_name == "step_to_stl":
        fn = args.get("file_name", "")
        out = args.get("output_name", fn.replace(".step", ".stl").replace(".stp", ".stl"))
        return await step_to_stl(file_name=fn, output_name=out)
    elif tool_name == "model_info":
        fn = args.get("file_name", "")
        return await model_info(file_name=fn)
    elif tool_name == "create_shape":
        st = args.get("shape_type", "box")
        params = args.get("params", {})
        out = args.get("output_name", "shape.stl")
        return await create_shape(shape_type=st, params=params, output_name=out)
    else:
        raise HTTPException(400, f"Unknown tool: {tool_name}")


# ── Entry point ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="FreeCAD MCP Server")
    parser.add_argument("--mode", choices=["stdio", "http", "dual"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=10944)
    parser.add_argument("--freecad-path", help="Path to FreeCADCmd.exe")
    args = parser.parse_args()

    if args.freecad_path:
        os.environ["FREECAD_PATH"] = args.freecad_path

    if args.mode == "stdio":
        asyncio.run(_run_stdio())
    else:
        logger.info("Starting FreeCAD MCP on %s:%s", args.host, args.port)
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    import argparse
    main()
