"""Construction tools that create serializable GeoObject recipes through commands."""

from __future__ import annotations

from dataclasses import dataclass

from pygeolab.commands import CommandHistory, CreateObjectsCommand
from pygeolab.geometry import Circle2D, Line2D, Point2D, Polygon2D, Ray2D, Segment2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject, number
from pygeolab.rendering.hit_test import first_hit
from pygeolab.rendering.viewport import Viewport
from pygeolab.interaction.tools.base import GeometryPreview, PointerContext, Tool


@dataclass(slots=True)
class _PointChoice:
    obj: GeoObject
    pending: bool


class _DocumentTool(Tool):
    def __init__(self, document: Document, history: CommandHistory, viewport: Viewport) -> None:
        self.document = document
        self.history = history
        self.viewport = viewport
        self._implicit_serial = 1

    def set_viewport(self, viewport: Viewport) -> None:
        """Update the camera used for hit-testing after pan, zoom or resize."""
        self.viewport = viewport

    def _hit(self, context: PointerContext, kinds: frozenset[str] | None = None) -> GeoObject | None:
        return first_hit(
            self.document, self.viewport, context.screen_x, context.screen_y, kinds=kinds
        )

    def _point_choice(self, context: PointerContext) -> _PointChoice:
        existing = self._hit(context, frozenset({"point", "midpoint", "intersection", "projection", "point_on", "translate", "rotate", "reflect_point", "reflect_line", "scale"}))
        if existing is not None and isinstance(existing.geometry, Point2D):
            return _PointChoice(existing, False)
        existing_names = {obj.name for obj in self.document.objects.values()}
        while f"P{self._implicit_serial}" in existing_names:
            self._implicit_serial += 1
        name = f"P{self._implicit_serial}"
        self._implicit_serial += 1
        point = GeoObject(
            "point",
            name,
            params={"x": context.world.x, "y": context.world.y},
        )
        return _PointChoice(point, True)

    def _execute(self, objects: tuple[GeoObject, ...]) -> None:
        self.history.execute(CreateObjectsCommand(self.document, objects))


class PointTool(_DocumentTool):
    """Create one free point at each click unless an existing point is hit."""

    name = "point"

    def press(self, context: PointerContext) -> None:
        choice = self._point_choice(context)
        if choice.pending:
            self._execute((choice.obj,))


class _TwoPointTool(_DocumentTool):
    kind = "segment"
    prefix = "s"

    def __init__(self, document: Document, history: CommandHistory, viewport: Viewport) -> None:
        super().__init__(document, history, viewport)
        self._first: _PointChoice | None = None
        self._cursor: Point2D | None = None

    def press(self, context: PointerContext) -> None:
        choice = self._point_choice(context)
        if self._first is None:
            self._first = choice
            self._cursor = context.world
            return
        first = self._first
        if first.obj.id == choice.obj.id:
            return
        result = GeoObject(
            self.kind,
            self.document.unique_name(self.prefix),
            dependencies=(first.obj.id, choice.obj.id),
        )
        objects = tuple(obj for obj, pending in ((first.obj, first.pending), (choice.obj, choice.pending)) if pending) + (result,)
        self._execute(objects)
        self.cancel()

    def move(self, context: PointerContext) -> None:
        if self._first is not None:
            self._cursor = context.world

    def cancel(self) -> None:
        self._first = None
        self._cursor = None

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        if self._first is None or self._cursor is None:
            return ()
        start = self._first.obj.geometry
        if not isinstance(start, Point2D):
            start = Point2D(number(self._first.obj.params, "x"), number(self._first.obj.params, "y"))
        if self.kind == "line":
            line = Line2D.from_points(start, self._cursor)
            return () if line is None else (line,)
        if self.kind == "circle":
            return (Circle2D(start, start.distance_to(self._cursor)),)
        return (Segment2D(start, self._cursor),)


class SegmentTool(_TwoPointTool):
    """Create a segment from two existing or implicit points."""

    name = "segment"
    kind = "segment"
    prefix = "s"


class LineTool(_TwoPointTool):
    """Create an infinite line through two points."""

    name = "line"
    kind = "line"
    prefix = "d"


class CircleTool(_TwoPointTool):
    """Create a center-through-point circle."""

    name = "circle"
    kind = "circle"
    prefix = "c"


class PolygonTool(_DocumentTool):
    """Create a polygon by clicking vertices and close by clicking the first vertex."""

    name = "polygon"

    def __init__(self, document: Document, history: CommandHistory, viewport: Viewport) -> None:
        super().__init__(document, history, viewport)
        self._vertices: list[_PointChoice] = []
        self._cursor: Point2D | None = None

    def press(self, context: PointerContext) -> None:
        if len(self._vertices) >= 3:
            first_point = self._point_value(self._vertices[0])
            if first_point.distance_to(context.world) * self.viewport.scale <= 8.0:
                self._finish()
                return
        choice = self._point_choice(context)
        if len(self._vertices) >= 3 and choice.obj.id == self._vertices[0].obj.id:
            self._finish()
            return
        if any(choice.obj.id == vertex.obj.id for vertex in self._vertices):
            return
        self._vertices.append(choice)
        self._cursor = context.world

    def move(self, context: PointerContext) -> None:
        if self._vertices:
            self._cursor = context.world

    def cancel(self) -> None:
        self._vertices.clear()
        self._cursor = None

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        points = [self._point_value(choice) for choice in self._vertices]
        if not points:
            return ()
        if self._cursor is not None:
            points.append(self._cursor)
        return tuple(Segment2D(a, b) for a, b in zip(points, points[1:]))

    def _finish(self) -> None:
        polygon = GeoObject(
            "polygon",
            self.document.unique_name("poly"),
            dependencies=tuple(choice.obj.id for choice in self._vertices),
        )
        pending = tuple(choice.obj for choice in self._vertices if choice.pending)
        self._execute(pending + (polygon,))
        self.cancel()

    @staticmethod
    def _point_value(choice: _PointChoice) -> Point2D:
        if isinstance(choice.obj.geometry, Point2D):
            return choice.obj.geometry
        return Point2D(number(choice.obj.params, "x"), number(choice.obj.params, "y"))


class MidpointTool(_DocumentTool):
    """Create a midpoint from one segment or two points."""

    name = "midpoint"

    def __init__(self, document: Document, history: CommandHistory, viewport: Viewport) -> None:
        super().__init__(document, history, viewport)
        self._first: GeoObject | None = None

    def press(self, context: PointerContext) -> None:
        segment = self._hit(context, frozenset({"segment"}))
        if segment is not None:
            self._execute((GeoObject("midpoint", self.document.unique_name("M"), (segment.id,)),))
            self._first = None
            return
        point = self._hit(context)
        if point is None or not isinstance(point.geometry, Point2D):
            return
        if self._first is None:
            self._first = point
        elif self._first.id != point.id:
            self._execute((GeoObject("midpoint", self.document.unique_name("M"), (self._first.id, point.id)),))
            self._first = None

    def cancel(self) -> None:
        self._first = None


class IntersectionTool(_DocumentTool):
    """Create the first finite intersection of two supported loci."""

    name = "intersection"

    def __init__(self, document: Document, history: CommandHistory, viewport: Viewport) -> None:
        super().__init__(document, history, viewport)
        self._first: GeoObject | None = None

    def press(self, context: PointerContext) -> None:
        obj = self._hit(context)
        if obj is None or not isinstance(obj.geometry, (Line2D, Segment2D, Ray2D, Circle2D)):
            return
        if self._first is None:
            self._first = obj
        elif self._first.id != obj.id:
            intersection = GeoObject(
                "intersection", self.document.unique_name("I"), (self._first.id, obj.id), params={"index": 0}
            )
            self._execute((intersection,))
            self._first = None

    def cancel(self) -> None:
        self._first = None


class _PointLineTool(_DocumentTool):
    kind = "parallel"
    prefix = "d"

    def __init__(self, document: Document, history: CommandHistory, viewport: Viewport) -> None:
        super().__init__(document, history, viewport)
        self._point: GeoObject | None = None

    def press(self, context: PointerContext) -> None:
        if self._point is None:
            obj = self._hit(context)
            if obj is not None and isinstance(obj.geometry, Point2D):
                self._point = obj
            return
        line = self._hit(context, frozenset({"line", "segment", "ray"}))
        if line is not None:
            self._execute((GeoObject(self.kind, self.document.unique_name(self.prefix), (self._point.id, line.id)),))
            self._point = None

    def cancel(self) -> None:
        self._point = None


class ParallelTool(_PointLineTool):
    """Create a line parallel to a selected linear object through a point."""

    name = "parallel"
    kind = "parallel"


class PerpendicularTool(_PointLineTool):
    """Create a line perpendicular to a selected linear object through a point."""

    name = "perpendicular"
    kind = "perpendicular"
