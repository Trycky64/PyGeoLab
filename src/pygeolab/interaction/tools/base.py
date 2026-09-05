"""Pure interaction tool protocol and pointer context values."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass

from pygeolab.geometry import Circle2D, Line2D, Point2D, Polygon2D, Ray2D, Segment2D, Vector2D

GeometryPreview = Point2D | Vector2D | Line2D | Segment2D | Ray2D | Circle2D | Polygon2D


@dataclass(frozen=True, slots=True)
class PointerContext:
    """Pointer coordinates expressed in both screen and mathematical world space."""

    screen_x: float
    screen_y: float
    world: Point2D
    shift: bool = False


class Tool(ABC):
    """Base class for one active interaction mode."""

    name = "tool"

    def press(self, context: PointerContext) -> None:
        """Handle a primary-button press."""

    def move(self, context: PointerContext) -> None:
        """Handle pointer movement for previews or drags."""

    def release(self, context: PointerContext) -> None:
        """Handle a primary-button release."""

    def cancel(self) -> None:
        """Cancel transient state without mutating committed document state."""

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Return transient geometry rendered above the document."""
        return ()
