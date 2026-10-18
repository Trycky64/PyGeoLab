"""Qt painter renderer translating immutable document geometry into pixels."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPalette, QPen, QPolygonF

from pygeolab.data.dataset import DatasetObject
from pygeolab.geometry import (
    Circle2D,
    Ellipse2D,
    Hyperbola2D,
    Line2D,
    Locus2D,
    Parabola2D,
    Point2D,
    Polygon2D,
    Ray2D,
    Segment2D,
    Vector2D,
)
from pygeolab.math_engine.functions import (
    FunctionObject,
    ParametricFunctionObject,
    PolarFunctionObject,
)
from pygeolab.math_engine.numerical import derivative, extrema, find_roots, intersections
from pygeolab.math_engine.sampling import (
    sample_function,
    sample_parametric,
    sample_polar,
)
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style
from pygeolab.rendering.clipping import clip_line, clip_ray, clip_segment
from pygeolab.rendering.grid import GridCache
from pygeolab.rendering.viewport import Viewport


class Renderer:
    """Draw a document without mutating it, using palette-driven UI decoration colors."""

    def __init__(self) -> None:
        self._grid_cache = GridCache()
        self._visible_revision = -1
        self._visible_filter: frozenset[str] | None = None
        self._visible_objects: tuple[GeoObject, ...] = ()
        self._function_cache: dict[tuple[object, ...], tuple[tuple[Point2D, ...], ...]] = {}
        self.show_grid = True
        self.show_axes = True
        self.show_labels = True

    def configure_display(self, *, grid: bool, axes: bool, labels: bool) -> None:
        """Apply global display preferences without changing the document."""
        if (grid, axes, labels) == (self.show_grid, self.show_axes, self.show_labels):
            return
        self.show_grid, self.show_axes, self.show_labels = grid, axes, labels
        self._grid_cache.clear()

    def render(
        self,
        painter: QPainter,
        document: Document,
        viewport: Viewport,
        palette: QPalette,
        selected_ids: Iterable[str] = (),
        *,
        draw_background: bool = True,
        object_ids: Iterable[str] | None = None,
    ) -> None:
        """Draw grid, axes, valid visible objects, labels and selection overlays."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if draw_background:
            painter.fillRect(QRectF(0, 0, viewport.width, viewport.height), palette.window())
        self._draw_grid_and_axes(painter, viewport, palette)
        selected = set(selected_ids)
        visible_filter = frozenset(object_ids) if object_ids is not None else None
        if document.revision != self._visible_revision or visible_filter != self._visible_filter:
            self._visible_objects = tuple(
                obj
                for obj in document.objects.values()
                if obj.visible
                and obj.valid
                and (visible_filter is None or obj.id in visible_filter)
            )
            self._visible_revision = document.revision
            self._visible_filter = visible_filter
        visible = self._visible_objects
        function_count = sum(isinstance(obj.geometry, FunctionObject) for obj in visible)
        for obj in visible:
            self._draw_object(painter, document, obj, viewport, function_count)
        self._draw_function_analysis(painter, document, visible, viewport, palette)
        if self.show_labels:
            self._draw_labels(painter, document, visible, viewport, palette)
        for obj in visible:
            if obj.id in selected:
                self._draw_selection(painter, document, obj, viewport, palette)
        painter.restore()

    def render_preview(
        self,
        painter: QPainter,
        document: Document,
        viewport: Viewport,
        palette: QPalette,
        geometries: Iterable[
            Point2D | Vector2D | Line2D | Ray2D | Segment2D | Circle2D | Polygon2D
        ],
    ) -> None:
        """Draw transient construction geometry without inserting it into the document."""
        painter.save()
        color = palette.highlight().color()
        preview_style = Style(color=color.name(), width=1.5, line_style="dash", fill_opacity=0.06)
        kind_by_type = {
            Point2D: "point",
            Line2D: "line",
            Ray2D: "ray",
            Segment2D: "segment",
            Circle2D: "circle",
            Polygon2D: "polygon",
        }
        for index, geometry in enumerate(geometries):
            kind = kind_by_type.get(type(geometry))
            if kind is None:
                continue
            obj = GeoObject(kind, f"preview{index}", style=preview_style, geometry=geometry)
            painter.setPen(self._pen(preview_style))
            self._draw_geometry(painter, document, obj, viewport, fill=True)
        painter.restore()

    @staticmethod
    def render_snap_indicator(
        painter: QPainter,
        viewport: Viewport,
        palette: QPalette,
        point: Point2D,
    ) -> None:
        """Draw a compact crosshair and ring around the active snap position."""
        x, y = viewport.world_to_screen(point)
        color = QColor(palette.highlight().color())
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(color, 2.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(x, y), 7.0, 7.0)
        painter.drawLine(QPointF(x - 10.0, y), QPointF(x + 10.0, y))
        painter.drawLine(QPointF(x, y - 10.0), QPointF(x, y + 10.0))
        painter.restore()

    def invalidate_cache(self) -> None:
        """Drop renderer-owned cached layout data."""
        self._grid_cache.clear()
        self._visible_revision = -1
        self._visible_filter = None
        self._visible_objects = ()
        self._function_cache.clear()

    def _draw_grid_and_axes(self, painter: QPainter, viewport: Viewport, palette: QPalette) -> None:
        if not self.show_grid and not self.show_axes:
            return
        layout = self._grid_cache.get(viewport)
        if self.show_grid:
            grid_color = QColor(palette.mid().color())
            grid_color.setAlpha(90)
            painter.setPen(QPen(grid_color, 1.0))
            for world_x in layout.vertical:
                x, _ = viewport.world_to_screen(Point2D(world_x, 0.0))
                painter.drawLine(QPointF(x, 0), QPointF(x, viewport.height))
            for world_y in layout.horizontal:
                _, y = viewport.world_to_screen(Point2D(0.0, world_y))
                painter.drawLine(QPointF(0, y), QPointF(viewport.width, y))

        if not self.show_axes:
            return
        axis_color = QColor(palette.text().color())
        axis_color.setAlpha(180)
        painter.setPen(QPen(axis_color, 1.4))
        left, bottom, right, top = viewport.world_bounds
        origin_x, origin_y = viewport.world_to_screen(Point2D(0.0, 0.0))
        if left <= 0 <= right:
            painter.drawLine(QPointF(origin_x, 0), QPointF(origin_x, viewport.height))
        if bottom <= 0 <= top:
            painter.drawLine(QPointF(0, origin_y), QPointF(viewport.width, origin_y))
        self._draw_axis_values(painter, viewport, layout.step, layout.vertical, layout.horizontal)

    @staticmethod
    def _format_tick(value: float, step: float) -> str:
        decimals = max(0, min(10, -math.floor(math.log10(step)))) if step < 1 else 0
        text = f"{value:.{decimals}f}"
        return "0" if text in {"-0", "-0.0"} else text

    def _draw_axis_values(
        self,
        painter: QPainter,
        viewport: Viewport,
        step: float,
        vertical: tuple[float, ...],
        horizontal: tuple[float, ...],
    ) -> None:
        left, bottom, right, top = viewport.world_bounds
        origin_x, origin_y = viewport.world_to_screen(Point2D(0.0, 0.0))
        metrics = QFontMetrics(painter.font())
        x_label_y = min(
            viewport.height - 4.0,
            max(float(metrics.height()), origin_y + metrics.height()),
        )
        y_axis_x = min(viewport.width - 4.0, max(4.0, origin_x + 4.0))
        for value in vertical:
            if abs(value) <= step * 1e-12:
                continue
            x, _ = viewport.world_to_screen(Point2D(value, 0.0))
            text = self._format_tick(value, step)
            painter.drawText(QPointF(x - metrics.horizontalAdvance(text) / 2, x_label_y), text)
        for value in horizontal:
            if abs(value) <= step * 1e-12:
                continue
            _, y = viewport.world_to_screen(Point2D(0.0, value))
            text = self._format_tick(value, step)
            painter.drawText(QPointF(y_axis_x, y + metrics.ascent() / 2), text)
        if left <= 0 <= right and bottom <= 0 <= top:
            painter.drawText(QPointF(origin_x + 4, origin_y + metrics.height()), "0")

    def _draw_object(
        self,
        painter: QPainter,
        document: Document,
        obj: GeoObject,
        viewport: Viewport,
        function_count: int = 1,
    ) -> None:
        geometry = obj.geometry
        if geometry is None:
            return
        painter.setPen(self._pen(obj.style))
        self._draw_geometry(
            painter, document, obj, viewport, fill=True, function_count=function_count
        )

    def _draw_selection(
        self,
        painter: QPainter,
        document: Document,
        obj: GeoObject,
        viewport: Viewport,
        palette: QPalette,
    ) -> None:
        selection = QColor(palette.highlight().color())
        selection.setAlpha(130)
        painter.setPen(QPen(selection, obj.style.width + 5.0))
        self._draw_geometry(painter, document, obj, viewport, fill=False)

    def _draw_geometry(
        self,
        painter: QPainter,
        document: Document,
        obj: GeoObject,
        viewport: Viewport,
        *,
        fill: bool,
        function_count: int = 1,
    ) -> None:
        geometry = obj.geometry
        if isinstance(geometry, Point2D):
            x, y = viewport.world_to_screen(geometry)
            radius = obj.style.point_size
            painter.setBrush(QColor(obj.style.color) if fill else Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(x, y), radius, radius)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            return
        if isinstance(geometry, Line2D):
            clipped = clip_line(geometry, viewport.world_bounds)
            self._draw_clipped_line(painter, clipped, viewport)
            return
        if isinstance(geometry, Ray2D):
            clipped = clip_ray(geometry, viewport.world_bounds)
            self._draw_clipped_line(painter, clipped, viewport)
            return
        if isinstance(geometry, Segment2D):
            clipped = clip_segment(geometry.start, geometry.end, viewport.world_bounds)
            self._draw_clipped_line(painter, clipped, viewport)
            return
        if isinstance(geometry, Circle2D):
            self._draw_circle(painter, geometry, obj.style, viewport, fill)
            return
        if isinstance(geometry, Ellipse2D):
            self._draw_ellipse(painter, geometry, obj.style, viewport, fill)
            return
        if isinstance(geometry, Parabola2D):
            self._draw_parabola(painter, geometry, obj.style, viewport)
            return
        if isinstance(geometry, Hyperbola2D):
            self._draw_hyperbola(painter, geometry, obj.style, viewport)
            return
        if isinstance(geometry, Polygon2D):
            self._draw_polygon(painter, geometry, obj.style, viewport, fill)
            return
        if isinstance(geometry, Vector2D):
            self._draw_vector(painter, document, obj, geometry, viewport)
            return
        if isinstance(geometry, FunctionObject):
            self._draw_function(painter, document, obj, geometry, viewport, function_count)
            return
        if isinstance(geometry, ParametricFunctionObject):
            self._draw_parametric(painter, document, obj, geometry, viewport)
            return
        if isinstance(geometry, PolarFunctionObject):
            self._draw_polar(painter, document, obj, geometry, viewport)
            return
        if isinstance(geometry, Locus2D):
            self._draw_locus(painter, geometry, viewport)
            return
        if isinstance(geometry, DatasetObject):
            self._draw_dataset(painter, geometry, obj.style, viewport)
            return

    @staticmethod
    def _draw_clipped_line(
        painter: QPainter,
        clipped: tuple[Point2D, Point2D] | None,
        viewport: Viewport,
    ) -> None:
        if clipped is None:
            return
        first = viewport.world_to_screen(clipped[0])
        second = viewport.world_to_screen(clipped[1])
        painter.drawLine(QPointF(*first), QPointF(*second))

    @staticmethod
    def _draw_circle(
        painter: QPainter, circle: Circle2D, style: Style, viewport: Viewport, fill: bool
    ) -> None:
        left, bottom, right, top = viewport.world_bounds
        if (
            circle.center.x + circle.radius < left
            or circle.center.x - circle.radius > right
            or circle.center.y + circle.radius < bottom
            or circle.center.y - circle.radius > top
        ):
            return
        center_x, center_y = viewport.world_to_screen(circle.center)
        radius = circle.radius * viewport.scale
        if not math.isfinite(radius) or radius > 1e9:
            return
        if fill and style.fill_opacity > 0:
            color = QColor(style.color)
            color.setAlphaF(style.fill_opacity)
            painter.setBrush(color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)
        painter.setBrush(Qt.BrushStyle.NoBrush)

    @staticmethod
    def _draw_ellipse(
        painter: QPainter, ellipse: Ellipse2D, style: Style, viewport: Viewport, fill: bool
    ) -> None:
        b_left, b_bottom, b_right, b_top = ellipse.bounding_box
        left, bottom, right, top = viewport.world_bounds
        if b_right < left or b_left > right or b_top < bottom or b_bottom > top:
            return
        cx, cy = viewport.world_to_screen(ellipse.center)
        rx = ellipse.a * viewport.scale
        ry = ellipse.b * viewport.scale
        if not math.isfinite(rx) or not math.isfinite(ry) or rx > 1e7 or ry > 1e7:
            return
        if fill and style.fill_opacity > 0:
            color = QColor(style.color)
            color.setAlphaF(style.fill_opacity)
            painter.setBrush(color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(-math.degrees(ellipse.angle))
        painter.drawEllipse(QPointF(0, 0), rx, ry)
        painter.restore()
        painter.setBrush(Qt.BrushStyle.NoBrush)

    @staticmethod
    def _draw_parabola(
        painter: QPainter, parabola: Parabola2D, style: Style, viewport: Viewport
    ) -> None:
        del style
        left, bottom, right, top = viewport.world_bounds
        diag = math.hypot(right - left, top - bottom)
        p = parabola.parameter
        t_max = max(10.0, math.sqrt(max(1.0, 4.0 * p * diag)))
        samples = parabola.sample_in_range(-t_max, t_max, num_points=120)
        path = QPainterPath()
        started = False
        for pt in samples:
            sx, sy = viewport.world_to_screen(pt)
            if abs(sx) > 5e4 or abs(sy) > 5e4:
                continue
            if not started:
                path.moveTo(sx, sy)
                started = True
            else:
                path.lineTo(sx, sy)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    @staticmethod
    def _draw_hyperbola(
        painter: QPainter, hyperbola: Hyperbola2D, style: Style, viewport: Viewport
    ) -> None:
        del style
        for branch in (1, 2):
            samples = hyperbola.sample_branch(branch, t_max=3.5, num_points=70)
            path = QPainterPath()
            started = False
            for pt in samples:
                sx, sy = viewport.world_to_screen(pt)
                if abs(sx) > 5e4 or abs(sy) > 5e4:
                    continue
                if not started:
                    path.moveTo(sx, sy)
                    started = True
                else:
                    path.lineTo(sx, sy)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

    @staticmethod
    def _draw_polygon(
        painter: QPainter, polygon: Polygon2D, style: Style, viewport: Viewport, fill: bool
    ) -> None:
        screen_points = [viewport.world_to_screen(point) for point in polygon.vertices]
        if not all(
            math.isfinite(value) and abs(value) <= 1e9 for point in screen_points for value in point
        ):
            for edge in polygon.edges:
                Renderer._draw_clipped_line(
                    painter, clip_segment(edge.start, edge.end, viewport.world_bounds), viewport
                )
            return
        path = QPolygonF([QPointF(*point) for point in screen_points])
        if fill and style.fill_opacity > 0:
            color = QColor(style.color)
            color.setAlphaF(style.fill_opacity)
            painter.setBrush(color)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(path)
        painter.setBrush(Qt.BrushStyle.NoBrush)

    @staticmethod
    def _draw_vector(
        painter: QPainter,
        document: Document,
        obj: GeoObject,
        vector: Vector2D,
        viewport: Viewport,
    ) -> None:
        if not obj.dependencies:
            return
        parent = document.get(obj.dependencies[0]).geometry
        if not isinstance(parent, Point2D):
            return
        end = Point2D(parent.x + vector.x, parent.y + vector.y)
        clipped = clip_segment(parent, end, viewport.world_bounds)
        Renderer._draw_clipped_line(painter, clipped, viewport)
        if clipped is None or not end.almost_equals(clipped[1], tolerance=1e-8):
            return
        sx, sy = viewport.world_to_screen(parent)
        ex, ey = viewport.world_to_screen(end)
        dx, dy = ex - sx, ey - sy
        length = math.hypot(dx, dy)
        if length <= 1e-9:
            return
        ux, uy = dx / length, dy / length
        size = 10.0
        left = QPointF(ex - size * ux + size * 0.5 * uy, ey - size * uy - size * 0.5 * ux)
        right = QPointF(ex - size * ux - size * 0.5 * uy, ey - size * uy + size * 0.5 * ux)
        painter.drawLine(QPointF(ex, ey), left)
        painter.drawLine(QPointF(ex, ey), right)

    def _draw_function(
        self,
        painter: QPainter,
        document: Document,
        obj: GeoObject,
        function: FunctionObject,
        viewport: Viewport,
        function_count: int,
    ) -> None:
        """Sample and draw a safe mathematical function inside the visible world bounds."""
        variables: dict[str, float] = {}
        for dependency_id in obj.dependencies:
            parent = document.get(dependency_id)
            if isinstance(parent.geometry, float):
                variables[parent.name] = parent.geometry
        left, _, right, _ = viewport.world_bounds
        cache_key = (
            obj.revision,
            obj.id,
            viewport.center.x,
            viewport.scale,
            viewport.width,
            function_count,
            document.scene.get("function_sampling_quality", "medium"),
            tuple(sorted(variables.items())),
        )
        pieces = self._function_cache.get(cache_key)
        if pieces is None:
            quality_name = document.scene.get("function_sampling_quality", "medium")
            quality = {"low": 0.75, "medium": 1.5, "high": 3.0}.get(
                quality_name if isinstance(quality_name, str) else "medium", 1.5
            )
            zoom_factor = math.sqrt(min(4.0, max(0.5, viewport.scale / 80.0)))
            base_samples = round(viewport.width * quality * zoom_factor)
            sample_budget = max(1, math.ceil(math.sqrt(function_count)))
            sampled = sample_function(
                function,
                left,
                right,
                samples=min(4000, max(120, base_samples // sample_budget)),
                variables=variables,
            )
            pieces = sampled.segments
            if len(self._function_cache) >= 256:
                self._function_cache.clear()
            self._function_cache[cache_key] = pieces
        for piece in pieces:
            screen_points = [viewport.world_to_screen(point) for point in piece]
            painter.drawPolyline(QPolygonF([QPointF(*point) for point in screen_points]))

    def _draw_parametric(
        self,
        painter: QPainter,
        document: Document,
        obj: GeoObject,
        parametric: ParametricFunctionObject,
        viewport: Viewport,
    ) -> None:
        variables: dict[str, float] = {}
        for dependency_id in obj.dependencies:
            parent = document.get(dependency_id)
            if isinstance(parent.geometry, float):
                variables[parent.name] = parent.geometry
        quality_name = document.scene.get("function_sampling_quality", "medium")
        quality = {"low": 0.75, "medium": 1.5, "high": 3.0}.get(
            quality_name if isinstance(quality_name, str) else "medium", 1.5
        )
        samples = min(4000, max(200, round(600 * quality)))
        sampled = sample_parametric(parametric, samples=samples, variables=variables)
        for piece in sampled.segments:
            screen_points = [viewport.world_to_screen(point) for point in piece]
            painter.drawPolyline(QPolygonF([QPointF(*point) for point in screen_points]))

    def _draw_polar(
        self,
        painter: QPainter,
        document: Document,
        obj: GeoObject,
        polar: PolarFunctionObject,
        viewport: Viewport,
    ) -> None:
        variables: dict[str, float] = {}
        for dependency_id in obj.dependencies:
            parent = document.get(dependency_id)
            if isinstance(parent.geometry, float):
                variables[parent.name] = parent.geometry
        quality_name = document.scene.get("function_sampling_quality", "medium")
        quality = {"low": 0.75, "medium": 1.5, "high": 3.0}.get(
            quality_name if isinstance(quality_name, str) else "medium", 1.5
        )
        samples = min(4000, max(200, round(600 * quality)))
        sampled = sample_polar(polar, samples=samples, variables=variables)
        for piece in sampled.segments:
            screen_points = [viewport.world_to_screen(point) for point in piece]
            painter.drawPolyline(QPolygonF([QPointF(*point) for point in screen_points]))

    @staticmethod
    def _draw_locus(
        painter: QPainter,
        locus: Locus2D,
        viewport: Viewport,
    ) -> None:
        for piece in locus.segments:
            screen_points = [viewport.world_to_screen(point) for point in piece]
            painter.drawPolyline(QPolygonF([QPointF(*point) for point in screen_points]))

    @staticmethod
    def _draw_dataset(
        painter: QPainter,
        dataset: DatasetObject,
        style: Style,
        viewport: Viewport,
    ) -> None:
        """Render statistical visualization modes for a dataset."""
        if dataset.row_count == 0:
            return

        mode = dataset.plot_kind
        color = QColor(style.color)
        painter.save()

        if mode == "scatter" or (mode == "regression" and dataset.row_count < 2):
            # Render points as markers
            size = max(3.0, style.point_size)
            fill_color = QColor(style.color)
            fill_color.setAlphaF(max(0.2, style.fill_opacity))
            painter.setBrush(fill_color)
            pen = QPen(color, max(1.0, style.width))
            pen.setCosmetic(True)
            painter.setPen(pen)

            for pt in dataset.points:
                sx, sy = viewport.world_to_screen(pt)
                painter.drawEllipse(QPointF(sx, sy), size, size)

        elif mode == "regression":
            # 1. Render scatter points
            size = max(2.5, style.point_size * 0.8)
            fill_color = QColor(style.color)
            fill_color.setAlphaF(0.3)
            painter.setBrush(fill_color)
            pen_dots = QPen(color, 1.0)
            pen_dots.setCosmetic(True)
            painter.setPen(pen_dots)
            for pt in dataset.points:
                sx, sy = viewport.world_to_screen(pt)
                painter.drawEllipse(QPointF(sx, sy), size, size)

            # 2. Render regression line
            try:
                reg = dataset.linear_regression(0, 1)
                left, _, right, _ = viewport.world_bounds
                p1 = Point2D(left, reg.predict(left))
                p2 = Point2D(right, reg.predict(right))
                line_pen = QPen(color, max(1.5, style.width))
                line_pen.setCosmetic(True)
                painter.setPen(line_pen)
                s1 = viewport.world_to_screen(p1)
                s2 = viewport.world_to_screen(p2)
                painter.drawLine(QPointF(*s1), QPointF(*s2))
            except Exception:
                pass

        elif mode == "histogram":
            # Histogram computed on first column
            try:
                vals = dataset.column(0)
                stats = dataset.descriptive_stats(0)
                n = len(vals)
                bins_count = max(3, min(30, int(math.ceil(math.sqrt(n)))))
                val_min, val_max = stats.min, stats.max
                if val_min == val_max:
                    val_min -= 1.0
                    val_max += 1.0
                bin_width = (val_max - val_min) / bins_count
                counts = [0] * bins_count
                for v in vals:
                    idx = int((v - val_min) / bin_width)
                    if idx >= bins_count:
                        idx = bins_count - 1
                    counts[idx] += 1

                fill_col = QColor(style.color)
                fill_col.setAlphaF(max(0.3, style.fill_opacity))
                painter.setBrush(fill_col)
                border_pen = QPen(color, max(1.0, style.width))
                border_pen.setCosmetic(True)
                painter.setPen(border_pen)

                for i, cnt in enumerate(counts):
                    if cnt == 0:
                        continue
                    b_left = val_min + i * bin_width
                    b_right = b_left + bin_width
                    # Rectangle in world coordinates: [b_left, 0] to [b_right, cnt]
                    sx1, sy1 = viewport.world_to_screen(Point2D(b_left, 0.0))
                    sx2, sy2 = viewport.world_to_screen(Point2D(b_right, float(cnt)))
                    rect = QRectF(
                        min(sx1, sx2),
                        min(sy1, sy2),
                        abs(sx2 - sx1),
                        abs(sy2 - sy1),
                    )
                    painter.drawRect(rect)
            except Exception:
                pass

        elif mode == "boxplot":
            # Box plot on first column, centered at x=1.0 or custom offset
            try:
                stats = dataset.descriptive_stats(0)
                cx = 0.0
                box_width = 1.0
                # World coordinates
                q1, med, q3 = stats.q1, stats.median, stats.q3
                w_min = max(stats.min, q1 - 1.5 * stats.iqr)
                w_max = min(stats.max, q3 + 1.5 * stats.iqr)

                fill_col = QColor(style.color)
                fill_col.setAlphaF(max(0.2, style.fill_opacity))
                painter.setBrush(fill_col)
                pen = QPen(color, max(1.5, style.width))
                pen.setCosmetic(True)
                painter.setPen(pen)

                # 1. Box Q1 to Q3
                s_left, s_top = viewport.world_to_screen(Point2D(cx - box_width / 2, q3))
                s_right, s_bot = viewport.world_to_screen(Point2D(cx + box_width / 2, q1))
                painter.drawRect(
                    QRectF(
                        min(s_left, s_right),
                        min(s_top, s_bot),
                        abs(s_right - s_left),
                        abs(s_bot - s_top),
                    )
                )

                # 2. Median line
                sm1 = viewport.world_to_screen(Point2D(cx - box_width / 2, med))
                sm2 = viewport.world_to_screen(Point2D(cx + box_width / 2, med))
                painter.drawLine(QPointF(*sm1), QPointF(*sm2))

                # 3. Whiskers (vertical stem and caps)
                sw_top = viewport.world_to_screen(Point2D(cx, w_max))
                sq3 = viewport.world_to_screen(Point2D(cx, q3))
                painter.drawLine(QPointF(*sw_top), QPointF(*sq3))

                sw_bot = viewport.world_to_screen(Point2D(cx, w_min))
                sq1 = viewport.world_to_screen(Point2D(cx, q1))
                painter.drawLine(QPointF(*sw_bot), QPointF(*sq1))

                # Caps
                cap_w = box_width * 0.4
                c1_top = viewport.world_to_screen(Point2D(cx - cap_w / 2, w_max))
                c2_top = viewport.world_to_screen(Point2D(cx + cap_w / 2, w_max))
                painter.drawLine(QPointF(*c1_top), QPointF(*c2_top))

                c1_bot = viewport.world_to_screen(Point2D(cx - cap_w / 2, w_min))
                c2_bot = viewport.world_to_screen(Point2D(cx + cap_w / 2, w_min))
                painter.drawLine(QPointF(*c1_bot), QPointF(*c2_bot))

                # 4. Outliers
                for out_v in stats.outliers:
                    so = viewport.world_to_screen(Point2D(cx, out_v))
                    painter.drawEllipse(QPointF(*so), 3.0, 3.0)
            except Exception:
                pass

        elif mode == "bar":
            # Bar chart: x coordinate (column 0 or 1..N) and height (column 1 or column 0)
            try:
                xs = dataset.x_values
                ys = dataset.y_values
                fill_col = QColor(style.color)
                fill_col.setAlphaF(max(0.3, style.fill_opacity))
                painter.setBrush(fill_col)
                border_pen = QPen(color, max(1.0, style.width))
                border_pen.setCosmetic(True)
                painter.setPen(border_pen)

                bar_w = 0.6
                for xi, yi in zip(xs, ys, strict=False):
                    sx1, sy1 = viewport.world_to_screen(Point2D(xi - bar_w / 2, 0.0))
                    sx2, sy2 = viewport.world_to_screen(Point2D(xi + bar_w / 2, yi))
                    rect = QRectF(
                        min(sx1, sx2),
                        min(sy1, sy2),
                        abs(sx2 - sx1),
                        abs(sy2 - sy1),
                    )
                    painter.drawRect(rect)
            except Exception:
                pass

        painter.restore()

    @staticmethod
    def render_transient_traces(
        painter: QPainter,
        viewport: Viewport,
        palette: QPalette,
        traces: Mapping[str, list[Point2D]],
    ) -> None:
        """Draw ephemeral canvas trace points and segments outside the persistent model."""
        if not traces:
            return
        painter.save()
        trace_color = QColor(palette.highlight().color())
        trace_color.setAlpha(160)
        pen = QPen(trace_color, 1.5, Qt.PenStyle.DotLine)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(trace_color)
        for points in traces.values():
            if len(points) >= 2:
                screen_points = [viewport.world_to_screen(p) for p in points]
                painter.drawPolyline(QPolygonF([QPointF(*p) for p in screen_points]))
            for pt in points:
                sx, sy = viewport.world_to_screen(pt)
                painter.drawEllipse(QPointF(sx, sy), 2.5, 2.5)
        painter.restore()

    def _draw_function_analysis(
        self,
        painter: QPainter,
        document: Document,
        objects: Iterable[GeoObject],
        viewport: Viewport,
        palette: QPalette,
    ) -> None:
        functions = [
            (obj, obj.geometry, self._function_variables(document, obj))
            for obj in objects
            if isinstance(obj.geometry, FunctionObject)
        ]
        if not functions:
            return
        left, _, right, _ = viewport.world_bounds
        marker_color = QColor(palette.highlight().color())
        painter.save()
        painter.setPen(QPen(marker_color, 1.5))
        painter.setBrush(marker_color)
        if document.scene.get("show_function_roots", False) is True:
            for _obj, function, variables in functions:
                for x in self._safe_roots(function, left, right, variables):
                    self._draw_analysis_marker(painter, viewport, Point2D(x, 0))
        if document.scene.get("show_function_extrema", False) is True:
            for _obj, function, variables in functions:
                try:
                    function_extrema = extrema(function, left, right, variables, samples=256)
                except (ValueError, ArithmeticError):
                    function_extrema = ()
                for extremum in function_extrema:
                    self._draw_analysis_marker(painter, viewport, Point2D(extremum.x, extremum.y))
        if document.scene.get("show_function_intersections", False) is True:
            for index, (_obj, first, first_variables) in enumerate(functions):
                for _other_obj, second, second_variables in functions[index + 1 :]:
                    variables = {**first_variables, **second_variables}
                    try:
                        points = intersections(first, second, left, right, variables, samples=256)
                    except (ValueError, ArithmeticError):
                        points = ()
                    for x, y in points:
                        self._draw_analysis_marker(painter, viewport, Point2D(x, y))
        if document.scene.get("show_function_derivative", False) is True:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            derivative_pen = QPen(marker_color, 1.2, Qt.PenStyle.DotLine)
            derivative_pen.setCosmetic(True)
            painter.setPen(derivative_pen)
            for _obj, function, variables in functions:
                self._draw_derivative(painter, function, variables, viewport)
        painter.restore()

    @staticmethod
    def _safe_roots(
        function: FunctionObject,
        left: float,
        right: float,
        variables: dict[str, float],
    ) -> tuple[float, ...]:
        try:
            return find_roots(function, left, right, variables, samples=256)
        except (ValueError, ArithmeticError):
            return ()

    @staticmethod
    def _draw_analysis_marker(painter: QPainter, viewport: Viewport, point: Point2D) -> None:
        x, y = viewport.world_to_screen(point)
        if -6 <= x <= viewport.width + 6 and -6 <= y <= viewport.height + 6:
            painter.drawEllipse(QPointF(x, y), 4.0, 4.0)

    @staticmethod
    def _function_variables(document: Document, obj: GeoObject) -> dict[str, float]:
        return {
            parent.name: parent.geometry
            for dependency_id in obj.dependencies
            if isinstance((parent := document.get(dependency_id)).geometry, float)
        }

    @staticmethod
    def _draw_derivative(
        painter: QPainter,
        function: FunctionObject,
        variables: dict[str, float],
        viewport: Viewport,
    ) -> None:
        left, _, right, _ = viewport.world_bounds
        samples = min(1200, max(100, viewport.width))
        previous: Point2D | None = None
        for index in range(samples):
            x = left + (right - left) * index / (samples - 1)
            try:
                point = Point2D(x, derivative(function, x, variables))
            except (ValueError, ArithmeticError):
                previous = None
                continue
            if (
                previous is not None
                and abs(point.y - previous.y) * viewport.scale < viewport.height * 4
            ):
                Renderer._draw_clipped_line(
                    painter,
                    clip_segment(previous, point, viewport.world_bounds),
                    viewport,
                )
            previous = point

    def _draw_labels(
        self,
        painter: QPainter,
        document: Document,
        objects: Iterable[GeoObject],
        viewport: Viewport,
        palette: QPalette,
    ) -> None:
        painter.setPen(QPen(palette.text().color()))
        for obj in objects:
            if not obj.style.show_label:
                continue
            anchor = self._label_anchor(document, obj, viewport)
            if anchor is None:
                continue
            x, y = viewport.world_to_screen(anchor)
            if -100 <= x <= viewport.width + 100 and -100 <= y <= viewport.height + 100:
                painter.drawText(QPointF(x + 7, y - 7), obj.name)

    @staticmethod
    def _label_anchor(document: Document, obj: GeoObject, viewport: Viewport) -> Point2D | None:
        geometry = obj.geometry
        if isinstance(geometry, Point2D):
            return geometry
        if isinstance(geometry, Segment2D):
            return Point2D(
                geometry.start.x + (geometry.end.x - geometry.start.x) / 2,
                geometry.start.y + (geometry.end.y - geometry.start.y) / 2,
            )
        if isinstance(geometry, Line2D):
            return geometry.project(viewport.center)
        if isinstance(geometry, Ray2D):
            return geometry.start
        if isinstance(geometry, Circle2D):
            return Point2D(geometry.center.x + geometry.radius, geometry.center.y)
        if isinstance(geometry, Ellipse2D):
            return Point2D(
                geometry.center.x + geometry.a * math.cos(geometry.angle),
                geometry.center.y + geometry.a * math.sin(geometry.angle),
            )
        if isinstance(geometry, Parabola2D):
            return geometry.vertex
        if isinstance(geometry, Hyperbola2D):
            return geometry.vertices[1]
        if isinstance(geometry, Polygon2D):
            return geometry.centroid or geometry.vertices[0]
        if isinstance(geometry, FunctionObject):
            variables: dict[str, float] = {}
            for dependency_id in obj.dependencies:
                parent = document.get(dependency_id)
                if isinstance(parent.geometry, float):
                    variables[parent.name] = parent.geometry
            try:
                return Point2D(viewport.center.x, geometry.evaluate(viewport.center.x, variables))
            except (ValueError, ArithmeticError):
                return None
        if isinstance(geometry, ParametricFunctionObject):
            variables = {
                parent.name: parent.geometry
                for dependency_id in obj.dependencies
                if isinstance((parent := document.get(dependency_id)).geometry, float)
            }
            try:
                return geometry.evaluate(geometry.t_min, variables)
            except (ValueError, ArithmeticError):
                return None
        if isinstance(geometry, PolarFunctionObject):
            variables = {
                parent.name: parent.geometry
                for dependency_id in obj.dependencies
                if isinstance((parent := document.get(dependency_id)).geometry, float)
            }
            try:
                return geometry.evaluate(geometry.theta_min, variables)
            except (ValueError, ArithmeticError):
                return None
        if isinstance(geometry, Locus2D):
            for piece in geometry.segments:
                if piece:
                    return piece[len(piece) // 2]
            return None
        if isinstance(geometry, DatasetObject):
            if geometry.points:
                return geometry.points[0]
            return None
        if isinstance(geometry, Vector2D) and obj.dependencies:
            parent_geometry = document.get(obj.dependencies[0]).geometry
            if isinstance(parent_geometry, Point2D):
                return Point2D(
                    parent_geometry.x + geometry.x,
                    parent_geometry.y + geometry.y,
                )
        return None

    @staticmethod
    def _pen(style: Style) -> QPen:
        pen = QPen(QColor(style.color), style.width)
        line_styles = {
            "solid": Qt.PenStyle.SolidLine,
            "dash": Qt.PenStyle.DashLine,
            "dot": Qt.PenStyle.DotLine,
        }
        pen.setStyle(line_styles[style.line_style])
        pen.setCosmetic(True)
        return pen
