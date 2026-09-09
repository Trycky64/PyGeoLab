"""Exercise recoverable failures and user-copyable diagnostics without native dialogs."""

from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from pytestqt.qtbot import QtBot

from pygeolab.model.objects import GeoObject
from pygeolab.persistence import RecoveryManager
from pygeolab.ui import main_window as main_window_module
from pygeolab.ui.dialogs.export_dialog import ExportOptions
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.preferences import Preferences


class _AcceptedExportDialog:
    def __init__(self, width, height, scale, transparent, has_selection, parent=None) -> None:
        del has_selection, parent
        self._options = ExportOptions("viewport", transparent, scale, width, height)

    def exec(self) -> QDialog.DialogCode:
        return QDialog.DialogCode.Accepted

    def options(self) -> ExportOptions:
        return self._options


def _window(qtbot: QtBot, monkeypatch, tmp_path: Path) -> MainWindow:
    monkeypatch.setattr(Preferences, "load", classmethod(lambda cls: Preferences()))
    monkeypatch.setattr(Preferences, "save", lambda self, settings=None: None)
    monkeypatch.setattr(
        main_window_module, "RecoveryManager", lambda: RecoveryManager(tmp_path / "recovery")
    )
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def _capture_critical(monkeypatch) -> list[tuple[str, str]]:
    messages: list[tuple[str, str]] = []

    def capture(parent, title: str, text: str, *args, **kwargs):
        del parent, args, kwargs
        messages.append((title, text))
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(main_window_module.QMessageBox, "critical", capture)
    return messages


def test_corrupt_project_preserves_current_document_and_reports_context(
    qtbot: QtBot, monkeypatch, tmp_path: Path
) -> None:
    window = _window(qtbot, monkeypatch, tmp_path)
    current = window.document
    point = current.add(GeoObject("point", "A", params={"x": 1.0, "y": 2.0}))
    corrupt = tmp_path / "corrupt.pgl"
    corrupt.write_text("{broken", encoding="utf-8")
    messages = _capture_critical(monkeypatch)

    assert not window._open_path(str(corrupt))

    assert window.document is current
    assert window.document.get(point.id).name == "A"
    assert "document courant a été conservé" in messages[0][1]
    assert "Détail :" in messages[0][1]
    assert "Journal :" in messages[0][1]
    window.session.save(tmp_path / "current.pgl")


def test_save_export_and_clipboard_failures_remain_non_blocking(
    qtbot: QtBot, monkeypatch, tmp_path: Path
) -> None:
    window = _window(qtbot, monkeypatch, tmp_path)
    messages = _capture_critical(monkeypatch)
    monkeypatch.setattr(
        main_window_module.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(tmp_path / "target.pgl"), ""),
    )

    def fail_save(path=None):
        del path
        raise ValueError("disque plein")

    monkeypatch.setattr(window.session, "save", fail_save)

    assert not window._save_project_as()

    monkeypatch.setattr(main_window_module, "ExportDialog", _AcceptedExportDialog)
    monkeypatch.setattr(
        main_window_module.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(tmp_path / "target.png"), ""),
    )

    def fail_export(*args, **kwargs):
        del args, kwargs
        raise OSError("accès refusé")

    monkeypatch.setattr(main_window_module, "export_png", fail_export)
    window._export_png()

    monkeypatch.setattr(
        main_window_module,
        "copy_png_to_clipboard",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("presse-papiers indisponible")),
    )
    window._copy_png()

    assert [title for title, _text in messages] == [
        "Enregistrement impossible",
        "Export impossible",
        "Copie impossible",
    ]
    assert all("Journal :" in text for _title, text in messages)


def test_system_information_can_be_copied_from_help_menu(
    qtbot: QtBot, monkeypatch, tmp_path: Path, qapp: QApplication
) -> None:
    window = _window(qtbot, monkeypatch, tmp_path)

    window._copy_system_info()

    copied = qapp.clipboard().text()
    assert "PyGeoLab:" in copied
    assert "Python:" in copied
    assert "Qt:" in copied
    assert window.statusBar().currentMessage() == "Informations système copiées"
