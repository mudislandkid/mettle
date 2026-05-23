# PyInstaller spec for the Mettle desktop sidecar.
#
# Produces a single-file binary at dist/mettle-sidecar that Tauri spawns on
# launch. Build with:
#
#   pyinstaller --clean --noconfirm web/sidecar.spec
#
# The Tauri build copies the result to src-tauri/binaries/ and renames it
# per Tauri's target-triple convention.

# ruff: noqa: F821  - PyInstaller injects spec-time globals
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

REPO_ROOT = Path(SPECPATH).resolve().parent

block_cipher = None

hidden = []
# uvicorn + websockets + asyncio loop deps are dynamic.
hidden += collect_submodules("uvicorn")
hidden += collect_submodules("websockets")
hidden += collect_submodules("anyio")
hidden += collect_submodules("h11")
hidden += collect_submodules("httptools")
hidden += collect_submodules("uvloop")
# SQLAlchemy + alembic load dialects via importlib.
hidden += collect_submodules("sqlalchemy.dialects")
hidden += collect_submodules("sqlmodel")
hidden += collect_submodules("alembic")
# Mettle's own analyzers and metrics are imported by string in places.
hidden += collect_submodules("mettle")

# Some libraries (alembic, sqlalchemy) read their version via importlib.metadata.
datas = []
datas += copy_metadata("alembic")
datas += copy_metadata("sqlalchemy")
datas += copy_metadata("sqlmodel")
datas += copy_metadata("fastapi")
datas += copy_metadata("uvicorn")

# Bundle the alembic migrations + ini file at the bundle root so
# `%(here)s/alembic` in alembic.ini resolves correctly inside _MEIPASS.
datas += [
    (str(REPO_ROOT / "alembic.ini"), "."),
    (str(REPO_ROOT / "alembic"), "alembic"),
]

# Excluded for size: matplotlib + reportlab are only used by the CLI's
# PDF/HTML reporters, which the web/desktop build never invokes.
excludes = [
    "matplotlib",
    "reportlab",
    "PyQt5", "PyQt6", "PySide2", "PySide6", "tkinter",
    "IPython", "jupyter", "notebook",
    "pytest", "pytest_cov", "_pytest",
    "mypy", "ruff",
]

a = Analysis(
    [str(REPO_ROOT / "web" / "backend" / "desktop.py")],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="mettle-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,         # stdout/stderr must reach Tauri for the handshake
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
