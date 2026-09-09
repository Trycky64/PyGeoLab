"""Stable build and runtime diagnostics suitable for logs and the clipboard."""

from __future__ import annotations

import os
import platform
import sys

import PySide6
from PySide6.QtCore import qVersion

from pygeolab import __version__


def build_identifier() -> str:
    """Return the injected build identifier or a clear development marker."""
    value = os.environ.get("PYGEOLAB_BUILD_ID") or os.environ.get("GITHUB_SHA")
    return value[:12] if value else "development"


def system_information() -> str:
    """Return copyable version information without machine-specific user data."""
    return "\n".join(
        (
            f"PyGeoLab: {__version__}",
            f"Build: {build_identifier()}",
            f"Python: {platform.python_version()} ({platform.python_implementation()})",
            f"PySide6: {PySide6.__version__}",
            f"Qt: {qVersion()}",
            f"OS: {platform.platform()}",
            f"Architecture: {platform.machine() or 'unknown'}",
            f"Executable: {sys.executable}",
        )
    )
