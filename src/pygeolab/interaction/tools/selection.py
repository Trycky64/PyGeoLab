"""Selection tool with screen-space hit testing and coalesced free-point dragging."""

from __future__ import annotations

from pygeolab.commands import CommandHistory, MovePointCommand
from pygeolab.geometry import Point2D
from pygeolab.interaction.selection import SelectionModel
from pygeolab.interaction.tools.base import PointerContext, Tool
from pygeolab.model.document import Document
from pygeolab.rendering.hit_test import first_hit
from pygeolab.rendering.viewport import Viewport


class SelectionTool(Tool):
    """Select objects and directly drag only unlocked free points."""

    name = "select"

    def __init__(
        self,
        document: Document,
        history: CommandHistory,
        selection: SelectionModel,
        viewport: Viewport,
    ) -> None:
        self.document = document
        self.history = history
        self.selection = selection
        self.viewport = viewport
        self._drag_id: str | None = None
        self._drag_start: Point2D | None = None

    def set_viewport(self, viewport: Viewport) -> None:
        """Update the camera used for screen-distance hit testing."""
        self.viewport = viewport

    def press(self, context: PointerContext) -> None:
        """Select the topmost hit and begin a drag when it is a movable free point."""
        obj = first_hit(self.document, self.viewport, context.screen_x, context.screen_y)
        if obj is None:
            if not context.shift:
                self.selection.clear()
            return
        if context.shift:
            self.selection.toggle(obj.id)
        else:
            self.selection.replace(obj.id)
        if obj.movable and isinstance(obj.geometry, Point2D) and not context.shift:
            self._drag_id = obj.id
            self._drag_start = obj.geometry

    def move(self, context: PointerContext) -> None:
        """Apply interactive drag positions directly so dependents update live."""
        if self._drag_id is not None:
            self.document.move_point(self._drag_id, context.world)

    def release(self, context: PointerContext) -> None:
        """Record one reversible movement for the whole drag gesture."""
        del context
        if self._drag_id is None or self._drag_start is None:
            return
        current = self.document.get(self._drag_id).geometry
        if isinstance(current, Point2D) and not current.almost_equals(self._drag_start):
            self.history.record_applied(
                MovePointCommand(self.document, self._drag_id, self._drag_start, current)
            )
        self._drag_id = None
        self._drag_start = None

    def cancel(self) -> None:
        """Abort an active drag by restoring its initial point without history."""
        if self._drag_id is not None and self._drag_start is not None:
            self.document.move_point(self._drag_id, self._drag_start)
        self._drag_id = None
        self._drag_start = None
