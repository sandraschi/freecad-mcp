"""
FluidX3D GPU CFD MCP tools — native GPU lattice-Boltzmann solver integration.

FluidX3D (ProjectPhysX/FluidX3D) runs on ALL GPUs via OpenCL — NVIDIA, AMD,
Intel Arc, Apple Silicon. 55 bytes/cell memory efficiency (6x better than
traditional LBM). 5k+ stars, v3.7 (May 2026), active maintenance.

These tools generate C++ setup files, compile via g++/MSVC, run the GPU
simulation, and parse structured output (forces, residuals, MLUPS throughput).

Requires: FluidX3D cloned locally. Default path auto-detected from common
locations; configurable via FLUIDX3D_PATH env var.

Registered via register_fluidx3d_tools(mcp, **deps) — called from server.py.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
from typing import Annotated

from pydantic import Field

logger = logging.getLogger("freecad-mcp.fluidx3d")

_README_ONLY = {"readonly": True}

# ── FluidX3D path detection ──────────────────────────────────────────────────

_FLUIDX3D_DEFAULT_PATHS = [
    r"D:\Dev\repos\FluidX3D",
    os.path.expanduser("~/FluidX3D"),
    os.path.expanduser("~/fluidx3d"),
    "/opt/FluidX3D",
]


def _find_fluidx3d() -> str | None:
    """Find FluidX3D installation from env var or common paths."""
    env_path = os.environ.get("FLUIDX3D_PATH")
    if env_path and os.path.isdir(env_path):
        return env_path
    for p in _FLUIDX3D_DEFAULT_PATHS:
        if os.path.isdir(p) and os.path.isdir(os.path.join(p, "src")):
            return p
    return None


def _find_vs_vcvars64() -> str | None:
    """Locate vcvars64.bat via vswhere (MSVC not always on PATH)."""
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    vswhere = os.path.join(pf86, "Microsoft Visual Studio", "Installer", "vswhere.exe")
    if not os.path.isfile(vswhere):
        return None
    try:
        result = subprocess.run(  # noqa: S603
            [
                vswhere,
                "-latest",
                "-requires",
                "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "-property",
                "installationPath",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        vcvars = os.path.join(result.stdout.strip(), "VC", "Auxiliary", "Build", "vcvars64.bat")
        return vcvars if os.path.isfile(vcvars) else None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        logger.debug("vswhere lookup failed", exc_info=True)
        return None


def _opencl_paths(f3d_path: str) -> tuple[str, str]:
    include_dir = os.path.join(f3d_path, "src", "OpenCL", "include")
    lib_dir = os.path.join(f3d_path, "src", "OpenCL", "lib")
    return include_dir, lib_dir


def _read_stock_defines(f3d_path: str) -> str:
    """Load upstream FluidX3D defines.hpp (git HEAD preferred over working tree)."""
    git_exe = shutil.which("git")
    if not git_exe:
        git_exe = "git"
    try:
        result = subprocess.run(  # noqa: S603
            [git_exe, "-C", f3d_path, "show", "HEAD:src/defines.hpp"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        logger.debug("git show defines.hpp failed", exc_info=True)

    stock_path = os.path.join(f3d_path, "src", "defines.hpp")
    with open(stock_path, encoding="utf-8") as f:
        return f.read()


def _generate_defines_hpp(
    f3d_path: str,
    case_name: str,
    *,
    enable_moving: bool = False,
    enable_volume_force: bool = False,
    enable_non_newtonian: bool = False,
    enable_free_surface: bool = False,
    enable_thermal: bool = False,
) -> tuple[str, list[str]]:
    """Patch stock defines.hpp for a case (never replace with a minimal stub)."""
    content = _read_stock_defines(f3d_path)
    content = re.sub(r"(?m)^#define BENCHMARK\b", "//#define BENCHMARK", content)

    stock_extensions = {
        "VOLUME_FORCE": enable_volume_force,
        "FORCE_FIELD": True,
        "EQUILIBRIUM_BOUNDARIES": True,
        "MOVING_BOUNDARIES": enable_moving,
        "SURFACE": enable_free_surface,
        "TEMPERATURE": enable_thermal,
    }
    enabled: list[str] = []
    for define_name, on in stock_extensions.items():
        if on:
            content = re.sub(rf"(?m)^//(#define {define_name}\b)", r"\1", content)
            enabled.append(f"#define {define_name}")

    extras: list[str] = []
    if enable_non_newtonian:
        extras.append("#define NON_NEWTONIAN")
    if enable_thermal:
        extras.append("#define THERMAL")

    header = f"// FluidX3D defines -- auto-generated for case: {case_name}\n"
    body = header + content
    if extras:
        body += "\n// freecad-mcp custom extension flags\n" + "\n".join(extras) + "\n"
        enabled.extend(extras)

    return body, enabled


def _pick_velocity_vtk(vtk_files: list[str]) -> str | None:
    """Prefer FluidX3D velocity VTK (u-*.vtk) over density/other fields."""
    if not vtk_files:
        return None
    u_named = [p for p in vtk_files if re.search(r"^u-", os.path.basename(p), re.I)]
    if u_named:
        return max(u_named, key=os.path.getsize)
    vectorish: list[str] = []
    for path in vtk_files:
        try:
            with open(path, "rb") as f:
                head = f.read(1024)
        except OSError:
            logger.debug("VTK head read failed for %s", path, exc_info=True)
            continue
        if b"VECTORS" in head or (b"SCALARS" in head and b"float 3" in head):
            vectorish.append(path)
    if vectorish:
        return max(vectorish, key=os.path.getsize)
    return max(vtk_files, key=os.path.getsize)


def _vtk_velocity_data_offset(content: bytes, vel_start: int) -> int:
    lookup = content.find(b"LOOKUP_TABLE", vel_start)
    if lookup >= 0:
        return content.index(b"\n", lookup) + 1
    first_line_end = content.index(b"\n", vel_start) + 1
    if content[vel_start:].startswith(b"VECTORS"):
        return content.index(b"\n", first_line_end) + 1
    return content.index(b"\n", first_line_end) + 1


def _find_compiler() -> str | None:
    """Find a C++ compiler (g++ preferred, then MSVC via vswhere)."""
    exes = ["g++", "g++-14", "g++-13", "g++-12", "clang++"]
    for exe in exes:
        try:
            result = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=5)  # noqa: S603
            if result.returncode == 0:
                return exe
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    try:
        result = subprocess.run(["cl"], capture_output=True, text=True, timeout=5, shell=True)  # noqa: S602, S607
        if "Microsoft" in result.stdout or "Microsoft" in result.stderr:
            return "msvc"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        logger.debug("MSVC cl.exe not on PATH")
    if _find_vs_vcvars64():
        return "msvc"
    return None


def _find_prebuilt(
    f3d_case_dir: str,
    f3d_path: str | None = None,
) -> str | None:
    """Find a pre-compiled FluidX3D binary (allows skipping compilation).

    Checks, in priority order:
    1. FLUIDX3D_BINARY environment variable
    2. <f3d_case_dir>/bin/fluidx3d_run.exe (Windows) or fluidx3d_run
    3. <f3d_path>/bin/ for pre-existing compiled binaries
    """
    exe_suffix = ".exe" if os.name == "nt" else ""

    env_bin = os.environ.get("FLUIDX3D_BINARY")
    if env_bin and os.path.isfile(env_bin):
        return env_bin

    run_bin = os.path.join(f3d_case_dir, "bin", f"fluidx3d_run{exe_suffix}")
    if os.path.isfile(run_bin):
        return run_bin

    if f3d_path:
        f3d_bin_dir = os.path.join(f3d_path, "bin")
        if os.path.isdir(f3d_bin_dir):
            for fname in os.listdir(f3d_bin_dir):
                fpath = os.path.join(f3d_bin_dir, fname)
                if not os.path.isfile(fpath):
                    continue
                if fname in ("FluidX3D.exe", "FluidX3D"):
                    return fpath
                if fname.startswith("fluidx3d") and fname.endswith(exe_suffix):
                    return fpath

    return None


# ── GPU device query ─────────────────────────────────────────────────────────


def _query_gpu_devices() -> list[dict]:
    """Query available OpenCL GPU devices via clinfo or pyopencl.

    Returns a list of dicts with keys: platform, device, vendor.
    Empty list if query is unavailable.
    """
    devices: list[dict] = []

    try:
        r = subprocess.run(
            ["clinfo", "--raw"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
        )
        plat_name = ""
        for line in r.stdout.splitlines():
            if line.startswith("CL_PLATFORM_NAME "):
                plat_name = line.split(" ", 1)[1].strip()
            if line.startswith("CL_DEVICE_NAME ") and plat_name:
                dev_name = line.split(" ", 1)[1].strip()
                devices.append({
                    "platform": plat_name,
                    "device": dev_name,
                    "vendor": "",
                })
        if devices:
            return devices
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    try:
        r = subprocess.run(
            ["clinfo", "-l"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
        )
        for line in r.stdout.splitlines():
            m = re.match(r".*Device #(\d+):\s+(.+)", line)
            if m:
                devices.append({
                    "platform": "",
                    "device": m.group(2).strip(),
                    "vendor": "",
                })
        if devices:
            return devices
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    try:
        nvidia_smi = shutil.which("nvidia-smi")
        if not nvidia_smi:
            return devices
        result = subprocess.run(  # noqa: S603
            [nvidia_smi, "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                name = line.strip()
                if name:
                    devices.append({"platform": "NVIDIA", "device": name, "vendor": "NVIDIA"})
        if devices:
            return devices
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    return devices


# ── Setup template ───────────────────────────────────────────────────────────

_TEMPLATE = """#include "setup.hpp"
#include "info.hpp"

// FluidX3D setup — auto-generated by freecad-mcp cfd_fluidx3d_setup
// Case: {case_name} | Domain: {domain_type} | GPU CFD via OpenCL

void main_setup() {{
    const float lbm_len = {lbm_length}f;
    const float lbm_vel = {lbm_velocity}f;
    const float si_len = {si_length}f;
    const float si_vel = {si_velocity}f;

    units.set_m_kg_s(lbm_len, lbm_vel, 1.0f, si_len, si_vel, {si_density}f);

    const uint Nx = {Nx}u, Ny = {Ny}u, Nz = {Nz}u;
    const float nu = {nu}f;
{lbm_constructor}

    const uint N = lbm.get_N();
    const auto mid = lbm.center();

    parallel_for(N, [&](ulong n) {{
        uint x = 0u, y = 0u, z = 0u;
        lbm.coordinates(n, x, y, z);
        lbm.u.x[n] = lbm.u.y[n] = lbm.u.z[n] = 0.0f;
        lbm.rho[n] = 1.0f;
        lbm.flags[n] = 0u;
{boundary_code}
{profile_code}
{free_surface_code}
{thermal_init_code}
    }});
{stl_imports}
{non_newtonian_code}
{thermal_defs}

    const uint lbm_T = {time_steps}u;
    const uint write_intv = {write_interval}u;

    print_info("FluidX3D-MCP case:{case_name} res:" + to_string(Nx) + "x" + to_string(Ny) + "x" + to_string(Nz) + " cells:" + to_string(N) + " nu:" + to_string(nu));

    lbm.run(0u);
    const auto t0 = std::chrono::high_resolution_clock::now();

    while(lbm.get_t() < lbm_T) {{
        if(lbm.get_t() % write_intv == 0u && lbm.get_t() > 0u) {{
            const float3 f = lbm.object_force(TYPE_S);
            print_info("STEP " + to_string(lbm.get_t()) + " F " + to_string(units.si_F(f.x)) + " " + to_string(units.si_F(f.y)) + " " + to_string(units.si_F(f.z)));
            if(lbm.get_t() % (write_intv * 50u) == 0u) {{
                lbm.u.write_device_to_vtk();
                lbm.rho.write_device_to_vtk();
            }}
        }}
        lbm.run(1u);
    }}

    const auto t1 = std::chrono::high_resolution_clock::now();
    const float dt = std::chrono::duration<float>(t1 - t0).count();
    const float3 f = lbm.object_force(TYPE_S);

    print_info("DONE steps:" + to_string(lbm_T) + " time:" + to_string(dt) + "s mlups:" + to_string((float)N*(float)lbm_T/dt/1e6f));
    print_info("FORCES " + to_string(units.si_F(f.x)) + " " + to_string(units.si_F(f.y)) + " " + to_string(units.si_F(f.z)));
{object_forces_loop}
    lbm.u.write_device_to_vtk();
    lbm.rho.write_device_to_vtk();
}}
"""

# BC templates for common domain types
# {outlet_rho} expands to "lbm.rho[n] = 1.0f;" (fixed_rho) or "" (neumann)

_BC_CHANNEL = """        if(x == 0u) {{ lbm.flags[n] = TYPE_E; lbm.u.x[n] = {u_inlet_x}f; lbm.u.y[n] = {u_inlet_y}f; lbm.u.z[n] = {u_inlet_z}f; }}
        else if(x == Nx - 1u) {{ lbm.flags[n] = TYPE_E; {outlet_rho} }}
        else if(y == 0u || y == Ny - 1u || z == 0u || z == Nz - 1u) {{ lbm.flags[n] = TYPE_S|TYPE_X; }}"""

_BC_PIPE = """        if(x == 0u) {{ lbm.flags[n] = TYPE_E; lbm.u.x[n] = {u_inlet_x}f; }}
        else if(x == Nx - 1u) {{ lbm.flags[n] = TYPE_E; {outlet_rho} }}
        else {{
            const float ry = (float)(int)y - (float)(int)(Ny/2u);
            const float rz = (float)(int)z - (float)(int)(Nz/2u);
            const float r2 = ry*ry + rz*rz;
            const float R2 = (float)(Ny/2u) * (float)(Ny/2u) * 0.95f;
            if(r2 > R2) {{ lbm.flags[n] = TYPE_S|TYPE_X; }}
        }}"""

_BC_BOX = """        if(x == 0u || x == Nx - 1u || y == 0u || y == Ny - 1u || z == 0u || z == Nz - 1u) {{ lbm.flags[n] = TYPE_S|TYPE_X; }}"""

_BC_SYMMETRY_Y = """        if(x == 0u) {{ lbm.flags[n] = TYPE_E; lbm.u.x[n] = {u_inlet_x}f; lbm.u.y[n] = {u_inlet_y}f; lbm.u.z[n] = {u_inlet_z}f; }}
        else if(x == Nx - 1u) {{ lbm.flags[n] = TYPE_E; {outlet_rho} }}
        else if(y == 0u || y == Ny - 1u) {{ lbm.flags[n] = TYPE_Z; }}
        else if(z == 0u || z == Nz - 1u) {{ lbm.flags[n] = TYPE_S|TYPE_X; }}"""

_BC_SYMMETRY_Z = """        if(x == 0u) {{ lbm.flags[n] = TYPE_E; lbm.u.x[n] = {u_inlet_x}f; lbm.u.y[n] = {u_inlet_y}f; lbm.u.z[n] = {u_inlet_z}f; }}
        else if(x == Nx - 1u) {{ lbm.flags[n] = TYPE_E; {outlet_rho} }}
        else if(z == 0u || z == Nz - 1u) {{ lbm.flags[n] = TYPE_Z; }}
        else if(y == 0u || y == Ny - 1u) {{ lbm.flags[n] = TYPE_S|TYPE_X; }}"""

BC_TEMPLATES = {
    "channel": _BC_CHANNEL,
    "pipe": _BC_PIPE,
    "box": _BC_BOX,
    "nozzle": _BC_PIPE,  # Same as pipe for now — STL import for complex
    "custom": "",
}

BC_TEMPLATES_SYMMETRY = {
    "channel_y": _BC_SYMMETRY_Y,
    "channel_z": _BC_SYMMETRY_Z,
}


def _generate_boundary_code(
    domain_type: str,
    u_inlet_x: float,
    u_inlet_y: float,
    u_inlet_z: float,
    has_stl: bool = False,
    outlet_type: str = "fixed_rho",
    symmetry_axis: str = "",
) -> str:
    """Generate the boundary condition C++ code block."""
    if has_stl:
        return "        // Boundaries set via STL voxelization"

    outlet_rho = "" if outlet_type == "neumann" else "lbm.rho[n] = 1.0f;"

    if symmetry_axis:
        key = f"{domain_type}_{symmetry_axis}"
        template = BC_TEMPLATES_SYMMETRY.get(key, _BC_SYMMETRY_Y)
        return template.format(
            u_inlet_x=u_inlet_x, u_inlet_y=u_inlet_y, u_inlet_z=u_inlet_z,
            outlet_rho=outlet_rho,
        )

    template = BC_TEMPLATES.get(domain_type, _BC_BOX)
    return template.format(
        u_inlet_x=u_inlet_x, u_inlet_y=u_inlet_y, u_inlet_z=u_inlet_z,
        outlet_rho=outlet_rho,
    )


def _generate_profile_code(
    profile_shape: str,
    domain_type: str,
    u_inlet_x: float,
    u_inlet_y: float,
    u_inlet_z: float,
) -> str:
    """Generate C++ code for inlet velocity profile (parabolic, blasius, uniform).

    Returns empty string for 'uniform' — the BC template handles uniform velocity.
    """
    if profile_shape == "uniform":
        return ""

    ux = u_inlet_x

    if profile_shape == "parabolic":
        if domain_type in ("channel", "box"):
            return f"""        if(x == 0u) {{
            const float y_frac = (float)(int)y / (float)(int)max(Ny - 1u, 1u);
            const float z_frac = (float)(int)z / (float)(int)max(Nz - 1u, 1u);
            const float p = 6.0f * y_frac * (1.0f - y_frac) * 4.0f * z_frac * (1.0f - z_frac);
            lbm.u.x[n] = {ux}f * p;
        }}"""
        if domain_type in ("pipe", "nozzle"):
            return f"""        if(x == 0u) {{
            const float ry = (float)(int)y - (float)(int)(Ny/2u);
            const float rz = (float)(int)z - (float)(int)(Nz/2u);
            const float r2 = ry*ry + rz*rz;
            const float R2 = (float)(Ny/2u) * (float)(Ny/2u);
            if(r2 < R2) {{
                lbm.u.x[n] = {ux}f * 2.0f * (1.0f - r2 / R2);
            }}
        }}"""
        return ""

    if profile_shape == "blasius":
        if domain_type in ("channel", "box"):
            return f"""        if(x == 0u) {{
            const float y_frac = (float)(int)y / (float)(int)max(Ny - 1u, 1u);
            const float z_frac = (float)(int)z / (float)(int)max(Nz - 1u, 1u);
            const float w = 2.0f * fmin(y_frac, 1.0f - y_frac);
            const float w2 = 2.0f * fmin(z_frac, 1.0f - z_frac);
            lbm.u.x[n] = {ux}f * 1.2247f * pow(fmin(w, w2), 0.142857f);
        }}"""
        if domain_type in ("pipe", "nozzle"):
            return f"""        if(x == 0u) {{
            const float ry = (float)(int)y - (float)(int)(Ny/2u);
            const float rz = (float)(int)z - (float)(int)(Nz/2u);
            const float r = sqrt(ry*ry + rz*rz);
            const float R = (float)(Ny/2u);
            if(r < R) {{
                lbm.u.x[n] = {ux}f * 1.2247f * pow(1.0f - r/R, 0.142857f);
            }}
        }}"""
        return ""

    return ""


def _generate_free_surface_code(
    free_surface: bool,
    fill_fraction: float,
) -> str:
    """Generate C++ code for free-surface (liquid-gas) initialization.

    Sets TYPE_L for interior cells below fill height, TYPE_G above.
    Only activates for cells with lbm.flags[n] == 0u (not a boundary).
    """
    if not free_surface:
        return ""
    return f"""        if(lbm.flags[n] == 0u) {{
            const float fill_z = {fill_fraction}f * (float)Nz;
            lbm.flags[n] = ((float)z < fill_z) ? TYPE_L : TYPE_G;
        }}"""


def _generate_thermal_init_code(thermal: bool, T_hot: float, T_cold: float) -> str:
    """Generate C++ code for temperature field initialization inside parallel_for."""
    if not thermal:
        return ""
    return f"""        if constexpr (THERMAL) {{
            const float z_frac = (float)z / (float)max(Nz - 1u, 1u);
            lbm.T[n] = {T_hot}f * (1.0f - z_frac) + {T_cold}f * z_frac;
        }}"""


def _generate_thermal_defs(thermal: bool, beta: float) -> str:
    """Generate C++ code for thermal expansion coefficient definition."""
    if not thermal:
        return ""
    return f"    const float beta = {beta}f;\n"


def _generate_non_newtonian_code(
    non_newtonian: bool,
    nu0: float,
    n_index: float,
    consistency: float,
) -> str:
    """Generate C++ code for power-law (Ostwald) non-Newtonian viscosity model."""
    if not non_newtonian:
        return ""
    return f"""    if constexpr (NON_NEWTONIAN) {{
        lbm.set_nu_non_newtonian({nu0}f, {n_index}f, {consistency}f);
    }}
"""


def _generate_object_forces_loop(stl_configs: list[dict]) -> str:
    """Generate C++ code to report per-object forces after the run loop.

    Each STL object with a distinct type_flag gets an object_force() call.
    """
    if not stl_configs:
        return ""

    lines: list[str] = []
    seen_flags: set[str] = set()

    for i, cfg in enumerate(stl_configs):
        flag = cfg.get("type_flag", "TYPE_S")
        if flag not in seen_flags:
            seen_flags.add(flag)
        lines.append(
            f'    const float3 f_o{i} = lbm.object_force({flag});'
        )
        lines.append(
            f'    print_info("OBJ_FORCE " + to_string({i}) + " Fx:" + '
            f'to_string(units.si_F(f_o{i}.x)) + " Fy:" + '
            f'to_string(units.si_F(f_o{i}.y)) + " Fz:" + '
            f'to_string(units.si_F(f_o{i}.z)));'
        )
    if lines:
        lines.insert(0, "")
        lines.insert(1, "    // Per-object forces")
    return "\n".join(lines)


def _generate_stl_imports(
    stl_files: list[str],
    stl_configs: list[dict] | None = None,
) -> str:
    """Generate STL import C++ code with per-object type flag assignment."""
    if not stl_files:
        return "    // No STL geometry — using pure primitive boundaries"

    configs = stl_configs or [{"type_flag": "TYPE_S|TYPE_X"} for _ in stl_files]

    lines = []
    for i, stl_path in enumerate(stl_files):
        fname = os.path.basename(stl_path)
        type_flag = configs[i].get("type_flag", "TYPE_S|TYPE_X") if i < len(configs) else "TYPE_S|TYPE_X"
        lines.append(f'    Mesh* mesh_{i} = read_stl(get_exe_path() + "../stl/{fname}");')
        lines.append(f"    mesh_{i}->translate(mid - 0.5f * (mesh_{i}->pmin + mesh_{i}->pmax));")
        lines.append(f"    lbm.voxelize_mesh_on_device(mesh_{i}, {type_flag});")
    return "\n".join(lines)


def _generate_setup_cpp(
    case_name: str,
    domain_type: str,
    Nx: int, Ny: int, Nz: int,
    nu: float,
    lbm_length: float, lbm_velocity: float,
    si_length: float, si_velocity: float, si_density: float,
    fx: float, fy: float, fz: float,
    u_inlet_x: float, u_inlet_y: float, u_inlet_z: float,
    time_steps: int, write_interval: int,
    stl_files: list[str] | None = None,
    stl_configs: list[dict] | None = None,
    profile_shape: str = "uniform",
    outlet_type: str = "fixed_rho",
    symmetry_axis: str = "",
    free_surface: bool = False,
    fill_fraction: float = 0.5,
    thermal: bool = False,
    beta: float = 0.0,
    T_hot: float = 1.0,
    T_cold: float = 0.0,
    non_newtonian: bool = False,
    nu0: float = 0.1,
    n_index: float = 1.0,
    consistency: float = 1.0,
) -> str:
    """Generate complete FluidX3D setup.cpp content."""
    stl_files = stl_files or []
    has_stl = len(stl_files) > 0

    if abs(fx) < 1e-12 and abs(fy) < 1e-12 and abs(fz) < 1e-12:
        lbm_constructor = f"    LBM lbm(Nx, Ny, Nz, {nu}f);"
    else:
        lbm_constructor = f"    LBM lbm(Nx, Ny, Nz, {nu}f, {fx}f, {fy}f, {fz}f);"

    return _TEMPLATE.format(
        case_name=case_name,
        domain_type=domain_type,
        Nx=Nx, Ny=Ny, Nz=Nz,
        nu=nu,
        lbm_constructor=lbm_constructor,
        lbm_length=lbm_length, lbm_velocity=lbm_velocity,
        si_length=si_length, si_velocity=si_velocity, si_density=si_density,
        boundary_code=_generate_boundary_code(
            domain_type, u_inlet_x, u_inlet_y, u_inlet_z,
            has_stl, outlet_type, symmetry_axis,
        ),
        profile_code=_generate_profile_code(profile_shape, domain_type, u_inlet_x, u_inlet_y, u_inlet_z),
        free_surface_code=_generate_free_surface_code(free_surface, fill_fraction),
        thermal_init_code=_generate_thermal_init_code(thermal, T_hot, T_cold),
        stl_imports=_generate_stl_imports(stl_files, stl_configs),
        non_newtonian_code=_generate_non_newtonian_code(non_newtonian, nu0, n_index, consistency),
        thermal_defs=_generate_thermal_defs(thermal, beta),
        time_steps=time_steps,
        write_interval=write_interval,
        object_forces_loop=_generate_object_forces_loop(stl_configs or []),
    )


# ── Registration ─────────────────────────────────────────────────────────────


def register_fluidx3d_tools(
    mcp,
    state: dict,
    bridge_send,
    run_freecad,
    work_dir: str,
    output_dir: str,
    upload_dir: str,
    build_result,
):
    """Register all 7 FluidX3D MCP tools on the FastMCP instance.

    Returns a dict mapping tool_name -> callable for REST dispatch.
    """

    F3D_CASE_DIR = os.path.join(work_dir, "fluidx3d_cases")
    os.makedirs(F3D_CASE_DIR, exist_ok=True)

    # ── cfd_fluidx3d_status ──────────────────────────────────────────────

    @mcp.tool(annotations=_README_ONLY)
    async def cfd_fluidx3d_status() -> dict:
        """Check FluidX3D installation, compiler availability, and GPU devices.

        Reports the FluidX3D source path, compiler found, GPUs detected
        via OpenCL (clinfo), and whether the pipeline is ready for GPU CFD.
        Call this first to assess the environment.

        ## Return Format
        {"success": bool, "fluidx3d_path": str, "compiler": str, "ready": bool, "gpu_devices": list, "gpu_count": int}

        ## Examples
        await cfd_fluidx3d_status()
        """
        f3d_path = _find_fluidx3d()
        compiler = _find_compiler()
        gpu_devices = _query_gpu_devices()
        ready = f3d_path is not None and compiler is not None

        if not f3d_path:
            return {
                "success": True,
                "fluidx3d_path": None,
                "compiler": compiler,
                "ready": False,
                "gpu_devices": gpu_devices,
                "gpu_count": len(gpu_devices),
                "error": "FluidX3D not found. Clone: git clone https://github.com/ProjectPhysX/FluidX3D.git. Set env var FLUIDX3D_PATH if non-standard location.",
            }

        return {
            "success": True,
            "fluidx3d_path": f3d_path,
            "compiler": compiler or "not found",
            "ready": ready,
            "gpu_devices": gpu_devices,
            "gpu_count": len(gpu_devices),
        }

    # ── cfd_fluidx3d_prebuilt ───────────────────────────────────────────

    @mcp.tool(annotations=_README_ONLY)
    async def cfd_fluidx3d_prebuilt() -> dict:
        """Check for a pre-compiled FluidX3D binary that can skip compilation.

        Detects a prebuilt binary from FLUIDX3D_BINARY env var,
        fluidx3d_cases/bin/, or the FluidX3D source tree's bin/ directory.

        ## Return Format
        {"success": bool, "prebuilt_path": str|null, "message": str}

        ## Examples
        await cfd_fluidx3d_prebuilt()
        """
        f3d_path = _find_fluidx3d()
        prebuilt = _find_prebuilt(F3D_CASE_DIR, f3d_path)

        if prebuilt:
            return {
                "success": True,
                "prebuilt_path": prebuilt,
                "message": f"Pre-built FluidX3D binary found: {prebuilt}",
            }
        return {
            "success": True,
            "prebuilt_path": None,
            "message": "No pre-built FluidX3D binary found. Compilation will be required.",
        }

    # ── cfd_fluidx3d_setup ──────────────────────────────────────────────

    @mcp.tool()
    async def cfd_fluidx3d_setup(
        case_name: Annotated[str, Field(description="Case directory name.")] = "f3d_channel",
        domain_type: Annotated[str, Field(description="Domain shape: channel, pipe, box, nozzle, stl.")] = "channel",
        resolution_x: Annotated[int, Field(description="Grid cells in X direction.", ge=2)] = 512,
        resolution_y: Annotated[int, Field(description="Grid cells in Y direction.", ge=2)] = 128,
        resolution_z: Annotated[int, Field(description="Grid cells in Z direction (auto-set to 1 when mode_2d=True).", ge=1)] = 128,
        length_m: Annotated[float, Field(description="Physical length in metres.", ge=0.001)] = 1.0,
        velocity_ms: Annotated[float, Field(description="Inlet velocity in m/s.", ge=0.0001)] = 0.01,
        viscosity_m2s: Annotated[float, Field(description="Kinematic viscosity in m²/s.", ge=1e-10)] = 1e-6,
        density_kgm3: Annotated[float, Field(description="Fluid density in kg/m³.", ge=1e-6)] = 1000.0,
        time_steps: Annotated[int, Field(description="Total simulation time steps.", ge=100)] = 50000,
        write_interval: Annotated[int, Field(description="Write results every N steps.", ge=10)] = 1000,
        stl_file: Annotated[str, Field(description="STL filename in uploads for 'stl' domain type.")] = "",
        of_case_name: Annotated[str, Field(description="OpenFOAM case name for auto-discovering STL from cfd_cases/<name>/geometry.stl.")] = "",
        # Gap 1: Inlet profiles
        profile_shape: Annotated[str, Field(description="Inlet velocity profile shape: uniform, parabolic, blasius.")] = "uniform",
        # Gap 2: Multiple STL objects
        stl_configs_json: Annotated[str, Field(description="JSON array of per-object STL configs: '[{\"file\":\"a.stl\",\"type_flag\":\"TYPE_S|TYPE_X\"}]'. File paths relative to uploads dir.")] = "",
        # Gap 3: Symmetry planes
        symmetry_axis: Annotated[str, Field(description="Symmetry plane axis (y or z). Empty = no symmetry. Sets TYPE_Z boundary condition.")] = "",
        # Gap 4: Non-Newtonian viscosity
        non_newtonian: Annotated[bool, Field(description="Enable power-law (Ostwald) non-Newtonian viscosity model.")] = False,
        nn_nu0: Annotated[float, Field(description="Reference viscosity (lbm units) for non-Newtonian model.", ge=0.001)] = 0.1,
        nn_n_index: Annotated[float, Field(description="Power-law index n. n<1 = shear-thinning, n>1 = shear-thickening.", ge=0.01)] = 1.0,
        nn_consistency: Annotated[float, Field(description="Consistency index K for power-law model.", ge=0.0)] = 1.0,
        # Gap 5: Free surface
        free_surface: Annotated[bool, Field(description="Enable free-surface (liquid-gas) LBM model.")] = False,
        fill_fraction: Annotated[float, Field(description="Initial liquid fill fraction of domain height (0-1).", ge=0.01, le=0.99)] = 0.5,
        # Gap 6: Thermal LBM
        thermal: Annotated[bool, Field(description="Enable thermal LBM with Boussinesq buoyancy (requires #define THERMAL).")] = False,
        beta: Annotated[float, Field(description="Thermal expansion coefficient (1/K) for Boussinesq approximation.", ge=0.0)] = 0.0,
        T_hot: Annotated[float, Field(description="Hot wall temperature (lbm units) for thermal stratification init.")] = 1.0,
        T_cold: Annotated[float, Field(description="Cold wall temperature (lbm units) for thermal stratification init.")] = 0.0,
        # Gap 7: Pressure outlet
        outlet_type: Annotated[str, Field(description="Outlet BC type: fixed_rho (rho=1.0) or neumann (zero-gradient).")] = "fixed_rho",
        # Gap 8: 2D mode
        mode_2d: Annotated[bool, Field(description="Enable 2D simulation mode. Forces Nz=1.")] = False,
    ) -> dict:
        """Generate a FluidX3D C++ setup file for GPU CFD simulation.

        Creates a complete setup.cpp with the specified domain, boundary
        conditions, and simulation parameters. The generated file replaces
        src/setup.cpp in a FluidX3D clone. Compile with cfd_fluidx3d_compile.

        STL geometry is auto-discovered from multiple sources (in priority):
        1. Explicit stl_file in uploads/outputs (for domain_type='stl')
        2. of_case_name -> cfd_cases/<of_case_name>/geometry.stl
        3. case_name -> cfd_cases/<case_name>/geometry.stl
        4. fluidx3d_cases/<case_name>/geometry.stl (exported by cfd_create_domain)

        Domain types:
        - channel: rectangular duct, velocity inlet/outlet, no-slip walls
        - pipe: cylindrical tube with circular cross-section
        - box: all-sides closed (driven cavity)
        - nozzle: convergent-divergent (STL import)
        - stl: custom geometry from STL file in uploads

        ## Return Format
        {"success": bool, "case_name": str, "data": {"setup_file": str, "resolution": str, "cells": int, "Re": float}, "features": list}

        ## Examples
        await cfd_fluidx3d_setup(case_name="pipe_gpu", domain_type="pipe", resolution_x=512, resolution_y=128, resolution_z=128, length_m=2.0, velocity_ms=0.05)
        await cfd_fluidx3d_setup(case_name="airfoil_gpu", domain_type="stl", stl_file="naca0012.stl", resolution_x=768, time_steps=100000)
        await cfd_fluidx3d_setup(case_name="parabolic_pipe", profile_shape="parabolic", resolution_x=512)
        await cfd_fluidx3d_setup(case_name="free_surface", domain_type="box", free_surface=True, fill_fraction=0.5)
        """
        # Gap 8: 2D mode forces Nz = 1
        if mode_2d:
            resolution_z = 1

        # Gap 2: Parse STL configs JSON
        stl_configs: list[dict] = []
        if stl_configs_json:
            try:
                parsed = json.loads(stl_configs_json)
                if isinstance(parsed, list):
                    stl_configs = parsed
            except json.JSONDecodeError:
                return {"success": False, "error": "stl_configs_json is not valid JSON."}

        case_dir = os.path.join(F3D_CASE_DIR, case_name)
        os.makedirs(case_dir, exist_ok=True)

        # Handle STL file — multi-source discovery cascade
        stl_files = []
        stl_src = None

        # If stl_configs_json is provided, resolve each file from uploads
        if stl_configs and domain_type == "stl":
            all_found = True
            resolved: list[str] = []
            for cfg in stl_configs:
                fn = cfg.get("file", "")
                src = os.path.join(upload_dir, fn)
                if not os.path.isfile(src):
                    src = os.path.join(output_dir, fn)
                if os.path.isfile(src):
                    resolved.append(src)
                else:
                    all_found = False
            if all_found and resolved:
                stl_files = resolved
                stl_src = resolved[0]  # for the copy below
            elif not all_found:
                # Fall through to single-file discovery
                logger.warning("Not all stl_configs files found on disk; falling back to single-file discovery")
                stl_configs = []

        if not stl_files and domain_type == "stl" and stl_file:
            src = os.path.join(upload_dir, stl_file)
            if not os.path.isfile(src):
                src = os.path.join(output_dir, stl_file)
            if os.path.isfile(src):
                stl_src = src

        if not stl_src and of_case_name:
            of_stl = os.path.join(work_dir, "cfd_cases", of_case_name, "geometry.stl")
            if os.path.isfile(of_stl):
                stl_src = of_stl

        if not stl_src:
            auto_stl = os.path.join(work_dir, "cfd_cases", case_name, "geometry.stl")
            if os.path.isfile(auto_stl):
                stl_src = auto_stl

        if not stl_src:
            f3d_stl = os.path.join(F3D_CASE_DIR, case_name, "geometry.stl")
            if os.path.isfile(f3d_stl):
                stl_src = f3d_stl

        if stl_src and not stl_files:
            dst = os.path.join(case_dir, os.path.basename(stl_src))
            if os.path.abspath(stl_src).lower() != os.path.abspath(dst).lower():
                shutil.copy(stl_src, dst)
            stl_files = [dst]
        elif domain_type == "stl" and stl_file and not stl_files:
            return {"success": False, "error": f"STL file '{stl_file}' not found in uploads, outputs, or CFD cases."}

        # Copy multi-STL files to case directory
        if stl_configs and stl_files:
            for src_path, cfg in zip(stl_files, stl_configs):
                dst = os.path.join(case_dir, os.path.basename(src_path))
                if os.path.abspath(src_path).lower() != os.path.abspath(dst).lower():
                    shutil.copy(src_path, dst)

        # LBM unit conversion (keep u <= 0.1 for stability)
        lbm_velocity = min(velocity_ms * 0.05, 0.08)
        lbm_length = 1.0
        si_length = length_m
        si_velocity = velocity_ms

        # Viscosity in LBM units
        nu_si = viscosity_m2s
        lbm_nu = max(nu_si * lbm_velocity / (si_velocity * lbm_length) if si_velocity > 0 else 1.0 / 6.0, 0.001, min(0.2, 1.0 / 6.0))

        # Inlet-driven cases use zero volume force unless explicitly set later
        fx = 0.0
        fy = 0.0
        fz = 0.0

        ux = lbm_velocity
        uy = 0.0
        uz = 0.0

        # Generate C++ setup
        cpp_content = _generate_setup_cpp(
            case_name=case_name,
            domain_type=domain_type,
            Nx=resolution_x, Ny=resolution_y, Nz=resolution_z,
            nu=round(lbm_nu, 6),
            lbm_length=lbm_length, lbm_velocity=lbm_velocity,
            si_length=si_length, si_velocity=si_velocity, si_density=density_kgm3,
            fx=fx, fy=fy, fz=fz,
            u_inlet_x=ux, u_inlet_y=uy, u_inlet_z=uz,
            time_steps=time_steps, write_interval=write_interval,
            stl_files=stl_files if stl_files else None,
            stl_configs=stl_configs if stl_configs else None,
            profile_shape=profile_shape,
            outlet_type=outlet_type,
            symmetry_axis=symmetry_axis,
            free_surface=free_surface,
            fill_fraction=fill_fraction,
            thermal=thermal,
            beta=beta,
            T_hot=T_hot,
            T_cold=T_cold,
            non_newtonian=non_newtonian,
            nu0=nn_nu0,
            n_index=nn_n_index,
            consistency=nn_consistency,
        )

        setup_path = os.path.join(case_dir, "setup.cpp")
        with open(setup_path, "w") as f:
            f.write(cpp_content)

        # Generate defines.hpp by patching stock FluidX3D template (do not replace wholesale)
        f3d_path = _find_fluidx3d()
        if not f3d_path:
            return {"success": False, "error": "FluidX3D not found. Clone: git clone https://github.com/ProjectPhysX/FluidX3D.git"}

        defines_content, enabled_defines = _generate_defines_hpp(
            f3d_path,
            case_name,
            enable_moving=bool(stl_files),
            enable_volume_force=abs(fx) >= 1e-12 or abs(fy) >= 1e-12 or abs(fz) >= 1e-12,
            enable_non_newtonian=non_newtonian,
            enable_free_surface=free_surface,
            enable_thermal=thermal,
        )

        defines_path = os.path.join(case_dir, "defines.hpp")
        with open(defines_path, "w", encoding="utf-8") as f:
            f.write(defines_content)

        # Save config for later tools
        cfg = {
            "case_name": case_name,
            "domain_type": domain_type,
            "resolution": [resolution_x, resolution_y, resolution_z],
            "cells": resolution_x * resolution_y * resolution_z,
            "lbm_nu": round(lbm_nu, 6),
            "si_velocity": si_velocity,
            "si_viscosity": nu_si,
            "si_length": si_length,
            "time_steps": time_steps,
            "write_interval": write_interval,
            "profile_shape": profile_shape,
            "outlet_type": outlet_type,
            "symmetry_axis": symmetry_axis,
            "free_surface": free_surface,
            "fill_fraction": fill_fraction,
            "thermal": thermal,
            "beta": beta,
            "non_newtonian": non_newtonian,
            "mode_2d": mode_2d,
        }
        Re = si_velocity * si_length / nu_si if nu_si > 0 else 0
        with open(os.path.join(case_dir, ".f3d_config.json"), "w") as f:
            json.dump(cfg, f)

        stl_file_name = os.path.basename(stl_files[0]) if stl_files else None

        # Collect enabled features for return
        active_features: list[str] = []
        if profile_shape != "uniform":
            active_features.append(f"profile:{profile_shape}")
        if symmetry_axis:
            active_features.append(f"symmetry:{symmetry_axis}")
        if non_newtonian:
            active_features.append("non_newtonian")
        if free_surface:
            active_features.append("free_surface")
        if thermal:
            active_features.append("thermal")
        if outlet_type != "fixed_rho":
            active_features.append(f"outlet:{outlet_type}")
        if mode_2d:
            active_features.append("2d_mode")
        if stl_configs and len(stl_configs) > 1:
            active_features.append(f"multi_stl({len(stl_configs)} objects)")

        return {
            "success": True,
            "case_name": case_name,
            "data": {
                "setup_file": setup_path,
                "resolution": f"{resolution_x}x{resolution_y}x{resolution_z}",
                "cells": resolution_x * resolution_y * resolution_z,
                "Re_estimate": round(Re, 1),
                "lbm_nu": round(lbm_nu, 6),
                "lbm_velocity": round(lbm_velocity, 4),
                "stl_file_name": stl_file_name,
                "features": active_features,
                "defines": enabled_defines,
            },
        }

    # ── cfd_fluidx3d_compile ────────────────────────────────────────────

    @mcp.tool()
    async def cfd_fluidx3d_compile(
        case_name: Annotated[str, Field(description="Case directory name.")],
        opencl_lib: Annotated[str, Field(description="OpenCL library path hint (auto-detected if empty).")] = "",
    ) -> dict:
        """Compile a FluidX3D case into an executable binary.

        Copies the generated setup.cpp and defines.hpp into the FluidX3D
        source tree, then compiles with g++ (Linux/Mac/WSL) or MSVC (Windows).
        Requires FluidX3D cloned locally and a C++ compiler.

        ## Return Format
        {"success": bool, "case_name": str, "data": {"binary": str, "compiler": str, "compile_time_s": float}}

        ## Examples
        await cfd_fluidx3d_compile(case_name="pipe_gpu")
        """
        f3d_path = _find_fluidx3d()
        if not f3d_path:
            return {"success": False, "error": "FluidX3D not found. Clone: git clone https://github.com/ProjectPhysX/FluidX3D.git"}

        compiler = _find_compiler()
        if not compiler:
            return {"success": False, "error": "No C++ compiler found. Install g++ (MinGW/WSL/Linux) or Visual Studio with MSVC."}

        case_dir = os.path.join(F3D_CASE_DIR, case_name)
        if not os.path.isdir(case_dir):
            return {"success": False, "error": f"Case '{case_name}' not found. Run cfd_fluidx3d_setup first."}

        setup_src = os.path.join(case_dir, "setup.cpp")
        defines_src = os.path.join(case_dir, "defines.hpp")
        if not os.path.isfile(setup_src):
            return {"success": False, "error": f"setup.cpp not found in case '{case_name}'. Run cfd_fluidx3d_setup first."}

        # Copy setup into FluidX3D source tree
        f3d_src = os.path.join(f3d_path, "src")
        if not os.path.isdir(f3d_src):
            return {"success": False, "error": f"FluidX3D src/ not found at {f3d_src}. Is FluidX3D cloned correctly?"}

        shutil.copy(setup_src, os.path.join(f3d_src, "setup.cpp"))
        shutil.copy(defines_src, os.path.join(f3d_src, "defines.hpp"))

        # Build binary path
        bin_dir = os.path.join(case_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        binary_name = f"fluidx3d_{case_name}" + (".exe" if os.name == "nt" else "")
        binary_path = os.path.join(bin_dir, binary_name)

        # Find all source files
        cpp_files = [os.path.join(f3d_src, f) for f in os.listdir(f3d_src) if f.endswith((".cpp", ".c"))]
        if not cpp_files:
            return {"success": False, "error": f"No C++ source files found in {f3d_src}"}

        import time
        t0 = time.time()
        compile_timeout = int(os.environ.get("FREECAD_F3D_COMPILE_TIMEOUT_S", "300"))
        opencl_inc, opencl_lib = _opencl_paths(f3d_path)
        stdout_text = ""
        stderr_text = ""

        if compiler == "msvc":
            vcvars = _find_vs_vcvars64()
            if not vcvars:
                return {"success": False, "error": "MSVC vcvars64.bat not found. Install VS Build Tools C++ workload."}
            vcxproj = os.path.join(f3d_path, "FluidX3D.vcxproj")
            if not os.path.isfile(vcxproj):
                return {"success": False, "error": f"FluidX3D.vcxproj not found at {vcxproj}"}
            built_exe = os.path.join(f3d_path, "bin", "FluidX3D.exe")
            cmd = (
                f'call "{vcvars}" >nul && msbuild "{vcxproj}" /nologo '
                f"/p:Configuration=Release /p:Platform=x64 /m"
            )
            try:
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    cwd=f3d_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=compile_timeout)
                stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
                stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""
                if proc.returncode == 0 and os.path.isfile(built_exe):
                    shutil.copy2(built_exe, binary_path)
                elif proc.returncode == 0 and not os.path.isfile(binary_path):
                    proc.returncode = 1
                    stderr_text = (stderr_text + "\n" if stderr_text else "") + f"Expected binary missing: {built_exe}"
            except TimeoutError:
                return {"success": False, "error": f"MSBuild compilation timed out after {compile_timeout}s"}
        elif "g++" in compiler or "clang" in compiler:
            src_list = [os.path.join(f3d_src, f) for f in os.listdir(f3d_src) if f.endswith((".cpp", ".c"))]
            cmd = [
                compiler,
                "-std=c++17",
                "-O3",
                "-pthread",
                "-Wno-comment",
                f"-I{opencl_inc}",
                f"-L{opencl_lib}",
                "-o",
                binary_path,
                *src_list,
                "-lOpenCL",
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=f3d_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=compile_timeout)
                stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
                stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""
            except TimeoutError:
                return {"success": False, "error": f"g++ compilation timed out after {compile_timeout}s"}
        else:
            return {"success": False, "error": f"Unsupported compiler: {compiler}"}

        dt = time.time() - t0
        compile_log = (stdout_text + "\n" + stderr_text).strip()

        if proc.returncode != 0 or not os.path.isfile(binary_path):
            return {
                "success": False,
                "error": f"Compilation failed (exit {proc.returncode})",
                "data": {
                    "compiler": compiler,
                    "stderr": compile_log[-8000:],
                    "binary_expected": binary_path,
                },
            }

        return {
            "success": True,
            "case_name": case_name,
            "data": {
                "binary": binary_path,
                "compiler": compiler,
                "compile_time_s": round(dt, 2),
                "warnings": stderr_text[:2000] if stderr_text else "",
            },
        }

    # ── cfd_fluidx3d_run ────────────────────────────────────────────────

    @mcp.tool()
    async def cfd_fluidx3d_run(
        case_name: Annotated[str, Field(description="Case directory name.")],
        gpu_device: Annotated[str, Field(description="OpenCL GPU device index (0 = auto) or device name substring for multi-GPU selection.")] = "0",
        timeout_s: Annotated[int, Field(description="Maximum runtime in seconds.", ge=10)] = 3600,
    ) -> dict:
        """Run a compiled FluidX3D simulation on the GPU.

        Executes the binary compiled by cfd_fluidx3d_compile. The simulation
        runs entirely on GPU via OpenCL. Captures stdout for force/residual
        parsing by cfd_fluidx3d_results.

        Use gpu_device="0" for auto-selection (default). For multi-GPU
        systems, pass a device name substring (e.g. "RTX 4090", "Arc A770")
        or the numeric index as a string.

        VTK output files are written to the FluidX3D binary's export directory
        (bin/export/). These can be loaded in ParaView for post-processing.

        ## Return Format
        {"success": bool, "case_name": str, "data": {"exit_code": int, "output": str, "runtime_s": float, "vtk_files": list, "gpu_device_used": str}}

        ## Examples
        await cfd_fluidx3d_run(case_name="pipe_gpu")
        await cfd_fluidx3d_run(case_name="airfoil_gpu", gpu_device="NVIDIA", timeout_s=7200)
        """
        case_dir = os.path.join(F3D_CASE_DIR, case_name)
        if not os.path.isdir(case_dir):
            return {"success": False, "error": f"Case '{case_name}' not found."}

        f3d_path = _find_fluidx3d()
        binary_name = f"fluidx3d_{case_name}" + (".exe" if os.name == "nt" else "")
        binary_path = os.path.join(case_dir, "bin", binary_name)

        prebuilt_used = False
        if not os.path.isfile(binary_path):
            prebuilt = _find_prebuilt(F3D_CASE_DIR, f3d_path)
            if prebuilt and f3d_path:
                setup_src = os.path.join(case_dir, "setup.cpp")
                defines_src = os.path.join(case_dir, "defines.hpp")
                f3d_src = os.path.join(f3d_path, "src")
                if os.path.isfile(setup_src) and os.path.isdir(f3d_src):
                    shutil.copy(setup_src, os.path.join(f3d_src, "setup.cpp"))
                    shutil.copy(defines_src, os.path.join(f3d_src, "defines.hpp"))
                    os.makedirs(os.path.join(case_dir, "bin"), exist_ok=True)
                    shutil.copy(prebuilt, binary_path)
                    os.chmod(binary_path, 0o755)  # noqa: S103
                    prebuilt_used = True
                else:
                    return {
                        "success": False,
                        "error": f"Binary not found at {binary_path} and cannot stage setup.cpp. Run cfd_fluidx3d_compile first.",
                    }
            else:
                return {
                    "success": False,
                    "error": f"Binary not found at {binary_path}. Run cfd_fluidx3d_compile first.",
                }

        # Resolve GPU device index
        gpu_index = 0
        gpu_device_used = gpu_device
        try:
            gpu_index = int(gpu_device)
        except ValueError:
            # Substring match against available devices
            gpu_devices = _query_gpu_devices()
            for i, dev in enumerate(gpu_devices):
                if gpu_device.lower() in dev.get("device", "").lower():
                    gpu_index = i
                    gpu_device_used = f"{i} ({dev['device']})"
                    break

        import time
        t0 = time.time()
        log_path = os.path.join(case_dir, "run.log")
        proc: asyncio.subprocess.Process | None = None

        try:
            with open(log_path, "wb") as log_file:
                proc = await asyncio.create_subprocess_exec(
                    binary_path,
                    str(gpu_index),
                    stdout=log_file,
                    stderr=asyncio.subprocess.STDOUT,
                    stdin=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(proc.wait(), timeout=timeout_s)
        except TimeoutError:
            if proc is not None and proc.returncode is None:
                proc.kill()
                await proc.wait()
            return {
                "success": False,
                "error": f"Simulation timed out after {timeout_s}s",
                "data": {"exit_code": -1, "log_file": log_path},
            }

        dt = time.time() - t0
        out_text = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as f:
                out_text = f.read()
        err_text = ""

        # Find VTK files
        vtk_files = []
        for root, dirs, files in os.walk(case_dir):
            for fn in files:
                if fn.endswith(".vtk"):
                    vtk_files.append(os.path.join(root, fn))
        # Also check FluidX3D export directory
        f3d_path = _find_fluidx3d()
        if f3d_path:
            export_dir = os.path.join(f3d_path, "bin", "export")
            if os.path.isdir(export_dir):
                for fn in os.listdir(export_dir):
                    if fn.endswith(".vtk"):
                        vtk_files.append(os.path.join(export_dir, fn))

        return {
            "success": proc is not None and proc.returncode == 0,
            "case_name": case_name,
            "data": {
                "exit_code": proc.returncode if proc is not None else -1,
                "output": out_text[-10000:],
                "stderr": err_text[-2000:] if err_text else "",
                "runtime_s": round(dt, 2),
                "vtk_files": vtk_files[:50],
                "log_file": log_path,
                "prebuilt_used": prebuilt_used,
                "gpu_device_used": gpu_device_used,
            },
        }

    # ── cfd_fluidx3d_results ────────────────────────────────────────────

    @mcp.tool(annotations=_README_ONLY)
    async def cfd_fluidx3d_results(
        case_name: Annotated[str, Field(description="Case directory name.")],
    ) -> dict:
        """Parse FluidX3D simulation results from the run log.

        Extracts forces, per-object forces (for multi-STL cases), throughput
        (MLUPS), time step history, and whether the simulation completed.

        ## Return Format
        {"success": bool, "case_name": str, "data": {"forces": list, "object_forces": list, "final_forces": {"Fx": float, "Fy": float, "Fz": float}, "mlups": float, "time_steps": int, "completed": bool}}

        ## Examples
        await cfd_fluidx3d_results(case_name="pipe_gpu")
        """
        case_dir = os.path.join(F3D_CASE_DIR, case_name)
        if not os.path.isdir(case_dir):
            return {"success": False, "error": f"Case '{case_name}' not found."}

        log_path = os.path.join(case_dir, "run.log")
        if not os.path.isfile(log_path):
            return {"success": False, "error": "No run log found. Run cfd_fluidx3d_run first."}

        with open(log_path) as f:
            content = f.read()

        # Parse STEP lines: "STEP <N> F <Fx> <Fy> <Fz>"
        forces = []
        for match in re.finditer(r"STEP (\d+) F ([\d.e+\-]+) ([\d.e+\-]+) ([\d.e+\-]+)", content):
            forces.append({
                "step": int(match.group(1)),
                "Fx": float(match.group(2)),
                "Fy": float(match.group(3)),
                "Fz": float(match.group(4)),
            })

        # Parse OBJ_FORCE lines: "OBJ_FORCE <idx> Fx:<Fx> Fy:<Fy> Fz:<Fz>"
        object_forces = []
        for match in re.finditer(r"OBJ_FORCE (\d+) Fx:([\d.e+\-]+) Fy:([\d.e+\-]+) Fz:([\d.e+\-]+)", content):
            object_forces.append({
                "object_index": int(match.group(1)),
                "Fx": float(match.group(2)),
                "Fy": float(match.group(3)),
                "Fz": float(match.group(4)),
            })

        # Parse DONE line
        done_match = re.search(
            r"DONE steps:(\d+) time:([\d.eE+\-]+)s mlups:([\d.eE+\-]+)",
            content,
        )
        completed = done_match is not None
        total_steps = int(done_match.group(1)) if done_match else 0
        runtime = float(done_match.group(2)) if done_match else 0
        mlups = float(done_match.group(3)) if done_match else 0

        # Parse final FORCES line
        final_forces = {"Fx": 0.0, "Fy": 0.0, "Fz": 0.0}
        force_match = re.search(r"FORCES ([\d.e+\-]+) ([\d.e+\-]+) ([\d.e+\-]+)", content)
        if force_match:
            final_forces = {
                "Fx": float(force_match.group(1)),
                "Fy": float(force_match.group(2)),
                "Fz": float(force_match.group(3)),
            }

        # Load config for context
        cfg = {}
        cfg_path = os.path.join(case_dir, ".f3d_config.json")
        if os.path.isfile(cfg_path):
            with open(cfg_path) as f:
                cfg = json.load(f)

        return {
            "success": True,
            "case_name": case_name,
            "data": {
                "forces": forces[-100:],
                "force_count": len(forces),
                "object_forces": object_forces,
                "object_force_count": len(object_forces),
                "final_forces": final_forces,
                "mlups": round(mlups, 2),
                "mlups_unit": "Million Lattice Updates Per Second",
                "time_steps_completed": total_steps,
                "runtime_s": round(runtime, 2),
                "completed": completed,
                "config": cfg,
            },
        }

    # ── cfd_fluidx3d_explain ─────────────────────────────────────────────

    @mcp.tool(annotations=_README_ONLY)
    async def cfd_fluidx3d_explain(
        case_name: Annotated[str, Field(description="Case directory name.")],
    ) -> dict:
        """Explain what a FluidX3D simulation would compute and how to interpret results.

        Reads the stored config and provides a human-readable summary of the
        flow physics, expected Reynolds number, and what the forces mean.

        ## Return Format
        {"success": bool, "case_name": str, "data": {"summary": str, "Re": float, "regime": str, "solver_notes": str}}

        ## Examples
        await cfd_fluidx3d_explain(case_name="pipe_gpu")
        """
        cfg_path = os.path.join(F3D_CASE_DIR, case_name, ".f3d_config.json")
        if not os.path.isfile(cfg_path):
            return {"success": False, "error": f"Case '{case_name}' not found or no config saved."}

        with open(cfg_path) as f:
            cfg = json.load(f)

        v = cfg.get("si_velocity", 0)
        L = cfg.get("si_length", 0)
        nu = cfg.get("si_viscosity", 0)
        Re = v * L / nu if nu > 0 else 0
        res = cfg.get("resolution", [0, 0, 0])
        cells = res[0] * res[1] * res[2]
        domain = cfg.get("domain_type", "unknown")

        if Re < 1:
            regime = "creeping/stokes flow -- viscous forces dominate, linear flow"
        elif Re < 2300:
            regime = "laminar -- smooth streamlines, predictable, no turbulent mixing"
        elif Re < 10000:
            regime = "transitional -- intermittent turbulence, sensitive to perturbations"
        else:
            regime = "turbulent -- chaotic eddies, enhanced mixing, subgrid model active"

        if domain == "pipe":
            if Re < 2300:
                regime += ". Darcy friction factor f ~ 64/Re."
            else:
                regime += ". Blasius: f ~ 0.316/Re^0.25 (smooth pipe)."

        # Feature summary
        feature_notes = ""
        if cfg.get("non_newtonian"):
            feature_notes += " Non-Newtonian (power-law) viscosity active."
        if cfg.get("free_surface"):
            feature_notes += f" Free-surface LBM with fill fraction {cfg.get('fill_fraction', 0.5)}."
        if cfg.get("thermal"):
            feature_notes += f" Thermal LBM with beta={cfg.get('beta', 0)}."

        summary = (
            f"FluidX3D GPU simulation of {domain} flow. "
            f"{cells:,} cells on a {res[0]}x{res[1]}x{res[2]} grid. "
            f"Inlet velocity {v} m/s, domain length {L} m, "
            f"kinematic viscosity {nu:.2e} m/s. "
            f"Reynolds number Re = {Re:,.1f} -- {regime} "
            f"FluidX3D uses the lattice-Boltzmann method (LBM) with "
            f"D3Q19 velocity set and single-relaxation-time (SRT/BGK) collision. "
            f"The Smagorinsky-Lilly subgrid model handles turbulence at high Re."
            f"{feature_notes}"
        )

        solver_notes = (
            "LBM is an explicit solver -- time steps are small (~10^-5 s in SI) "
            "but throughput is high (100s of MLUPS on GPU). "
            "Forces are summed over all solid boundary cells marked TYPE_S|TYPE_X. "
            "VTK output files contain volumetric velocity and density fields "
            "for post-processing in ParaView or further ML analysis."
        )

        return {
            "success": True,
            "case_name": case_name,
            "data": {
                "summary": summary,
                "Re": round(Re, 1),
                "regime": regime,
                "solver_notes": solver_notes,
            },
        }

    # ── cfd_fluidx3d_export_for_render ─────────────────────────────────

    @mcp.tool()
    async def cfd_fluidx3d_export_for_render(
        case_name: Annotated[str, Field(description="Case directory name.")] = "",
        n_streamlines: Annotated[int, Field(description="Number of streamlines to trace.", ge=2)] = 20,
        streamline_length: Annotated[int, Field(description="Steps per streamline.", ge=10)] = 100,
        step_size: Annotated[float, Field(description="Integration step in grid units.", ge=0.001)] = 0.5,
        export_csv: Annotated[bool, Field(description="Also export velocity point cloud CSV.")] = False,
    ) -> dict:
        """Export FluidX3D simulation results for 3D rendering.

        Reads the VTK velocity field output and generates:
        1. OBJ file with streamlines (polylines) — importable into
           Unity3D, Resonite, Blender, and any 3D tool
        2. Optional CSV with velocity point cloud for custom shader workflows

        This bridges CFD simulation to virtual world visualization:
        streamlines show the flow field as 3D curves that can be
        rendered, animated, or used as path-following guides for
        virtual bots (vbots) in game engines.

        ## Return Format
        {"success": bool, "data": {"streamline_obj": str, "csv_file": str|null, "n_streamlines": int, "bbox": {...}}}

        ## Examples
        await cfd_fluidx3d_export_for_render(case_name="pipe_gpu")
        await cfd_fluidx3d_export_for_render(case_name="river_flow", n_streamlines=50, export_csv=True)
        """
        case_dir = os.path.join(F3D_CASE_DIR, case_name)
        if not os.path.isdir(case_dir):
            return {"success": False, "error": f"Case '{case_name}' not found."}

        # Find latest VTK file
        vtk_files = []
        for root, _dirs, files in os.walk(case_dir):
            for fn in files:
                if fn.endswith(".vtk"):
                    vtk_files.append(os.path.join(root, fn))
        f3d_path = _find_fluidx3d()
        if f3d_path:
            export_dir = os.path.join(f3d_path, "bin", "export")
            if os.path.isdir(export_dir):
                for fn in os.listdir(export_dir):
                    if fn.endswith(".vtk"):
                        vtk_files.append(os.path.join(export_dir, fn))

        if not vtk_files:
            return {"success": False, "error": f"No VTK files found for case '{case_name}'. Run cfd_fluidx3d_run first."}

        # Use velocity VTK (FluidX3D writes u-*.vtk with SCALARS data float 3)
        vtk_path = _pick_velocity_vtk(vtk_files)
        if not vtk_path:
            return {"success": False, "error": f"No VTK files found for case '{case_name}'. Run cfd_fluidx3d_run first."}
        vtk_name = os.path.basename(vtk_path)

        # Parse VTK structured grid velocity field
        try:
            with open(vtk_path, "rb") as f:
                header = f.read(4096).decode("latin-1", errors="replace")

            # Parse dimensions and velocity data
            dim_match = re.search(r"DIMENSIONS\s+(\d+)\s+(\d+)\s+(\d+)", header)
            origin_match = re.search(r"ORIGIN\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)", header)
            space_match = re.search(r"SPACING\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)", header)

            if not dim_match:
                return {"success": False, "error": "Cannot parse VTK dimensions. Is this a structured grid?"}

            Nx, Ny, Nz = int(dim_match.group(1)), int(dim_match.group(2)), int(dim_match.group(3))
            ox = float(origin_match.group(1)) if origin_match else 0.0
            oy = float(origin_match.group(2)) if origin_match else 0.0
            oz = float(origin_match.group(3)) if origin_match else 0.0
            sx = float(space_match.group(1)) if space_match else 1.0
            sy = float(space_match.group(2)) if space_match else 1.0
            sz = float(space_match.group(3)) if space_match else 1.0

            # Read velocity binary data after headers
            content = open(vtk_path, "rb").read()
            vel_start = content.find(b"VECTORS")
            if vel_start < 0:
                vel_start = content.find(b"SCALARS")
            if vel_start < 0:
                return {"success": False, "error": "VTK has no velocity field (VECTORS/SCALARS)."}

            data_start = _vtk_velocity_data_offset(content, vel_start)

            import struct
            total_cells = Nx * Ny * Nz
            try:
                raw = content[data_start:data_start + total_cells * 3 * 4]
                if len(raw) < total_cells * 3 * 4:
                    text = content[data_start:].decode("latin-1", errors="replace")
                    values = [float(x) for x in text.split()[: total_cells * 3]]
                else:
                    # FluidX3D writes binary VTK as big-endian floats
                    values = list(struct.unpack(f">{total_cells * 3}f", raw))
            except Exception:
                # Best-effort ASCII fallback
                text = content[data_start:].decode("latin-1", errors="replace")
                values = [float(x) for x in text.split()[:total_cells * 3]]

            if len(values) < total_cells * 3:
                return {"success": False, "error": f"Incomplete velocity data: got {len(values)} values, need {total_cells * 3}"}

            # Build velocity grid
            vx = values[0::3]
            vy = values[1::3]
            vz = values[2::3]

            def cell_index(x: int, y: int, z: int) -> int:
                return x + (y + z * Ny) * Nx

            def get_vel(x: int, y: int, z: int) -> tuple[float, float, float]:
                idx = cell_index(x, y, z)
                return (
                    vx[idx] if idx < len(vx) else 0.0,
                    vy[idx] if idx < len(vy) else 0.0,
                    vz[idx] if idx < len(vz) else 0.0,
                )

            # Generate streamlines via Euler integration
            objs = []
            csv_lines = ["x,y,z,vx,vy,vz"] if export_csv else []
            bbox_min = [1e30, 1e30, 1e30]
            bbox_max = [-1e30, -1e30, -1e30]

            for sl in range(n_streamlines):
                # Seed at inlet face (x=0) with uniform distribution
                seed_y = int((Ny * 0.1) + (sl * Ny * 0.8) / max(1, n_streamlines - 1))
                seed_z = int(Nz * 0.5)

                cx, cy, cz = 0.5, float(seed_y) + 0.5, float(seed_z) + 0.5
                streamline_pts = []
                for step in range(streamline_length):
                    ix, iy, iz = int(cx), int(cy), int(cz)
                    ix = max(0, min(Nx - 2, ix))
                    iy = max(0, min(Ny - 2, iy))
                    iz = max(0, min(Nz - 2, iz))

                    # Trilinear interpolation
                    def interp(fx: float, fy: float, fz: float, field: list[float]) -> float:
                        d000 = field[cell_index(ix, iy, iz)]
                        d100 = field[cell_index(ix + 1, iy, iz)]
                        d010 = field[cell_index(ix, iy + 1, iz)]
                        d110 = field[cell_index(ix + 1, iy + 1, iz)]
                        d001 = field[cell_index(ix, iy, iz + 1)] if iz + 1 < Nz else d000
                        d101 = field[cell_index(ix + 1, iy, iz + 1)] if iz + 1 < Nz else d100
                        d011 = field[cell_index(ix, iy + 1, iz + 1)] if iz + 1 < Nz else d010
                        d111 = field[cell_index(ix + 1, iy + 1, iz + 1)] if iz + 1 < Nz else d110
                        c00 = d000 * (1 - fx) + d100 * fx
                        c10 = d010 * (1 - fx) + d110 * fx
                        c01 = d001 * (1 - fx) + d101 * fx
                        c11 = d011 * (1 - fx) + d111 * fx
                        c0 = c00 * (1 - fy) + c10 * fy
                        c1 = c01 * (1 - fy) + c11 * fy
                        return c0 * (1 - fz) + c1 * fz

                    fx, fy, fz = cx - float(ix), cy - float(iy), cz - float(iz)
                    u = interp(fx, fy, fz, vx)
                    v = interp(fx, fy, fz, vy)
                    w = interp(fx, fy, fz, vz)
                    mag = (u * u + v * v + w * w) ** 0.5
                    if mag < 1e-12:
                        break
                    u, v, w = u / mag * step_size, v / mag * step_size, w / mag * step_size
                    cx += u
                    cy += v
                    cz += w
                    if cx < 0 or cx >= Nx or cy < 0 or cy >= Ny or cz < 0 or cz >= Nz:
                        break

                    wx = ox + cx * sx
                    wy = oy + cy * sy
                    wz = oz + cz * sz
                    streamline_pts.append((wx, wy, wz))
                    bbox_min[0] = min(bbox_min[0], wx)
                    bbox_min[1] = min(bbox_min[1], wy)
                    bbox_min[2] = min(bbox_min[2], wz)
                    bbox_max[0] = max(bbox_max[0], wx)
                    bbox_max[1] = max(bbox_max[1], wy)
                    bbox_max[2] = max(bbox_max[2], wz)

                    if export_csv:
                        vlx, vly, vlz = mag * u / step_size, mag * v / step_size, mag * w / step_size
                        csv_lines.append(f"{wx},{wy},{wz},{vlx:.6f},{vly:.6f},{vlz:.6f}")

                if len(streamline_pts) >= 2:
                    obj_path = os.path.join(case_dir, f"streamline_{sl}.obj")
                    with open(obj_path, "w") as f:
                        f.write(f"# FluidX3D streamline {sl} — case {case_name}\n")
                        f.write(f"# {len(streamline_pts)} points\n")
                        for pt in streamline_pts:
                            f.write(f"v {pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f}\n")
                        for i in range(len(streamline_pts) - 1):
                            f.write(f"l {i + 1} {i + 2}\n")
                    objs.append(obj_path)

            if not objs:
                return {"success": False, "error": "No streamlines generated — check domain size or velocity field."}

            # Write merged OBJ
            merged_path = os.path.join(case_dir, f"{case_name}_streamlines.obj")
            with open(merged_path, "w") as fout:
                fout.write(f"# FluidX3D streamlines — case {case_name}\n")
                fout.write(f"# {n_streamlines} streamlines, VTK: {vtk_name}\n")
                vertex_offset = 0
                for obj in objs:
                    with open(obj) as fin:
                        for line in fin:
                            if line.startswith("v "):
                                fout.write(line)
                            elif line.startswith("l "):
                                parts = line.strip().split()
                                fout.write(f"l {int(parts[1]) + vertex_offset} {int(parts[2]) + vertex_offset}\n")
                    vertex_offset += sum(1 for _ in open(obj)) - len([ln for ln in open(obj) if ln.startswith("l ")]) - 1

            csv_path = None
            if export_csv:
                csv_path = os.path.join(case_dir, f"{case_name}_velocity.csv")
                with open(csv_path, "w") as f:
                    f.write("\n".join(csv_lines))

            return {
                "success": True,
                "case_name": case_name,
                "data": {
                    "streamline_obj": merged_path,
                    "obj_filename": os.path.basename(merged_path),
                    "csv_file": csv_path,
                    "n_streamlines": len(objs),
                    "vtk_source": vtk_name,
                    "bbox": {
                        "xmin": bbox_min[0], "ymin": bbox_min[1], "zmin": bbox_min[2],
                        "xmax": bbox_max[0], "ymax": bbox_max[1], "zmax": bbox_max[2],
                    },
                },
            }
        except Exception as e:
            logger.exception("Export for render failed")
            return {"success": False, "error": f"Export failed: {e}"}

    logger.info(
        "FluidX3D tools registered: cfd_fluidx3d_status, cfd_fluidx3d_prebuilt, cfd_fluidx3d_setup, cfd_fluidx3d_compile, "
        "cfd_fluidx3d_run, cfd_fluidx3d_results, cfd_fluidx3d_explain, cfd_fluidx3d_export_for_render"
    )

    return {
        "cfd_fluidx3d_status": cfd_fluidx3d_status,
        "cfd_fluidx3d_prebuilt": cfd_fluidx3d_prebuilt,
        "cfd_fluidx3d_setup": cfd_fluidx3d_setup,
        "cfd_fluidx3d_compile": cfd_fluidx3d_compile,
        "cfd_fluidx3d_run": cfd_fluidx3d_run,
        "cfd_fluidx3d_results": cfd_fluidx3d_results,
        "cfd_fluidx3d_explain": cfd_fluidx3d_explain,
        "cfd_fluidx3d_export_for_render": cfd_fluidx3d_export_for_render,
    }
