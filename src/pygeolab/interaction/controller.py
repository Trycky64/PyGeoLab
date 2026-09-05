"""Coordinate active tools, selection, history and pointer state for one document."""

from __future__ import annotations

from collections.abc import Callable

from pygeolab.commands import CommandHistory
from pygeolab.interaction.selection import SelectionModel
from pygeolab.interaction.tools import (
    CircleTool,
    IntersectionTool,
    LineTool,
    MidpointTool,
    ParallelTool,
    PerpendicularTool,
    PointTool,
    PointerContext,
    PolygonTool,
    SegmentTool,
    Tool,
)
from pygeolab.interaction.tools.base import GeometryPreview
from pygeolab.interaction.tools.selection import SelectionTool
from pygeolab.model.document import Document
from pygeolab.rendering.viewport import Viewport


class InteractionController:
    """Own one active geometry tool and expose Qt-independent pointer operations."""

    def __init__(
        self,
        document: Document,
        viewport: Viewport,
        history: CommandHistory | None = None,
        on_changed: Callable[[], None] | None = None,
    ) -> None:
        self.document = document
        self.history = history or CommandHistory()
        self.selection = SelectionModel()
        self.viewport = viewport
        self._on_changed = on_changed or (lambda: None)
        selection = SelectionTool(document, self.history, self.selection, viewport)
        self._tools: dict[str, Tool] = {
            "select": selection,
            "point": PointTool(document, self.history, viewport),
            "segment": SegmentTool(document, self.history, viewport),
            "line": LineTool(document, self.history, viewport),
            "circle": CircleTool(document, self.history, viewport),
            "polygon": PolygonTool(document, self.history, viewport),
            "midpoint": MidpointTool(document, self.history, viewport),
            "intersection": IntersectionTool(document, self.history, viewport),
            "parallel": ParallelTool(document, self.history, viewport),
            "perpendicular": PerpendicularTool(document, self.history, viewport),
        }
        self._active_name = "select"

    @property
    def active_tool_name(self) -> str:
        """Return the stable identifier of the currently active tool."""
        return self._active_name

    @property
    def active_tool(self) -> Tool:
        """Return the active tool instance."""
        return self._tools[self._active_name]

    @property
    def selected_ids(self) -> frozenset[str]:
        """Expose current selection identities for rendering and panels."""
        return self.selection.ids

    @property
    def preview(self) -> tuple[GeometryPreview, ...]:
        """Return transient geometry produced by the active construction tool."""
        return self.active_tool.preview

    @property
    def tool_names(self) -> tuple[str, ...]:
        """Return all available tool identifiers in toolbar order."""
        return tuple(self._tools)

    def activate(self, name: str) -> None:
        """Cancel transient state then activate one known tool."""
        if name not in self._tools:
            raise ValueError(f"Outil inconnu : {name}")
        if name == self._active_name:
            return
        self.active_tool.cancel()
        self._active_name = name
        self._on_changed()

    def set_viewport(self, viewport: Viewport) -> None:
        """Synchronize camera-dependent hit-testing for all tools."""
        self.viewport = viewport
        for tool in self._tools.values():
            setter = getattr(tool, "set_viewport", None)
            if setter is not None:
                setter(viewport)

    def pointer_press(self, x: float, y: float, shift: bool = False) -> None:
        """Forward a primary pointer press in screen coordinates."""
        self.active_tool.press(self._context(x, y, shift))
        self._on_changed()

    def pointer_move(self, x: float, y: float, shift: bool = False) -> None:
        """Forward pointer movement for previews and drag updates."""
        self.active_tool.move(self._context(x, y, shift))
        self._on_changed()

    def pointer_release(self, x: float, y: float, shift: bool = False) -> None:
        """Forward a primary pointer release."""
        self.active_tool.release(self._context(x, y, shift))
        self._on_changed()

    def cancel(self) -> None:
        """Cancel active transient construction or drag state."""
        self.active_tool.cancel()
        self._on_changed()

    def undo(self) -> bool:
        """Undo one command and clear selection entries that no longer exist."""
        changed = self.history.undo()
        self._prune_selection()
        if changed:
            self._on_changed()
        return changed

    def redo(self) -> bool:
        """Redo one command and refresh dependent presentation state."""
        changed = self.history.redo()
        self._prune_selection()
        if changed:
            self._on_changed()
        return changed

    def _context(self, x: float, y: float, shift: bool) -> PointerContext:
        return PointerContext(x, y, self.viewport.screen_to_world(x, y), shift)

    def _prune_selection(self) -> None:
        for object_id in tuple(self.selection.ids):
            if object_id not in self.document.objects:
                self.selection.toggle(object_id)
