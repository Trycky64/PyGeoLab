"""Exercise numerical-analysis UI and dynamic length/area measurements."""

import pytest
from pytestqt.qtbot import QtBot

from pygeolab.geometry import Point2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.numerical_panel import NumericalPanel


def _function(name: str, source: str) -> GeoObject:
    return GeoObject("function", name, params={"variable": "x", "source": source})


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        ("derivative", "4"),
        ("integral", "1.333"),
        ("roots", "-1"),
        ("extrema", "minimum"),
        ("intersections", "-1"),
    ],
)
def test_numerical_panel_calculates_all_function_operations(
    qtbot: QtBot, operation: str, expected: str
) -> None:
    document = Document()
    document.add(_function("f", "x^2-1"))
    document.add(_function("g", "0"))
    panel = NumericalPanel(document)
    qtbot.addWidget(panel)
    panel.operation.setCurrentIndex(panel.operation.findData(operation))
    panel.start.setValue(2 if operation == "derivative" else -2)
    panel.end.setValue(2)
    panel.first_function.setCurrentIndex(0)
    panel.second_function.setCurrentIndex(1)

    panel.calculate()

    text = " ".join(panel.results.item(index).text() for index in range(panel.results.count()))
    assert expected in text
    assert not panel.message.text().startswith("Erreur")
    assert panel.samples.maximum() == 10_000
    assert panel.tolerance.minimum() == pytest.approx(1e-12)


def test_numerical_panel_reports_discontinuous_integral_inline(qtbot: QtBot) -> None:
    document = Document()
    document.add(_function("f", "1/(x-0.013)"))
    panel = NumericalPanel(document)
    qtbot.addWidget(panel)
    panel.operation.setCurrentIndex(panel.operation.findData("integral"))
    panel.start.setValue(-1)
    panel.end.setValue(1)

    panel.calculate()

    assert "Erreur" in panel.message.text()
    assert "discontinue" in panel.message.text()
    assert panel.results.count() == 0


def test_length_and_area_measurements_follow_their_geometry() -> None:
    document = Document()
    a = document.add(GeoObject("point", "A", params={"x": 0, "y": 0}))
    b = document.add(GeoObject("point", "B", params={"x": 3, "y": 0}))
    c = document.add(GeoObject("point", "C", params={"x": 0, "y": 4}))
    segment = document.add(GeoObject("segment", "s", (a.id, b.id)))
    polygon = document.add(GeoObject("polygon", "p", (a.id, b.id, c.id)))
    length = document.add(GeoObject("length", "L", (segment.id,)))
    area = document.add(GeoObject("area", "Aire", (polygon.id,)))

    assert length.geometry == pytest.approx(3)
    assert area.geometry == pytest.approx(6)
    document.move_point(b.id, Point2D(6, 0))
    assert document.get(length.id).geometry == pytest.approx(6)
    assert document.get(area.id).geometry == pytest.approx(12)


def test_main_window_creates_selected_dynamic_measurements(qtbot: QtBot, tmp_path) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    a = window.document.add(GeoObject("point", "A", params={"x": 0, "y": 0}))
    b = window.document.add(GeoObject("point", "B", params={"x": 3, "y": 0}))
    segment = window.document.add(GeoObject("segment", "s", (a.id, b.id)))
    window.geometry_view.set_selected_ids({segment.id})

    window._measure_selected("length")

    measurement = next(obj for obj in window.document.objects.values() if obj.kind == "length")
    assert measurement.geometry == pytest.approx(3)
    assert window.geometry_view.history.undo_count == 1
    window.geometry_view.history.undo()
    assert measurement.id not in window.document.objects
    window.session.save(tmp_path / "measurements.pgl")
