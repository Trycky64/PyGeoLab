"""Unit and rendering tests for statistical visualisations (PyGeoLab 1.3 Section 4)."""

from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QPainter

from pygeolab.data.dataset import DatasetObject
from pygeolab.geometry import Point2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style
from pygeolab.rendering.hit_test import first_hit, hit_test
from pygeolab.rendering.renderer import Renderer
from pygeolab.rendering.viewport import Viewport


def test_dataset_render_modes_without_crashing() -> None:
    ds = DatasetObject.from_xy(
        x=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        y=[2.0, 4.0, 5.0, 4.0, 8.0, 10.0],
        name="StatsPlot",
    )
    viewport = Viewport(
        width=800,
        height=600,
        center=Point2D(3.5, 5.0),
        scale=40.0,
    )
    style = Style(color="#2980b9", width=2.0, fill_opacity=0.3, point_size=4.0)
    modes = ("scatter", "regression", "histogram", "boxplot", "bar")

    for mode in modes:
        image = QImage(QSize(800, 600), QImage.Format.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        try:
            mod_ds = ds.with_plot_kind(mode)
            Renderer._draw_dataset(painter, mod_ds, style, viewport)
        finally:
            painter.end()


def test_dataset_hit_testing_points() -> None:
    import uuid

    ds = DatasetObject.from_xy(
        x=[0.0, 5.0, 10.0],
        y=[0.0, 5.0, 10.0],
        name="HitDS",
    )
    doc = Document()
    obj_id = str(uuid.uuid4())
    obj = GeoObject(
        id=obj_id,
        name="HitDS",
        kind="dataset",
        geometry=ds,
        style=Style(),
    )
    doc.add(obj)

    viewport = Viewport(
        width=800,
        height=600,
        center=Point2D(0.0, 0.0),
        scale=50.0,
    )

    # Screen coordinates of (5.0, 5.0)
    sx, sy = viewport.world_to_screen(Point2D(5.0, 5.0))

    # Hit test directly on point
    hits = hit_test(doc, viewport, sx, sy, tolerance_px=10.0)
    assert len(hits) >= 1
    assert hits[0].object_id == obj_id

    # first_hit
    hit_obj = first_hit(doc, viewport, sx, sy, tolerance_px=10.0)
    assert hit_obj is not None
    assert hit_obj.id == obj_id

    # Far away point should miss
    miss = first_hit(doc, viewport, sx + 50.0, sy + 50.0, tolerance_px=5.0)
    assert miss is None
