"""Selection tool with screen-space hit testing and coalesced free-point dragging."""

from __future__ import annotations

import math

from pygeolab.commands import CommandHistory, MovePointCommand
from pygeolab.geometry import Point2D, Polygon2D
from pygeolab.interaction.selection import SelectionModel
from pygeolab.interaction.tools.base import PointerContext, Tool
from pygeolab.model.document import Document
from pygeolab.rendering.hit_test import hit_test, objects_in_screen_rect
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
        self._marquee_start: tuple[float, float] | None = None
        self._marquee_current: tuple[float, float] | None = None
        self._marquee_shift = False
        self._marquee_ctrl = False
        self._cycle_position: tuple[float, float] | None = None
        self._cycle_hits: tuple[str, ...] = ()
        self._cycle_index = 0

    def set_viewport(self, viewport: Viewport) -> None:
        """Update the camera used for screen-distance hit testing."""
        self.viewport = viewport

    def press(self, context: PointerContext) -> None:
        """Select the topmost hit and begin a drag when it is a movable free point."""
        hits = hit_test(self.document, self.viewport, context.screen_x, context.screen_y)
        if not hits:
            self._marquee_start = (context.screen_x, context.screen_y)
            self._marquee_current = self._marquee_start
            self._marquee_shift = context.shift
            self._marquee_ctrl = context.ctrl
            return
        hit_ids = tuple(hit.object_id for hit in hits)
        if (
            self._cycle_position is not None
            and math.hypot(
                context.screen_x - self._cycle_position[0],
                context.screen_y - self._cycle_position[1],
            )
            <= 4.0
            and hit_ids == self._cycle_hits
        ):
            self._cycle_index = (self._cycle_index + 1) % len(hit_ids)
        else:
            self._cycle_index = 0
        self._cycle_position = (context.screen_x, context.screen_y)
        self._cycle_hits = hit_ids
        obj = self.document.get(hit_ids[self._cycle_index])
        if context.ctrl:
            self.selection.toggle(obj.id)
        elif context.shift:
            self.selection.add_many(frozenset({obj.id}))
        else:
            self.selection.replace(obj.id)
        if (
            obj.movable
            and isinstance(obj.geometry, Point2D)
            and not context.shift
            and not context.ctrl
        ):
            self._drag_id = obj.id
            self._drag_start = obj.geometry

    def move(self, context: PointerContext) -> None:
        """Apply interactive drag positions directly so dependents update live."""
        if self._drag_id is not None:
            self.document.move_point(self._drag_id, context.world)
        elif self._marquee_start is not None:
            self._marquee_current = (context.screen_x, context.screen_y)

    def release(self, context: PointerContext) -> None:
        """Record one reversible movement for the whole drag gesture."""
        if self._drag_id is not None and self._drag_start is not None:
            current = self.document.get(self._drag_id).geometry
            if isinstance(current, Point2D) and not current.almost_equals(self._drag_start):
                self.history.record_applied(
                    MovePointCommand(self.document, self._drag_id, self._drag_start, current)
                )
            self._drag_id = None
            self._drag_start = None
            return
        if self._marquee_start is None:
            return
        distance = math.hypot(
            context.screen_x - self._marquee_start[0],
            context.screen_y - self._marquee_start[1],
        )
        selected = (
            objects_in_screen_rect(
                self.document,
                self.viewport,
                *self._marquee_start,
                context.screen_x,
                context.screen_y,
            )
            if distance >= 4.0
            else frozenset()
        )
        if self._marquee_ctrl:
            self.selection.toggle_many(selected)
        elif self._marquee_shift:
            self.selection.add_many(selected)
        else:
            self.selection.replace_many(selected)
        self._clear_marquee()

    def cancel(self) -> None:
        """Abort an active drag by restoring its initial point without history."""
        if self._drag_id is not None and self._drag_start is not None:
            self.document.move_point(self._drag_id, self._drag_start)
        self._drag_id = None
        self._drag_start = None
        self._clear_marquee()

    @property
    def preview(self) -> tuple[Polygon2D, ...]:
        """Return a world-space marquee rectangle after a meaningful pointer drag."""
        if self._marquee_start is None or self._marquee_current is None:
            return ()
        if math.dist(self._marquee_start, self._marquee_current) < 4.0:
            return ()
        first = self.viewport.screen_to_world(*self._marquee_start)
        second = self.viewport.screen_to_world(*self._marquee_current)
        return (
            Polygon2D(
                (
                    Point2D(first.x, first.y),
                    Point2D(second.x, first.y),
                    Point2D(second.x, second.y),
                    Point2D(first.x, second.y),
                )
            ),
        )

    @property
    def snap_excluded_ids(self) -> frozenset[str]:
        """Exclude the moving point so it can leave its previous position."""
        return frozenset() if self._drag_id is None else frozenset({self._drag_id})

    def _clear_marquee(self) -> None:
        self._marquee_start = None
        self._marquee_current = None
        self._marquee_shift = False
        self._marquee_ctrl = False
