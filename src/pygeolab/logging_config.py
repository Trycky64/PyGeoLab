"""Application logging configuration using rotating UTF-8 files and standard logging only."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def log_directory() -> Path:
    """Return a per-user writable log directory without requiring external dependencies."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "PyGeoLab" / "logs"
    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home) if state_home else Path.home() / ".local" / "state"
    return base / "pygeolab" / "logs"


def configure_logging(debug: bool = False) -> Path:
    """Configure root logging once and return the active log file path."""
    directory = log_directory()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "pygeolab.log"
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    if not any(isinstance(handler, RotatingFileHandler) for handler in root.handlers):
        handler = RotatingFileHandler(
            path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(handler)
    return path
