"""User-facing internal-error reporting that keeps tracebacks in logs instead of raw dialogs."""

from __future__ import annotations

import logging
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from types import TracebackType

from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

ExceptionHook = Callable[[type[BaseException], BaseException, TracebackType | None], None]


def install_exception_handler(log_path: Path) -> ExceptionHook:
    """Install a hook that logs uncaught exceptions and presents contextual UI feedback."""
    previous = sys.excepthook

    def handle(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            previous(exc_type, exc_value, exc_traceback)
            return
        logging.getLogger("pygeolab").critical(
            "Erreur interne non gérée\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
        )
        application = QApplication.instance()
        parent = application.activeWindow() if isinstance(application, QApplication) else None
        widget_parent = parent if isinstance(parent, QWidget) else None
        QMessageBox.critical(
            widget_parent,
            "Erreur interne — PyGeoLab",
            "Une erreur interne est survenue. Elle a été enregistrée dans :\n" + str(log_path),
        )

    sys.excepthook = handle
    return previous
