# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata

datas = [("src/freecad_mcp", "freecad_mcp")]
for pkg in ("fastmcp", "fastapi", "uvicorn", "pydantic", "starlette", "httpx", "prefab_ui"):
    datas += copy_metadata(pkg)

a = Analysis(
    ["run_server.py"],
    pathex=["src"],
    binaries=[],
    
    datas=datas,
    hiddenimports=[

    "_datetime",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "prefab_ui.app",
        "prefab_ui.components",
        "freecad_mcp.tools",
    "_strptime",
],
    hookspath=[],
    
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'setuptools', 'pip', 'wheel', 'test', 'tests', 'unittest'],
    noarchive=True,
    optimize=0,
)
SKIP = ['torch', 'playwright', 'bitsandbytes', 'llvmlite', 'pyarrow', 'pymupdf', 'grpc',
        'numba', 'Cython', 'google', 'azure', 'boto3', 'botocore', 'matplotlib', 'PIL',
        'pandas', 'scipy', 'sklearn', 'onnxruntime']
a.binaries = [b for b in a.binaries if not any(s in b[0].lower() for s in SKIP)]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="freecad-mcp-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)





