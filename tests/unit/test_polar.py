"""Unit tests for polar curves.

Tests PolarFunctionObject, sampling, hit-testing, persistence, and UI.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage, QPainter, QPalette

from pygeolab.commands import (
    ChangeFunctionCommand,
    ChangeNumberValueCommand,
    CommandHistory,
    CreateObjectCommand,
)
from pygeolab.exporting.viewport_export import fitted_viewport
from pygeolab.geometry import Point2D
from pygeolab.math_engine.functions import PolarFunctionObject
from pygeolab.math_engine.sampling import sample_polar
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.persistence.loader import load_project, save_project
from pygeolab.persistence.serializer import serialize_document
from pygeolab.persistence.validation import validate_project
from pygeolab.rendering.hit_test import first_hit
from pygeolab.rendering.renderer import Renderer
from pygeolab.rendering.viewport import Viewport
from pygeolab.ui.algebra_panel import AlgebraPanel
from pygeolab.ui.dialogs.polar_dialog import PolarFunctionDialog
from pygeolab.ui.properties_panel import PropertiesPanel

# ==============================================================================
# Model & Math Engine Tests
# ==============================================================================


def test_polar_function_model_and_evaluation() -> None:
    polar = PolarFunctionObject.from_source(
        name="r1",
        parameter="theta",
        r_source="1 + cos(theta)",
        theta_min=0.0,
        theta_max=2.0 * math.pi,
        use_degrees=False,
    )
    assert polar.name == "r1"
    assert polar.parameter == "theta"
    assert polar.theta_min == 0.0
    assert math.isclose(polar.theta_max, 2.0 * math.pi)
    assert polar.external_dependencies == frozenset()

    p0 = polar.evaluate(0.0)
    assert math.isclose(p0.x, 2.0, abs_tol=1e-7)
    assert math.isclose(p0.y, 0.0, abs_tol=1e-7)

    p_half_pi = polar.evaluate(math.pi / 2.0)
    assert math.isclose(p_half_pi.x, 0.0, abs_tol=1e-7)
    assert math.isclose(p_half_pi.y, 1.0, abs_tol=1e-7)

    p_pi = polar.evaluate(math.pi)
    assert math.isclose(p_pi.x, 0.0, abs_tol=1e-7)
    assert math.isclose(p_pi.y, 0.0, abs_tol=1e-7)


def test_polar_function_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        PolarFunctionObject.from_source("", "theta", "cos(theta)", 0.0, 1.0)

    with pytest.raises(ValueError):
        PolarFunctionObject.from_source("r", "123invalid", "cos(theta)", 0.0, 1.0)

    with pytest.raises(ValueError):
        PolarFunctionObject.from_source("r", "theta", "cos(theta)", 2.0, 1.0)

    polar = PolarFunctionObject.from_source("r", "theta", "1", 0.0, 1.0)
    with pytest.raises(ValueError):
        polar.evaluate(2.0)


def test_polar_function_slider_dependencies() -> None:
    polar = PolarFunctionObject.from_source(
        name="limacon",
        parameter="theta",
        r_source="a + b * cos(theta)",
        theta_min=0.0,
        theta_max=2.0 * math.pi,
    )
    assert polar.external_dependencies == {"a", "b"}

    pt = polar.evaluate(0.0, {"a": 2.0, "b": 3.0})
    assert math.isclose(pt.x, 5.0, abs_tol=1e-7)
    assert math.isclose(pt.y, 0.0, abs_tol=1e-7)


def test_polar_sampling_smooth_and_discontinuous() -> None:
    cardioid = PolarFunctionObject.from_source("r", "theta", "1 + cos(theta)", 0.0, 2.0 * math.pi)
    sampled = sample_polar(cardioid, samples=100)
    assert len(sampled.segments) == 1
    assert len(sampled.segments[0]) == 100

    pole_polar = PolarFunctionObject.from_source("r", "theta", "1 / (theta - 1.0)", 0.0, 2.0)
    sampled_disc = sample_polar(pole_polar, samples=300)
    assert len(sampled_disc.segments) >= 2


# ==============================================================================
# Document & Dependency Graph Integration
# ==============================================================================


def test_document_polar_curve_lifecycle_and_slider() -> None:
    doc = Document()
    slider = GeoObject("number", "k", params={"value": 2.0})
    doc.add(slider)

    polar_obj = GeoObject(
        "polar",
        "r",
        (slider.id,),
        {
            "parameter": "theta",
            "r_source": "k * sin(2 * theta)",
            "theta_min": 0.0,
            "theta_max": 2.0 * math.pi,
            "use_degrees": False,
        },
    )
    doc.add(polar_obj)

    curve = doc.get(polar_obj.id).geometry
    assert isinstance(curve, PolarFunctionObject)
    assert curve.external_dependencies == {"k"}

    doc.update(slider.id, params={"value": 5.0})
    updated_curve = doc.get(polar_obj.id).geometry
    assert isinstance(updated_curve, PolarFunctionObject)
    p_pi4 = updated_curve.evaluate(math.pi / 4.0, {"k": 5.0})
    expected_r = 5.0
    assert math.isclose(p_pi4.x, expected_r * math.cos(math.pi / 4.0), abs_tol=1e-7)
    assert math.isclose(p_pi4.y, expected_r * math.sin(math.pi / 4.0), abs_tol=1e-7)


def test_document_polar_invalid_dependencies() -> None:
    doc = Document()
    polar_obj = GeoObject(
        "polar",
        "r",
        (),
        {
            "parameter": "theta",
            "r_source": "k * cos(theta)",
            "theta_min": 0.0,
            "theta_max": 2.0 * math.pi,
        },
    )
    doc.add(polar_obj)
    assert not doc.get(polar_obj.id).valid


# ==============================================================================
# Hit-Testing & Viewport Export
# ==============================================================================


def test_polar_hit_testing_and_viewport_export() -> None:
    doc = Document()
    polar_obj = GeoObject(
        "polar",
        "r",
        (),
        {
            "parameter": "theta",
            "r_source": "4",
            "theta_min": 0.0,
            "theta_max": 2.0 * math.pi,
        },
    )
    doc.add(polar_obj)

    vp = Viewport(center=Point2D(0, 0), scale=50.0, width=800, height=600)
    sx, sy = vp.world_to_screen(Point2D(4.0, 0.0))
    hit = first_hit(doc, vp, sx, sy, tolerance_px=10.0)
    assert hit is not None
    assert hit.id == polar_obj.id

    sx_far, sy_far = vp.world_to_screen(Point2D(10.0, 10.0))
    hit_far = first_hit(doc, vp, sx_far, sy_far, tolerance_px=10.0)
    assert hit_far is None

    fit_vp = fitted_viewport(doc, width=800, height=600)
    left, bottom, right, top = fit_vp.world_bounds
    assert left <= -4.0 and right >= 4.0
    assert bottom <= -4.0 and top >= 4.0


def test_polar_rendering(qapp: object) -> None:
    del qapp
    doc = Document()
    polar_obj = GeoObject(
        "polar",
        "rose",
        (),
        {
            "parameter": "theta",
            "r_source": "cos(3 * theta)",
            "theta_min": 0.0,
            "theta_max": math.pi,
        },
    )
    doc.add(polar_obj)

    image = QImage(400, 300, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor("white"))
    painter = QPainter(image)
    try:
        renderer = Renderer()
        vp = Viewport(center=Point2D(0, 0), scale=50.0, width=400, height=300)
        renderer.render(painter, doc, vp, QPalette())
    finally:
        painter.end()


# ==============================================================================
# Persistence & Undo/Redo
# ==============================================================================


def test_polar_persistence_roundtrip(tmp_path: Path) -> None:
    doc = Document()
    polar_obj = GeoObject(
        "polar",
        "cardioid",
        (),
        {
            "parameter": "theta",
            "r_source": "2 * (1 - cos(theta))",
            "theta_min": 0.0,
            "theta_max": 2.0 * math.pi,
            "use_degrees": True,
        },
    )
    doc.add(polar_obj)

    serialized = serialize_document(doc)
    assert validate_project(serialized) is not None

    file_path = tmp_path / "polar_project.pgl"
    save_project(doc, file_path)

    loaded_doc = load_project(file_path)
    loaded_obj = loaded_doc.get(polar_obj.id)
    assert loaded_obj.kind == "polar"
    assert loaded_obj.name == "cardioid"
    assert loaded_obj.params["r_source"] == "2 * (1 - cos(theta))"
    assert loaded_obj.params["use_degrees"] is True
    assert isinstance(loaded_obj.geometry, PolarFunctionObject)


def test_polar_undo_redo() -> None:
    doc = Document()
    history = CommandHistory()
    slider = GeoObject("number", "a", params={"value": 2.0})
    history.execute(CreateObjectCommand(doc, slider))

    polar_obj = GeoObject(
        "polar",
        "spiral",
        (slider.id,),
        {
            "parameter": "theta",
            "r_source": "a * theta",
            "theta_min": 0.0,
            "theta_max": 4.0 * math.pi,
        },
    )
    history.execute(CreateObjectCommand(doc, polar_obj))
    assert polar_obj.id in doc.objects
    assert isinstance(doc.get(polar_obj.id).geometry, PolarFunctionObject)

    history.execute(
        ChangeFunctionCommand(
            doc,
            polar_obj.id,
            "spiral2",
            (slider.id,),
            {
                "parameter": "theta",
                "r_source": "a * theta^2",
                "theta_min": 0.0,
                "theta_max": 2.0 * math.pi,
            },
        )
    )
    assert doc.get(polar_obj.id).name == "spiral2"
    assert doc.get(polar_obj.id).params["r_source"] == "a * theta^2"

    history.undo()
    assert doc.get(polar_obj.id).name == "spiral"
    assert doc.get(polar_obj.id).params["r_source"] == "a * theta"

    history.undo()
    assert polar_obj.id not in doc.objects

    history.redo()
    assert polar_obj.id in doc.objects

    history.execute(ChangeNumberValueCommand(doc, slider.id, 5.0))
    assert doc.get(slider.id).geometry == 5.0


# ==============================================================================
# UI Panels & Dialog Tests
# ==============================================================================


def test_polar_dialog_and_degree_mode(qapp: object) -> None:
    del qapp
    doc = Document()
    slider = GeoObject("number", "a", params={"value": 1.5})
    doc.add(slider)

    dialog = PolarFunctionDialog(doc)
    dialog.name_edit.setText("r_test")
    dialog.param_edit.setText("theta")
    dialog.r_edit.setText("a * (1 + cos(theta))")

    assert not dialog.degree_mode_checkbox.isChecked()
    dialog.theta_min_spin.setValue(0.0)
    dialog.theta_max_spin.setValue(math.pi)

    name, deps, params = dialog.definition()
    assert name == "r_test"
    assert deps == (slider.id,)
    assert math.isclose(float(params["theta_max"]), math.pi, abs_tol=1e-5)
    assert params["use_degrees"] is False

    dialog.degree_mode_checkbox.setChecked(True)
    assert dialog.degree_mode_checkbox.isChecked()
    dialog.theta_min_spin.setValue(0.0)
    dialog.theta_max_spin.setValue(180.0)

    name_deg, deps_deg, params_deg = dialog.definition()
    assert params_deg["use_degrees"] is True
    assert math.isclose(float(params_deg["theta_max"]), math.pi, abs_tol=1e-5)

    obj = dialog.object_definition()
    assert obj.kind == "polar"
    assert obj.name == "r_test"
    assert obj.dependencies == (slider.id,)


def test_algebra_and_properties_panels_polar(qapp: object) -> None:
    del qapp
    doc = Document()
    polar_obj = GeoObject(
        "polar",
        "r_panel",
        (),
        {
            "parameter": "theta",
            "r_source": "2 + cos(theta)",
            "theta_min": 0.0,
            "theta_max": 2.0 * math.pi,
            "use_degrees": True,
        },
    )
    doc.add(polar_obj)

    algebra = AlgebraPanel(doc, lambda cmd: None)
    algebra.refresh()
    eval_obj = doc.get(polar_obj.id)
    category = algebra._category(eval_obj.geometry)
    assert category == "Courbes polaires"
    value_str = algebra._format_value(eval_obj)
    assert value_str == "r(theta) = 2 + cos(theta)"

    prop_panel = PropertiesPanel(doc, lambda cmd: None)
    prop_panel.set_selection(frozenset({polar_obj.id}))
    assert not prop_panel._analytics_widget.isHidden()


def test_polar_dialog_edit_existing_and_toggle_back(qapp: object) -> None:
    del qapp
    doc = Document()
    existing = GeoObject(
        "polar",
        "r_deg",
        (),
        {
            "parameter": "theta",
            "r_source": "1 + sin(theta)",
            "theta_min": 0.0,
            "theta_max": math.pi,
            "use_degrees": True,
        },
    )
    doc.add(existing)

    dialog = PolarFunctionDialog(doc, polar=existing)
    assert dialog.degree_mode_checkbox.isChecked()
    assert math.isclose(dialog.theta_max_spin.value(), 180.0, abs_tol=1e-3)

    # Toggle back to radians
    dialog.degree_mode_checkbox.setChecked(False)
    assert not dialog.degree_mode_checkbox.isChecked()
    assert math.isclose(dialog.theta_max_spin.value(), math.pi, abs_tol=1e-3)


def test_polar_properties_radians_mode(qapp: object) -> None:
    del qapp
    doc = Document()
    polar_obj = GeoObject(
        "polar",
        "r_rad",
        (),
        {
            "parameter": "theta",
            "r_source": "cos(theta)",
            "theta_min": 0.0,
            "theta_max": math.pi,
            "use_degrees": False,
        },
    )
    doc.add(polar_obj)
    prop_panel = PropertiesPanel(doc, lambda cmd: None)
    prop_panel.set_selection(frozenset({polar_obj.id}))
    assert not prop_panel._analytics_widget.isHidden()


def test_polar_constructions_error_cases() -> None:
    from pygeolab.model.constructions import evaluate

    obj = GeoObject("polar", "r", (), {"r_source": 123})
    with pytest.raises(ValueError):
        evaluate(obj, ())

    obj2 = GeoObject("polar", "r", (), {"r_source": "theta", "theta_min": "bad"})
    with pytest.raises(ValueError):
        evaluate(obj2, ())


def test_main_window_polar_actions(qapp: object, monkeypatch) -> None:
    del qapp
    from PySide6.QtWidgets import QDialog

    from pygeolab.ui.main_window import MainWindow

    window = MainWindow(offer_recovery=False)

    created = GeoObject(
        "polar",
        "r_mw",
        (),
        {
            "parameter": "theta",
            "r_source": "cos(theta)",
            "theta_min": 0.0,
            "theta_max": 2.0 * math.pi,
        },
    )
    monkeypatch.setattr(PolarFunctionDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(PolarFunctionDialog, "object_definition", lambda self: created)
    monkeypatch.setattr(
        PolarFunctionDialog,
        "definition",
        lambda self: (
            "r_edited",
            (),
            {
                "parameter": "theta",
                "r_source": "sin(theta)",
                "theta_min": 0.0,
                "theta_max": 2.0 * math.pi,
            },
        ),
    )

    window._new_polar()
    assert window.document.get(created.id).kind == "polar"

    # Select and edit
    window.geometry_view.set_selected_ids({created.id})
    window._edit_polar()
    assert window.document.get(created.id).name == "r_edited"
    monkeypatch.setattr(window, "_confirm_discard_changes", lambda: True)
    window.close()
