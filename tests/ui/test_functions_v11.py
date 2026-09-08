"""Exercise the v1.1 function editor, menu controls and graph rendering."""

from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QImage, QPainter, QPalette
from PySide6.QtWidgets import QApplication, QDialog
from pytestqt.qtbot import QtBot

from pygeolab.math_engine import SampledFunction
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.rendering.renderer import Renderer
from pygeolab.rendering.viewport import Viewport
from pygeolab.ui.dialogs.function_dialog import FunctionDialog
from pygeolab.ui.main_window import MainWindow


def test_function_dialog_resolves_slider_and_optional_domain(qtbot: QtBot) -> None:
    document = Document()
    slider = document.add(GeoObject("number", "a", params={"value": 2.0}))
    dialog = FunctionDialog(document)
    qtbot.addWidget(dialog)
    dialog.name_edit.setText("courbe")
    dialog.variable_edit.setText("t")
    dialog.source_edit.setText("a*t + 1")
    dialog.domain_check.setChecked(True)
    dialog.domain_start.setValue(-4)
    dialog.domain_end.setValue(6)

    function = dialog.object_definition()
    evaluated = document.add(function)

    assert evaluated.dependencies == (slider.id,)
    assert evaluated.params["domain"] == (-4.0, 6.0)
    assert evaluated.style.color == "#9333ea"
    assert evaluated.geometry is not None
    assert evaluated.geometry.evaluate(3, {"a": 2}) == 7


def test_main_window_creates_edits_and_deletes_function_with_history(
    qtbot: QtBot, monkeypatch, tmp_path
) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    created = GeoObject("function", "f", params={"variable": "x", "source": "x"})
    monkeypatch.setattr(FunctionDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(FunctionDialog, "object_definition", lambda self: created)

    window._new_function()
    assert window.document.get(created.id).kind == "function"
    assert window.geometry_view.history.undo_count == 1

    window.geometry_view.set_selected_ids({created.id})
    monkeypatch.setattr(
        FunctionDialog,
        "definition",
        lambda self: ("g", (), {"variable": "u", "source": "u^2"}),
    )
    window._edit_function()
    assert window.document.get(created.id).name == "g"
    assert window.document.get(created.id).geometry is not None

    window._delete_selection()
    assert created.id not in window.document.objects
    assert window.geometry_view.history.undo()
    assert window.document.get(created.id).name == "g"
    assert window.geometry_view.history.undo()
    assert window.document.get(created.id).name == "f"
    window.session.save(tmp_path / "function-ui.pgl")


def test_function_menu_controls_scene_options(qtbot: QtBot, tmp_path) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    window.function_quality_actions["high"].trigger()
    window.function_overlay_actions["roots"].setChecked(True)
    window.function_overlay_actions["derivative"].setChecked(True)

    assert window.document.scene["function_sampling_quality"] == "high"
    assert window.document.scene["show_function_roots"] is True
    assert window.document.scene["show_function_derivative"] is True
    window.session.save(tmp_path / "function-options.pgl")


def test_loaded_scene_options_are_reflected_in_function_menu(qtbot: QtBot, tmp_path) -> None:
    source = Document()
    source.set_scene_option("function_sampling_quality", "low")
    source.set_scene_option("show_function_extrema", True)
    window = MainWindow()
    qtbot.addWidget(window)
    path = tmp_path / "scene-options.pgl"
    from pygeolab.persistence import ProjectSession

    ProjectSession(source).save(path)
    window.session.open(path)
    window._adopt_session_document()

    assert window.function_quality_actions["low"].isChecked()
    assert window.function_overlay_actions["extrema"].isChecked()


def test_renderer_adapts_sampling_and_draws_analysis_overlays(
    qapp: QApplication, monkeypatch
) -> None:
    del qapp
    document = Document()
    document.add(GeoObject("function", "f", params={"variable": "x", "source": "x^2-1"}))
    document.add(GeoObject("function", "g", params={"variable": "x", "source": "0"}))
    viewport = Viewport(scale=160, width=320, height=240)
    requested_samples: list[int] = []
    from pygeolab.rendering import renderer as renderer_module

    real_sample_function = renderer_module.sample_function

    def recording_sample(*args, **kwargs) -> SampledFunction:
        requested_samples.append(kwargs["samples"])
        return real_sample_function(*args, **kwargs)

    monkeypatch.setattr(renderer_module, "sample_function", recording_sample)
    renderer = Renderer()
    image = QImage(320, 240, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor("transparent"))

    document.set_scene_option("function_sampling_quality", "low")
    painter = QPainter(image)
    renderer.render(painter, document, viewport, QPalette(), set())
    painter.end()
    low_samples = max(requested_samples)

    requested_samples.clear()
    document.set_scene_option("function_sampling_quality", "high")
    for overlay in ("roots", "extrema", "intersections", "derivative"):
        document.set_scene_option(f"show_function_{overlay}", True)
    painter = QPainter(image)
    renderer.render(painter, document, viewport, QPalette(), set())
    painter.end()

    assert min(requested_samples) > low_samples
    assert any(image.pixelColor(QPoint(x, y)).alpha() > 0 for x in range(320) for y in range(240))
