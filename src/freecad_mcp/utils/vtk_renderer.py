"""
Lightweight VTK structured-points reader and video renderer.

Reads FluidX3D VTK velocity field output, renders 2D slices as
heatmap PNGs, and stitches them into a WebM video via ffmpeg.

No external deps beyond stdlib + Pillow (PIL).
"""

import os
import re
import struct
import subprocess
from pathlib import Path

try:
    from PIL import Image, ImageDraw

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def _find_ffmpeg() -> str | None:
    """Locate ffmpeg executable on PATH or known install paths."""
    candidates = [
        "ffmpeg",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        str(Path.home() / "scoop" / "shims" / "ffmpeg.exe"),
        str(Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe"),
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
    ]
    for c in candidates:
        if not c:
            continue
        try:
            r = subprocess.run([c, "-version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return c
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


_WARNED_FFMPEG = False


def _ensure_ffmpeg(install: bool = True) -> tuple[str | None, str]:
    """Find or auto-install ffmpeg.

    Returns (path_or_none, message) where message is a user-facing string
    with remediation instructions if installation fails.
    """
    global _WARNED_FFMPEG
    existing = _find_ffmpeg()
    if existing:
        return existing, ""

    if not install:
        return None, "ffmpeg not found. Install with: winget install ffmpeg"

    # Auto-install via winget (Windows)
    if os.name == "nt":
        try:
            r = subprocess.run(
                ["winget", "install", "ffmpeg", "--accept-package-agreements", "--silent"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if r.returncode == 0:
                found = _find_ffmpeg()
                if found:
                    return found, ""
                # winget may need PATH refresh
                os.environ["PATH"] = os.pathsep.join(
                    filter(
                        None,
                        [
                            os.environ.get("PATH", ""),
                            str(Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links"),
                        ],
                    )
                )
                found = _find_ffmpeg()
                if found:
                    return found, ""
                return (
                    None,
                    "ffmpeg: winget install completed but binary not on PATH. Restart your terminal or add WinGet\\Links to PATH manually.",
                )
            return None, (f"ffmpeg: winget install failed (exit {r.returncode}). Manual fix: winget install ffmpeg")
        except FileNotFoundError:
            if not _WARNED_FFMPEG:
                _WARNED_FFMPEG = True
            return None, (
                "ffmpeg: winget not available. Install manually:\n"
                "  Option A: winget install ffmpeg  (if winget is available)\n"
                "  Option B: choco install ffmpeg    (Chocolatey)\n"
                "  Option C: scoop install ffmpeg    (Scoop)\n"
                "  Option D: Download from https://ffmpeg.org/download.html\n"
                "    Extract to a folder and add to PATH."
            )
        except subprocess.TimeoutExpired:
            return (
                None,
                "ffmpeg: winget install timed out. Check your internet connection and try: winget install ffmpeg",
            )

    # macOS / Linux
    for pm, cmd in [("brew", ["brew", "install", "ffmpeg"]), ("apt", ["sudo", "apt", "install", "-y", "ffmpeg"])]:
        try:
            r = subprocess.run(["which", pm], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                r2 = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if r2.returncode == 0 and _find_ffmpeg():
                    return _find_ffmpeg(), ""
                return None, f"{pm} install ffmpeg completed but binary not found. Try: {pm} install ffmpeg"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    return None, (
        "ffmpeg not found and could not be auto-installed.\n"
        "Install manually:\n"
        "  Windows: winget install ffmpeg\n"
        "  macOS:   brew install ffmpeg\n"
        "  Linux:   sudo apt install ffmpeg\n"
        "  Or download from https://ffmpeg.org/download.html"
    )


def parse_vtk_structured_points(path: str) -> dict:
    """Parse a legacy VTK structured points file.

    Returns dict with:
        dims: (nx, ny, nz)
        origin: (ox, oy, oz)
        spacing: (sx, sy, sz)
        velocity: list of (vx, vy, vz) tuples
        velocity_magnitude: list of floats
    """
    with open(path, "rb") as f:
        raw = f.read()

    header = raw[:4096].decode("latin-1", errors="replace")

    dim_match = re.search(r"DIMENSIONS\s+(\d+)\s+(\d+)\s+(\d+)", header)
    origin_match = re.search(r"ORIGIN\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)", header)
    space_match = re.search(r"SPACING\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)", header)

    if not dim_match:
        raise ValueError("Not a VTK structured points file")

    nx, ny, nz = int(dim_match.group(1)), int(dim_match.group(2)), int(dim_match.group(3))
    ox = float(origin_match.group(1)) if origin_match else 0.0
    oy = float(origin_match.group(2)) if origin_match else 0.0
    oz = float(origin_match.group(3)) if origin_match else 0.0
    sx = float(space_match.group(1)) if space_match else 1.0
    sy = float(space_match.group(2)) if space_match else 1.0
    sz = float(space_match.group(3)) if space_match else 1.0

    total_cells = nx * ny * nz

    # Find velocity data
    pos = raw.find(b"VECTORS")
    is_ascii = b"ASCII" in raw[:256]

    if pos < 0:
        raise ValueError("No VECTORS field found in VTK")

    # Find start of data (skip field name line)
    data_start = raw.find(b"\n", pos) + 1
    # Skip "float/double" keyword if present
    next_line_end = raw.find(b"\n", data_start)
    field_line = raw[data_start:next_line_end].decode("latin-1", errors="replace").strip()
    if field_line in ("float", "double"):
        data_start = next_line_end + 1

    values = []
    if is_ascii:
        text = raw[data_start:].decode("latin-1", errors="replace")
        tokens = text.split()
        for t in tokens[: total_cells * 3]:
            try:
                values.append(float(t))
            except ValueError:
                break
    else:
        raw_data = raw[data_start : data_start + total_cells * 3 * 4]
        if len(raw_data) >= total_cells * 3 * 4:
            values = list(struct.unpack(f">{total_cells * 3}f", raw_data[: total_cells * 3 * 4]))
        else:
            # Fallback to ASCII read
            text = raw[data_start:].decode("latin-1", errors="replace")
            tokens = text.split()
            for t in tokens[: total_cells * 3]:
                try:
                    values.append(float(t))
                except ValueError:
                    break

    if len(values) < total_cells * 3:
        raise ValueError(f"Incomplete velocity data: got {len(values)}, need {total_cells * 3}")

    velocities = [(values[i], values[i + 1], values[i + 2]) for i in range(0, len(values), 3)]
    vel_mag = [(vx**2 + vy**2 + vz**2) ** 0.5 for vx, vy, vz in velocities]

    return {
        "dims": (nx, ny, nz),
        "origin": (ox, oy, oz),
        "spacing": (sx, sy, sz),
        "velocity": velocities,
        "velocity_magnitude": vel_mag,
    }


def render_slice_png(
    data: dict,
    slice_z: int,
    output_path: str,
    width: int = 800,
    height: int = 600,
) -> str:
    """Render an XY slice at Z=slice_z as a velocity magnitude heatmap PNG.

    Uses turbo-like colormap: blue → cyan → green → yellow → red.
    """
    if not HAS_PIL:
        raise ImportError("Pillow required for PNG rendering")

    nx, ny, nz = data["dims"]
    vel_mag = data["velocity_magnitude"]

    if slice_z >= nz:
        slice_z = nz - 1

    # Extract slice data
    slice_data = []
    for iy in range(ny):
        for ix in range(nx):
            idx = ix + (iy + slice_z * ny) * nx
            slice_data.append(vel_mag[idx] if idx < len(vel_mag) else 0.0)

    if not slice_data:
        raise ValueError("Empty slice data")

    # Normalize
    vmin = min(slice_data)
    vmax = max(slice_data)
    span = vmax - vmin if vmax > vmin else 1.0

    # Turbo-like colormap: 5 stops
    def turbo(t):
        t = max(0.0, min(1.0, t))
        if t < 0.25:
            r, g, b = 0, t * 4, 1.0
        elif t < 0.5:
            r, g, b = 0, 1.0, 1.0 - (t - 0.25) * 4
        elif t < 0.75:
            r, g, b = (t - 0.5) * 4, 1.0, 0
        else:
            r, g, b = 1.0, 1.0 - (t - 0.75) * 4, 0
        return max(0, min(255, int(r * 255))), max(0, min(255, int(g * 255))), max(0, min(255, int(b * 255)))

    # Scale slice to output dimensions
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    scale_x = width / nx
    scale_y = height / ny

    for iy in range(ny):
        for ix in range(nx):
            idx = ix + iy * nx
            val = slice_data[idx]
            t = (val - vmin) / span
            color = turbo(t)
            x0 = int(ix * scale_x)
            y0 = int(iy * scale_y)
            x1 = int((ix + 1) * scale_x)
            y1 = int((iy + 1) * scale_y)
            draw.rectangle([x0, y0, x1, y1], fill=color)

    # Draw colorbar
    cbar_h = 20
    cbar_y = height - cbar_h - 10
    for i in range(width):
        t = i / width
        color = turbo(t)
        draw.rectangle([i, cbar_y, i + 1, cbar_y + cbar_h], fill=color)

    # Labels
    oz = data["origin"][2] + slice_z * data["spacing"][2]
    draw.text((5, 5), f"Z slice {slice_z} ({oz:.3f} m)", fill=(255, 255, 255))
    draw.text((5, cbar_y - 12), f"{vmin:.4f}", fill=(200, 200, 200))
    draw.text((width - 60, cbar_y - 12), f"{vmax:.4f}", fill=(200, 200, 200))

    img.save(output_path)
    return output_path


def render_video(
    case_dir: str,
    vtk_files: list[str],
    output_path: str,
    fps: int = 10,
    slice_axis: str = "z",
    quality: int = 23,
) -> dict:
    """Render VTK time series as a WebM video.

    Args:
        case_dir: Case directory for temp frames
        vtk_files: Sorted list of VTK file paths (time series)
        output_path: Output video path (should end in .webm or .mp4)
        fps: Frames per second
        slice_axis: 'x', 'y', or 'z' — which axis to slice
        quality: CRF quality (lower = better, 23 = good)

    Returns:
        dict with success, output_path, frame_count, duration_s
    """
    if not HAS_PIL:
        # Auto-install Pillow
        try:
            r = subprocess.run(["uv", "pip", "install", "Pillow"], capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                globals()["HAS_PIL"] = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        if not HAS_PIL:
            return {
                "success": False,
                "error": (
                    "Pillow (PIL) not installed. Auto-install failed.\n"
                    "Run: uv pip install Pillow\n"
                    "Or: pip install Pillow\n"
                    "This is a Python imaging library needed to render VTK frames to PNG."
                ),
            }

    ffmpeg, msg = _ensure_ffmpeg(install=True)
    if not ffmpeg:
        return {"success": False, "error": msg}

    frames_dir = os.path.join(case_dir, "_frames")
    os.makedirs(frames_dir, exist_ok=True)

    frame_paths = []
    for i, vtk_path in enumerate(vtk_files):
        try:
            data = parse_vtk_structured_points(vtk_path)
            nx, ny, nz = data["dims"]

            if slice_axis == "z":
                n_slices = nz
            elif slice_axis == "y":
                n_slices = ny
            else:
                n_slices = nx

            # Render middle slice
            slice_idx = n_slices // 2
            frame_path = os.path.join(frames_dir, f"frame_{i:04d}.png")
            render_slice_png(data, slice_idx, frame_path)
            frame_paths.append(frame_path)
        except Exception as e:
            import logging

            logging.getLogger("vtk_renderer").warning("Skip VTK %s: %s", vtk_path, e)

    if not frame_paths:
        return {"success": False, "error": "No frames rendered"}

    # Stitch with ffmpeg
    input_pattern = os.path.join(frames_dir, "frame_%04d.png")
    cmd = [
        ffmpeg,
        "-y",
        "-framerate",
        str(fps),
        "-i",
        input_pattern,
        "-c:v",
        "libvpx-vp9" if output_path.endswith(".webm") else "libx264",
        "-crf",
        str(quality),
        "-b:v",
        "0",
        "-pix_fmt",
        "yuv420p",
        output_path,
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return {"success": False, "error": f"ffmpeg failed: {r.stderr[:500]}"}
    except FileNotFoundError:
        return {"success": False, "error": "ffmpeg not found"}

    # Clean up frames
    for fp in frame_paths:
        try:
            os.remove(fp)
        except OSError:
            pass
    try:
        os.rmdir(frames_dir)
    except OSError:
        pass

    duration = len(frame_paths) / fps
    return {
        "success": True,
        "output_path": output_path,
        "frame_count": len(frame_paths),
        "duration_s": round(duration, 1),
    }
