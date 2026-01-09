"""Path utilities for resource resolution.

This module handles resource path resolution for both development and packaged
application scenarios (Nuitka, PyInstaller). Ensures model paths remain valid
after compilation by using relative paths from project root.
"""

import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory.

    Returns:
        Path: Project root directory, handling both script and compiled modes.
              For frozen executables (PyInstaller/Nuitka), uses sys._MEIPASS.
              For script execution, calculates from __file__ location.
    """
    if getattr(sys, "frozen", False):
        # Running as compiled executable (Nuitka/PyInstaller). Use getattr to satisfy type checkers.
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        # Fallback if attribute missing
        return Path(__file__).parent.parent.parent
    else:
        # Running as script: paths.py -> utils/ -> src/ -> project_root/
        return Path(__file__).parent.parent.parent


def get_model_path(model_name: str = "vosk-model-pt-fb-v0.1.1-20220516_2113") -> Path:
    """Get path to Vosk model directory.

    Args:
        model_name: Name of the model subdirectory in stt_models/

    Returns:
        Path: Full path to model directory

    Example:
        >>> model_path = get_model_path()
        >>> model_path.exists()
        True
    """
    return get_project_root() / "stt_models" / model_name


def get_assets_path() -> Path:
    """Get path to assets directory.

    Returns:
        Path: Full path to assets directory
    """
    return get_project_root() / "assets"
