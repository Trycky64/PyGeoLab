"""Unit tests for parametric curves.

Tests ParametricFunctionObject, sampling, hit-testing, persistence, and UI.
"""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtGui import QColor, QImage, QPainter, QPalette

from pygeolab.commands import (
    ChangeFunctionCommand,
    ChangeNumberValueCommand,
    CommandHistory,
    CreateObjectCommand,
)
from pygeolab.exporting.viewport_export import fitted_viewport
from pygeolab.geometry import Point2D
from pygeolab.math_engine.functions import ParametricFunctionObject
from pygeolab.math_engine.sampling import sample_parametric
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.persistence.loader import load_project, save_project
from pygeolab.persistence.serializer import serialize_document
from pygeolab.persistence.validation import validate_project
from pygeolab.rendering.hit_test import first_hit
from pygeolab.rendering.renderer import Renderer
from pygeolab.rendering.viewport import Viewport
from pygeolab.ui.algebra_panel import AlgebraPanel
from pygeolab.ui.dialogs.parametric_dialog import ParametricFunctionDialog
from pygeolab.ui.properties_panel import PropertiesPanel

# ==============================================================================
# Model & Math Engine Tests
# ==============================================================================


def test_parametric_model_creation_and_evaluation() -> None:
    curve = ParametricFunctionObject.from_source(
        name="c",
        parameter="t",
        x_source="cos(t)",
        y_source="sin(t)",
        t_min=0.0,
        t_max=2.0 * math.pi,
    )
    assert curve.name == "c"
    assert curve.parameter == "t"
    assert curve.external_dependencies == frozenset()

    p0 = curve.evaluate(0.0)
    assert math.isclose(p0.x, 1.0, abs_tol=1e-7)
    assert math.isclose(p0.y, 0.0, abs_tol=1e-7)

    p_half_pi = curve.evaluate(math.pi / 2.0)
    assert math.isclose(p_half_pi.x, 0.0, abs_tol=1e-7)
    assert math.isclose(p_half_pi.y, 1.0, abs_tol=1e-7)


def test_parametric_model_with_slider_dependencies() -> None:
    curve = ParametricFunctionObject.from_source(
        name="ellipse",
        parameter="t",
        x_source="a * cos(t)",
        y_source="b * sin(t)",
        t_min=0.0,
        t_max=2.0 * math.pi,
    )
    assert curve.external_dependencies == frozenset({"a", "b"})

    pt = curve.evaluate(0.0, {"a": 4.0, "b": 2.5})
    assert math.isclose(pt.x, 4.0)
    assert math.isclose(pt.y, 0.0)


def test_parametric_model_invalid_domain_and_syntax() -> None:
    import pytest

    with pytest.raises(ValueError, match="Domaine paramétrique invalide"):
        ParametricFunctionObject.from_source("c", "t", "t", "t", t_min=5.0, t_max=2.0)

    with pytest.raises(ValueError, match="Nom de courbe ou paramètre invalide"):
        ParametricFunctionObject.from_source("", "t", "t", "t", 0.0, 1.0)

    with pytest.raises(ValueError, match="Nom de courbe ou paramètre invalide"):
        ParametricFunctionObject.from_source("c", "123bad", "t", "t", 0.0, 1.0)


# ==============================================================================
# Sampling & Discontinuities
# ==============================================================================


def test_parametric_sampling_smooth() -> None:
    curve = ParametricFunctionObject.from_source(
        name="circle",
        parameter="t",
        x_source="cos(t)",
        y_source="sin(t)",
        t_min=0.0,
        t_max=2.0 * math.pi,
    )
    sampled = sample_parametric(curve, samples=200)
    assert len(sampled.segments) == 1
    assert len(sampled.segments[0]) == 200


def test_parametric_sampling_discontinuity() -> None:
    curve = ParametricFunctionObject.from_source(
        name="disc",
        parameter="t",
        x_source="1 / t",
        y_source="t",
        t_min=-2.0,
        t_max=2.0,
    )
    sampled = sample_parametric(curve, samples=300)
    # The pole at t=0 must split the curve into at least 2 distinct segments
    assert len(sampled.segments) >= 2


# ==============================================================================
# Document & Dependency Graph Integration
# ==============================================================================


def test_document_parametric_dependency_and_update() -> None:
    doc = Document("Parametric Test")
    history = CommandHistory()

    slider_a = GeoObject("number", "a", params={"value": 3.0, "minimum": 1.0, "maximum": 10.0})
    slider_b = GeoObject("number", "b", params={"value": 2.0, "minimum": 1.0, "maximum": 10.0})
    doc.add(slider_a)
    doc.add(slider_b)

    curve_obj = GeoObject(
        "parametric",
        "c",
        dependencies=(slider_a.id, slider_b.id),
        params={
            "parameter": "t",
            "x_source": "a * cos(t)",
            "y_source": "b * sin(t)",
            "t_min": 0.0,
            "t_max": 2.0 * math.pi,
        },
    )
    history.execute(CreateObjectCommand(doc, curve_obj))

    assert doc.get(curve_obj.id).valid
    geom = doc.get(curve_obj.id).geometry
    assert isinstance(geom, ParametricFunctionObject)

    # Change slider a value and verify dynamic update
    history.execute(ChangeNumberValueCommand(doc, slider_a.id, 5.0))
    assert doc.get(slider_a.id).geometry == 5.0

    # Undo
    history.undo()
    assert doc.get(slider_a.id).geometry == 3.0


# ==============================================================================
# Hit-Testing
# ==============================================================================


def test_parametric_hit_test() -> None:
    doc = Document("Hit Test")
    curve_obj = GeoObject(
        "parametric",
        "c",
        (),
        {
            "parameter": "t",
            "x_source": "4 * cos(t)",
            "y_source": "3 * sin(t)",
            "t_min": 0.0,
            "t_max": 2.0 * math.pi,
        },
    )
    doc.add(curve_obj)

    viewport = Viewport(center=Point2D(0.0, 0.0), scale=40.0, width=800, height=600)

    # Point (4, 0) is on the curve: screen coords: x = 400 + 4*40 = 560, y = 300
    hit = first_hit(doc, viewport, 560, 300, kinds=frozenset({"parametric"}))
    assert hit is not None and hit.id == curve_obj.id

    # Far away point (0, 0)
    hit_miss = first_hit(doc, viewport, 400, 300, kinds=frozenset({"parametric"}))
    assert hit_miss is None


# ==============================================================================
# Rendering & Export
# ==============================================================================


def test_parametric_rendering_and_fitted_viewport(qapp: object) -> None:
    del qapp
    doc = Document("Render Test")
    curve_obj = GeoObject(
        "parametric",
        "c",
        (),
        {
            "parameter": "t",
            "x_source": "cos(t)",
            "y_source": "sin(t)",
            "t_min": 0.0,
            "t_max": 2.0 * math.pi,
        },
    )
    doc.add(curve_obj)

    fitted = fitted_viewport(doc, 400, 300)
    assert fitted is not None

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


def test_parametric_persistence_roundtrip(tmp_path: Path) -> None:
    doc = Document("Persistence Test")
    a = GeoObject("number", "k", params={"value": 2.5, "minimum": 0.1, "maximum": 10.0})
    doc.add(a)

    curve_obj = GeoObject(
        "parametric",
        "spiral",
        (a.id,),
        {
            "parameter": "t",
            "x_source": "k * t * cos(t)",
            "y_source": "k * t * sin(t)",
            "t_min": 0.0,
            "t_max": 4.0 * math.pi,
        },
    )
    doc.add(curve_obj)

    raw = serialize_document(doc)
    validated = validate_project(raw)
    assert validated is not None

    path = tmp_path / "parametric.pgl"
    save_project(doc, path)

    loaded = load_project(path)
    assert len(loaded.objects) == 2
    loaded_c = loaded.get(curve_obj.id)
    assert loaded_c.kind == "parametric"
    assert isinstance(loaded_c.geometry, ParametricFunctionObject)
    assert loaded_c.geometry.x_source == "k * t * cos(t)"
    assert loaded_c.geometry.y_source == "k * t * sin(t)"


# ==============================================================================
# Undo / Redo & Editing
# ==============================================================================


def test_parametric_undo_redo_editing() -> None:
    doc = Document("Undo Test")
    history = CommandHistory()

    curve_obj = GeoObject(
        "parametric",
        "c",
        (),
        {
            "parameter": "t",
            "x_source": "t",
            "y_source": "t^2",
            "t_min": -2.0,
            "t_max": 2.0,
        },
    )
    history.execute(CreateObjectCommand(doc, curve_obj))
    assert doc.get(curve_obj.id).geometry.x_source == "t"

    # Edit expression
    new_params = {
        "parameter": "t",
        "x_source": "t",
        "y_source": "t^3",
        "t_min": -2.0,
        "t_max": 2.0,
    }
    history.execute(ChangeFunctionCommand(doc, curve_obj.id, "c", (), new_params))
    assert doc.get(curve_obj.id).geometry.y_source == "t^3"

    history.undo()
    assert doc.get(curve_obj.id).geometry.y_source == "t^2"

    history.redo()
    assert doc.get(curve_obj.id).geometry.y_source == "t^3"


# ==============================================================================
# UI Integration: Dialog, Algebra & Properties Panel
# ==============================================================================


def test_parametric_dialog_and_panels(qtbot) -> None:
    doc = Document("UI Test")
    dialog = ParametricFunctionDialog(doc)
    qtbot.addWidget(dialog)

    dialog.name_edit.setText("gamma")
    dialog.param_edit.setText("u")
    dialog.x_edit.setText("cos(u)")
    dialog.y_edit.setText("sin(u)")
    dialog.t_min_spin.setValue(0.0)
    dialog.t_max_spin.setValue(6.28)

    obj = dialog.object_definition()
    assert obj.kind == "parametric"
    assert obj.name == "gamma"
    assert obj.params["parameter"] == "u"

    doc.add(obj)

    # Algebra panel
    algebra = AlgebraPanel(doc, lambda cmd: None)
    qtbot.addWidget(algebra)
    algebra.refresh()
    assert algebra._category(doc.get(obj.id).geometry) == "Courbes paramétriques"

    # Properties panel
    properties = PropertiesPanel(doc, lambda cmd: None)
    qtbot.addWidget(properties)
    properties.set_selection(frozenset({obj.id}))
    assert not properties._analytics_widget.isHidden()


def test_main_window_parametric_actions(qapp: object, monkeypatch) -> None:
    del qapp
    from PySide6.QtWidgets import QDialog

    from pygeolab.ui.main_window import MainWindow

    window = MainWindow(offer_recovery=False)

    created = GeoObject(
        "parametric",
        "c_mw",
        (),
        {
            "parameter": "t",
            "x_source": "cos(t)",
            "y_source": "sin(t)",
            "t_min": 0.0,
            "t_max": 2.0 * math.pi,
        },
    )
    monkeypatch.setattr(ParametricFunctionDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(ParametricFunctionDialog, "object_definition", lambda self: created)
    monkeypatch.setattr(
        ParametricFunctionDialog,
        "definition",
        lambda self: (
            "c_edited",
            (),
            {
                "parameter": "t",
                "x_source": "2 * cos(t)",
                "y_source": "2 * sin(t)",
                "t_min": 0.0,
                "t_max": 2.0 * math.pi,
            },
        ),
    )

    window._new_parametric()
    assert window.document.get(created.id).kind == "parametric"

    window.geometry_view.set_selected_ids({created.id})
    window._edit_parametric()
    assert window.document.get(created.id).name == "c_edited"
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)
    window.close()
