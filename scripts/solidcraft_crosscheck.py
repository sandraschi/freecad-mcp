#!/usr/bin/env python3
"""Cross-check SolidCraft against FreeCAD on the same part.

SolidCraft builds its own B-rep in Rust (the truck crates). FreeCAD builds
on OpenCASCADE. They share no code. Building the same part in both and
comparing volume, surface area and bounding box turns a silent modelling
bug into a concrete number.

Why this exists
---------------
Upstream SolidCraft validates itself by rebuilding its own recipes in
FreeCAD (their tools/freecad-oracle). This script is the same idea from
our side: freecad-mcp gains a second independent kernel to test against,
and SolidCraft gains a second oracle. Two kernels disagreeing is a bug in
one of them. Two kernels agreeing is not proof of correctness, but it is
cheap evidence.

The part definitions are deliberately written twice, once as SolidCraft
commands and once as FreeCAD Python. Deriving one from the other would
test the translation, not the kernel.

Precision floor (measured 2026-10-29, SolidCraft 0.26.1)
-------------------------------------------------------
SolidCraft's reported volume is exact for planar bodies and about
1.1e-4 relative LOW for every body with a curved face: a cylinder of
r=5,h=10 and one of r=20,h=30 both come back at ratio 0.999887162,
independent of size. That is a chord tessellation (roughly 240 segments
per full turn) integrated for the measurement, not a defect in the
geometry - the B-rep really does hold cylindrical faces (face_types
reports "cylinder"). FreeCAD's value is the exact one on the same parts.

Consequence: SolidCraft cannot adjudicate FreeCAD better than ~2e-4 on
curved geometry. The per-case tolerances below are set from that floor
rather than from a round number, so a genuine regression still trips.
Planar cases are held to 1e-9.

Usage
-----
    uv run python scripts/solidcraft_crosscheck.py
    uv run python scripts/solidcraft_crosscheck.py --case box_fillet -v
    uv run python scripts/solidcraft_crosscheck.py --freecadcmd "C:/FreeCAD/bin/freecadcmd.exe"
    uv run python scripts/solidcraft_crosscheck.py --tol 1e-4 --keep

Programs are found from --solidcraft-cli / --freecadcmd, then the
SOLIDCRAFT_CLI / FREECADCMD environment variables, then PATH, then the
usual install folders. Nothing is hardcoded to one machine.

Exit code 0 when every case agrees within --tol, 1 otherwise.

This is a test tool. Nothing imports it; the server does not depend on it.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# --------------------------------------------------------------------------
# Cases
#
# sc:   SolidCraft command list (the same JSON a script file holds)
# fc:   FreeCAD Python, must leave the finished shape in `shape`
# vol:  analytic volume in mm^3, or None when it cannot be defended by hand
# --------------------------------------------------------------------------

CASES = [
    {
        "name": "box",
        "sc": [{"command": "solid.box", "params": {"length": 10, "width": 20, "height": 30}}],
        "fc": "shape = Part.makeBox(10, 20, 30)",
        "vol": 10 * 20 * 30,
        "tol": 1e-9,
        "why": "sanity floor: both kernels must agree exactly",
    },
    {
        "name": "box_fillet_vertical",
        "sc": [
            {"command": "solid.box", "params": {"length": 40, "width": 40, "height": 20}},
            {
                "command": "solid.fillet",
                "params": {"edges": [[0, 0, 10], [40, 0, 10], [40, 40, 10], [0, 40, 10]], "radius": 3},
            },
        ],
        "fc": """
shape = Part.makeBox(40, 40, 20)
vertical = [e for e in shape.Edges
            if abs(abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) - 20) < 1e-6]
shape = shape.makeFillet(3.0, vertical)
""",
        # square 40x40 with four r=3 corners, extruded 20:
        # 1600 - (4 - pi) * 9, times 20
        "vol": (40 * 40 - (4 - 3.141592653589793) * 9) * 20,
        "tol": 1e-4,
        "why": "fillet chains are where young kernels diverge",
    },
    {
        "name": "shell_open_top",
        "sc": [
            {"command": "solid.box", "params": {"length": 40, "width": 30, "height": 20}},
            {"command": "solid.shell", "params": {"faces": [[20, 15, 20]], "thickness": 2}},
        ],
        "fc": """
shape = Part.makeBox(40, 30, 20)
top = [f for f in shape.Faces if abs(f.normalAt(0, 0).z - 1.0) < 1e-6]
shape = shape.makeThickness(top, -2.0, 1e-6)
""",
        # outer 40*30*20 minus cavity 36*26*18
        "vol": 40 * 30 * 20 - 36 * 26 * 18,
        "tol": 1e-9,
        "why": "shell/thickness offset direction is a classic sign bug",
    },
    {
        "name": "plate_through_hole",
        "sc": [
            {"command": "solid.box", "params": {"length": 40, "width": 40, "height": 10}},
            {
                "command": "solid.cylinder",
                "params": {"radius": 5, "height": 20, "base": [20, 20, -5], "operation": "cut"},
            },
        ],
        "fc": """
plate = Part.makeBox(40, 40, 10)
drill = Part.makeCylinder(5, 20, Vector(20, 20, -5), Vector(0, 0, 1))
shape = plate.cut(drill)
""",
        "vol": 40 * 40 * 10 - 3.141592653589793 * 25 * 10,
        "tol": 1e-4,
        "why": "boolean cut through a solid",
    },
    {
        "name": "revolve_tube",
        "sc": [
            {"command": "sketch.create", "params": {"plane": "XZ"}},
            {"command": "sketch.rectangle.two_point", "params": {"p0": [10, 0], "p1": [20, 30]}},
            {"command": "sketch.finish", "params": {}},
            {"command": "solid.revolve", "params": {"axis": "Z", "angle": 360}},
        ],
        "fc": """
pts = [Vector(10, 0, 0), Vector(20, 0, 0), Vector(20, 0, 30), Vector(10, 0, 30), Vector(10, 0, 0)]
wire = Part.Wire(Part.makePolygon(pts))
rev = wire.revolve(Vector(0, 0, 0), Vector(0, 0, 1), 360)
shape = Part.Solid(rev)
""",
        # annulus: pi * (20^2 - 10^2) * 30
        "vol": 3.141592653589793 * (20**2 - 10**2) * 30,
        "tol": 5e-4,
        "why": "non-boolean feature: profile sweep and axis handling",
    },
]

# --------------------------------------------------------------------------
# Program discovery
# --------------------------------------------------------------------------


def find_solidcraft_cli(explicit: str | None) -> str | None:
    """Locate solidcraft-cli.exe: flag, env, PATH, then usual install folders."""
    if explicit:
        return explicit if Path(explicit).is_file() else None
    env = os.environ.get("SOLIDCRAFT_CLI")
    if env and Path(env).is_file():
        return env
    found = shutil.which("solidcraft-cli")
    if found:
        return found
    roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("LOCALAPPDATA"),
        str(Path.home()),
    ]
    for root in roots:
        if not root:
            continue
        candidate = Path(root) / "SolidCraft" / "solidcraft-cli.exe"
        if candidate.is_file():
            return str(candidate)
        # macOS / Linux app bundles and packages
        for alt in (Path(root) / "solidcraft-cli", Path(root) / "SolidCraft" / "solidcraft-cli"):
            if alt.is_file():
                return str(alt)
    return None


def find_freecadcmd(explicit: str | None) -> str | None:
    """Locate freecadcmd: flag, env, PATH, then the usual install folders."""
    if explicit:
        return explicit if Path(explicit).is_file() else None
    env = os.environ.get("FREECADCMD")
    if env and Path(env).is_file():
        return env
    for name in ("freecadcmd", "FreeCADCmd"):
        found = shutil.which(name)
        if found:
            return found
    roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("LOCALAPPDATA"),
        str(Path.home()),
        "/usr/bin",
        "/usr/local/bin",
        "/opt",
    ]
    names = {"nt": ["FreeCADCmd.exe", "freecadcmd.exe"], "posix": ["freecadcmd", "FreeCADCmd"]}
    wanted = names.get(os.name, names["posix"])
    for root in roots:
        if not root:
            continue
        base = Path(root)
        if not base.is_dir():
            continue
        # direct hit, then one level of versioned folders (FreeCAD_1.1.1_.../)
        for candidate in _iter_candidates(base, wanted, depth=3):
            return str(candidate)
    return None


def _iter_candidates(base: Path, wanted: list[str], depth: int):
    """Yield matches for `wanted` under `base`, at most `depth` levels deep.

    Skips huge unrelated trees by only descending into directories whose
    name looks like a FreeCAD install or that are shallow.
    """
    try:
        entries = list(base.iterdir())
    except (PermissionError, OSError):
        return
    for entry in entries:
        if entry.is_file() and entry.name in wanted:
            yield entry
    if depth <= 0:
        return
    for entry in entries:
        if not entry.is_dir():
            continue
        if entry.name.lower().startswith(("freecad", "bin")) or depth > 1:
            yield from _iter_candidates(entry, wanted, depth - 1)


# --------------------------------------------------------------------------
# Runners
# --------------------------------------------------------------------------


def run_solidcraft(cli: str, script: list[dict], workdir: Path, timeout: int, verbose: bool) -> dict:
    """Run a SolidCraft command list with `eval` and return its measurements."""
    script_path = workdir / "part.json"
    out_path = workdir / "measure.json"
    script_path.write_text(json.dumps(script, indent=2), encoding="utf-8")
    cmd = [cli, "eval", str(script_path), "--json-out", str(out_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if verbose:
        print(f"    $ {' '.join(cmd)}", file=sys.stderr)
        if proc.stderr.strip():
            print(f"    stderr: {proc.stderr.strip()[:800]}", file=sys.stderr)
    if proc.returncode != 0:
        raise RuntimeError(
            f"solidcraft-cli eval exited {proc.returncode}: {(proc.stderr or proc.stdout).strip()[:800]}"
        )
    if not out_path.is_file():
        raise RuntimeError("solidcraft-cli wrote no measurement JSON")
    return json.loads(out_path.read_text(encoding="utf-8"))


def run_freecad(cmd_path: str, body: str, workdir: Path, timeout: int, verbose: bool) -> dict:
    """Run a FreeCAD build script with freecadcmd and read its RESULT line."""
    script_path = workdir / "build.py"
    source = (
        "import json\n"
        "import Part\n"
        "from FreeCAD import Vector\n"
        f"{body}\n"
        "r = {\n"
        "    'volume': float(shape.Volume),\n"
        "    'area': float(shape.Area),\n"
        "    'bbox': [float(shape.BoundBox.XLength), float(shape.BoundBox.YLength),\n"
        "             float(shape.BoundBox.ZLength)],\n"
        "}\n"
        "print('RESULT ' + json.dumps(r))\n"
    )
    script_path.write_text(source, encoding="utf-8")
    cmd = [cmd_path, str(script_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if verbose:
        print(f"    $ {' '.join(cmd)}", file=sys.stderr)
    payload = None
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            payload = line[len("RESULT ") :]
    if payload is None:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-8:]
        raise RuntimeError("freecadcmd produced no RESULT line:\n" + "\n".join(tail))
    return json.loads(payload)


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------


def rel_err(a: float, b: float) -> float:
    scale = max(abs(a), abs(b))
    return 0.0 if scale == 0 else abs(a - b) / scale


def compare(name: str, sc: dict, fc: dict, analytic: float | None, tol: float) -> tuple[bool, list[str]]:
    """Compare one case. Returns (ok, lines-to-print)."""
    sc_vol = sc["total"]["volume_mm3"]
    sc_area = sc["total"]["area_mm2"]
    sc_bbox = [b["bbox"]["max"][i] - b["bbox"]["min"][i] for i in range(3) for b in [sc["bodies"][0]]]
    fc_vol = fc["volume"]
    fc_area = fc["area"]
    fc_bbox = fc["bbox"]

    dv = rel_err(sc_vol, fc_vol)
    da = rel_err(sc_area, fc_area)
    db = max(rel_err(a, b) for a, b in zip(sc_bbox, fc_bbox))
    ok = dv <= tol and da <= tol and db <= tol

    extra = ""
    if analytic is not None:
        av = rel_err(sc_vol, analytic)
        bv = rel_err(fc_vol, analytic)
        extra = f"  analytic={analytic:12.4f} sc_err={av:8.2e} fc_err={bv:8.2e}"
        if max(av, bv) > tol:
            ok = False

    verdict = "ok  " if ok else "FAIL"
    lines = [
        f"{verdict} {name:<22} vol {sc_vol:12.4f} vs {fc_vol:12.4f}  d={dv:8.2e}"
        f" | area {sc_area:12.4f} vs {fc_area:12.4f}  d={da:8.2e} | bbox d={db:8.2e}{extra}"
    ]
    return ok, lines


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-check SolidCraft against FreeCAD.")
    parser.add_argument("--case", action="append", metavar="NAME", help="run only this case (repeatable); default: all")
    parser.add_argument(
        "--tol", type=float, default=None, help="override every case's relative tolerance (default: per case)"
    )
    parser.add_argument("--solidcraft-cli", metavar="PATH", default=None)
    parser.add_argument("--freecadcmd", metavar="PATH", default=None)
    parser.add_argument("--timeout", type=int, default=180, help="per-call seconds (default 180)")
    parser.add_argument("--keep", action="store_true", help="keep temp scripts for debugging")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    cli = find_solidcraft_cli(args.solidcraft_cli)
    if not cli:
        print(
            "error: solidcraft-cli not found. Pass --solidcraft-cli PATH, set SOLIDCRAFT_CLI,\n"
            "       or install SolidCraft (https://solidcraft.io/download).",
            file=sys.stderr,
        )
        return 2
    fcc = find_freecadcmd(args.freecadcmd)
    if not fcc:
        print(
            "error: freecadcmd not found. Pass --freecadcmd PATH, set FREECADCMD,\n"
            "       or install FreeCAD (https://www.freecad.org/downloads.php).",
            file=sys.stderr,
        )
        return 2

    print(f"solidcraft-cli : {cli}")
    print(f"freecadcmd     : {fcc}")
    print("tolerance      : " + (f"{args.tol:g} (override)" if args.tol is not None else "per case") + "\n")

    selected = [c for c in CASES if not args.case or c["name"] in args.case]
    if not selected:
        known = ", ".join(c["name"] for c in CASES)
        print(f"error: no case matched. Known cases: {known}", file=sys.stderr)
        return 2

    failures = 0
    for case in selected:
        print(f"[{case['name']}] {case['why']}")
        workdir = Path(tempfile.mkdtemp(prefix="crosscheck-"))
        try:
            sc = run_solidcraft(cli, case["sc"], workdir, args.timeout, args.verbose)
            fc = run_freecad(fcc, case["fc"], workdir, args.timeout, args.verbose)
            case_tol = args.tol if args.tol is not None else case.get("tol", 1e-3)
            ok, lines = compare(case["name"], sc, fc, case["vol"], case_tol)
            for line in lines:
                print(line)
            if not ok:
                failures += 1
        except Exception as exc:
            print(f"ERROR {case['name']}: {exc}")
            failures += 1
        finally:
            if args.keep:
                print(f"  (kept {workdir})")
            else:
                shutil.rmtree(workdir, ignore_errors=True)
        print()

    total = len(selected)
    print(f"{total - failures}/{total} cases agree within their tolerance")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
