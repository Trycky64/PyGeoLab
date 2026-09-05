"""Exercise application creation and the essential desktop window structure."""

import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDockWidget, QToolBar
from pytestqt.qtbot import QtBot

from pygeolab.app import create_application
from pygeolab.ui.main_window import MainWindow


def test_create_application_reuses_qt_instance(qapp: QApplication) -> None:
    """Repeated startup requests must preserve Qt's single application instance."""
    application = create_application([])

    assert application is qapp
    assert create_application([]) is application


def test_create_application_sets_metadata_in_fresh_process() -> None:
    """A standalone launch sets identity without relying on pytest's Qt instance."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pygeolab import __version__; "
            "from pygeolab.app import create_application; "
            "app = create_application([]); "
            "assert app.applicationName() == 'PyGeoLab'; "
            "assert app.applicationVersion() == __version__",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_main_window_provides_desktop_layout(qtbot: QtBot) -> None:
    """The initial window exposes the documented workspace and dock layout."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(window.isVisible)

    assert "PyGeoLab" in window.windowTitle()
    assert window.centralWidget() is not None
    assert window.centralWidget().isVisible()
    assert window.menuBar().actions()
    assert window.findChildren(QToolBar)
    assert window.statusBar().isVisible()

    docks = window.findChildren(QDockWidget)
    assert len(docks) >= 2
    assert all(dock.widget() is not None for dock in docks)
    areas = {window.dockWidgetArea(dock) for dock in docks}
    assert Qt.DockWidgetArea.LeftDockWidgetArea in areas
    assert Qt.DockWidgetArea.RightDockWidgetArea in areas

    assert window.close()
    assert not window.isVisible()
