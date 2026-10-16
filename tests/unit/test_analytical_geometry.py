"""Tests for analytical Euclidean calculations, equations, and properties display."""

from __future__ import annotations

import math
from uuid import uuid4

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from pygeolab.geometry import (
    ANGLE_EPSILON,
    EPSILON,
    Circle2D,
    Line2D,
    Point2D,
    Ray2D,
    Segment2D,
    Vector2D,
    analyze_circle,
    analyze_line,
    analyze_ray,
    analyze_segment,
    angle_between_lines,
    angle_between_vectors,
    are_lines_orthogonal,
    are_lines_parallel,
    are_points_collinear,
    are_vectors_collinear,
    are_vectors_orthogonal,
    circle_area,
    circle_perimeter,
    determinant_2d,
    distance_point_to_line,
    distance_point_to_point,
    dot_product,
    format_circle_canonical,
    format_circle_general,
    format_number,
    format_slope_intercept_line,
    line_is_horizontal,
    line_is_vertical,
    line_slope,
    line_x_intercept,
    line_y_intercept,
    midpoint,
    project_point_on_line,
    squared_distance_point_to_point,
    vector_norm,
)
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style
from pygeolab.ui.properties_panel import PropertiesPanel


def test_format_number_handles_integers_decimals_and_zeros() -> None:
    assert format_number(0.0) == "0"
    assert format_number(-0.0) == "0"
    assert format_number(1.0) == "1"
    assert format_number(-5.0) == "-5"
    assert format_number(2.5) == "2.5"
    assert format_number(-3.125) == "-3.125"
    assert format_number(1e-12) == "0"


def test_point_to_point_metrics() -> None:
    p1 = Point2D(1.0, 2.0)
    p2 = Point2D(4.0, 6.0)

    assert distance_point_to_point(p1, p2) == pytest.approx(5.0)
    assert squared_distance_point_to_point(p1, p2) == pytest.approx(25.0)

    mid = midpoint(p1, p2)
    assert mid.x == pytest.approx(2.5)
    assert mid.y == pytest.approx(4.0)


def test_point_to_line_and_projection() -> None:
    # Line: x - y = 0  (normalized unit normal)
    line = Line2D.from_points(Point2D(0.0, 0.0), Point2D(1.0, 1.0))
    assert line is not None

    p = Point2D(0.0, 2.0)
    assert distance_point_to_line(p, line) == pytest.approx(math.sqrt(2.0))

    proj = project_point_on_line(p, line)
    assert proj.x == pytest.approx(1.0)
    assert proj.y == pytest.approx(1.0)
    assert distance_point_to_line(proj, line) == pytest.approx(0.0, abs=EPSILON)


def test_vector_algebra_and_metrics() -> None:
    u = Vector2D(3.0, 4.0)
    v = Vector2D(-4.0, 3.0)

    assert vector_norm(u) == pytest.approx(5.0)
    assert dot_product(u, v) == pytest.approx(0.0)
    assert are_vectors_orthogonal(u, v)
    assert determinant_2d(u, v) == pytest.approx(25.0)
    assert not are_vectors_collinear(u, v)

    w = Vector2D(6.0, 8.0)
    assert are_vectors_collinear(u, w)
    assert not are_vectors_orthogonal(u, w)


def test_angle_between_vectors_signed_and_unsigned() -> None:
    ux = Vector2D(1.0, 0.0)
    uy = Vector2D(0.0, 1.0)

    # Unsigned
    assert angle_between_vectors(ux, uy) == pytest.approx(math.pi / 2.0)
    assert angle_between_vectors(uy, ux) == pytest.approx(math.pi / 2.0)

    # Signed
    assert angle_between_vectors(ux, uy, signed=True) == pytest.approx(math.pi / 2.0)
    assert angle_between_vectors(uy, ux, signed=True) == pytest.approx(-math.pi / 2.0)

    # Opposite vectors
    neg_ux = Vector2D(-1.0, 0.0)
    assert angle_between_vectors(ux, neg_ux) == pytest.approx(math.pi)

    # Degenerate zero vector
    zero = Vector2D(0.0, 0.0)
    assert angle_between_vectors(zero, ux) == 0.0


def test_collinear_points() -> None:
    p1 = Point2D(0.0, 0.0)
    p2 = Point2D(2.0, 2.0)
    p3 = Point2D(5.0, 5.0)
    p4 = Point2D(5.0, 6.0)

    assert are_points_collinear(p1, p2, p3)
    assert not are_points_collinear(p1, p2, p4)


def test_line_equations_and_slope_intercept() -> None:
    # 2x - y + 3 = 0 -> y = 2x + 3
    line = Line2D(2.0, -1.0, 3.0)

    assert not line_is_vertical(line)
    assert not line_is_horizontal(line)
    assert line_slope(line) == pytest.approx(2.0)
    assert line_y_intercept(line) == pytest.approx(3.0)
    assert line_x_intercept(line) == pytest.approx(-1.5)

    analysis = analyze_line(line)
    assert "x" in analysis.cartesian_equation
    assert "y" in analysis.cartesian_equation
    assert analysis.slope_intercept_equation == "y = 2x + 3"


def test_vertical_and_horizontal_lines() -> None:
    # Vertical line: x = 4 -> 1*x + 0*y - 4 = 0
    v_line = Line2D(1.0, 0.0, -4.0)
    assert line_is_vertical(v_line)
    assert not line_is_horizontal(v_line)
    assert line_slope(v_line) is None
    assert line_y_intercept(v_line) is None
    assert line_x_intercept(v_line) == pytest.approx(4.0)
    assert format_slope_intercept_line(v_line) == "x = 4"

    # Horizontal line: y = -3 -> 0*x + 1*y + 3 = 0
    h_line = Line2D(0.0, 1.0, 3.0)
    assert not line_is_vertical(h_line)
    assert line_is_horizontal(h_line)
    assert line_slope(h_line) == pytest.approx(0.0)
    assert line_y_intercept(h_line) == pytest.approx(-3.0)
    assert line_x_intercept(h_line) is None
    assert format_slope_intercept_line(h_line) == "y = -3"


def test_line_relationships_angle_parallel_orthogonal() -> None:
    l1 = Line2D(1.0, 1.0, 0.0)  # x + y = 0
    l2 = Line2D(1.0, 1.0, -5.0)  # x + y - 5 = 0
    l3 = Line2D(1.0, -1.0, 0.0)  # x - y = 0
    l4 = Line2D(1.0, 0.0, 0.0)  # x = 0

    assert are_lines_parallel(l1, l2)
    assert not are_lines_parallel(l1, l3)
    assert are_lines_orthogonal(l1, l3)
    assert not are_lines_orthogonal(l1, l2)

    assert angle_between_lines(l1, l2) == pytest.approx(0.0, abs=ANGLE_EPSILON)
    assert angle_between_lines(l1, l3) == pytest.approx(math.pi / 2.0, abs=ANGLE_EPSILON)
    assert angle_between_lines(l1, l4) == pytest.approx(math.pi / 4.0, abs=ANGLE_EPSILON)


def test_circle_analytical_forms() -> None:
    c1 = Circle2D(Point2D(2.0, -3.0), 5.0)

    assert circle_perimeter(c1) == pytest.approx(10.0 * math.pi)
    assert circle_area(c1) == pytest.approx(25.0 * math.pi)

    canonical = format_circle_canonical(c1)
    assert canonical == "(x - 2)² + (y + 3)² = 25"

    general = format_circle_general(c1)
    assert "x² + y² - 4x + 6y - 12 = 0" in general

    analysis = analyze_circle(c1)
    assert analysis.radius == 5.0
    assert analysis.canonical_equation == canonical


def test_segment_and_ray_analysis() -> None:
    p1 = Point2D(0.0, 0.0)
    p2 = Point2D(3.0, 4.0)
    seg = Segment2D(p1, p2)
    ray = Ray2D(p1, p2)

    s_res = analyze_segment(seg)
    assert s_res["length"] == pytest.approx(5.0)
    assert s_res["midpoint_x"] == pytest.approx(1.5)
    assert s_res["midpoint_y"] == pytest.approx(2.0)

    r_res = analyze_ray(ray)
    assert r_res["origin_x"] == pytest.approx(0.0)
    assert r_res["origin_y"] == pytest.approx(0.0)


# ============================================================================
# PropertiesPanel Analytics UI Integration Tests
# ============================================================================


def _get_analytics_rows(panel: PropertiesPanel) -> dict[str, str]:
    rows: dict[str, str] = {}
    form = panel._analytics_form
    for i in range(form.rowCount()):
        label_item = form.itemAt(i, form.ItemRole.LabelRole)
        field_item = form.itemAt(i, form.ItemRole.FieldRole)
        if label_item is not None and field_item is not None:
            lbl_widget = label_item.widget()
            val_widget = field_item.widget()
            if isinstance(lbl_widget, QLabel) and isinstance(val_widget, QLabel):
                assert (
                    val_widget.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse
                )
                rows[lbl_widget.text()] = val_widget.text()
    return rows


def test_properties_panel_analytics_single_point(qapp: object) -> None:
    doc = Document()
    oid = str(uuid4())
    obj = GeoObject(id=oid, name="A", kind="point", params={"x": 3.0, "y": 4.0}, style=Style())
    doc.add(obj)

    panel = PropertiesPanel(doc, lambda cmd: None)
    panel.set_selection({oid})

    assert not panel._analytics_widget.isHidden()
    rows = _get_analytics_rows(panel)
    assert "Coordonnées" in rows
    assert rows["Coordonnées"] == "(3, 4)"
    assert "Coordonnées polaires" in rows
    assert "r = 5" in rows["Coordonnées polaires"]


def test_properties_panel_analytics_single_line(qapp: object) -> None:
    doc = Document()
    p1 = doc.add(
        GeoObject(
            id=str(uuid4()), name="A", kind="point", params={"x": 0.0, "y": 2.0}, style=Style()
        )
    )
    p2 = doc.add(
        GeoObject(
            id=str(uuid4()), name="B", kind="point", params={"x": 2.0, "y": 4.0}, style=Style()
        )
    )
    oid = str(uuid4())
    doc.add(GeoObject(id=oid, name="d", kind="line", dependencies=(p1.id, p2.id), style=Style()))

    panel = PropertiesPanel(doc, lambda cmd: None)
    panel.set_selection({oid})

    assert not panel._analytics_widget.isHidden()
    rows = _get_analytics_rows(panel)
    assert "Équation cartésienne" in rows
    assert "Équation réduite" in rows
    assert "Pente" in rows
    assert "Vecteur directeur" in rows


def test_properties_panel_analytics_single_circle(qapp: object) -> None:
    doc = Document()
    p_center = doc.add(
        GeoObject(
            id=str(uuid4()), name="O", kind="point", params={"x": 0.0, "y": 0.0}, style=Style()
        )
    )
    oid = str(uuid4())
    doc.add(
        GeoObject(
            id=oid,
            name="C",
            kind="circle_radius",
            dependencies=(p_center.id,),
            params={"radius": 3.0},
            style=Style(),
        )
    )

    panel = PropertiesPanel(doc, lambda cmd: None)
    panel.set_selection({oid})

    assert not panel._analytics_widget.isHidden()
    rows = _get_analytics_rows(panel)
    assert "Équation canonique" in rows
    assert rows["Équation canonique"] == "x² + y² = 9"
    assert "Rayon" in rows
    assert rows["Rayon"] == "3"
    assert "Périmètre" in rows
    assert "Aire" in rows


def test_properties_panel_analytics_two_points(qapp: object) -> None:
    doc = Document()
    id1, id2 = str(uuid4()), str(uuid4())
    doc.add(GeoObject(id=id1, name="A", kind="point", params={"x": 0.0, "y": 0.0}, style=Style()))
    doc.add(GeoObject(id=id2, name="B", kind="point", params={"x": 6.0, "y": 8.0}, style=Style()))

    panel = PropertiesPanel(doc, lambda cmd: None)
    panel.set_selection({id1, id2})

    assert not panel._analytics_widget.isHidden()
    rows = _get_analytics_rows(panel)
    assert "Distance" in rows
    assert rows["Distance"] == "10"
    assert "Milieu" in rows
    assert rows["Milieu"] == "(3, 4)"


def test_properties_panel_analytics_point_and_line(qapp: object) -> None:
    doc = Document()
    id_p, id_l = str(uuid4()), str(uuid4())
    doc.add(GeoObject(id=id_p, name="P", kind="point", params={"x": 0.0, "y": 5.0}, style=Style()))
    p1 = doc.add(
        GeoObject(
            id=str(uuid4()), name="A", kind="point", params={"x": 0.0, "y": 0.0}, style=Style()
        )
    )
    p2 = doc.add(
        GeoObject(
            id=str(uuid4()), name="B", kind="point", params={"x": 1.0, "y": 0.0}, style=Style()
        )
    )
    doc.add(GeoObject(id=id_l, name="d", kind="line", dependencies=(p1.id, p2.id), style=Style()))

    panel = PropertiesPanel(doc, lambda cmd: None)
    panel.set_selection({id_p, id_l})

    assert not panel._analytics_widget.isHidden()
    rows = _get_analytics_rows(panel)
    assert "Distance" in rows
    assert rows["Distance"] == "5"
    assert "Projection" in rows
    assert rows["Projection"] == "(0, 0)"


def test_properties_panel_analytics_two_lines(qapp: object) -> None:
    doc = Document()
    id1, id2 = str(uuid4()), str(uuid4())
    pa1 = doc.add(
        GeoObject(
            id=str(uuid4()), name="A1", kind="point", params={"x": 0.0, "y": 0.0}, style=Style()
        )
    )
    pa2 = doc.add(
        GeoObject(
            id=str(uuid4()), name="A2", kind="point", params={"x": 0.0, "y": 1.0}, style=Style()
        )
    )
    pb1 = doc.add(
        GeoObject(
            id=str(uuid4()), name="B1", kind="point", params={"x": 0.0, "y": 0.0}, style=Style()
        )
    )
    pb2 = doc.add(
        GeoObject(
            id=str(uuid4()), name="B2", kind="point", params={"x": 1.0, "y": 0.0}, style=Style()
        )
    )
    doc.add(GeoObject(id=id1, name="d1", kind="line", dependencies=(pa1.id, pa2.id), style=Style()))
    doc.add(GeoObject(id=id2, name="d2", kind="line", dependencies=(pb1.id, pb2.id), style=Style()))

    panel = PropertiesPanel(doc, lambda cmd: None)
    panel.set_selection({id1, id2})

    assert not panel._analytics_widget.isHidden()
    rows = _get_analytics_rows(panel)
    assert "Angle" in rows
    assert "90°" in rows["Angle"]
    assert "Orthogonales" in rows
    assert rows["Orthogonales"] == "Oui"
    assert "Intersection" in rows
    assert rows["Intersection"] == "(0, 0)"


def test_properties_panel_analytics_point_and_circle(qapp: object) -> None:
    doc = Document()
    id_center = str(uuid4())
    doc.add(
        GeoObject(id=id_center, name="O", kind="point", params={"x": 0.0, "y": 0.0}, style=Style())
    )
    id_c = str(uuid4())
    doc.add(
        GeoObject(
            id=id_c,
            name="C",
            kind="circle_radius",
            dependencies=(id_center,),
            params={"radius": 5.0},
            style=Style(),
        )
    )

    id_on, id_in, id_out = str(uuid4()), str(uuid4()), str(uuid4())
    doc.add(
        GeoObject(id=id_on, name="P1", kind="point", params={"x": 3.0, "y": 4.0}, style=Style())
    )
    doc.add(
        GeoObject(id=id_in, name="P2", kind="point", params={"x": 1.0, "y": 1.0}, style=Style())
    )
    doc.add(
        GeoObject(id=id_out, name="P3", kind="point", params={"x": 10.0, "y": 0.0}, style=Style())
    )

    panel = PropertiesPanel(doc, lambda cmd: None)

    panel.set_selection({id_c, id_on})
    rows = _get_analytics_rows(panel)
    assert rows["Position"] == "Sur le cercle"

    panel.set_selection({id_c, id_in})
    rows = _get_analytics_rows(panel)
    assert rows["Position"] == "Intérieur"

    panel.set_selection({id_c, id_out})
    rows = _get_analytics_rows(panel)
    assert rows["Position"] == "Extérieur"


def test_properties_panel_analytics_three_points(qapp: object) -> None:
    doc = Document()
    id1, id2, id3, id4 = str(uuid4()), str(uuid4()), str(uuid4()), str(uuid4())
    doc.add(GeoObject(id=id1, name="A", kind="point", params={"x": 1.0, "y": 1.0}, style=Style()))
    doc.add(GeoObject(id=id2, name="B", kind="point", params={"x": 2.0, "y": 2.0}, style=Style()))
    doc.add(GeoObject(id=id3, name="C", kind="point", params={"x": 3.0, "y": 3.0}, style=Style()))
    doc.add(GeoObject(id=id4, name="D", kind="point", params={"x": 3.0, "y": 4.0}, style=Style()))

    panel = PropertiesPanel(doc, lambda cmd: None)

    panel.set_selection({id1, id2, id3})
    rows = _get_analytics_rows(panel)
    assert rows["Colinéaires"] == "Oui"

    panel.set_selection({id1, id2, id4})
    rows = _get_analytics_rows(panel)
    assert rows["Colinéaires"] == "Non"


def test_properties_panel_analytics_empty_selection(qapp: object) -> None:
    doc = Document()
    panel = PropertiesPanel(doc, lambda cmd: None)
    panel.set_selection(set())
    assert not panel._analytics_widget.isVisible()
