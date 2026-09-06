"""Verify PNG and SVG viewport exports through real Qt paint devices."""

from PySide6.QtGui import QImage, QPalette

from pygeolab.exporting import export_png, export_svg
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.rendering.viewport import Viewport


def test_png_and_svg_export(tmp_path) -> None:
    """Both export formats preserve requested resolution and produce nonempty files."""
    document = Document("Export")
    document.restore(
        (
            GeoObject("point", "A", params={"x": -1.0, "y": 0.0}),
            GeoObject("point", "B", params={"x": 1.0, "y": 0.0}),
        )
    )
    viewport = Viewport(width=320, height=200)
    palette = QPalette()
    png = export_png(tmp_path / "scene", document, viewport, palette, scale=2.0)
    svg = export_svg(tmp_path / "scene", document, viewport, palette, transparent=True)

    image = QImage(str(png))
    assert not image.isNull()
    assert image.width() == 640
    assert image.height() == 400
    assert png.suffix == ".png"
    assert png.stat().st_size > 100
    text = svg.read_text(encoding="utf-8")
    assert "<svg" in text
    assert svg.stat().st_size > 100
