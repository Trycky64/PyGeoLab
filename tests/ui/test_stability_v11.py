"""Regression tests for cache reuse, widget cleanup and non-modal startup."""

from PySide6.QtGui import QImage, QPainter, QPalette
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from pygeolab.geometry import Point2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style
from pygeolab.persistence import RecoveryManager
from pygeolab.rendering import renderer as renderer_module
from pygeolab.rendering.renderer import Renderer
from pygeolab.rendering.viewport import Viewport
from pygeolab.ui import main_window as main_window_module
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.preferences import Preferences


def _paint(renderer: Renderer, document: Document) -> None:
    viewport = Viewport(width=640, height=480)
    image = QImage(640, 480, QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(image)
    try:
        renderer.render(painter, document, viewport, QPalette())
    finally:
        painter.end()


def test_function_sampling_cache_survives_unrelated_document_changes(monkeypatch) -> None:
    document = Document()
    slider = GeoObject("number", "a", params={"value": 1.0})
    function = GeoObject(
        "function",
        "f",
        (slider.id,),
        params={"source": "sin(x) + a", "variable": "x"},
    )
    point = GeoObject("point", "A", params={"x": 0.0, "y": 0.0})
    document.restore((slider, function, point))
    renderer = Renderer()
    calls = 0
    original = renderer_module.sample_function

    def counted_sample(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(renderer_module, "sample_function", counted_sample)
    _paint(renderer, document)
    document.move_point(point.id, Point2D(1.0, 1.0))
    _paint(renderer, document)
    assert calls == 1

    document.update(slider.id, params={"value": 2.0})
    _paint(renderer, document)
    assert calls == 2


def test_style_only_edit_does_not_recompute_geometry() -> None:
    document = Document()
    point = document.add(GeoObject("point", "A", params={"x": 0.0, "y": 0.0}))

    document.update(point.id, style=Style(color="#ff0000"))

    assert document.last_recomputed == ()


def test_main_window_close_stops_timers_and_releases_document_observers(
    qtbot: QtBot, monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(Preferences, "load", classmethod(lambda cls: Preferences()))
    monkeypatch.setattr(Preferences, "save", lambda self, settings=None: None)
    monkeypatch.setattr(
        main_window_module, "RecoveryManager", lambda: RecoveryManager(tmp_path / "recovery")
    )
    window = MainWindow()
    qtbot.addWidget(window)
    document = window.document
    assert document.observer_count == 6
    assert QApplication.activeModalWidget() is None

    window.show()
    assert window.close()

    assert document.observer_count == 0
    assert not window._autosave_timer.isActive()
    assert not window.slider_panel._timer.isActive()
