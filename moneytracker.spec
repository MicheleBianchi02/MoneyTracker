# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec file for MoneyTracker
#
# Build with:   ./build.sh
# Or manually:  pyinstaller moneytracker.spec
#
# Output:  dist/moneytracker/moneytracker   (the executable)
#          dist/moneytracker/_internal/     (bundled runtime)

a = Analysis(
    # Entry point — equivalent to: python -m moneytracker.api.main
    ["src/moneytracker/api/main.py"],
    # Add src/ to the path so the `moneytracker` package is found
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=[
        # ── uvicorn ─────────────────────────────────────────────────────────
        # Uvicorn selects its event loop, protocol, and lifespan handlers via
        # string-based dynamic imports that PyInstaller cannot auto-detect.
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.off",
        "uvicorn.lifespan.on",
        # ── FastAPI / Starlette ──────────────────────────────────────────────
        "starlette.routing",
        "starlette.middleware",
        "starlette.middleware.cors",
        "fastapi.security",
        "fastapi.security.oauth2",
        # ── anyio (async backend used by Starlette) ──────────────────────────
        "anyio._backends._asyncio",
        # ── jose / JWT (used by fastapi security helpers if present) ─────────
        # Uncomment if you add python-jose or python-multipart as a dep:
        # "jose",
        # "multipart",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Trim test frameworks from the bundle — they are not needed at runtime
    excludes=["pytest", "unittest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir mode: binaries go into COLLECT below
    name="moneytracker",
    debug=False,
    bootloader_ignore_signals=False,
    # strip=False keeps .so files intact; stripping can break them on Linux
    strip=False,
    # upx=False avoids rare decompression failures on some Linux distros
    upx=False,
    console=True,   # must be True — this is a TUI / CLI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="moneytracker",
)
