"""Repeatable performance scenarios for the v1.1 regression gate."""

from __future__ import annotations

import os
import time
from collections.abc import Callable

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage, QPainter, QPalette  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from pygeolab.geometry import Point2D  # noqa: E402
from pygeolab.model.document import Document  # noqa: E402
from pygeolab.model.objects import GeoObject  # noqa: E402
from pygeolab.rendering.hit_test import hit_test  # noqa: E402
from pygeolab.rendering.renderer import Renderer  # noqa: E402
from pygeolab.rendering.viewport import Viewport  # noqa: E402
from pygeolab.ui.slider_panel import SliderPanel  # noqa: E402

VIEWPORT = Viewport(width=1000, height=700)

# These limits intentionally leave ample room for shared GitHub runners while catching
# order-of-magnitude regressions. They are milliseconds for one complete scenario operation.
REGRESSION_LIMITS_MS = {
    "render_1000": 500.0,
    "render_10000": 1500.0,
    "hit_test_10000": 300.0,
    "deep_update_1000": 2000.0,
    "functions_100": 1500.0,
    "slider_tick_50": 1000.0,
}


def _elapsed(operation: Callable[[], object]) -> float:
    started = time.perf_counter()
    operation()
    return (time.perf_counter() - started) * 1000.0


def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def _render(document: Document) -> float:
    _application()
    image = QImage(VIEWPORT.width, VIEWPORT.height, QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(image)
    renderer = Renderer()
    renderer.configure_display(grid=False, axes=False, labels=False)
    try:
        return _elapsed(lambda: renderer.render(painter, document, VIEWPORT, QPalette()))
    finally:
        painter.end()


def profile_simple_objects(size: int) -> dict[str, float]:
    """Measure loading, rendering and point hit-testing for an object grid."""
    document = Document("Objets simples")
    points = tuple(
        GeoObject(
            "point",
            f"P{index}",
            params={"x": float(index % 200 - 100), "y": float(index // 200 - 25)},
        )
        for index in range(size)
    )
    restore_ms = _elapsed(lambda: document.restore(points))
    render_ms = _render(document)
    hit_test_ms = _elapsed(lambda: hit_test(document, VIEWPORT, 500.0, 350.0))
    return {
        f"restore_{size}": restore_ms,
        f"render_{size}": render_ms,
        f"hit_test_{size}": hit_test_ms,
    }


def profile_deep_graph(depth: int = 1000) -> dict[str, float]:
    """Measure initial evaluation and incremental propagation through a deep graph."""
    document = Document("Graphe profond")
    root = GeoObject("point", "A", params={"x": 1.0, "y": 0.0})
    center = GeoObject("point", "C", params={"x": 0.0, "y": 0.0})
    definitions = [root, center]
    parent = root
    for index in range(depth):
        child = GeoObject("reflect_point", f"R{index}", (parent.id, center.id))
        definitions.append(child)
        parent = child
    restore_ms = _elapsed(lambda: document.restore(definitions))
    update_ms = _elapsed(lambda: document.move_point(root.id, Point2D(2.0, 0.0)))
    if len(document.last_recomputed) != depth + 1:
        raise RuntimeError("Le benchmark profond n'a pas recalculé la chaîne complète")
    return {f"deep_restore_{depth}": restore_ms, f"deep_update_{depth}": update_ms}


def profile_functions(count: int = 100) -> dict[str, float]:
    """Measure creation and first rendering of many independent functions."""
    document = Document("Fonctions")
    definitions = tuple(
        GeoObject(
            "function",
            f"f{index}",
            params={"source": f"sin(x) + {index}", "variable": "x"},
        )
        for index in range(count)
    )
    restore_ms = _elapsed(lambda: document.restore(definitions))
    return {f"functions_restore_{count}": restore_ms, f"functions_{count}": _render(document)}


def profile_animated_sliders(count: int = 50) -> dict[str, float]:
    """Measure a real SliderPanel frame with independent animated variables."""
    _application()
    document = Document("Curseurs")
    definitions = tuple(
        GeoObject(
            "number",
            f"a{index}",
            params={
                "value": 0.0,
                "min": 0.0,
                "max": 10.0,
                "step": 0.01,
                "initial": 0.0,
                "animation_speed": 1.0,
            },
        )
        for index in range(count)
    )
    document.restore(definitions)
    panel = SliderPanel(document, lambda command: command.redo())
    try:
        for definition in definitions:
            panel.toggle_animation(definition.id)
        panel._timer.stop()
        tick_ms = _elapsed(lambda: panel._animate_tick(elapsed=0.1))
    finally:
        panel.dispose()
        panel.deleteLater()
    return {f"slider_tick_{count}": tick_ms}


def run_all() -> dict[str, float]:
    """Run every release-gate performance scenario."""
    results: dict[str, float] = {}
    for scenario in (
        lambda: profile_simple_objects(1000),
        lambda: profile_simple_objects(10_000),
        profile_deep_graph,
        profile_functions,
        profile_animated_sliders,
    ):
        results.update(scenario())
    return results


if __name__ == "__main__":
    for key, value in run_all().items():
        limit = REGRESSION_LIMITS_MS.get(key)
        suffix = "" if limit is None else f" (limite {limit:.0f} ms)"
        print(f"{key}: {value:.3f} ms{suffix}")
