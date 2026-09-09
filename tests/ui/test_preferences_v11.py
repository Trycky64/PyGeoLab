"""Verify centralized preference persistence and application to the workspace."""

from pathlib import Path

from PySide6.QtCore import QSettings
from pytestqt.qtbot import QtBot

from pygeolab.model.objects import GeoObject
from pygeolab.persistence import RecoveryManager
from pygeolab.ui import main_window as main_window_module
from pygeolab.ui.dialogs.preferences_dialog import PreferencesDialog
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.preferences import Preferences


def _settings(path: Path) -> QSettings:
    return QSettings(str(path), QSettings.Format.IniFormat)


def test_preferences_round_trip_every_qsettings_value(tmp_path: Path) -> None:
    settings = _settings(tmp_path / "preferences.ini")
    expected = Preferences(
        theme_mode="dark",
        show_grid=False,
        show_axes=False,
        show_labels=False,
        snapping_enabled=False,
        snap_threshold_px=17.5,
        default_width=4.5,
        default_point_size=9.0,
        default_color="#aa3377",
        export_scale=3.0,
        transparent_export=True,
        autosave_enabled=False,
        autosave_interval_minutes=11,
    )

    expected.save(settings)

    assert Preferences.load(settings) == expected
    assert Preferences.reset(settings) == Preferences()
    assert Preferences.load(settings) == Preferences()


def test_preferences_dialog_restores_all_defaults(qtbot: QtBot) -> None:
    dialog = PreferencesDialog(
        Preferences(theme_mode="dark", show_grid=False, default_color="#ff0000")
    )
    qtbot.addWidget(dialog)

    dialog._defaults.click()

    assert dialog.preferences() == Preferences()


def test_main_window_applies_display_snap_style_and_autosave_preferences(
    qtbot: QtBot, monkeypatch, tmp_path: Path
) -> None:
    preferences = Preferences(
        theme_mode="light",
        show_grid=False,
        show_axes=False,
        show_labels=False,
        snapping_enabled=False,
        snap_threshold_px=18,
        default_width=3.5,
        default_point_size=8,
        default_color="#cc5500",
        autosave_interval_minutes=7,
    )
    monkeypatch.setattr(Preferences, "load", classmethod(lambda cls: preferences))
    monkeypatch.setattr(Preferences, "save", lambda self, settings=None: None)
    monkeypatch.setattr(
        main_window_module, "RecoveryManager", lambda: RecoveryManager(tmp_path / "recovery")
    )

    window = MainWindow()
    qtbot.addWidget(window)
    point = window.document.add(GeoObject("point", "A", params={"x": 0, "y": 0}))

    assert not window.geometry_view._renderer.show_grid
    assert not window.geometry_view._renderer.show_axes
    assert not window.geometry_view._renderer.show_labels
    assert not window.geometry_view.interaction.snapping_options.enabled
    assert window.geometry_view.interaction.snapping_options.threshold_px == 18
    assert window.theme_actions["light"].isChecked()
    assert not window.snapping_action.isChecked()
    assert point.style.color == "#cc5500"
    assert point.style.width == 3.5
    assert point.style.point_size == 8
    assert window._autosave_timer.interval() == 7 * 60_000
    window.session.save(tmp_path / "preferences.pgl")
