"""User-facing internal-error reporting that keeps tracebacks in logs instead of raw dialogs."""

from __future__ import annotations

import logging
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from types import TracebackType

from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from pygeolab.ui.translations import translate_message

ExceptionHook = Callable[[type[BaseException], BaseException, TracebackType | None], None]


def operation_error_message(summary: str, error: BaseException, log_path: Path) -> str:
    """Build a consistent actionable message for a recoverable operation failure."""
    detail = translate_message(str(error).strip() or error.__class__.__name__)
    application = QApplication.instance()
    if isinstance(application, QApplication) and application.property("pygeolabLanguage") == "en":
        return f"{summary}\n\nDetails: {detail}\n\nLog: {log_path}"
    return f"{summary}\n\nDétail : {detail}\n\nJournal : {log_path}"


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
            "Unhandled internal error\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
        )
        application = QApplication.instance()
        parent = application.activeWindow() if isinstance(application, QApplication) else None
        widget_parent = parent if isinstance(parent, QWidget) else None
        QMessageBox.critical(
            widget_parent,
            translate_message("Erreur interne — PyGeoLab"),
            translate_message(
                "Une erreur interne est survenue. Elle a été enregistrée dans :\n" + str(log_path)
            ),
        )

    sys.excepthook = handle
    return previous
