"""PyInstaller runtime hook — fix importlib.metadata discovery in frozen onedir bundle.

Python 3.14 loads importlib.metadata from base_library.zip early in the bootstrap
sequence.  FastPath (used by MetadataPathFinder) caches its Lookup by (path, mtime).
If the cache is populated before sys._MEIPASS is stable in sys.path, subsequent
calls to importlib.metadata.version() or distribution() find nothing even though the
dist-info directories are physically present inside _internal/.

This hook runs after the full PyInstaller bootloader setup but before any third-party
package is imported.  It:

  1. Ensures sys._MEIPASS is at the front of sys.path.
  2. Calls MetadataPathFinder.invalidate_caches() to flush any stale FastPath/Lookup
     entries built during early bootstrap.

Without this, packages that query their own version at import time (e.g. streamlit
calls importlib.metadata.version("streamlit") inside streamlit/version.py) raise
PackageNotFoundError even though the dist-info was correctly bundled by --collect-all.
"""

import sys

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    # Ensure _MEIPASS is the first entry so dist-info dirs are found first.
    if sys._MEIPASS not in sys.path:
        sys.path.insert(0, sys._MEIPASS)

    # Flush stale FastPath / Lookup caches built during early bootstrap.
    try:
        from importlib.metadata import MetadataPathFinder
        MetadataPathFinder.invalidate_caches()
    except Exception:
        pass  # Non-fatal; worst case is the original PackageNotFoundError.
