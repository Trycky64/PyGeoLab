"""Shared pointer context, previews, and base interaction tool behavior."""

from dataclasses import dataclass

from pygeolab.geometry import Circle2D, Line2D, Point2D, Polygon2D, Ray2D, Segment2D

GeometryPreview = Point2D | Line2D | Segment2D | Ray2D | Circle2D | Polygon2D


@dataclass(frozen=True, slots=True)
class PointerContext:
    """Pointer coordinates and modifier state for a single interaction event."""

    world: Point2D
    screen_x: float
    screen_y: float
    shift: bool = False


class Tool:
    """Base class for one active interaction mode with optional event handlers."""

    name = "tool"

    def press(self, context: PointerContext) -> None:
        """Handle a primary-button press when the tool needs one."""

    def move(self, context: PointerContext) -> None:
        """Handle pointer movement for previews or drags when needed."""

    def release(self, context: PointerContext) -> None:
        """Handle a primary-button release when the tool needs one."""

    def cancel(self) -> None:
        """Cancel transient state without mutating committed document state."""

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Return transient geometry rendered above the document."""
        return ()
