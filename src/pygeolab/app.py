"""Qt application lifecycle, logging and global error handling."""

from __future__ import annotations

import logging
import sys
from importlib.resources import files

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from pygeolab import __version__
from pygeolab.diagnostics import system_information
from pygeolab.logging_config import configure_logging
from pygeolab.ui.error_handler import install_exception_handler
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.preferences import Preferences
from pygeolab.ui.theme import apply_theme
from pygeolab.ui.translations import install_application_translator


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
    logging.getLogger(__name__).info("Startup\n%s", system_information())
    application = create_application()
    preferences = Preferences.load()
    install_application_translator(application, preferences.language)
    apply_theme(application, preferences.theme_mode)
    window = MainWindow(offer_recovery="--smoke-test" not in sys.argv)
    window.show()
    if "--smoke-test" in sys.argv:
        application.processEvents()
        if not window.close():
            logging.getLogger(__name__).error("The smoke test could not close the window")
            return 1
        application.processEvents()
        logging.getLogger(__name__).info("Executable smoke test passed")
        return 0
    exit_code = application.exec()
    logging.getLogger(__name__).info("PyGeoLab shutdown (code %s)", exit_code)
    return exit_code
