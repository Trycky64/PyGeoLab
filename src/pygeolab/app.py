"""Qt application lifecycle, logging and global error handling."""

from __future__ import annotations

import logging
import sys
from importlib.resources import files

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from pygeolab import __version__
from pygeolab.logging_config import configure_logging
from pygeolab.ui.error_handler import install_exception_handler
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.preferences import Preferences
from pygeolab.ui.theme import apply_theme


def create_application(argv: list[str] | None = None) -> QApplication:
    """Reuse the process application for embedders and tests, or create one."""
    existing = QApplication.instance()
    application = (
        existing
        if isinstance(existing, QApplication)
        else QApplication(sys.argv if argv is None else argv)
    )
    application.setApplicationName("PyGeoLab")
    application.setOrganizationName("PyGeoLab")
    application.setApplicationVersion(__version__)
    application.setDesktopFileName("pygeolab")
    icon = QIcon(str(files("pygeolab.resources").joinpath("icon.svg")))
    if not icon.isNull():
        application.setWindowIcon(icon)
    return application


def main() -> int:
    """Start the desktop event loop and return Qt's process exit status."""
    log_path = configure_logging("--debug" in sys.argv)
    install_exception_handler(log_path)
    logging.getLogger(__name__).info("Démarrage de PyGeoLab %s", __version__)
    application = create_application()
    apply_theme(application, Preferences.load().dark_theme)
    window = MainWindow()
    window.show()
    exit_code = application.exec()
    logging.getLogger(__name__).info("Arrêt de PyGeoLab (code %s)", exit_code)
    return exit_code
