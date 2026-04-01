"""Build the Fortuna sidecar binary using PyInstaller.

Produces a --onedir bundle and copies it to src-tauri/binaries/
with the correct target-triple naming that Tauri expects.

Usage: python scripts/build_sidecar.py
"""

import os
import platform
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
TAURI_BIN_DIR = os.path.join(PROJECT_ROOT, "src-tauri", "binaries")


def get_target_triple() -> str:
    """Return the Rust-style target triple for the current platform."""
    machine = platform.machine().lower()
    system = platform.system().lower()

    arch_map = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "arm64": "aarch64",
        "aarch64": "aarch64",
    }
    arch = arch_map.get(machine, machine)

    if system == "darwin":
        return f"{arch}-apple-darwin"
    elif system == "windows":
        return f"{arch}-pc-windows-msvc"
    elif system == "linux":
        return f"{arch}-unknown-linux-gnu"
    else:
        raise RuntimeError(f"Unsupported platform: {system} {machine}")


def build():
    target_triple = get_target_triple()
    print(f"Building sidecar for target: {target_triple}")

    # Collect data files to bundle
    data_files = [
        (os.path.join(PROJECT_ROOT, "app.py"), "."),
        (os.path.join(PROJECT_ROOT, "database.py"), "."),
        (os.path.join(PROJECT_ROOT, "ai_engine.py"), "."),
        (os.path.join(PROJECT_ROOT, "market_data.py"), "."),
        (os.path.join(PROJECT_ROOT, "charts.py"), "."),
        (os.path.join(PROJECT_ROOT, "views"), "views"),
        (os.path.join(PROJECT_ROOT, "services"), "services"),
        (os.path.join(PROJECT_ROOT, "assets"), "assets"),
        (os.path.join(PROJECT_ROOT, ".streamlit", "config.toml"), ".streamlit"),
    ]

    add_data_args = []
    sep = ";" if platform.system() == "Windows" else ":"
    for src, dest in data_files:
        if os.path.exists(src):
            add_data_args.extend(["--add-data", f"{src}{sep}{dest}"])

    hidden_imports = [
        "pandas",
        "plotly",
        "yfinance",
        "cryptography",
        "platformdirs",
        "streamlit",
        "dotenv",
        "views",
        "services",
        "services.portfolio",
        "services.analysis",
        "services.dividends",
        "services.planner",
        "views.portfolio",
        "views.transactions",
        "views.analysis",
        "views.dividends",
        "views.planner",
        "views.settings",
        "views.logs",
    ]

    hidden_import_args = []
    for imp in hidden_imports:
        hidden_import_args.extend(["--hidden-import", imp])

    # Modules to exclude — not used by Fortuna, saves ~90 MB
    # Note: pyarrow is required by st.dataframe() — do NOT exclude it
    exclude_modules = [
        "PIL",
        "Pillow",
        "matplotlib",
        "scipy",
        "tkinter",
        "test",
        "unittest",
    ]

    exclude_args = []
    for mod in exclude_modules:
        exclude_args.extend(["--exclude-module", mod])

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--name",
        "fortuna-server",
        "--onedir",  # Critical: --onefile spawns unkillable child processes
        "--distpath",
        DIST_DIR,
        "--workpath",
        os.path.join(PROJECT_ROOT, "build", "pyinstaller"),
        "--specpath",
        os.path.join(PROJECT_ROOT, "build"),
        # Fix importlib.metadata discovery for Python 3.14 frozen bundles.
        # Flushes stale FastPath/Lookup caches so dist-info dirs inside _internal/
        # are visible to importlib.metadata.version() at package import time.
        "--runtime-hook",
        os.path.join(PROJECT_ROOT, "scripts", "pyi_rth_metadata_fix.py"),
        "--collect-all",
        "streamlit",
        *add_data_args,
        *hidden_import_args,
        *exclude_args,
        os.path.join(PROJECT_ROOT, "scripts", "fortuna_launcher.py"),
    ]

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    # Copy output to Tauri binaries directory.
    # PyInstaller onedir produces: fortuna-server/ containing the exe + _internal/.
    # Tauri externalBin resolves "binaries/fortuna-server" to
    # "binaries/fortuna-server-<target-triple>" at runtime.
    # The exe must be next to _internal/ so both go into binaries/.
    src_dir = os.path.join(DIST_DIR, "fortuna-server")
    os.makedirs(TAURI_BIN_DIR, exist_ok=True)

    # Copy _internal directory
    dest_internal = os.path.join(TAURI_BIN_DIR, "_internal")
    if os.path.exists(dest_internal):
        shutil.rmtree(dest_internal)
    shutil.copytree(os.path.join(src_dir, "_internal"), dest_internal)

    # Copy and rename the executable with target triple
    if platform.system() == "Windows":
        exe_name = "fortuna-server.exe"
        target_name = f"fortuna-server-{target_triple}.exe"
    else:
        exe_name = "fortuna-server"
        target_name = f"fortuna-server-{target_triple}"

    src_exe = os.path.join(src_dir, exe_name)
    dest_exe = os.path.join(TAURI_BIN_DIR, target_name)
    shutil.copy2(src_exe, dest_exe)

    print(f"Sidecar built successfully:")
    print(f"  Executable: {dest_exe}")
    print(f"  _internal:  {dest_internal}")


if __name__ == "__main__":
    build()
