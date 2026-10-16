"""Unit and system tests for TimelineController, TimelineWidget, and sliders."""

from __future__ import annotations

import math

from PySide6.QtWidgets import QApplication

from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.variables import slider_spec
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.preferences import Preferences
from pygeolab.ui.timeline_controller import TimelineController
from pygeolab.ui.timeline_widget import TimelineWidget


def test_timeline_controller_deterministic_playback() -> None:
    doc = Document()
    s1 = doc.add(
        GeoObject(
            "number",
            "a",
            params={"value": 0.0, "minimum": 0.0, "maximum": 10.0, "step": 0.1},
        )
    )
    s2 = doc.add(
        GeoObject(
            "number",
            "b",
            params={"value": -5.0, "minimum": -5.0, "maximum": 5.0, "step": 0.5},
        )
    )

    timeline = TimelineController(doc)
    timeline.set_duration(10.0)
    timeline.set_global_speed(1.0)
    timeline.set_loop(False)

    # Initial state
    timeline.save_initial_state()
    assert timeline.current_time == 0.0
    assert slider_spec(doc.get(s1.id)).value == 0.0
    assert slider_spec(doc.get(s2.id)).value == -5.0

    # Advance 5.0 seconds (half duration, normalized t = 0.5)
    timeline.advance(5.0)
    assert math.isclose(timeline.current_time, 5.0)
    assert math.isclose(timeline.normalized_time, 0.5)
    assert math.isclose(slider_spec(doc.get(s1.id)).value, 5.0, abs_tol=1e-5)
    assert math.isclose(slider_spec(doc.get(s2.id)).value, 0.0, abs_tol=1e-5)

    # Advance another 5.0 seconds (full duration, t = 1.0)
    timeline.advance(5.0)
    assert math.isclose(timeline.current_time, 10.0)
    assert math.isclose(timeline.normalized_time, 1.0)
    assert math.isclose(slider_spec(doc.get(s1.id)).value, 10.0, abs_tol=1e-5)
    assert math.isclose(slider_spec(doc.get(s2.id)).value, 5.0, abs_tol=1e-5)

    # Restore initial state
    timeline.restore_initial_state()
    assert math.isclose(timeline.current_time, 0.0)
    assert math.isclose(slider_spec(doc.get(s1.id)).value, 0.0, abs_tol=1e-5)
    assert math.isclose(slider_spec(doc.get(s2.id)).value, -5.0, abs_tol=1e-5)


def test_timeline_controller_loop_and_ping_pong() -> None:
    doc = Document()
    doc.add(
        GeoObject(
            "number",
            "t_var",
            params={"value": 0.0, "minimum": 0.0, "maximum": 100.0, "step": 1.0},
        )
    )

    timeline = TimelineController(doc)
    timeline.set_duration(10.0)

    # Test Loop: when t advances beyond duration (e.g. 12s on 10s duration), it wraps to 2s
    timeline.set_loop(True)
    timeline.set_ping_pong(False)
    timeline.advance(12.0)
    assert math.isclose(timeline.current_time, 2.0, abs_tol=1e-4)

    # Test Ping-Pong: bounces back and forth
    timeline.set_ping_pong(True)
    timeline.set_time(8.0)
    timeline.advance(4.0)  # 8 + 4 = 12 -> bounces to 10 - 2 = 8.0, reversing direction
    assert math.isclose(timeline.current_time, 8.0, abs_tol=1e-4)
    timeline.advance(3.0)  # moving backward: 8 - 3 = 5.0
    assert math.isclose(timeline.current_time, 5.0, abs_tol=1e-4)


def test_timeline_controller_markers() -> None:
    doc = Document()
    doc.add(
        GeoObject(
            "number",
            "v",
            params={"value": 0.0, "minimum": 0.0, "maximum": 10.0, "step": 0.1},
        )
    )

    timeline = TimelineController(doc)
    timeline.set_duration(10.0)
    # Range markers: [0.2, 0.8] -> from 2.0s to 8.0s
    timeline.set_markers(0.2, 0.8)
    assert timeline.start_marker == 0.2
    assert timeline.end_marker == 0.8

    timeline.set_normalized_time(0.2)
    assert math.isclose(timeline.current_time, 2.0)

    # Stop rewinds to start marker
    timeline.set_time(5.0)
    timeline.stop(restore_initial=False)
    assert math.isclose(timeline.current_time, 2.0)


def test_timeline_controller_active_subsets() -> None:
    doc = Document()
    s1 = doc.add(
        GeoObject(
            "number",
            "s1",
            params={"value": 0.0, "minimum": 0.0, "maximum": 10.0, "step": 1.0},
        )
    )
    s2 = doc.add(
        GeoObject(
            "number",
            "s2",
            params={"value": 0.0, "minimum": 0.0, "maximum": 10.0, "step": 1.0},
        )
    )

    timeline = TimelineController(doc)
    timeline.set_duration(10.0)
    # Only animate s1
    timeline.set_active_slider_ids({s1.id})

    timeline.advance(5.0)
    assert math.isclose(slider_spec(doc.get(s1.id)).value, 5.0, abs_tol=1e-4)
    # s2 remains untouched
    assert math.isclose(slider_spec(doc.get(s2.id)).value, 0.0, abs_tol=1e-4)


def test_timeline_widget_ui_integration(qapp: QApplication) -> None:
    del qapp
    doc = Document()
    doc.add(
        GeoObject(
            "number",
            "a",
            params={"value": 0.0, "minimum": 0.0, "maximum": 10.0, "step": 0.1},
        )
    )
    widget = TimelineWidget(doc)

    assert widget.play_button.text() == widget.tr("Lecture")

    # Click play -> toggles to pause
    widget.play_button.click()
    assert widget.controller.is_playing
    assert widget.play_button.text() == widget.tr("Pause")

    # Click stop
    widget.stop_button.click()
    assert not widget.controller.is_playing
    assert widget.play_button.text() == widget.tr("Lecture")

    # Scrub slider
    widget._on_slider_scrubbing(500)
    assert math.isclose(widget.controller.normalized_time, 0.5)

    # Duration change
    widget.duration_spin.setValue(20.0)
    assert widget.controller.duration == 20.0

    # Speed change
    widget.speed_spin.setValue(2.0)
    assert widget.controller.global_speed == 2.0

    # Markers
    widget.start_spin.setValue(0.1)
    widget.end_spin.setValue(0.9)
    assert widget.controller.start_marker == 0.1
    assert widget.controller.end_marker == 0.9

    widget.close()


def test_main_window_timeline_shortcuts_and_actions(qapp: QApplication, monkeypatch) -> None:
    del qapp
    window = MainWindow(offer_recovery=False)
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)

    assert hasattr(window, "timeline_dock")
    assert hasattr(window, "timeline_widget")
    assert "animation.toggle_play" in window.action_registry._actions
    assert "animation.stop" in window.action_registry._actions

    # Toggle play via action
    toggle_act = window.action_registry._actions["animation.toggle_play"]
    toggle_act.trigger()
    assert window.timeline_widget.controller.is_playing

    stop_act = window.action_registry._actions["animation.stop"]
    stop_act.trigger()
    assert not window.timeline_widget.controller.is_playing

    window.close()


def test_preferences_timeline_configuration() -> None:
    prefs = Preferences(timeline_fps=60, timeline_speed=2.5)
    assert prefs.timeline_fps == 60
    assert prefs.timeline_speed == 2.5

    import pytest

    with pytest.raises(ValueError):
        Preferences(timeline_fps=5)

    with pytest.raises(ValueError):
        Preferences(timeline_speed=0.05)
