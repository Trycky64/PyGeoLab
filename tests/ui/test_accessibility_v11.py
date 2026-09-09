"""Automated shortcut, keyboard, contrast and accessibility checks."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QPalette
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLineEdit,
    QWidget,
)
from pytestqt.qtbot import QtBot

from pygeolab.model.objects import GeoObject
from pygeolab.persistence import RecoveryManager
from pygeolab.ui import main_window as main_window_module
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.preferences import Preferences
from pygeolab.ui.theme import apply_theme


def _window(qtbot: QtBot, monkeypatch, tmp_path) -> MainWindow:
    monkeypatch.setattr(Preferences, "load", classmethod(lambda cls: Preferences()))
    monkeypatch.setattr(Preferences, "save", lambda self, settings=None: None)
    monkeypatch.setattr(
        main_window_module, "RecoveryManager", lambda: RecoveryManager(tmp_path / "recovery")
    )
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def test_shortcuts_are_unique_and_reference_window_is_non_modal(
    qtbot: QtBot, monkeypatch, tmp_path
) -> None:
    window = _window(qtbot, monkeypatch, tmp_path)
    shortcuts = [
        action.shortcut().toString()
        for action in window.findChildren(QAction)
        if not action.shortcut().isEmpty()
    ]

    assert len(shortcuts) == len(set(shortcuts))
    window._show_shortcuts()
    qtbot.addWidget(window._shortcuts_dialog)
    assert window._shortcuts_dialog.isVisible()
    assert window._shortcuts_dialog.table.rowCount() == len(shortcuts)


def test_focusable_controls_have_names_sizes_tooltips_and_visible_focus_style(
    qtbot: QtBot, monkeypatch, tmp_path
) -> None:
    window = _window(qtbot, monkeypatch, tmp_path)
    window.show()
    qtbot.waitUntil(window.isVisible)
    focusable = [
        widget
        for widget in window.findChildren(QWidget)
        if widget.focusPolicy() != Qt.FocusPolicy.NoFocus
    ]

    assert focusable
    assert all(widget.accessibleName() for widget in focusable)
    assert all(widget.accessibleDescription() for widget in focusable)
    sized = [
        widget
        for widget in focusable
        if isinstance(widget, (QAbstractButton, QAbstractSpinBox, QComboBox, QLineEdit))
    ]
    assert sized and all(widget.minimumHeight() >= 28 for widget in sized)
    assert ":focus" in window.styleSheet()
    assert all(action.toolTip() for action in window.tool_actions.values())

    keyboard_controls = [
        widget for widget in focusable if widget.isEnabled() and widget.isVisibleTo(window)
    ]
    assert len(keyboard_controls) > 1
    assert all(widget.nextInFocusChain() is not widget for widget in keyboard_controls)


def test_active_tool_and_selection_publish_explicit_feedback(
    qtbot: QtBot, monkeypatch, tmp_path
) -> None:
    window = _window(qtbot, monkeypatch, tmp_path)
    point = window.document.add(GeoObject("point", "A", params={"x": 0, "y": 0}))

    window.tool_actions["point"].trigger()
    assert window.tool_actions["point"].isChecked()
    assert "Point" in window.statusBar().currentMessage()
    window.geometry_view.set_selected_ids({point.id})
    window._selection_from_canvas(frozenset({point.id}))
    assert "1 objet" in window.statusBar().currentMessage()
    window.session.save(tmp_path / "feedback.pgl")


def _luminance(color: QColor) -> float:
    channels = []
    for value in (color.redF(), color.greenF(), color.blueF()):
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(first: QColor, second: QColor) -> float:
    lighter, darker = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def test_light_and_dark_palettes_meet_text_contrast(qapp: QApplication) -> None:
    for mode in ("light", "dark"):
        apply_theme(qapp, mode)
        palette: QPalette = qapp.palette()
        assert _contrast(palette.window().color(), palette.windowText().color()) >= 4.5
        assert _contrast(palette.base().color(), palette.text().color()) >= 4.5
        assert _contrast(palette.highlight().color(), palette.highlightedText().color()) >= 4.5
    apply_theme(qapp, "system")
