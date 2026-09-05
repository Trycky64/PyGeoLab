"""Qt application lifecycle, kept separate from the reusable mathematical domain."""

import sys

from PySide6.QtWidgets import QApplication

from pygeolab import __version__
from pygeolab.ui.main_window import MainWindow


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
    return application


def main() -> int:
    """Start the desktop event loop and return Qt's process exit status."""
    application = create_application()
    window = MainWindow()
    window.show()
    return application.exec()
