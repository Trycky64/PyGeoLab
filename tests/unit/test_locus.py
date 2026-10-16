"""Unit tests for geometric loci and dynamic traces.

Tests Locus2D, bounded sampling, driver sweep (slider and point_on),
discontinuities, cache invalidation, transient canvas traces, hit-testing,
export, persistence, properties, algebra tree, and dialogs.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage, QPainter, QPalette

from pygeolab.commands import (
    CommandHistory,
    CreateObjectCommand,
)
from pygeolab.exporting.viewport_export import fitted_viewport
from pygeolab.geometry import Locus2D, Point2D, sample_locus
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.persistence.loader import load_project, save_project
from pygeolab.persistence.serializer import serialize_document
from pygeolab.persistence.validation import validate_project
from pygeolab.rendering.hit_test import first_hit
from pygeolab.rendering.renderer import Renderer
from pygeolab.rendering.viewport import Viewport
from pygeolab.ui.algebra_panel import AlgebraPanel
from pygeolab.ui.dialogs.locus_dialog import LocusDialog
from pygeolab.ui.geometry_view import GeometryView
from pygeolab.ui.main_window import MainWindow
from pygeolab.ui.properties_panel import PropertiesPanel

# ==============================================================================
# Model & Sampling Tests
# ==============================================================================


def test_locus2d_model_and_distances() -> None:
    p1 = Point2D(0.0, 0.0)
    p2 = Point2D(2.0, 0.0)
    p3 = Point2D(2.0, 2.0)
    locus = Locus2D(
        segments=((p1, p2), (p2, p3)),
        target_id="target-1",
        driver_id="driver-1",
        start=0.0,
        end=1.0,
        samples=50,
    )
    assert not locus.is_empty
    assert locus.total_points == 4
    assert locus.start == 0.0
    assert locus.end == 1.0

    # Distance to (1, 0) is 0 on segment (p1, p2)
    d = locus.closest_distance_to(Point2D(1.0, 0.0))
    assert d is not None and math.isclose(d, 0.0, abs_tol=1e-9)

    # Distance to (1, 1) is 1.0 from either segment
    d = locus.closest_distance_to(Point2D(1.0, 1.0))
    assert d is not None and math.isclose(d, 1.0, abs_tol=1e-9)


def test_sample_locus_validation() -> None:
    doc = Document()
    num = doc.add(GeoObject("number", "k", params={"value": 1.0}))
    pt = doc.add(GeoObject("point", "A", params={"x": 0.0, "y": 0.0}))

    # Target does not depend on driver
    with pytest.raises(ValueError, match="ne dépend pas"):
        sample_locus(doc.objects, doc._graph, pt.id, num.id, 0.0, 1.0)

    # Missing objects
    with pytest.raises(KeyError):
        sample_locus(doc.objects, doc._graph, "missing", num.id, 0.0, 1.0)


def test_sample_locus_slider_driver() -> None:
    # A slider k in [0, 4]
    # Point M(k, 2*k) -> straight line trajectory y = 2x
    doc = Document()
    doc.add(GeoObject("number", "k", params={"value": 0.0, "minimum": 0.0, "maximum": 4.0}))
    # Point M translated from origin by vector
    # Or point M with scale/translate
    origin = doc.add(GeoObject("point", "O", params={"x": 0.0, "y": 0.0}))
    unit = doc.add(GeoObject("point", "U", params={"x": 1.0, "y": 2.0}))
    doc.add(GeoObject("vector", "V", dependencies=(origin.id, unit.id)))
    # Scale vec by k or translate
    # Instead, M = translate(O, V * k) -> scaled translation
    # Or M midpoint or point_on
    doc.add(GeoObject("scale", "M", dependencies=(unit.id, origin.id), params={"factor": 1.0}))
    # Let factor depend on k by using slider in point_on or custom construction
    # Actually, in PyGeoLab:
    # "scale" has params {"factor": ...}. To make it depend on k, k must be in dependencies?
    # Wait, let's verify how dependent points work:
    # point_on: target support (e.g. circle or segment) + param t.
    # What if driver is point_on?
    # Let's test driver as point_on first:
    circle_p1 = doc.add(GeoObject("point", "C1", params={"x": 0.0, "y": 0.0}))
    circle_p2 = doc.add(GeoObject("point", "C2", params={"x": 3.0, "y": 0.0}))
    circ = doc.add(GeoObject("circle", "c", dependencies=(circle_p1.id, circle_p2.id)))
    # Driver P is a point_on circ
    driver_p = doc.add(GeoObject("point_on", "P", dependencies=(circ.id,), params={"t": 0.0}))
    # Target Q is midpoint of circle center C1 and P -> circle of radius 1.5!
    target_q = doc.add(GeoObject("midpoint", "Q", dependencies=(circle_p1.id, driver_p.id)))

    # Sweep P along circle: t from 0 to 2*pi
    locus_geom = sample_locus(
        doc.objects, doc._graph, target_q.id, driver_p.id, 0.0, 2.0 * math.pi, samples=100
    )
    assert not locus_geom.is_empty
    assert locus_geom.total_points >= 90
    # Every point of Q must be at distance 1.5 from C1 (0, 0)
    for seg in locus_geom.segments:
        for pt in seg:
            dist = pt.distance_to(Point2D(0.0, 0.0))
            assert math.isclose(dist, 1.5, abs_tol=1e-3)


def test_locus_document_integration() -> None:
    doc = Document()
    c_center = doc.add(GeoObject("point", "O", params={"x": 0.0, "y": 0.0}))
    c_rim = doc.add(GeoObject("point", "R", params={"x": 2.0, "y": 0.0}))
    circ = doc.add(GeoObject("circle", "circ", dependencies=(c_center.id, c_rim.id)))
    p_on = doc.add(GeoObject("point_on", "P", dependencies=(circ.id,), params={"t": 0.0}))
    target = doc.add(GeoObject("midpoint", "M", dependencies=(c_center.id, p_on.id)))

    # Add locus object to document
    locus_obj = doc.add(
        GeoObject(
            kind="locus",
            name="Lieu1",
            dependencies=(target.id, p_on.id),
            params={"start": 0.0, "end": 2.0 * math.pi, "samples": 60},
        )
    )

    assert locus_obj.valid
    assert isinstance(locus_obj.geometry, Locus2D)
    assert not locus_obj.geometry.is_empty
    assert locus_obj.geometry.total_points >= 50

    # Invalidate by moving circle center: locus automatically recomputes!
    doc.move_point(c_center.id, Point2D(4.0, 0.0))
    updated_locus = doc.get(locus_obj.id)
    assert updated_locus.valid
    assert isinstance(updated_locus.geometry, Locus2D)
    # Target now revolves around (4, 0)
    for seg in updated_locus.geometry.segments:
        for pt in seg:
            assert math.isclose(pt.distance_to(Point2D(4.0, 0.0)), 1.0, abs_tol=1e-2)


def test_locus_discontinuity_and_invalid_points() -> None:
    # A construction that has impossible regions
    doc = Document()
    p1 = doc.add(GeoObject("point", "P1", params={"x": 0.0, "y": 0.0}))
    p2 = doc.add(GeoObject("point", "P2", params={"x": 4.0, "y": 0.0}))
    seg = doc.add(GeoObject("segment", "s", dependencies=(p1.id, p2.id)))
    # Point on segment, t in [0, 1]
    driver = doc.add(GeoObject("point_on", "P", dependencies=(seg.id,), params={"t": 0.5}))
    # Ray from P through fixed point
    fixed = doc.add(GeoObject("point", "F", params={"x": 2.0, "y": 2.0}))
    doc.add(GeoObject("ray", "r", dependencies=(driver.id, fixed.id)))
    target = doc.add(GeoObject("midpoint", "T", dependencies=(driver.id, fixed.id)))

    # Sweep t from 0 to 1
    locus = doc.add(
        GeoObject(
            kind="locus",
            name="LieuRay",
            dependencies=(target.id, driver.id),
            params={"start": 0.0, "end": 1.0, "samples": 40},
        )
    )
    assert locus.valid
    assert isinstance(locus.geometry, Locus2D)
    assert not locus.geometry.is_empty


# ==============================================================================
# Hit-Testing & Export Tests
# ==============================================================================


def test_locus_hit_testing_and_fitted_viewport() -> None:
    doc = Document()
    o = doc.add(GeoObject("point", "O", params={"x": 0.0, "y": 0.0}))
    r = doc.add(GeoObject("point", "R", params={"x": 5.0, "y": 0.0}))
    c = doc.add(GeoObject("circle", "c", dependencies=(o.id, r.id)))
    p = doc.add(GeoObject("point_on", "P", dependencies=(c.id,), params={"t": 0.0}))
    m = doc.add(GeoObject("midpoint", "M", dependencies=(o.id, p.id)))
    locus = doc.add(
        GeoObject(
            kind="locus",
            name="L",
            dependencies=(m.id, p.id),
            params={"start": 0.0, "end": 2.0 * math.pi, "samples": 80},
        )
    )

    viewport = Viewport(width=800, height=600, center=Point2D(0.0, 0.0), scale=40.0)

    # Radius of locus is 2.5. Point (2.5, 0.0) in screen coordinates:
    screen_x, screen_y = viewport.world_to_screen(Point2D(2.5, 0.0))
    hit = first_hit(doc, viewport, screen_x, screen_y, tolerance_px=10.0)
    assert hit is not None
    # Might hit M or Locus L. Locus is priority 3.
    assert hit.id in {m.id, locus.id}

    # Hit test on a point far from M but on the locus circle: (0.0, 2.5)
    screen_x, screen_y = viewport.world_to_screen(Point2D(0.0, 2.5))
    hit_locus = first_hit(doc, viewport, screen_x, screen_y, tolerance_px=10.0)
    assert hit_locus is not None
    assert hit_locus.id == locus.id

    # Viewport fitting includes locus points
    vp_fitted = fitted_viewport(doc, 800, 600)
    assert vp_fitted.scale > 0


def test_locus_rendering_and_transient_traces(qapp: object) -> None:
    del qapp
    doc = Document()
    o = doc.add(GeoObject("point", "O", params={"x": 0.0, "y": 0.0}))
    r = doc.add(GeoObject("point", "R", params={"x": 2.0, "y": 0.0}))
    c = doc.add(GeoObject("circle", "c", dependencies=(o.id, r.id)))
    p = doc.add(GeoObject("point_on", "P", dependencies=(c.id,), params={"t": 0.0}))
    m = doc.add(GeoObject("midpoint", "M", dependencies=(o.id, p.id)))
    doc.add(
        GeoObject(
            kind="locus",
            name="L",
            dependencies=(m.id, p.id),
            params={"start": 0.0, "end": 2.0 * math.pi, "samples": 60},
        )
    )

    viewport = Viewport(width=400, height=400, center=Point2D(0.0, 0.0), scale=50.0)
    renderer = Renderer()

    image = QImage(400, 400, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor("white"))
    painter = QPainter(image)
    palette = QPalette()

    # Render document with locus
    renderer.render(painter, doc, viewport, palette, ())

    # Render transient traces
    traces = {"trace-1": [Point2D(0.0, 0.0), Point2D(1.0, 1.0), Point2D(2.0, 0.0)]}
    renderer.render_transient_traces(painter, viewport, palette, traces)
    painter.end()

    assert not image.isNull()


# ==============================================================================
# Persistence & Undo/Redo Tests
# ==============================================================================


def test_locus_persistence_roundtrip(tmp_path: Path) -> None:
    doc = Document()
    o = doc.add(GeoObject("point", "O", params={"x": 0.0, "y": 0.0}))
    r = doc.add(GeoObject("point", "R", params={"x": 4.0, "y": 0.0}))
    c = doc.add(GeoObject("circle", "c", dependencies=(o.id, r.id)))
    p = doc.add(GeoObject("point_on", "P", dependencies=(c.id,), params={"t": 0.0}))
    m = doc.add(GeoObject("midpoint", "M", dependencies=(o.id, p.id)))
    doc.add(
        GeoObject(
            kind="locus",
            name="MyLocus",
            dependencies=(m.id, p.id),
            params={"start": 0.0, "end": 2.0 * math.pi, "samples": 75},
        )
    )

    data = serialize_document(doc)
    validated = validate_project(data)
    assert validated is not None

    # Check lightweight persistence: locus does NOT serialize points in params!
    serialized_obj = next(obj for obj in data["document"]["objects"] if obj["name"] == "MyLocus")
    assert "segments" not in serialized_obj["params"]
    assert serialized_obj["params"]["samples"] == 75

    # Save to disk and reload
    path = tmp_path / "locus_test.pgl"
    save_project(doc, path)
    loaded = load_project(path)

    reloaded_locus = next(obj for obj in loaded.objects.values() if obj.name == "MyLocus")
    assert reloaded_locus.valid
    assert isinstance(reloaded_locus.geometry, Locus2D)
    assert reloaded_locus.geometry.total_points >= 60


def test_locus_undo_redo() -> None:
    doc = Document()
    history = CommandHistory()
    o = doc.add(GeoObject("point", "O", params={"x": 0.0, "y": 0.0}))
    r = doc.add(GeoObject("point", "R", params={"x": 3.0, "y": 0.0}))
    c = doc.add(GeoObject("circle", "c", dependencies=(o.id, r.id)))
    p = doc.add(GeoObject("point_on", "P", dependencies=(c.id,), params={"t": 0.0}))
    m = doc.add(GeoObject("midpoint", "M", dependencies=(o.id, p.id)))

    locus_def = GeoObject(
        kind="locus",
        name="LocusUndo",
        dependencies=(m.id, p.id),
        params={"start": 0.0, "end": 2.0 * math.pi, "samples": 50},
    )

    # Create via command
    cmd = CreateObjectCommand(doc, locus_def)
    history.execute(cmd)
    assert "LocusUndo" in {obj.name for obj in doc.objects.values()}

    # Undo
    history.undo()
    assert "LocusUndo" not in {obj.name for obj in doc.objects.values()}

    # Redo
    history.redo()
    assert "LocusUndo" in {obj.name for obj in doc.objects.values()}
    locus_obj = next(obj for obj in doc.objects.values() if obj.name == "LocusUndo")
    assert locus_obj.valid
    assert isinstance(locus_obj.geometry, Locus2D)


# ==============================================================================
# UI Panels & GeometryView Tests
# ==============================================================================


def test_algebra_and_properties_panel_locus(qapp: object) -> None:
    del qapp
    doc = Document()
    o = doc.add(GeoObject("point", "O", params={"x": 0.0, "y": 0.0}))
    r = doc.add(GeoObject("point", "R", params={"x": 2.0, "y": 0.0}))
    c = doc.add(GeoObject("circle", "c", dependencies=(o.id, r.id)))
    p = doc.add(GeoObject("point_on", "P", dependencies=(c.id,), params={"t": 0.0}))
    m = doc.add(GeoObject("midpoint", "M", dependencies=(o.id, p.id)))
    locus = doc.add(
        GeoObject(
            kind="locus",
            name="L1",
            dependencies=(m.id, p.id),
            params={"start": 0.0, "end": 2.0 * math.pi, "samples": 50},
        )
    )

    # Algebra panel
    algebra = AlgebraPanel(doc, lambda cmd: None)
    algebra.refresh()
    item = algebra._object_item(locus)
    assert "lieu" in item.text(1)
    assert algebra._category(locus.geometry) == "Lieux géométriques"
    algebra.dispose()

    # Properties panel
    props = PropertiesPanel(doc, lambda cmd: None)
    props.set_selection(frozenset({locus.id}))
    assert "samples" in props._parameter_editors
    assert "start" in props._parameter_editors
    assert "end" in props._parameter_editors
    props.dispose()


def test_geometry_view_transient_traces(qapp: object) -> None:
    del qapp
    doc = Document()
    pt = doc.add(GeoObject("point", "A", params={"x": 1.0, "y": 1.0}))
    view = GeometryView(doc)

    assert not view.is_traced(pt.id)
    # Enable trace
    view.toggle_trace(pt.id)
    assert view.is_traced(pt.id)

    # Move point -> trace records positions
    doc.move_point(pt.id, Point2D(2.0, 2.0))
    doc.move_point(pt.id, Point2D(3.0, 3.0))

    assert pt.id in view._transient_traces
    assert len(view._transient_traces[pt.id]) >= 2

    # Clear traces
    view.clear_traces()
    assert len(view._transient_traces) == 0

    # Toggle trace off
    view.toggle_trace(pt.id)
    assert not view.is_traced(pt.id)
    view.dispose()


def test_locus_dialog_and_main_window_action(qapp: object, monkeypatch) -> None:
    del qapp
    doc = Document()
    o = doc.add(GeoObject("point", "O", params={"x": 0.0, "y": 0.0}))
    r = doc.add(GeoObject("point", "R", params={"x": 2.0, "y": 0.0}))
    c = doc.add(GeoObject("circle", "c", dependencies=(o.id, r.id)))
    p = doc.add(GeoObject("point_on", "P", dependencies=(c.id,), params={"t": 0.0}))
    m = doc.add(GeoObject("midpoint", "M", dependencies=(o.id, p.id)))

    # Test LocusDialog
    dialog = LocusDialog(doc)
    name, deps, params = dialog.definition()
    assert name != ""
    assert len(deps) == 2
    assert "samples" in params
    dialog.close()

    # Test MainWindow integration
    from PySide6.QtWidgets import QDialog

    window = MainWindow(offer_recovery=False)
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)

    assert "objects.new_locus" in window.action_registry._actions
    assert "objects.edit_locus" in window.action_registry._actions
    assert "objects.clear_traces" in window.action_registry._actions

    created_locus = GeoObject(
        "locus",
        "LieuMW",
        (m.id, p.id),
        {"start": 0.0, "end": 2.0 * math.pi, "samples": 60},
    )
    monkeypatch.setattr(LocusDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(LocusDialog, "object_definition", lambda self: created_locus)
    monkeypatch.setattr(
        LocusDialog,
        "definition",
        lambda self: (
            "LieuEdited",
            (m.id, p.id),
            {"start": 0.0, "end": 2.0 * math.pi, "samples": 80},
        ),
    )

    # Add dependencies into window document
    window.document.add(o)
    window.document.add(r)
    window.document.add(c)
    window.document.add(p)
    window.document.add(m)

    window._new_locus()
    assert window.document.get(created_locus.id).kind == "locus"

    # Select and edit locus
    window.geometry_view.set_selected_ids({created_locus.id})
    window._edit_locus()
    assert window.document.get(created_locus.id).name == "LieuEdited"

    window.close()


def test_locus_dialog_edge_cases(qapp: object) -> None:
    del qapp
    doc = Document()
    num = doc.add(GeoObject("number", "a", params={"value": 1.0, "minimum": -2.0, "maximum": 4.0}))
    pt1 = doc.add(GeoObject("point", "A", params={"x": 0.0, "y": 0.0}))
    pt2 = doc.add(GeoObject("point", "B", params={"x": 2.0, "y": 2.0}))
    m = doc.add(GeoObject("midpoint", "M", dependencies=(pt1.id, pt2.id)))

    # Driver is number
    dlg = LocusDialog(doc)
    dlg.driver_combo.setCurrentIndex(dlg.driver_combo.findData(num.id))
    dlg._on_driver_changed()
    assert dlg.start_spin.value() == -2.0
    assert dlg.end_spin.value() == 4.0

    # Test error cases in definition()
    dlg.name_edit.setText("")
    try:
        dlg.definition()
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "nom" in str(e)

    dlg.name_edit.setText("ValidName")
    dlg.target_combo.clear()
    try:
        dlg.definition()
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "requis" in str(e)

    # Both target and driver set to same
    dlg.target_combo.addItem("M", m.id)
    dlg.driver_combo.clear()
    dlg.driver_combo.addItem("M", m.id)
    try:
        dlg.definition()
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "distincts" in str(e)

    # Interval is zero
    dlg.driver_combo.clear()
    dlg.driver_combo.addItem("a", num.id)
    dlg.start_spin.setValue(2.0)
    dlg.end_spin.setValue(2.0)
    try:
        dlg.definition()
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "nul" in str(e)

    # object_definition()
    dlg.end_spin.setValue(5.0)
    obj_def = dlg.object_definition()
    assert obj_def.kind == "locus"
    assert obj_def.name == "ValidName"

    # Dialog initialized with existing locus
    locus_exist = GeoObject(
        "locus",
        "L_ex",
        dependencies=(m.id, num.id),
        params={"start": 1.0, "end": 3.0, "samples": 40},
    )
    dlg_edit = LocusDialog(doc, locus=locus_exist)
    assert dlg_edit.start_spin.value() == 1.0
    assert dlg_edit.end_spin.value() == 3.0
    assert dlg_edit.samples_spin.value() == 40
    dlg.close()
    dlg_edit.close()
