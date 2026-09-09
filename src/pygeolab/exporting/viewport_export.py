"""Raster/vector export, document fitting and Qt clipboard helpers."""

from __future__ import annotations

import math
from collections.abc import Iterable
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QMimeData, QRect, QSize
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPalette
from PySide6.QtSvg import QSvgGenerator

from pygeolab.geometry import Circle2D, Line2D, Point2D, Polygon2D, Ray2D, Segment2D, Vector2D
from pygeolab.math_engine.functions import FunctionObject
from pygeolab.math_engine.sampling import sample_function
from pygeolab.model.document import Document
from pygeolab.rendering.renderer import Renderer
from pygeolab.rendering.viewport import Viewport


def _scaled_viewport(
    viewport: Viewport, scale: float, width: int | None = None, height: int | None = None
) -> Viewport:
    if not 0.25 <= scale <= 8.0:
        raise ValueError("Le facteur de résolution doit être compris entre 0.25 et 8")
    base_width = viewport.width if width is None else width
    base_height = viewport.height if height is None else height
    if not 1 <= base_width <= 20_000 or not 1 <= base_height <= 20_000:
        raise ValueError("Les dimensions doivent être comprises entre 1 et 20 000 pixels")
    return Viewport(
        center=viewport.center,
        scale=viewport.scale * scale,
        width=max(1, round(base_width * scale)),
        height=max(1, round(base_height * scale)),
    )


def fitted_viewport(
    document: Document,
    width: int,
    height: int,
    object_ids: Iterable[str] | None = None,
    *,
    padding: float = 0.08,
) -> Viewport:
    """Fit finite document geometry into dimensions independently of the canvas camera."""
    if width <= 0 or height <= 0 or not 0 <= padding < 0.5:
        raise ValueError("Dimensions ou marge d'export invalides")
    selected = frozenset(object_ids) if object_ids is not None else None
    points: list[Point2D] = []
    functions: list[tuple[FunctionObject, dict[str, float]]] = []
    for obj in document.objects.values():
        if not obj.visible or not obj.valid or (selected is not None and obj.id not in selected):
            continue
        geometry = obj.geometry
        if isinstance(geometry, Point2D):
            points.append(geometry)
        elif isinstance(geometry, Segment2D):
            points.extend((geometry.start, geometry.end))
        elif isinstance(geometry, Ray2D):
            points.extend((geometry.start, geometry.through))
        elif isinstance(geometry, Circle2D):
            points.extend(
                (
                    Point2D(
                        geometry.center.x - geometry.radius,
                        geometry.center.y - geometry.radius,
                    ),
                    Point2D(
                        geometry.center.x + geometry.radius,
                        geometry.center.y + geometry.radius,
                    ),
                )
            )
        elif isinstance(geometry, Polygon2D):
            points.extend(geometry.vertices)
        elif isinstance(geometry, Vector2D):
            points.extend((Point2D(0, 0), Point2D(geometry.x, geometry.y)))
        elif isinstance(geometry, FunctionObject):
            variables = {
                parent.name: parent.geometry
                for dependency_id in obj.dependencies
                if isinstance((parent := document.get(dependency_id)).geometry, float)
            }
            functions.append((geometry, variables))
        elif isinstance(geometry, Line2D):
            continue
    left = min((point.x for point in points), default=-10.0)
    right = max((point.x for point in points), default=10.0)
    if math.isclose(left, right):
        left, right = left - 1, right + 1
    for function, variables in functions:
        start, end = function.domain or (left, right)
        sampled = sample_function(function, start, end, samples=600, variables=variables)
        points.extend(
            point for segment in sampled.segments for point in segment if abs(point.y) <= 1e6
        )
    if not points:
        points = [Point2D(-10, -10), Point2D(10, 10)]
    left = min(point.x for point in points)
    right = max(point.x for point in points)
    bottom = min(point.y for point in points)
    top = max(point.y for point in points)
    if math.isclose(left, right):
        left, right = left - 1, right + 1
    if math.isclose(bottom, top):
        bottom, top = bottom - 1, top + 1
    available_width = width * (1 - 2 * padding)
    available_height = height * (1 - 2 * padding)
    scale = min(available_width / (right - left), available_height / (top - bottom))
    return Viewport(Point2D((left + right) / 2, (bottom + top) / 2), scale, width, height)


def render_png_image(
    document: Document,
    viewport: Viewport,
    palette: QPalette,
    *,
    scale: float = 1.0,
    transparent: bool = False,
    width: int | None = None,
    height: int | None = None,
    object_ids: Iterable[str] | None = None,
) -> QImage:
    """Render and return an in-memory PNG-compatible image."""
    export_viewport = _scaled_viewport(viewport, scale, width, height)
    image = QImage(
        export_viewport.width,
        export_viewport.height,
        QImage.Format.Format_ARGB32_Premultiplied,
    )
    image.fill(QColor(0, 0, 0, 0) if transparent else palette.window().color())
    image.setText("Software", "PyGeoLab")
    image.setText("Title", document.name)
    painter = QPainter(image)
    try:
        Renderer().render(
            painter,
            document,
            export_viewport,
            palette,
            draw_background=not transparent,
            object_ids=object_ids,
        )
    finally:
        painter.end()
    return image


def export_png(
    path: str | Path,
    document: Document,
    viewport: Viewport,
    palette: QPalette,
    *,
    scale: float = 1.0,
    transparent: bool = False,
    width: int | None = None,
    height: int | None = None,
    object_ids: Iterable[str] | None = None,
) -> Path:
    """Render a lossless PNG at configurable dimensions and resolution."""
    target = Path(path)
    if target.suffix.lower() != ".png":
        target = target.with_suffix(".png")
    image = render_png_image(
        document,
        viewport,
        palette,
        scale=scale,
        transparent=transparent,
        width=width,
        height=height,
        object_ids=object_ids,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(target)):
        raise ValueError(f"Impossible d'exporter l'image PNG : {target}")
    return target


def _svg_generator(device: str | Path | QBuffer, viewport: Viewport, title: str) -> QSvgGenerator:
    generator = QSvgGenerator()
    if isinstance(device, QBuffer):
        generator.setOutputDevice(device)
    else:
        generator.setFileName(str(device))
    generator.setSize(QSize(viewport.width, viewport.height))
    generator.setViewBox(QRect(0, 0, viewport.width, viewport.height))
    generator.setTitle(title)
    generator.setDescription("Vector export generated by PyGeoLab")
    return generator


def _render_svg(
    generator: QSvgGenerator,
    document: Document,
    viewport: Viewport,
    palette: QPalette,
    transparent: bool,
    object_ids: Iterable[str] | None,
) -> None:
    painter = QPainter(generator)
    try:
        Renderer().render(
            painter,
            document,
            viewport,
            palette,
            draw_background=not transparent,
            object_ids=object_ids,
        )
    finally:
        painter.end()


def export_svg(
    path: str | Path,
    document: Document,
    viewport: Viewport,
    palette: QPalette,
    *,
    scale: float = 1.0,
    transparent: bool = False,
    width: int | None = None,
    height: int | None = None,
    object_ids: Iterable[str] | None = None,
) -> Path:
    """Render scalable vector geometry, curves and labels with clipping."""
    target = Path(path)
    if target.suffix.lower() != ".svg":
        target = target.with_suffix(".svg")
    export_viewport = _scaled_viewport(viewport, scale, width, height)
    target.parent.mkdir(parents=True, exist_ok=True)
    _render_svg(
        _svg_generator(target, export_viewport, document.name),
        document,
        export_viewport,
        palette,
        transparent,
        object_ids,
    )
    return target


def render_svg_bytes(
    document: Document,
    viewport: Viewport,
    palette: QPalette,
    *,
    transparent: bool = False,
    object_ids: Iterable[str] | None = None,
) -> bytes:
    """Render SVG into memory for clipboard transfer."""
    data = QByteArray()
    buffer = QBuffer(data)
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        raise ValueError("Impossible de préparer le SVG en mémoire")
    try:
        _render_svg(
            _svg_generator(buffer, viewport, document.name),
            document,
            viewport,
            palette,
            transparent,
            object_ids,
        )
    finally:
        buffer.close()
    return bytes(data.data())


def copy_png_to_clipboard(
    application: QGuiApplication,
    document: Document,
    viewport: Viewport,
    palette: QPalette,
) -> None:
    """Copy the current viewport as a Qt image."""
    application.clipboard().setImage(render_png_image(document, viewport, palette))


def copy_svg_to_clipboard(
    application: QGuiApplication,
    document: Document,
    viewport: Viewport,
    palette: QPalette,
) -> None:
    """Copy the current viewport as SVG MIME data and readable XML text."""
    data = render_svg_bytes(document, viewport, palette, transparent=True)
    mime = QMimeData()
    mime.setData("image/svg+xml", QByteArray(data))
    mime.setText(data.decode("utf-8"))
    application.clipboard().setMimeData(mime)
