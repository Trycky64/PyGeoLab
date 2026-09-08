"""Advanced construction and transformation tools built from existing recipes.

Every completed gesture executes one ``CreateObjectsCommand``. Intermediate
clicks and pointer moves remain transient, so Escape can discard them cleanly.
"""

from __future__ import annotations

import math

from pygeolab.commands import CommandHistory
from pygeolab.geometry import Circle2D, Line2D, Point2D, Ray2D, Segment2D, Vector2D
from pygeolab.geometry.transforms import (
    angle_bisector,
    circumcircle,
    perpendicular_bisector,
    reflect_line,
    reflect_point,
    rotate,
    scale,
    translate,
)
from pygeolab.interaction.tools.base import GeometryPreview, PointerContext
from pygeolab.interaction.tools.construction import DocumentTool, PointChoice, TwoPointTool
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.rendering.viewport import Viewport

_POINT_KINDS = frozenset(
    {
        "point",
        "midpoint",
        "intersection",
        "projection",
        "point_on",
        "translate",
        "rotate",
        "reflect_point",
        "reflect_line",
        "scale",
    }
)
_LINE_KINDS = frozenset(
    {
        "line",
        "segment",
        "ray",
        "parallel",
        "perpendicular",
        "perpendicular_bisector",
        "angle_bisector",
    }
)
_LOCUS_KINDS = _LINE_KINDS | frozenset({"circle", "circle_radius", "circumcircle"})


def _point_geometry(obj: GeoObject) -> Point2D | None:
    return obj.geometry if isinstance(obj.geometry, Point2D) else None


def _line_geometry(obj: GeoObject) -> Line2D | None:
    geometry = obj.geometry
    if isinstance(geometry, Line2D):
        return geometry
    if isinstance(geometry, (Segment2D, Ray2D)):
        end = geometry.end if isinstance(geometry, Segment2D) else geometry.through
        return Line2D.from_points(geometry.start, end)
    return None


class RayTool(TwoPointTool):
    """Create a ray from an origin and a second defining point."""

    name = "ray"
    kind = "ray"
    prefix = "r"


class VectorTool(TwoPointTool):
    """Create a vector from two existing or implicit points."""

    name = "vector"
    kind = "vector"
    prefix = "v"


class PerpendicularBisectorTool(TwoPointTool):
    """Create the perpendicular bisector of two chosen points."""

    name = "perpendicular_bisector"
    kind = "perpendicular_bisector"
    prefix = "m"

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Preview the infinite bisector after the first point is known."""
        if self._first is None or self._cursor is None:
            return ()
        line = perpendicular_bisector(self._point_value(self._first), self._cursor)
        return () if line is None else (line,)


class _ThreePointTool(DocumentTool):
    kind = "circumcircle"
    prefix = "c"

    def __init__(self, document: Document, history: CommandHistory, viewport: Viewport) -> None:
        super().__init__(document, history, viewport)
        self._points: list[PointChoice] = []
        self._cursor: Point2D | None = None

    def press(self, context: PointerContext) -> None:
        """Collect three distinct defining points and commit one recipe."""
        choice = self._point_choice(context)
        if any(choice.obj.id == selected.obj.id for selected in self._points):
            return
        self._points.append(choice)
        self._cursor = context.world
        if len(self._points) != 3:
            return
        result = GeoObject(
            self.kind,
            self.document.unique_name(self.prefix),
            dependencies=tuple(point.obj.id for point in self._points),
        )
        pending = tuple(point.obj for point in self._points if point.pending)
        self._execute(pending + (result,))
        self.cancel()

    def move(self, context: PointerContext) -> None:
        """Update the final defining point used by the preview."""
        if self._points:
            self._cursor = context.world

    def cancel(self) -> None:
        """Discard every uncommitted defining point."""
        self._points.clear()
        self._cursor = None

    def _preview_points(self) -> tuple[Point2D, ...]:
        points = tuple(self._point_value(choice) for choice in self._points)
        if self._cursor is not None and len(points) < 3:
            return points + (self._cursor,)
        return points


class AngleBisectorTool(_ThreePointTool):
    """Create the bisector of an angle selected as arm, vertex, arm."""

    name = "angle_bisector"
    kind = "angle_bisector"
    prefix = "b"

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Preview both arms and the resulting infinite bisector."""
        points = self._preview_points()
        if len(points) < 2:
            return ()
        arms: tuple[GeometryPreview, ...] = (Segment2D(points[1], points[0]),)
        if len(points) < 3:
            return arms
        line = angle_bisector(points[0], points[1], points[2])
        second_arm = Segment2D(points[1], points[2])
        return arms + (second_arm,) if line is None else arms + (second_arm, line)


class CircumcircleTool(_ThreePointTool):
    """Create the unique circle through three non-collinear points."""

    name = "circumcircle"
    kind = "circumcircle"
    prefix = "c"

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Preview a circumcircle as soon as three temporary points exist."""
        points = self._preview_points()
        if len(points) < 3:
            return () if len(points) < 2 else (Segment2D(points[0], points[1]),)
        circle = circumcircle(points[0], points[1], points[2])
        return () if circle is None else (circle,)


class AngleTool(_ThreePointTool):
    """Create a dynamic angle measure selected as arm, vertex, arm."""

    name = "angle"
    kind = "angle"
    prefix = "α"

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Preview the one or two segments defining the measured angle."""
        points = self._preview_points()
        if len(points) < 2:
            return ()
        first = Segment2D(points[1], points[0])
        return (first,) if len(points) < 3 else (first, Segment2D(points[1], points[2]))


class CircleRadiusTool(DocumentTool):
    """Create a circle with a persistent literal radius chosen on the canvas."""

    name = "circle_radius"

    def __init__(self, document: Document, history: CommandHistory, viewport: Viewport) -> None:
        super().__init__(document, history, viewport)
        self._center: PointChoice | None = None
        self._cursor: Point2D | None = None

    def press(self, context: PointerContext) -> None:
        """Choose a center, then use the second click distance as the radius."""
        if self._center is None:
            self._center = self._point_choice(context)
            self._cursor = context.world
            return
        radius = self._point_value(self._center).distance_to(context.world)
        if radius <= 1e-12:
            return
        circle = GeoObject(
            "circle_radius",
            self.document.unique_name("c"),
            dependencies=(self._center.obj.id,),
            params={"radius": radius},
        )
        pending = (self._center.obj,) if self._center.pending else ()
        self._execute(pending + (circle,))
        self.cancel()

    def move(self, context: PointerContext) -> None:
        """Update the radius preview after choosing the center."""
        if self._center is not None:
            self._cursor = context.world

    def cancel(self) -> None:
        """Discard the pending center and radius."""
        self._center = None
        self._cursor = None

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Return the temporary literal-radius circle."""
        if self._center is None or self._cursor is None:
            return ()
        center = self._point_value(self._center)
        return (Circle2D(center, center.distance_to(self._cursor)),)


class ProjectionTool(DocumentTool):
    """Project a chosen point orthogonally onto a linear support."""

    name = "projection"

    def __init__(self, document: Document, history: CommandHistory, viewport: Viewport) -> None:
        super().__init__(document, history, viewport)
        self._point: PointChoice | None = None
        self._hovered: GeoObject | None = None

    def press(self, context: PointerContext) -> None:
        """Choose a point followed by a line, segment, or ray."""
        if self._point is None:
            self._point = self._point_choice(context)
            return
        target = self._hit(context, _LINE_KINDS)
        if target is None:
            return
        result = GeoObject(
            "projection",
            self.document.unique_name("H"),
            dependencies=(self._point.obj.id, target.id),
        )
        pending = (self._point.obj,) if self._point.pending else ()
        self._execute(pending + (result,))
        self.cancel()

    def move(self, context: PointerContext) -> None:
        """Track the linear object currently eligible for projection."""
        self._hovered = self._hit(context, _LINE_KINDS) if self._point is not None else None

    def cancel(self) -> None:
        """Discard the selected point and hovered support."""
        self._point = None
        self._hovered = None

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Draw the perpendicular segment and its projected endpoint."""
        if self._point is None or self._hovered is None:
            return ()
        point = self._point_value(self._point)
        geometry = self._hovered.geometry
        if isinstance(geometry, (Segment2D, Ray2D)):
            projection = geometry.closest_point(point)
        else:
            line = _line_geometry(self._hovered)
            if line is None:
                return ()
            projection = line.project(point)
        return (Segment2D(point, projection), projection)


class PointOnObjectTool(DocumentTool):
    """Create a dependent point at the clicked parameter of a supported locus."""

    name = "point_on"

    def __init__(self, document: Document, history: CommandHistory, viewport: Viewport) -> None:
        super().__init__(document, history, viewport)
        self._hovered_preview: Point2D | None = None

    def press(self, context: PointerContext) -> None:
        """Store a normalized locus parameter rather than derived coordinates."""
        target = self._hit(context, _LOCUS_KINDS)
        if target is None:
            return
        parameter, point = _locus_parameter(target, context.world)
        result = GeoObject(
            "point_on",
            self.document.unique_name("P"),
            dependencies=(target.id,),
            params={"t": parameter},
        )
        self._execute((result,))
        self._hovered_preview = point

    def move(self, context: PointerContext) -> None:
        """Preview the closest point of the locus beneath the cursor."""
        target = self._hit(context, _LOCUS_KINDS)
        self._hovered_preview = (
            None if target is None else _locus_parameter(target, context.world)[1]
        )

    def cancel(self) -> None:
        """Clear the transient locus point preview."""
        self._hovered_preview = None

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Return the current closest locus point."""
        return () if self._hovered_preview is None else (self._hovered_preview,)


class DistanceTool(DocumentTool):
    """Create a dynamic distance from a point to a point or linear object."""

    name = "distance"

    def __init__(self, document: Document, history: CommandHistory, viewport: Viewport) -> None:
        super().__init__(document, history, viewport)
        self._first: PointChoice | None = None
        self._endpoint: Point2D | None = None

    def press(self, context: PointerContext) -> None:
        """Choose the first point and then a point or linear target."""
        if self._first is None:
            self._first = self._point_choice(context)
            return
        target = self._hit(context, _POINT_KINDS)
        second_choice: PointChoice | None = None
        if target is None:
            target = self._hit(context, _LINE_KINDS)
        elif target.id == self._first.obj.id:
            return
        if target is None:
            second_choice = self._point_choice(context)
            target = second_choice.obj
        result = GeoObject(
            "distance",
            self.document.unique_name("dist"),
            dependencies=(self._first.obj.id, target.id),
        )
        pending = tuple(
            choice.obj
            for choice in (self._first, second_choice)
            if choice is not None and choice.pending
        )
        self._execute(pending + (result,))
        self.cancel()

    def move(self, context: PointerContext) -> None:
        """Preview the shortest segment to the current target or cursor."""
        if self._first is None:
            return
        target = self._hit(context, _POINT_KINDS)
        if target is None:
            target = self._hit(context, _LINE_KINDS)
        point = self._point_value(self._first)
        if target is None:
            self._endpoint = context.world
        elif isinstance(target.geometry, Point2D):
            self._endpoint = target.geometry
        else:
            line = _line_geometry(target)
            self._endpoint = None if line is None else line.project(point)

    def cancel(self) -> None:
        """Discard the first point and temporary measurement endpoint."""
        self._first = None
        self._endpoint = None

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Return the temporary measurement segment."""
        if self._first is None or self._endpoint is None:
            return ()
        return (Segment2D(self._point_value(self._first), self._endpoint),)


class TranslationTool(DocumentTool):
    """Translate a selected point by an existing vector object."""

    name = "translate"

    def __init__(self, document: Document, history: CommandHistory, viewport: Viewport) -> None:
        super().__init__(document, history, viewport)
        self._point: GeoObject | None = None
        self._hovered: GeoObject | None = None

    def press(self, context: PointerContext) -> None:
        """Choose a point followed by the vector that drives its translation."""
        if self._point is None:
            candidate = self._hit(context, _POINT_KINDS)
            if candidate is not None and _point_geometry(candidate) is not None:
                self._point = candidate
            return
        vector = self._hit(context, frozenset({"vector"}))
        if vector is None or not isinstance(vector.geometry, Vector2D):
            return
        result = GeoObject(
            "translate",
            self.document.unique_name("T"),
            dependencies=(self._point.id, vector.id),
        )
        self._execute((result,))
        self.cancel()

    def move(self, context: PointerContext) -> None:
        """Track a vector beneath the pointer for the translated-point preview."""
        self._hovered = (
            self._hit(context, frozenset({"vector"})) if self._point is not None else None
        )

    def cancel(self) -> None:
        """Discard the selected source point and vector preview."""
        self._point = None
        self._hovered = None

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Return the translated point and displacement segment."""
        if self._point is None or self._hovered is None:
            return ()
        point = _point_geometry(self._point)
        vector = self._hovered.geometry
        if point is None or not isinstance(vector, Vector2D):
            return ()
        result = translate(point, vector)
        return (Segment2D(point, result), result)


class CentralReflectionTool(TwoPointTool):
    """Reflect a point through a selected center point."""

    name = "reflect_point"
    kind = "reflect_point"
    prefix = "S"

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Preview the centrally reflected point and its alignment segment."""
        if self._first is None or self._cursor is None:
            return ()
        source = self._point_value(self._first)
        result = reflect_point(source, self._cursor)
        return (Segment2D(source, result), result)


class AxialReflectionTool(ProjectionTool):
    """Reflect a selected point across a line, segment, or ray."""

    name = "reflect_line"

    def press(self, context: PointerContext) -> None:
        """Choose a point followed by the axis used for reflection."""
        if self._point is None:
            self._point = self._point_choice(context)
            return
        target = self._hit(context, _LINE_KINDS)
        if target is None:
            return
        result = GeoObject(
            "reflect_line",
            self.document.unique_name("S"),
            dependencies=(self._point.obj.id, target.id),
        )
        pending = (self._point.obj,) if self._point.pending else ()
        self._execute(pending + (result,))
        self.cancel()

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Preview the reflected point rather than the projection endpoint."""
        if self._point is None or self._hovered is None:
            return ()
        source = self._point_value(self._point)
        line = _line_geometry(self._hovered)
        if line is None:
            return ()
        result = reflect_line(source, line)
        return (Segment2D(source, result), result)


class _ParameterizedTransformTool(DocumentTool):
    kind = "rotate"
    prefix = "R"

    def __init__(self, document: Document, history: CommandHistory, viewport: Viewport) -> None:
        super().__init__(document, history, viewport)
        self._source: PointChoice | None = None
        self._center: PointChoice | None = None
        self._cursor: Point2D | None = None

    def press(self, context: PointerContext) -> None:
        """Choose source and center points, then commit the pointer-defined parameter."""
        if self._source is None:
            self._source = self._point_choice(context)
            return
        if self._center is None:
            choice = self._point_choice(context)
            if choice.obj.id == self._source.obj.id:
                return
            self._center = choice
            self._cursor = context.world
            return
        parameter = self._parameter(context.world)
        if parameter is None:
            return
        result = GeoObject(
            self.kind,
            self.document.unique_name(self.prefix),
            dependencies=(self._source.obj.id, self._center.obj.id),
            params={self._parameter_name: parameter},
        )
        pending = tuple(choice.obj for choice in (self._source, self._center) if choice.pending)
        self._execute(pending + (result,))
        self.cancel()

    def move(self, context: PointerContext) -> None:
        """Update the interactive angle or scale factor preview."""
        if self._center is not None:
            self._cursor = context.world

    def cancel(self) -> None:
        """Discard source, center, and parameter cursor."""
        self._source = None
        self._center = None
        self._cursor = None

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Preview the transformed point and its center connection."""
        if self._source is None or self._center is None or self._cursor is None:
            return ()
        parameter = self._parameter(self._cursor)
        if parameter is None:
            return ()
        source = self._point_value(self._source)
        center = self._point_value(self._center)
        result = self._transform(source, center, parameter)
        return (Segment2D(center, result), result)

    @property
    def _parameter_name(self) -> str:
        return "angle"

    def _parameter(self, cursor: Point2D) -> float | None:
        assert self._source is not None and self._center is not None
        source = Vector2D.between(self._point_value(self._center), self._point_value(self._source))
        target = Vector2D.between(self._point_value(self._center), cursor)
        if source.norm <= 1e-12 or target.norm <= 1e-12:
            return None
        return math.atan2(source.cross(target), source.dot(target))

    def _transform(self, source: Point2D, center: Point2D, parameter: float) -> Point2D:
        return rotate(source, parameter, center)


class RotationTool(_ParameterizedTransformTool):
    """Rotate a point using source, center, and target-direction clicks."""

    name = "rotate"
    kind = "rotate"
    prefix = "R"


class ScaleTool(_ParameterizedTransformTool):
    """Scale a point from a center using a signed projected cursor factor."""

    name = "scale"
    kind = "scale"
    prefix = "H"

    @property
    def _parameter_name(self) -> str:
        return "factor"

    def _parameter(self, cursor: Point2D) -> float | None:
        assert self._source is not None and self._center is not None
        source = Vector2D.between(self._point_value(self._center), self._point_value(self._source))
        squared = source.dot(source)
        if squared <= 1e-24:
            return None
        target = Vector2D.between(self._point_value(self._center), cursor)
        return target.dot(source) / squared

    def _transform(self, source: Point2D, center: Point2D, parameter: float) -> Point2D:
        return scale(source, parameter, center)


def _locus_parameter(target: GeoObject, cursor: Point2D) -> tuple[float, Point2D]:
    geometry = target.geometry
    if isinstance(geometry, Circle2D):
        angle = math.atan2(cursor.y - geometry.center.y, cursor.x - geometry.center.x)
        return angle, Point2D(
            geometry.center.x + geometry.radius * math.cos(angle),
            geometry.center.y + geometry.radius * math.sin(angle),
        )
    if isinstance(geometry, Line2D):
        anchor = geometry.project(Point2D(0, 0))
        parameter = Vector2D.between(anchor, cursor).dot(geometry.direction)
        return parameter, translate(anchor, geometry.direction * parameter)
    if isinstance(geometry, (Segment2D, Ray2D)):
        end = geometry.end if isinstance(geometry, Segment2D) else geometry.through
        direction = Vector2D.between(geometry.start, end)
        squared = direction.dot(direction)
        if squared <= 1e-24:
            return 0.0, geometry.start
        parameter = Vector2D.between(geometry.start, cursor).dot(direction) / squared
        parameter = (
            max(0.0, min(1.0, parameter))
            if isinstance(geometry, Segment2D)
            else max(0.0, parameter)
        )
        return parameter, translate(geometry.start, direction * parameter)
    raise ValueError("Un support linéaire ou circulaire est attendu")
