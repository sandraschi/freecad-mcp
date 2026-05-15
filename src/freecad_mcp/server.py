"""
FastMCP 3.2 Unified Gateway for FreeCAD operations.

Architecture:
  MCP client/tool → FreeCADCmd subprocess (Python script piped to stdin) → parsed output → JSON response

The server does NOT import FreeCAD Python modules directly (too heavy, ~2 GB).
Instead it spawns FreeCADCmd.exe as a lightweight subprocess and pipes Python scripts to it.
"""

import asyncio
import collections
import json
import logging
import os
import subprocess
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastmcp import FastMCP
from prefab_ui.app import PrefabApp
from pydantic import BaseModel, Field

from freecad_mcp.tools import register_bim_tools, register_cfd_tools

logger = logging.getLogger("freecad-mcp")

# ── Config ───────────────────────────────────────────────────────────────────

FREECAD_PATH = os.environ.get("FREECAD_PATH") or next(
    (
        p
        for p in [
            r"D:\Dev\repos\FreeCAD\FreeCAD_1.1.1-Windows-x86_64-py311\bin\FreeCAD.exe",
            r"D:\Dev\repos\FreeCAD\FreeCAD_1.1.1-Windows-x86_64-py311\FreeCAD.exe",
            os.path.join(
                os.environ.get("TEMP", ""),
                "freecad_extracted",
                "FreeCAD_1.1.1-Windows-x86_64-py311",
                "bin",
                "FreeCAD.exe",
            ),
        ]
        if os.path.isfile(p)
    ),
    r"D:\Dev\repos\FreeCAD\FreeCAD_1.1.1-Windows-x86_64-py311\bin\FreeCAD.exe",
)
BRIDGE_PORT = int(os.environ.get("FC_BRIDGE_PORT", "10946"))
BRIDGE_SCRIPT = Path(__file__).parent / "fc_bridge.py"
WORK_DIR = os.environ.get("FREECAD_MCP_WORK_DIR", os.path.join(os.environ.get("TEMP", ""), "freecad_mcp_work"))
os.makedirs(WORK_DIR, exist_ok=True)

UPLOAD_DIR = os.path.join(WORK_DIR, "uploads")
OUTPUT_DIR = os.path.join(WORK_DIR, "output")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Lifespan ─────────────────────────────────────────────────────────────────

_state: dict = {}
_req_id = 0
_bridge_proc: subprocess.Popen | None = None
_bridge_reader: asyncio.StreamReader | None = None
_bridge_writer: asyncio.StreamWriter | None = None


async def _bridge_send(method: str, params: dict | None = None, timeout: float = 120) -> dict:
    """Send a JSON command to the FreeCAD bridge and return the response."""
    global _req_id
    _req_id += 1
    req = {"id": _req_id, "method": method, "params": params or {}}
    payload = json.dumps(req) + "\n"

    if _bridge_writer is None:
        return {"success": False, "error": "FreeCAD bridge not connected", "fallback": True}

    try:
        _bridge_writer.write(payload.encode("utf-8"))
        await _bridge_writer.drain()
        data = await asyncio.wait_for(_bridge_reader.readline(), timeout=timeout)
        return json.loads(data.decode("utf-8"))
    except TimeoutError:
        return {"success": False, "error": f"Bridge timeout ({timeout}s)", "fallback": True}
    except Exception as e:
        return {"success": False, "error": str(e), "fallback": True}


async def _bridge_connect():
    """Connect to the FreeCAD bridge TCP socket."""
    global _bridge_reader, _bridge_writer
    try:
        r, w = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", BRIDGE_PORT),
            timeout=10,
        )
        _bridge_reader, _bridge_writer = r, w
        # Verify with ping
        resp = await _bridge_send("ping", timeout=5)
        return resp.get("data") == "pong"
    except Exception as e:
        logger.warning("Bridge connect failed: %s", e)
        _bridge_reader = _bridge_writer = None
        return False


def _freecad_already_running() -> bool:
    """Check if any FreeCAD GUI process is already running."""
    import subprocess

    try:
        r = subprocess.run(
            ["tasklist.exe", "/FI", "IMAGENAME eq FreeCAD.exe", "/NH"], capture_output=True, text=True, timeout=5
        )
        return "FreeCAD.exe" in r.stdout
    except Exception:
        return False


def _start_freecad_bridge():
    """Launch FreeCAD GUI with the bridge script — only if no FreeCAD is already running."""
    global _bridge_proc
    if _freecad_already_running():
        logger.info("FreeCAD GUI already running — skipping bridge launch (will attempt to connect)")
        return False
    if not os.path.isfile(FREECAD_PATH):
        logger.warning("FreeCAD not found at %s", FREECAD_PATH)
        return False
    if not os.path.isfile(BRIDGE_SCRIPT):
        logger.warning("Bridge script not found at %s", BRIDGE_SCRIPT)
        return False
    try:
        env = os.environ.copy()
        env["FC_BRIDGE_PORT"] = str(BRIDGE_PORT)
        _bridge_proc = subprocess.Popen(
            [FREECAD_PATH, str(BRIDGE_SCRIPT)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("FreeCAD bridge launched (PID %s)", _bridge_proc.pid)
        return True
    except Exception as e:
        logger.error("Failed to start FreeCAD bridge: %s", e)
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: launch FreeCAD bridge (if not already running), connect, then serve."""
    logger.info("FreeCAD MCP startup")
    _state["freecad_ok"] = False
    _state["freecad_version"] = None
    _state["bridge_mode"] = "none"

    # Check if FreeCAD bridge is already running on its port
    bridge_already_running = False
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", BRIDGE_PORT), timeout=1)
        writer.close()
        await writer.wait_closed()
        bridge_already_running = True
        logger.info("FreeCAD bridge already running on port %s", BRIDGE_PORT)
    except (TimeoutError, ConnectionRefusedError, OSError):
        pass

    if not bridge_already_running:
        if not os.path.isfile(FREECAD_PATH):
            logger.warning("FreeCAD not found at %s", FREECAD_PATH)
        else:
            try:
                r = subprocess.run([FREECAD_PATH, "--version"], capture_output=True, text=True, timeout=10, check=False)
                _state["freecad_version"] = r.stdout.strip() or r.stderr.strip() or "unknown"
            except Exception as e:
                _state["freecad_version"] = f"error: {e}"

            # Start bridge
            if _start_freecad_bridge():
                for attempt in range(5):
                    await asyncio.sleep(2)
                    if await _bridge_connect():
                        _state["freecad_ok"] = True
                        _state["bridge_mode"] = "tcp"
                        logger.info("FreeCAD bridge connected")
                        break
                    logger.info("Waiting for bridge (attempt %d/5)...", attempt + 1)

            if not _state.get("freecad_ok"):
                _state["bridge_mode"] = "subprocess"
                logger.info("Falling back to subprocess mode (limited STEP support)")
    else:
        # Bridge already running, just connect
        _state["freecad_version"] = "bridge_running"
        for attempt in range(5):
            await asyncio.sleep(1)
            if await _bridge_connect():
                _state["freecad_ok"] = True
                _state["bridge_mode"] = "tcp"
                logger.info("Connected to existing FreeCAD bridge")
                break
        if not _state.get("freecad_ok"):
            _state["bridge_mode"] = "tcp"  # still tcp, just not connected yet
            logger.warning("Existing bridge found but could not connect")

    _state["work_dir"] = WORK_DIR
    yield

    # Shutdown
    if _bridge_writer and not bridge_already_running:
        try:
            _bridge_writer.close()
            await _bridge_writer.wait_closed()
        except Exception:
            pass


# ── Subprocess Fallback ───────────────────────────────────────────────────────


async def _run_freecad(script: str, timeout: int = 120) -> tuple[str, str, int]:
    """Run a Python script via FreeCADCmd subprocess (fallback when bridge unavailable)."""
    fd, sp = tempfile.mkstemp(suffix=".py", prefix="fc_", text=True)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(script)
        proc = await asyncio.create_subprocess_exec(
            FREECAD_PATH.replace("FreeCAD.exe", "FreeCADCmd.exe"),
            sp,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace"), proc.returncode or 0
    except TimeoutError:
        return "", "TIMEOUT", -1
    except FileNotFoundError:
        return "", "FreeCADCmd not found", -2
    except Exception as e:
        return "", str(e), -3
    finally:
        try:
            os.unlink(sp)
        except OSError:
            pass


# ── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

mcp = FastMCP.from_fastapi(app, name="FreeCAD MCP")


# ── Response builder ─────────────────────────────────────────────────────────


def _build_result(script_type: str, out: str, err: str, code: int, extra: dict | None = None) -> dict:
    """Parse FreeCAD subprocess output into a standard result dict."""
    result = {"success": code == 0, "type": script_type, "exit_code": code}
    if extra:
        result.update(extra)
    lines = [ln.strip() for ln in out.split("\n") if ln.strip()]
    for line in reversed(lines):
        try:
            result["data"] = json.loads(line)
            break
        except (json.JSONDecodeError, ValueError):
            continue
    if err:
        result["stderr"] = err.strip()
    if out:
        result["stdout"] = out.strip()[:2000]
    return result


# Register BIM tools (bound to mcp via decorator closures) — must be after _build_result
_bim_tools = register_bim_tools(
    mcp=mcp,
    state=_state,
    bridge_send=_bridge_send,
    run_freecad=_run_freecad,
    work_dir=WORK_DIR,
    output_dir=OUTPUT_DIR,
    upload_dir=UPLOAD_DIR,
    build_result=_build_result,
)

# Register CFD tools (10 tools for FreeCAD → OpenFOAM pipeline)
_cfd_tools = register_cfd_tools(
    mcp=mcp,
    state=_state,
    bridge_send=_bridge_send,
    run_freecad=_run_freecad,
    work_dir=WORK_DIR,
    output_dir=OUTPUT_DIR,
    upload_dir=UPLOAD_DIR,
    build_result=_build_result,
)


# ── Pydantic models ──────────────────────────────────────────────────────────


class StepToStlRequest(BaseModel):
    """Convert a STEP file to STL."""

    file_name: str = Field(description="Filename in the uploads directory (must end with .step or .stp)")
    output_name: str = Field(default="output.stl", description="Desired output STL filename")


class CreateShapeRequest(BaseModel):
    """Create basic geometry and export to STL."""

    shape_type: str = Field(description="Shape type: box, cylinder, sphere, cone")
    params: dict = Field(
        default_factory=dict,
        description="Shape parameters: width/height/depth for box, radius/height for cylinder/sphere/cone",
    )
    output_name: str = Field(default="shape.stl", description="Output filename")


class ToolRequest(BaseModel):
    """Execute an MCP tool via REST."""

    tool: str = Field(description="Tool name: step_to_stl, model_info, create_shape, freecad_status")
    arguments: dict = Field(default_factory=dict, description="Tool arguments as a dict")


# ── MCP Tools ───────────────────────────────────────────────────────────────

_README_ONLY = {"readonly": True}


@mcp.tool(annotations=_README_ONLY)
async def freecad_status() -> dict:
    """
    Check if the FreeCAD executable is reachable and report version info.

    Use this first to confirm FreeCADCmd.exe is available before calling
    any conversion or geometry tools.

    ## Return Format
    {"success": bool, "freecad_ok": bool, "version": str, "work_dir": str}

    ## Examples
    await freecad_status()
    """
    return {
        "success": _state.get("freecad_ok", False),
        "freecad_ok": _state.get("freecad_ok", False),
        "version": _state.get("freecad_version"),
        "work_dir": WORK_DIR,
    }


@mcp.tool()
async def step_to_stl(
    file_name: Annotated[str, Field(description="STEP filename in the uploads directory, e.g. model.step")],
    output_name: Annotated[str, Field(default="output.stl", description="Desired output STL filename.")] = "output.stl",
) -> dict:
    """
    Convert a STEP or STP assembly file to an STL mesh.

    Upload the file first via POST /api/v1/upload, then call this tool with the filename.
    The resulting STL can be downloaded from GET /api/v1/download/{output_name}.

    ## Return Format
    {"success": bool, "output": str, "data": {"objects": int, "size_kb": float}}

    ## Examples
    await step_to_stl(file_name="raspbot_v2_step.STEP", output_name="boomy.stl")
    """
    step_path = os.path.join(UPLOAD_DIR, file_name)
    stl_path = os.path.join(OUTPUT_DIR, output_name)

    if not os.path.isfile(step_path):
        return {
            "success": False,
            "error": f"File {file_name} not found in uploads. Upload first via POST /api/v1/upload.",
        }

    if _state.get("bridge_mode") == "tcp":
        resp = await _bridge_send("open", {"path": step_path, "name": "STEP_Import"}, timeout=300)
        if not resp.get("success"):
            return {"success": False, "error": resp.get("error", "STEP import failed"), "stderr": resp.get("error")}
        resp2 = await _bridge_send("export_stl", {"path": stl_path}, timeout=300)
        if not resp2.get("success"):
            return {"success": False, "error": resp2.get("error", "STL export failed")}
        return {"success": True, "output": output_name, "data": resp2.get("data")}

    # Fallback to subprocess
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


@mcp.tool(annotations=_README_ONLY)
async def model_info(
    file_name: Annotated[str, Field(description="STEP, STP, or STL filename in the uploads directory.")],
) -> dict:
    """
    Read a CAD file and return metadata: object count, solid count, bounding box, volume.

    Supports STEP assemblies (object list) and STL meshes (vertex/facet count).

    ## Return Format
    {"success": bool, "data": {"objects": [...], "total": int} | {"type": str, "vertices": int, "facets": int}}

    ## Examples
    await model_info(file_name="raspbot_v2_step.STEP")
    await model_info(file_name="boomy.stl")
    """
    path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.isfile(path):
        return {"success": False, "error": f"File {file_name} not found."}

    if _state.get("bridge_mode") == "tcp":
        resp = await _bridge_send("model_info", {"path": path}, timeout=120)
        if resp.get("success"):
            return {"success": True, "type": "model_info", "data": resp.get("data")}
        # fall through to subprocess on failure
        logger.warning("Bridge model_info failed, trying subprocess: %s", resp.get("error"))

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
    shape_type: Annotated[str, Field(description="Shape type: box, cylinder, sphere, or cone.")],
    params: Annotated[
        dict | None,
        Field(
            default=None,
            description="Parameters dict: width/height/depth for box, radius/height for cylinder/sphere/cone.",
        ),
    ] = None,
    output_name: Annotated[str, Field(default="shape.stl", description="Output STL filename.")] = "shape.stl",
) -> dict:
    """
    Create a basic geometric primitive and export it as an STL mesh.

    Supported shapes:
    - box: {"width": 10, "height": 10, "depth": 10}
    - cylinder: {"radius": 5, "height": 20}
    - sphere: {"radius": 10}
    - cone: {"radius": 5, "height": 15}

    All dimensions are in millimetres. The output STL is saved to the outputs directory
    and is downloadable via GET /api/v1/download/{output_name}.

    ## Return Format
    {"success": bool, "output": str, "data": {"size_kb": float}}

    ## Examples
    await create_shape(shape_type="box", params={"width": 20, "height": 10, "depth": 5})
    await create_shape(shape_type="cylinder", params={"radius": 5, "height": 20}, output_name="tube.stl")
    """
    p = params or {}
    stl_path = os.path.join(OUTPUT_DIR, output_name)

    if _state.get("bridge_mode") == "tcp":
        resp = await _bridge_send("create_shape", {"shape_type": shape_type, "params": p, "path": stl_path}, timeout=30)
        if resp.get("success"):
            return {"success": True, "output": output_name, "data": resp.get("data")}
        logger.warning("Bridge create_shape failed, trying subprocess: %s", resp.get("error"))

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


# ── PrusaSlicer Tools ────────────────────────────────────────────────────────

_SLICER_PATH = os.environ.get(
    "PRUSA_SLICER_PATH",
    r"D:\Dev\repos\PrusaSlicer\PrusaSlicer-2.8.1+win64-202409181359\prusa-slicer.exe",
)
_SLICER_OUTPUT_DIR = os.path.join(WORK_DIR, "gcode")
os.makedirs(_SLICER_OUTPUT_DIR, exist_ok=True)


def _slicer_available() -> bool:
    return os.path.exists(_SLICER_PATH)


@mcp.tool(annotations=_README_ONLY)
async def slicer_status() -> dict:
    """
    Check if PrusaSlicer is available and report version.

    ## Return Format
    {"success": bool, "available": bool, "version": str, "profiles_dir": str}

    ## Examples
    await slicer_status()
    """
    if not _slicer_available():
        return {"success": False, "available": False, "version": None, "profiles_dir": None}

    try:
        r = subprocess.run([_SLICER_PATH, "--help"], capture_output=True, text=True, timeout=10)
        first = r.stdout.strip().split("\n")[0] if r.stdout else "unknown"
        return {
            "success": True,
            "available": True,
            "version": first,
            "profiles_dir": str(Path(_SLICER_PATH).parent / "profiles"),
        }
    except Exception as e:
        return {"success": False, "available": False, "version": str(e), "profiles_dir": None}


@mcp.tool()
async def slice_stl(
    file_name: Annotated[str, Field(description="STL filename in the uploads directory.")],
    printer_profile: Annotated[
        str, Field(default="", description="Printer profile name. Empty = default Prusa MK4.")
    ] = "",
    filament_profile: Annotated[str, Field(default="", description="Filament profile name. Empty = default PLA.")] = "",
    quality: Annotated[
        str, Field(default="0.20mm SPEED", description="Layer height / quality preset.")
    ] = "0.20mm SPEED",
    output_name: Annotated[
        str | None, Field(default=None, description="Output G-code filename. Auto-generated if omitted.")
    ] = None,
) -> dict:
    """
    Slice an STL file using PrusaSlicer and produce G-code for 3D printing.

    Upload the STL first via POST /api/v1/upload, then call this tool.
    The resulting .gcode file can be downloaded from GET /api/v1/download/{output_name}.

    ## Return Format
    {"success": bool, "output": str, "data": {"size_kb": float, "path": str, "printer": str, "filament": str}}

    ## Examples
    await slice_stl(file_name="bracket.stl", printer_profile="Prusa MK4")
    await slice_stl(file_name="bracket.stl")
    """
    if not _slicer_available():
        return {"success": False, "error": "PrusaSlicer not found. Set PRUSA_SLICER_PATH."}

    stl_path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.exists(stl_path):
        return {"success": False, "error": f"File not found: {file_name}"}

    out_name = output_name or file_name.replace(".stl", ".gcode")
    gcode_path = os.path.join(_SLICER_OUTPUT_DIR, out_name)

    cmd = [_SLICER_PATH, "--slice", stl_path, "--output", gcode_path, "--center", "0,0"]
    if printer_profile:
        cmd += ["--print-settings", printer_profile]
    if filament_profile:
        cmd += ["--filament-settings", filament_profile]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return {"success": False, "error": r.stderr.strip() or r.stdout.strip()}
        size_kb = round(os.path.getsize(gcode_path) / 1024, 1)
        return {
            "success": True,
            "output": out_name,
            "data": {
                "size_kb": size_kb,
                "path": gcode_path,
                "printer": printer_profile or "default",
                "filament": filament_profile or "default",
            },
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Slicing timed out after 300s"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def freecad_gui(
    file_name: Annotated[
        str | None, Field(default=None, description="Optional file to open (STL, STEP, FCStd).")
    ] = None,
) -> dict:
    """
    Launch the FreeCAD GUI application, optionally opening a file.

    The GUI runs as a separate process. This tool returns immediately after launch.

    ## Return Format
    {"success": bool, "message": str, "process_pid": int}

    ## Examples
    await freecad_gui()
    await freecad_gui(file_name="tfmini_bracket_final.stl")
    """
    gui_path = FREECAD_PATH.replace("FreeCADCmd.exe", "FreeCAD.exe")
    if not os.path.isfile(gui_path):
        gui_path = os.path.join(os.path.dirname(FREECAD_PATH), "FreeCAD.exe")
    if not os.path.isfile(gui_path):
        return {"success": False, "error": "FreeCAD GUI not found (FreeCAD.exe)"}

    args = [gui_path]
    if file_name:
        fpath = os.path.join(UPLOAD_DIR, file_name)
        if os.path.isfile(fpath):
            args.append(fpath)
        elif os.path.isfile(file_name):
            args.append(file_name)

    try:
        proc = subprocess.Popen(args, shell=False)
        return {"success": True, "message": f"FreeCAD GUI launched (PID {proc.pid})", "process_pid": proc.pid}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
    if ext not in (".step", ".stp", ".stl", ".ifc", ".fcstd"):
        raise HTTPException(400, f"Unsupported format: {ext}. Use .step, .stp, .stl, .ifc, or .fcstd.")
    dest = os.path.join(UPLOAD_DIR, file.filename)
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    return {"success": True, "filename": file.filename, "size_bytes": len(content), "path": dest}


@app.get("/api/v1/download/{filename}")
async def download_file(filename: str):
    """Download a processed STL, G-code, IFC, or FCStd file."""
    for d in (OUTPUT_DIR, _SLICER_OUTPUT_DIR):
        path = os.path.join(d, filename)
        if os.path.isfile(path):
            if filename.endswith(".gcode"):
                media = "text/x.gcode"
            elif filename.endswith(".ifc"):
                media = "application/x-step"
            elif filename.endswith(".fcstd"):
                media = "application/octet-stream"
            else:
                media = "application/sla"
            return FileResponse(path, media_type=media, filename=filename)
    raise HTTPException(404, f"File {filename} not found.")


@app.get("/api/v1/files")
async def list_files():
    """List uploaded and output files including G-code, IFC, and FCStd."""
    uploads = [
        {"name": f, "size_kb": round(os.path.getsize(os.path.join(UPLOAD_DIR, f)) / 1024, 1)}
        for f in os.listdir(UPLOAD_DIR)
        if os.path.isfile(os.path.join(UPLOAD_DIR, f))
    ]
    outputs = [
        {"name": f, "size_kb": round(os.path.getsize(os.path.join(OUTPUT_DIR, f)) / 1024, 1)}
        for f in os.listdir(OUTPUT_DIR)
        if os.path.isfile(os.path.join(OUTPUT_DIR, f))
    ]
    gcodes = [
        {"name": f, "size_kb": round(os.path.getsize(os.path.join(_SLICER_OUTPUT_DIR, f)) / 1024, 1)}
        for f in os.listdir(_SLICER_OUTPUT_DIR)
        if os.path.isfile(os.path.join(_SLICER_OUTPUT_DIR, f))
    ]
    return {"uploads": uploads, "outputs": outputs, "gcodes": gcodes}


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
    # BIM tool dispatch (registered via register_bim_tools closures)
    elif tool_name in _bim_tools:
        return await _bim_tools[tool_name](**args)
    # CFD tool dispatch (registered via register_cfd_tools closures)
    elif tool_name in _cfd_tools:
        return await _cfd_tools[tool_name](**args)
    else:
        raise HTTPException(400, f"Unknown tool: {tool_name}")


# ── Log Ring Buffer ──────────────────────────────────────────────────────────


LOG_RING = collections.deque(maxlen=2000)


class LogHandler(logging.Handler):
    def emit(self, record):
        LOG_RING.append(self.format(record))


# Add handler to the server logger
_log_handler = LogHandler()
_log_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(_log_handler)


@app.get("/api/v1/logs/stream")
async def stream_logs():
    """SSE log stream."""

    async def gen():
        for line in list(LOG_RING):
            yield f"data: {line}\n\n"
        idx = len(LOG_RING)
        while True:
            if idx < len(LOG_RING):
                yield f"data: {LOG_RING[idx]}\n\n"
                idx += 1
            await asyncio.sleep(0.1)

    return StreamingResponse(gen(), media_type="text/event-stream")


# ── Marketplace Proxy ─────────────────────────────────────────────────────────


class MarketplaceSearchRequest(BaseModel):
    source: str = Field(description="Marketplace: printables, grabcad, thingiverse")
    query: str = Field(description="Search query")
    limit: int = Field(default=20, description="Max results")
    page: int = Field(default=1, description="Page number")


class MarketplaceDownloadRequest(BaseModel):
    source: str = Field(description="Marketplace source")
    model_id: str = Field(description="Model ID to download")
    file_url: str = Field(description="Direct download URL")
    filename: str = Field(description="Desired filename")


_PRINTABLES_GQL = "https://api.printables.com/graphql/"
_GRABCAD_API = "https://grabcad.com/api/v1"
_THINGIVERSE_API = "https://api.thingiverse.com"
_HEADERS = {
    "User-Agent": "freecad-mcp/0.3.0 (MCP server; +https://github.com/sandraschi/freecad-mcp)",
    "Accept": "application/json",
}

_MARKETPLACE_CATEGORIES = {
    "printables": [
        {"id": "", "label": "All"},
        {"id": "3D-Printing", "label": "3D Printing"},
        {"id": "Art", "label": "Art"},
        {"id": "Automotive", "label": "Automotive"},
        {"id": "Electronics", "label": "Electronics"},
        {"id": "Fashion", "label": "Fashion"},
        {"id": "Gadgets", "label": "Gadgets"},
        {"id": "Games", "label": "Games"},
        {"id": "Household", "label": "Household"},
        {"id": "Kitchen", "label": "Kitchen & Dining"},
        {"id": "Organization", "label": "Organization"},
        {"id": "Outdoor", "label": "Outdoor & Garden"},
        {"id": "Pets", "label": "Pets"},
        {"id": "Sports", "label": "Sports"},
        {"id": "Tools", "label": "Tools"},
        {"id": "Toys", "label": "Toys"},
    ],
    "thingiverse": [
        {"id": "", "label": "All"},
        {"id": "3D-Printing", "label": "3D Printing"},
        {"id": "Art", "label": "Art"},
        {"id": "DIY", "label": "DIY"},
        {"id": "Electronics", "label": "Electronics"},
        {"id": "Gadgets", "label": "Gadgets"},
        {"id": "Games", "label": "Games"},
        {"id": "Household", "label": "Household"},
        {"id": "Learning", "label": "Learning"},
        {"id": "Models", "label": "Models"},
        {"id": "Music", "label": "Music"},
        {"id": "Pets", "label": "Pets"},
        {"id": "Robotics", "label": "Robotics"},
        {"id": "Sports", "label": "Sports"},
        {"id": "Tools", "label": "Tools"},
        {"id": "Toys", "label": "Toys & Games"},
        {"id": "Wearables", "label": "Wearables"},
    ],
    "grabcad": [
        {"id": "", "label": "All"},
        {"id": "3d-printing", "label": "3D Printing"},
        {"id": "aerospace", "label": "Aerospace"},
        {"id": "automotive", "label": "Automotive"},
        {"id": "consumer-products", "label": "Consumer Products"},
        {"id": "electronics", "label": "Electronics"},
        {"id": "furniture", "label": "Furniture"},
        {"id": "industrial-design", "label": "Industrial Design"},
        {"id": "machine-design", "label": "Machine Design"},
        {"id": "marine", "label": "Marine"},
        {"id": "mechanical", "label": "Mechanical"},
        {"id": "medical", "label": "Medical"},
        {"id": "robotics", "label": "Robotics"},
        {"id": "sports", "label": "Sports"},
        {"id": "tools", "label": "Tools"},
        {"id": "toys", "label": "Toys"},
    ],
}


def _safe_json(response: httpx.Response) -> dict | list | None:
    """Parse JSON safely — return None on empty or non-JSON."""
    if response.status_code >= 400:
        logger.warning("Marketplace API error %s: %s", response.status_code, response.text[:500])
        return None
    try:
        return response.json()
    except Exception as e:
        logger.warning("Marketplace API non-JSON response: %s — %s", response.text[:200], e)
        return None


_PRINTABLES_SEARCH_QUERY = """query Search($query: String!, $limit: Int!, $offset: Int!) {
  searchPrints2(query: $query, limit: $limit, offset: $offset) {
    totalCount
    items {
      id
      name
      slug
      summary
      downloadCount
      likesCount
      user {
        publicUsername
        handle
      }
      images {
        filePath
      }
    }
  }
}"""


async def _marketplace_search(source: str, query: str, category: str = "", limit: int = 20, page: int = 1) -> dict:
    """Shared marketplace search logic — used by both REST and MCP tools."""
    offset = (page - 1) * limit

    if source not in ("printables", "grabcad", "thingiverse"):
        return {"success": False, "error": f"Unknown source: {source}"}

    try:
        if source == "printables":
            q = f"{query} {category}" if category else query
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                r = await client.post(
                    _PRINTABLES_GQL,
                    headers=_HEADERS,
                    json={
                        "query": _PRINTABLES_SEARCH_QUERY,
                        "variables": {"query": q, "limit": limit, "offset": offset},
                    },
                )
                data = _safe_json(r)
                if not data:
                    return {
                        "success": False,
                        "source": source,
                        "results": [],
                        "error": f"Empty response from Printables (HTTP {r.status_code})",
                    }
                items = data.get("data", {}).get("searchPrints2", {}).get("items", []) or []
                total = data.get("data", {}).get("searchPrints2", {}).get("totalCount", 0)
                results = []
                for item in items:
                    img = item.get("images", [{}])[0].get("filePath", "") if item.get("images") else ""
                    item_id = str(item.get("id", ""))
                    results.append(
                        {
                            "id": item_id,
                            "title": item.get("name", ""),
                            "summary": (item.get("summary") or "")[:200],
                            "author": item.get("user", {}).get(
                                "publicUsername", item.get("user", {}).get("handle", "")
                            ),
                            "downloads": item.get("downloadCount", 0),
                            "likes": item.get("likesCount", 0),
                            "image_url": f"https://media.printables.com/{img}" if img else "",
                            "model_url": f"https://www.printables.com/model/{item_id}",
                            "download_url": "",
                            "source": "printables",
                        }
                    )
                return {"success": True, "source": source, "results": results, "total": total}

        elif source == "grabcad":
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                params = {"query": query, "per_page": limit, "page": page}
                if category:
                    params["category"] = category
                r = await client.get(f"{_GRABCAD_API}/search", headers=_HEADERS, params=params)
                data = _safe_json(r)
                if not data:
                    return {
                        "success": False,
                        "source": source,
                        "results": [],
                        "error": f"Empty response from GrabCAD (HTTP {r.status_code})",
                    }
                items = data.get("items", []) or data.get("models", []) or []
                results = []
                for item in items:
                    results.append(
                        {
                            "id": str(item.get("id", "")),
                            "title": item.get("name", ""),
                            "summary": (item.get("description") or "")[:200],
                            "author": item.get("author", {}).get("name", "")
                            if isinstance(item.get("author"), dict)
                            else "",
                            "downloads": item.get("download_count", 0),
                            "likes": item.get("like_count", 0),
                            "image_url": item.get("preview_image", ""),
                            "model_url": item.get("url", f"https://grabcad.com/library/{item.get('slug', '')}"),
                            "download_url": "",
                            "source": "grabcad",
                        }
                    )
                total = data.get("total_count", data.get("total", len(results)))
                return {"success": True, "source": source, "results": results, "total": total}

        elif source == "thingiverse":
            token = _marketplace_settings.get("thingiverse_api_key", "") or os.environ.get("THINGIVERSE_API_KEY", "")
            headers = dict(_HEADERS)
            if token:
                headers["Authorization"] = f"Bearer {token}"
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                params = {"type": "things", "page": page, "per_page": limit}
                if category:
                    params["category"] = category
                r = await client.get(f"https://api.thingiverse.com/search/{query}", headers=headers, params=params)
                data = _safe_json(r)
                if not data:
                    return {
                        "success": False,
                        "source": source,
                        "results": [],
                        "error": f"Empty response from Thingiverse (HTTP {r.status_code})",
                    }
                hits = data.get("hits", [])
                results = []
                for item in hits:
                    results.append(
                        {
                            "id": str(item.get("id", "")),
                            "title": item.get("name", ""),
                            "summary": (item.get("description") or "")[:200],
                            "author": item.get("creator", {}).get("name", "")
                            if isinstance(item.get("creator"), dict)
                            else "",
                            "downloads": item.get("download_count", 0),
                            "likes": item.get("like_count", 0),
                            "image_url": item.get("thumbnail", ""),
                            "model_url": item.get("public_url", item.get("url", "")),
                            "download_url": f"https://www.thingiverse.com/thing:{item.get('id', '')}/zip"
                            if item.get("id")
                            else "",
                            "source": "thingiverse",
                        }
                    )
                total = data.get("total", 0)
                return {"success": True, "source": source, "results": results, "total": total}

    except Exception as e:
        logger.error("Marketplace search error (%s): %s", source, e)
        return {"success": False, "source": source, "results": [], "error": str(e)}


async def _marketplace_download(source: str, model_id: str, file_url: str, filename: str) -> dict:
    """Shared marketplace download logic — used by both REST and MCP tools."""
    ext = Path(filename).suffix.lower()
    if ext not in (".step", ".stp", ".stl", ".zip"):
        return {"success": False, "error": f"Unsupported format: {ext}. Use .step, .stp, .stl, or .zip."}
    dest = os.path.join(UPLOAD_DIR, filename)
    try:
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            r = await client.get(file_url, headers=_HEADERS)
            r.raise_for_status()
            content = r.content
            with open(dest, "wb") as f:
                f.write(content)
        extracted = []
        if filename.endswith(".zip"):
            import zipfile

            with zipfile.ZipFile(dest) as zf:
                for name in zf.namelist():
                    if name.lower().endswith((".stl", ".step", ".stp")):
                        out_path = os.path.join(UPLOAD_DIR, Path(name).name)
                        with zf.open(name) as src, open(out_path, "wb") as dst:
                            dst.write(src.read())
                        extracted.append({"filename": Path(name).name, "size_bytes": os.path.getsize(out_path)})
        return {
            "success": True,
            "filename": filename,
            "size_bytes": len(content),
            "path": dest,
            "extracted": extracted or None,
        }
    except Exception as e:
        logger.error("Marketplace download error: %s", e)
        return {"success": False, "error": f"Download failed: {e}"}


@app.get("/api/v1/marketplace/categories")
async def categories_endpoint(source: str = ""):
    """List categories for a marketplace source."""
    if source:
        if source not in _MARKETPLACE_CATEGORIES:
            raise HTTPException(400, f"Unknown source: {source}")
        return {"success": True, "source": source, "categories": _MARKETPLACE_CATEGORIES[source]}
    return {"success": True, "categories": _MARKETPLACE_CATEGORIES}


@app.get("/api/v1/marketplace/search")
async def search_endpoint(source: str, query: str, category: str = "", limit: int = 20, page: int = 1):
    """Search a marketplace for CAD models."""
    if source not in ("printables", "grabcad", "thingiverse"):
        raise HTTPException(400, f"Unknown source: {source}. Use 'printables', 'grabcad', or 'thingiverse'.")
    return await _marketplace_search(source, query, category, limit, page)


@app.post("/api/v1/marketplace/download")
async def download_endpoint(req: MarketplaceDownloadRequest):
    """Download a model from a marketplace URL into the uploads directory."""
    result = await _marketplace_download(req.source, req.model_id, req.file_url, req.filename)
    if not result.get("success"):
        raise HTTPException(500, result.get("error", "Download failed"))
    return result


# ── Marketplace MCP Tools ──────────────────────────────────────────────────────


@mcp.tool(annotations=_README_ONLY)
async def marketplace_search(
    source: Annotated[str, Field(description="Marketplace source: printables, thingiverse, grabcad")],
    query: Annotated[str, Field(description="Search query. Pair with a category to browse all.")],
    category: Annotated[
        str, Field(default="", description="Category filter (empty = all). Use marketplace_categories to list.")
    ] = "",
    page: Annotated[int, Field(default=1, description="Page number (1-based).")] = 1,
) -> dict:
    """Search Printables, Thingiverse, or GrabCAD for CAD models.

    Use marketplace_categories first to list available categories per source.
    Results include title, author, thumbnail, download/like counts, and model URL.
    Download a model via marketplace_download.

    ## Return Format
    {"success": bool, "source": str, "results": list, "total": int}

    ## Examples
    await marketplace_search(source="printables", query="robot chassis")
    await marketplace_search(source="thingiverse", query="gear", category="Tools")
    """
    return await _marketplace_search(source, query, category, 20, page)


@mcp.tool()
async def marketplace_download(
    source: Annotated[str, Field(description="Marketplace source.")],
    model_id: Annotated[str, Field(description="Model ID (from search results).")],
    file_url: Annotated[str, Field(description="Direct download URL from search results.")],
    filename: Annotated[str, Field(description="Desired filename, e.g. model.stl or model.zip")],
) -> dict:
    """Download a model from a marketplace into the uploads directory.

    Thingiverse downloads are ZIP files — the server auto-extracts STL/STEP files.
    After download, use step_to_stl or model_info on the imported file.

    ## Return Format
    {"success": bool, "filename": str, "size_bytes": int, "extracted": list | None}

    ## Examples
    await marketplace_download(source="printables", model_id="12345", file_url="https://...", filename="chassis.stl")
    """
    return await _marketplace_download(source, model_id, file_url, filename)


@mcp.tool(annotations=_README_ONLY)
async def marketplace_categories(
    source: Annotated[str, Field(description="Marketplace source: printables, thingiverse, grabcad")],
) -> dict:
    """List available categories for a marketplace source.

    Use the category id from the result as the `category` argument
    in marketplace_search to filter.

    ## Return Format
    {"success": bool, "source": str, "categories": [{"id": str, "label": str}, ...]}

    ## Examples
    await marketplace_categories(source="printables")
    """
    cats = _MARKETPLACE_CATEGORIES.get(source, [])
    return {"success": True, "source": source, "categories": cats}


# ── Prefab UI Cards ────────────────────────────────────────────────────────────


@mcp.tool(app=True)
async def show_marketplace_card(
    source: Annotated[str, Field(description="Marketplace source: printables, thingiverse, grabcad")],
    query: Annotated[str, Field(description="Search query.")],
    category: Annotated[str, Field(default="", description="Optional category filter.")] = "",
) -> PrefabApp:
    """Display marketplace search results as a rich Prefab card in the chat.

    Shows up to 6 results with thumbnails, author, download/like stats.
    Full results available via marketplace_search tool.

    ## Return Format
    PrefabApp card rendered in the MCP client.

    ## Examples
    await show_marketplace_card(source="printables", query="robot chassis")
    await show_marketplace_card(source="thingiverse", query="gear", category="Tools")
    """
    from prefab_ui.components import Card, Column, Heading, Image, Link, Muted, Row, Separator, Text

    data = await _marketplace_search(source, query, category, 20, 1)
    source_labels = {"printables": "Printables", "thingiverse": "Thingiverse", "grabcad": "GrabCAD"}

    if not data.get("success"):
        with Column(gap=3, css_class="p-4") as view:
            Heading("Marketplace Search Error")
            Muted(data.get("error", "Unknown error"))
        return PrefabApp(view=view, title="Marketplace Error")

    items = data.get("results", [])[:6]
    total = data.get("total", 0)

    with Column(gap=3, css_class="p-4") as view:
        Heading(f"🔍 {source_labels.get(source, source)} — {query}")
        Muted(f"{total:,} result{'s' if total != 1 else ''}" + (f" in {category}" if category else ""))
        Separator()
        for item in items:
            with Card(css_class="overflow-hidden"):
                with Row(gap=3, css_class="items-start"):
                    if item.get("image_url"):
                        Image(src=item["image_url"], css_class="w-20 h-20 rounded-lg object-cover shrink-0")
                    with Column(gap=1, css_class="flex-1 min-w-0"):
                        Heading(item.get("title", ""), level=4)
                        Muted(f"by {item.get('author', 'unknown')}")
                        with Row(gap=3):
                            Text(f"⬇ {item['downloads']:,}" if item.get("downloads") else "", css_class="text-xs")
                            Text(f"⭐ {item['likes']:,}" if item.get("likes") else "", css_class="text-xs")
                        if item.get("summary"):
                            Text(item["summary"][:150], css_class="text-xs text-slate-500")
            Separator()
        if len(items) < total:
            Muted(f"... and {total - len(items)} more results. Use marketplace_search for full list.")
        if items:
            Link("Open on marketplace ↗", href=items[0].get("model_url", ""), css_class="text-indigo-400 text-sm")

    return PrefabApp(view=view, title=f"Marketplace — {query}")


# ── Chat / LLM ───────────────────────────────────────────────────────────────


_llm_settings = {"ollama_url": "http://192.168.1.11:11434", "model": "gemma3:1b"}
_marketplace_settings = {
    "thingiverse_api_key": os.environ.get("THINGIVERSE_API_KEY", ""),
    "grabcad_api_key": os.environ.get("GRABCAD_API_KEY", ""),
}


class ChatRequest(BaseModel):
    messages: list[dict] = []
    system: str = ""
    provider: str = "ollama"
    model: str = "gemma3:1b"


class SettingsUpdate(BaseModel):
    ollama_url: str | None = None
    model: str | None = None
    thingiverse_api_key: str | None = None
    grabcad_api_key: str | None = None


@app.get("/api/v1/settings")
async def get_settings():
    """Get LLM and marketplace settings."""
    return {**_llm_settings, **_marketplace_settings, "marketplace": _marketplace_settings}


@app.put("/api/v1/settings")
async def update_settings(body: SettingsUpdate):
    """Update LLM or marketplace settings."""
    if body.ollama_url:
        _llm_settings["ollama_url"] = body.ollama_url
    if body.model:
        _llm_settings["model"] = body.model
    if body.thingiverse_api_key is not None:
        _marketplace_settings["thingiverse_api_key"] = body.thingiverse_api_key
    if body.grabcad_api_key is not None:
        _marketplace_settings["grabcad_api_key"] = body.grabcad_api_key
    return {**_llm_settings, "marketplace": _marketplace_settings}


@app.post("/api/v1/chat")
async def chat_completion(req: ChatRequest):
    """Chat with CAD expert via Ollama."""
    url = req.provider == "ollama" and f"{_llm_settings.get('ollama_url', 'http://192.168.1.11:11434')}/api/chat"
    model = req.model or _llm_settings.get("model", "gemma3:1b")

    if not url:
        return {"content": "Only Ollama provider is supported currently."}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                url,
                json={
                    "model": model,
                    "messages": [{"role": "system", "content": req.system or "You are a CAD expert."}, *req.messages],
                    "stream": False,
                },
            )
            data = r.json()
            return {"content": (data.get("message") or {}).get("content", "") or data.get("response", "")}
    except Exception as e:
        logger.error("Chat error: %s", e)
        return {"content": f"Error: {e}"}


# ── Entry point ──────────────────────────────────────────────────────────────


async def _run_stdio():
    """Serve MCP over stdio (for CLI MCP clients)."""
    await mcp.run_stdio_async()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="FreeCAD MCP Server")
    parser.add_argument("--mode", choices=["stdio", "http", "dual"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")  # noqa: S104
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
    main()
