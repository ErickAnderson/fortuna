"""Fortuna PyInstaller entry point — starts Streamlit programmatically.

Usage: fortuna_launcher <port>

Tauri spawns this as a sidecar, passing a dynamically-chosen free port.
"""

import sys
import os
import threading


def _pre_init_db() -> None:
    """Run DB schema init in background while Streamlit server starts.

    Safe to call before Streamlit's session threads exist. Uses only sqlite3
    and stdlib — no Streamlit context required. app.py will call init_db()
    again on first session load; CREATE TABLE IF NOT EXISTS is idempotent.
    """
    try:
        import database as db
        db.init_db()
    except Exception:
        pass  # app.py session guard will retry on first load


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

    # Pre-initialize DB schema concurrently with Streamlit server startup (D-05)
    threading.Thread(target=_pre_init_db, daemon=True).start()

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
