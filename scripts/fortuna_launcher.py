"""Fortuna PyInstaller entry point — starts Streamlit programmatically.

Usage: fortuna_launcher <port>

Tauri spawns this as a sidecar, passing a dynamically-chosen free port.
"""

import sys
import os


def main():
    # When frozen by PyInstaller, _MEIPASS is the temp extraction dir (onedir mode)
    if getattr(sys, "frozen", False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(base_dir)  # Go up from scripts/ to project root

    app_path = os.path.join(base_dir, "app.py")
    port = sys.argv[1] if len(sys.argv) > 1 else "8501"

    # Set DB_PATH to OS-standard location (platformdirs handles this in database.py,
    # but we ensure the env is clean for the frozen bundle)
    if "DB_PATH" not in os.environ:
        import platformdirs

        data_dir = platformdirs.user_data_dir("Fortuna", "Fortuna")
        os.makedirs(data_dir, exist_ok=True)
        os.environ["DB_PATH"] = os.path.join(data_dir, "fortuna.db")

    # Start Streamlit programmatically
    from streamlit.web import cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        f"--server.port={port}",
        "--server.headless=true",
        "--server.address=127.0.0.1",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false",
    ]
    stcli.main()


if __name__ == "__main__":
    main()
