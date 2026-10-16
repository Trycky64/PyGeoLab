"""Unit tests for conics geometry, models, analytics, rendering, hit-testing, and persistence."""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtGui import QColor, QImage, QPainter, QPalette

from pygeolab.commands import (
    CommandHistory,
    CreateObjectsCommand,
    MovePointCommand,
)
from pygeolab.exporting.viewport_export import fitted_viewport
from pygeolab.geometry import (
    Ellipse2D,
    Hyperbola2D,
    Line2D,
    Parabola2D,
    Point2D,
    analyze_ellipse,
    analyze_hyperbola,
    analyze_parabola,
    format_ellipse_equation,
    format_hyperbola_equation,
    format_parabola_equation,
)
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.persistence.loader import load_project, save_project
from pygeolab.persistence.serializer import serialize_document
from pygeolab.persistence.validation import validate_project
from pygeolab.rendering.hit_test import first_hit
from pygeolab.rendering.renderer import Renderer
from pygeolab.rendering.viewport import Viewport
from pygeolab.ui.algebra_panel import AlgebraPanel
from pygeolab.ui.properties_panel import PropertiesPanel

# ==============================================================================
# Pure Geometry: Ellipse2D
# ==============================================================================


def test_ellipse_from_foci_and_point() -> None:
    f1 = Point2D(-3.0, 0.0)
    f2 = Point2D(3.0, 0.0)
    pt = Point2D(0.0, 4.0)

    ellipse = Ellipse2D.from_foci_and_point(f1, f2, pt)
    assert ellipse is not None
    assert math.isclose(ellipse.center.x, 0.0, abs_tol=1e-7)
    assert math.isclose(ellipse.center.y, 0.0, abs_tol=1e-7)
    # d(pt, f1) = 5, d(pt, f2) = 5 => 2a = 10 => a = 5
    assert math.isclose(ellipse.a, 5.0, abs_tol=1e-7)
    # c = 3 => b = sqrt(5^2 - 3^2) = 4
    assert math.isclose(ellipse.b, 4.0, abs_tol=1e-7)
    assert math.isclose(ellipse.linear_eccentricity, 3.0, abs_tol=1e-7)
    assert math.isclose(ellipse.eccentricity, 0.6, abs_tol=1e-7)
    assert math.isclose(ellipse.area, math.pi * 5.0 * 4.0, abs_tol=1e-7)
    assert ellipse.perimeter > 0.0

    # Bounds
    min_x, min_y, max_x, max_y = ellipse.bounding_box
    assert min_x <= -5.0 and max_x >= 5.0
    assert min_y <= -4.0 and max_y >= 4.0

    # Distance to boundary point (5, 0)
    assert math.isclose(ellipse.distance_to(Point2D(5.0, 0.0)), 0.0, abs_tol=1e-4)


def test_ellipse_from_center_and_axes() -> None:
    center = Point2D(2.0, 1.0)
    major_pt = Point2D(6.0, 1.0)  # a = 4.0
    ellipse = Ellipse2D.from_center_axes(center, major_pt, 3.0)
    assert ellipse is not None
    assert math.isclose(ellipse.a, 4.0)
    assert math.isclose(ellipse.b, 3.0)
    assert math.isclose(ellipse.linear_eccentricity, math.sqrt(7.0))


def test_ellipse_degeneracies() -> None:
    # 2a <= d(f1, f2)
    f1 = Point2D(-2.0, 0.0)
    f2 = Point2D(2.0, 0.0)
    # Point on segment between foci: d1 + d2 = d(f1, f2) => 2a == dist => degenerate
    pt_collinear = Point2D(0.0, 0.0)
    assert Ellipse2D.from_foci_and_point(f1, f2, pt_collinear) is None

    # Invalid axes
    assert Ellipse2D.from_center_axes(Point2D(0, 0), Point2D(0, 0), 1.0) is None
    assert Ellipse2D.from_center_axes(Point2D(0, 0), Point2D(2, 0), 0.0) is None
    assert Ellipse2D.from_center_axes(Point2D(0, 0), Point2D(2, 0), -1.0) is None


# ==============================================================================
# Pure Geometry: Parabola2D
# ==============================================================================


def test_parabola_from_focus_and_directrix() -> None:
    focus = Point2D(0.0, 1.0)
    directrix = Line2D(0.0, 1.0, 1.0)  # y + 1 = 0 => y = -1

    parabola = Parabola2D.from_focus_and_directrix(focus, directrix)
    assert parabola is not None
    # Vertex is midway between focus (0, 1) and directrix projection (0, -1) => (0, 0)
    assert math.isclose(parabola.vertex.x, 0.0, abs_tol=1e-7)
    assert math.isclose(parabola.vertex.y, 0.0, abs_tol=1e-7)
    # p = distance from focus to directrix = 2.0
    assert math.isclose(parabola.parameter, 2.0, abs_tol=1e-7)

    # Point on parabola: x = 2 => y = x^2 / (2p) = 4 / 4 = 1
    pt_on_parabola = Point2D(2.0, 1.0)
    assert math.isclose(parabola.distance_to(pt_on_parabola), 0.0, abs_tol=1e-4)

    # Degenerate: focus lies on directrix
    focus_on_dir = Point2D(0.0, -1.0)
    assert Parabola2D.from_focus_and_directrix(focus_on_dir, directrix) is None


# ==============================================================================
# Pure Geometry: Hyperbola2D
# ==============================================================================


def test_hyperbola_from_foci_and_point() -> None:
    f1 = Point2D(-5.0, 0.0)
    f2 = Point2D(5.0, 0.0)
    # For a hyperbola x^2 / 16 - y^2 / 9 = 1: a = 4, b = 3, c = 5
    # Point (4, 0) is a vertex: |d1 - d2| = |9 - 1| = 8 = 2a => a = 4
    pt = Point2D(4.0, 0.0)

    hyperbola = Hyperbola2D.from_foci_and_point(f1, f2, pt)
    assert hyperbola is not None
    assert math.isclose(hyperbola.center.x, 0.0, abs_tol=1e-7)
    assert math.isclose(hyperbola.center.y, 0.0, abs_tol=1e-7)
    assert math.isclose(hyperbola.a, 4.0, abs_tol=1e-7)
    assert math.isclose(hyperbola.linear_eccentricity, 5.0, abs_tol=1e-7)
    assert math.isclose(hyperbola.b, 3.0, abs_tol=1e-7)
    assert math.isclose(hyperbola.eccentricity, 1.25, abs_tol=1e-7)

    # Distance to vertex is 0
    assert math.isclose(hyperbola.distance_to(pt), 0.0, abs_tol=1e-4)
    # Asymptotes: slopes +- 3/4
    asymp1, asymp2 = hyperbola.asymptotes
    assert isinstance(asymp1, Line2D) and isinstance(asymp2, Line2D)


def test_hyperbola_from_foci_and_parameter() -> None:
    f1 = Point2D(0.0, -5.0)
    f2 = Point2D(0.0, 5.0)
    hyperbola = Hyperbola2D.from_foci_and_parameter(f1, f2, a=3.0)
    assert hyperbola is not None
    assert math.isclose(hyperbola.a, 3.0)
    assert math.isclose(hyperbola.b, 4.0)
    assert math.isclose(hyperbola.linear_eccentricity, 5.0)


def test_hyperbola_degeneracies() -> None:
    f1 = Point2D(-3.0, 0.0)
    f2 = Point2D(3.0, 0.0)
    # 2a >= 2c = 6.0
    assert Hyperbola2D.from_foci_and_parameter(f1, f2, a=3.5) is None
    assert Hyperbola2D.from_foci_and_parameter(f1, f2, a=3.0) is None
    assert Hyperbola2D.from_foci_and_parameter(f1, f2, a=-1.0) is None

    # Point equidistant from foci => 2a = 0
    pt_mid = Point2D(0.0, 5.0)
    assert Hyperbola2D.from_foci_and_point(f1, f2, pt_mid) is None


# ==============================================================================
# Conic2D General Model
# ==============================================================================


def test_conic_general_model() -> None:
    ellipse = Ellipse2D.from_center_axes(Point2D(0, 0), Point2D(5, 0), 3.0)
    parabola = Parabola2D.from_focus_and_directrix(Point2D(0, 1), Line2D(0, 1, 1))
    hyperbola = Hyperbola2D.from_foci_and_parameter(Point2D(-5, 0), Point2D(5, 0), 4.0)

    assert isinstance(ellipse, Ellipse2D)
    assert isinstance(parabola, Parabola2D)
    assert isinstance(hyperbola, Hyperbola2D)


# ==============================================================================
# Analytical Formatting & Analytics
# ==============================================================================


def test_conic_analytics() -> None:
    ellipse = Ellipse2D.from_center_axes(Point2D(0, 0), Point2D(5, 0), 3.0)
    assert ellipse is not None
    eq_e = format_ellipse_equation(ellipse)
    assert "x" in eq_e and "y" in eq_e
    res_e = analyze_ellipse(ellipse)
    assert res_e["a"] == 5.0 and res_e["b"] == 3.0

    parabola = Parabola2D.from_focus_and_directrix(Point2D(0, 1), Line2D(0, 1, 1))
    assert parabola is not None
    eq_p = format_parabola_equation(parabola)
    assert "x" in eq_p or "y" in eq_p
    res_p = analyze_parabola(parabola)
    assert res_p["parameter"] == 2.0

    hyperbola = Hyperbola2D.from_foci_and_parameter(Point2D(-5, 0), Point2D(5, 0), 4.0)
    assert hyperbola is not None
    eq_h = format_hyperbola_equation(hyperbola)
    assert "x" in eq_h and "y" in eq_h
    res_h = analyze_hyperbola(hyperbola)
    assert res_h["a"] == 4.0 and res_h["b"] == 3.0


# ==============================================================================
# Document & Dependency Recomputations
# ==============================================================================


def test_document_conics_dependency_graph() -> None:
    doc = Document("Conic Test")

    # 1. Ellipse (f1, f2, pt)
    f1 = GeoObject("point", "F1", (), {"x": -3.0, "y": 0.0})
    f2 = GeoObject("point", "F2", (), {"x": 3.0, "y": 0.0})
    pt = GeoObject("point", "P", (), {"x": 0.0, "y": 4.0})
    ellipse = GeoObject("ellipse", "E", (f1.id, f2.id, pt.id))

    # 2. Ellipse Center (center, pt_major, param b)
    c = GeoObject("point", "C", (), {"x": 0.0, "y": 0.0})
    p_maj = GeoObject("point", "Pmaj", (), {"x": 4.0, "y": 0.0})
    e_center = GeoObject("ellipse_center", "Ec", (c.id, p_maj.id), {"b": 2.0})

    # 3. Parabola (focus, directrix)
    f = GeoObject("point", "F", (), {"x": 0.0, "y": 1.0})
    d1 = GeoObject("point", "D1", (), {"x": -5.0, "y": -1.0})
    d2 = GeoObject("point", "D2", (), {"x": 5.0, "y": -1.0})
    dir_line = GeoObject("line", "dir", (d1.id, d2.id))
    parabola = GeoObject("parabola", "Par", (f.id, dir_line.id))

    # 4. Hyperbola (hf1, hf2, h_pt) with 2c = 10, 2a = 8 => a = 4 < c = 5
    hf1 = GeoObject("point", "HF1", (), {"x": -5.0, "y": 0.0})
    hf2 = GeoObject("point", "HF2", (), {"x": 5.0, "y": 0.0})
    h_pt = GeoObject("point", "Hp", (), {"x": 4.0, "y": 0.0})
    hyperbola = GeoObject("hyperbola", "Hyp", (hf1.id, hf2.id, h_pt.id))

    history = CommandHistory()
    history.execute(
        CreateObjectsCommand(
            doc,
            (
                f1,
                f2,
                pt,
                ellipse,
                c,
                p_maj,
                e_center,
                f,
                d1,
                d2,
                dir_line,
                parabola,
                hf1,
                hf2,
                h_pt,
                hyperbola,
            ),
        )
    )

    # Verify geometries are properly calculated
    assert isinstance(doc.get(ellipse.id).geometry, Ellipse2D)
    assert isinstance(doc.get(e_center.id).geometry, Ellipse2D)
    assert isinstance(doc.get(parabola.id).geometry, Parabola2D)
    assert isinstance(doc.get(hyperbola.id).geometry, Hyperbola2D)

    # Move focus 1 dynamically and verify ellipse recalculates
    history.execute(MovePointCommand(doc, f1.id, Point2D(-3.0, 0.0), Point2D(-3.5, 0.0)))
    new_e = doc.get(ellipse.id).geometry
    assert isinstance(new_e, Ellipse2D)
    assert math.isclose(new_e.foci[0].x, -3.5)

    # Move directrix line dynamically and verify parabola recalculates
    history.execute(MovePointCommand(doc, d1.id, Point2D(-5.0, -1.0), Point2D(-5.0, -2.0)))
    history.execute(MovePointCommand(doc, d2.id, Point2D(5.0, -1.0), Point2D(5.0, -2.0)))
    new_par = doc.get(parabola.id).geometry
    assert isinstance(new_par, Parabola2D)
    # Focus at (0, 1), directrix y = -2 => vertex at y = -0.5, p = 3.0
    assert math.isclose(new_par.parameter, 3.0, abs_tol=1e-5)

    # Undo
    history.undo()
    history.undo()
    history.undo()
    assert math.isclose(doc.get(f1.id).geometry.x, -3.0)


# ==============================================================================
# Hit-Testing
# ==============================================================================


def test_conics_hit_test() -> None:
    doc = Document("Hit Test")
    f1 = GeoObject("point", "F1", (), {"x": -3.0, "y": 0.0})
    f2 = GeoObject("point", "F2", (), {"x": 3.0, "y": 0.0})
    pt = GeoObject("point", "P", (), {"x": 0.0, "y": 4.0})
    ellipse = GeoObject("ellipse", "E", (f1.id, f2.id, pt.id))

    doc.add(f1)
    doc.add(f2)
    doc.add(pt)
    doc.add(ellipse)

    viewport = Viewport(center=Point2D(0.0, 0.0), scale=40.0, width=800, height=600)

    # Point (5, 0) is on the ellipse (a = 5)
    # Screen coord of (5, 0): screen_x = 400 + 5 * 40 = 600, screen_y = 300
    hit = first_hit(doc, viewport, 600, 300, kinds=frozenset({"ellipse"}))
    assert hit is not None and hit.id == ellipse.id

    # Far away point (e.g. 0, 0)
    hit_miss = first_hit(doc, viewport, 400, 300, kinds=frozenset({"ellipse"}))
    assert hit_miss is None


# ==============================================================================
# Rendering & Export
# ==============================================================================


def test_conics_rendering_and_viewport_bounds(qapp: object) -> None:
    del qapp
    doc = Document("Render Test")
    f1 = GeoObject("point", "F1", (), {"x": -3.0, "y": 0.0})
    f2 = GeoObject("point", "F2", (), {"x": 3.0, "y": 0.0})
    pt = GeoObject("point", "P", (), {"x": 0.0, "y": 4.0})
    ellipse = GeoObject("ellipse", "E", (f1.id, f2.id, pt.id))

    f = GeoObject("point", "F", (), {"x": 0.0, "y": 1.0})
    d1 = GeoObject("point", "D1", (), {"x": -5.0, "y": -1.0})
    d2 = GeoObject("point", "D2", (), {"x": 5.0, "y": -1.0})
    dir_line = GeoObject("line", "dir", (d1.id, d2.id))
    parabola = GeoObject("parabola", "Par", (f.id, dir_line.id))

    doc.add(f1)
    doc.add(f2)
    doc.add(pt)
    doc.add(ellipse)
    doc.add(f)
    doc.add(d1)
    doc.add(d2)
    doc.add(dir_line)
    doc.add(parabola)

    # Test fitted_viewport
    fitted = fitted_viewport(doc, 400, 300)
    assert fitted is not None

    # Render to QImage
    img = QImage(400, 300, QImage.Format.Format_ARGB32)
    img.fill(QColor("white"))
    painter = QPainter(img)
    try:
        renderer = Renderer()
        renderer.render(painter, doc, fitted, QPalette())
    finally:
        painter.end()


# ==============================================================================
# Persistence Round-Trip
# ==============================================================================


def test_conics_persistence_roundtrip(tmp_path: Path) -> None:
    doc = Document("Persistence Test")
    c = GeoObject("point", "C", (), {"x": 1.0, "y": 2.0})
    maj = GeoObject("point", "Maj", (), {"x": 5.0, "y": 2.0})
    ellipse = GeoObject("ellipse_center", "Ec", (c.id, maj.id), {"b": 2.5})

    f1 = GeoObject("point", "F1", (), {"x": -4.0, "y": 0.0})
    f2 = GeoObject("point", "F2", (), {"x": 4.0, "y": 0.0})
    hyp = GeoObject("hyperbola", "H", (f1.id, f2.id), {"a": 2.0})

    doc.add(c)
    doc.add(maj)
    doc.add(ellipse)
    doc.add(f1)
    doc.add(f2)
    doc.add(hyp)

    # Validate schema
    raw = serialize_document(doc)
    validated = validate_project(raw)
    assert validated is not None

    # Save to disk and reload
    path = tmp_path / "conics.pgl"
    save_project(doc, path)

    loaded = load_project(path)
    assert len(loaded.objects) == 6
    loaded_e = loaded.get(ellipse.id)
    assert loaded_e.kind == "ellipse_center"
    assert isinstance(loaded_e.geometry, Ellipse2D)
    assert math.isclose(loaded_e.geometry.a, 4.0)
    assert math.isclose(loaded_e.geometry.b, 2.5)

    loaded_h = loaded.get(hyp.id)
    assert loaded_h.kind == "hyperbola"
    assert isinstance(loaded_h.geometry, Hyperbola2D)
    assert math.isclose(loaded_h.geometry.a, 2.0)


# ==============================================================================
# UI Properties & Algebra Panel Integration
# ==============================================================================


def test_conics_properties_panel(qtbot) -> None:
    doc = Document("UI Test")
    c = GeoObject("point", "C", (), {"x": 0.0, "y": 0.0})
    maj = GeoObject("point", "Maj", (), {"x": 4.0, "y": 0.0})
    e = GeoObject("ellipse_center", "E", (c.id, maj.id), {"b": 2.0})
    doc.add(c)
    doc.add(maj)
    doc.add(e)

    commands = []
    panel = PropertiesPanel(doc, lambda cmd: commands.append(cmd))
    qtbot.addWidget(panel)

    panel.set_selection(frozenset({e.id}))
    assert "b" in panel._parameter_editors
    assert not panel._analytics_widget.isHidden()


def test_conics_algebra_panel(qtbot) -> None:
    doc = Document("Algebra Test")
    f1 = GeoObject("point", "F1", (), {"x": -3.0, "y": 0.0})
    f2 = GeoObject("point", "F2", (), {"x": 3.0, "y": 0.0})
    pt = GeoObject("point", "P", (), {"x": 0.0, "y": 4.0})
    e = GeoObject("ellipse", "E", (f1.id, f2.id, pt.id))
    doc.add(f1)
    doc.add(f2)
    doc.add(pt)
    doc.add(e)

    panel = AlgebraPanel(doc, lambda cmd: None)
    qtbot.addWidget(panel)
    panel.refresh()

    assert panel._category(doc.get(e.id).geometry) == "Coniques"
