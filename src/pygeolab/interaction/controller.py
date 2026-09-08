"""Coordinate active tools, selection, history and pointer state for one document."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from pygeolab.commands import (
    ChangeLockCommand,
    ChangeStyleCommand,
    ChangeVisibilityCommand,
    Command,
    CommandHistory,
    CompositeCommand,
    CreateObjectsCommand,
    DeleteObjectsCommand,
    ReorderObjectsCommand,
)
from pygeolab.interaction.selection import SelectionModel
from pygeolab.interaction.snapping import SnapEngine, SnappingOptions, SnapResult
from pygeolab.interaction.tools import (
    AngleBisectorTool,
    AngleTool,
    AxialReflectionTool,
    CentralReflectionTool,
    CircleRadiusTool,
    CircleTool,
    CircumcircleTool,
    DistanceTool,
    IntersectionTool,
    LineTool,
    MidpointTool,
    ParallelTool,
    PerpendicularBisectorTool,
    PerpendicularTool,
    PointerContext,
    PointOnObjectTool,
    PointTool,
    PolygonTool,
    ProjectionTool,
    RayTool,
    RotationTool,
    ScaleTool,
    SegmentTool,
    Tool,
    TranslationTool,
    VectorTool,
)
from pygeolab.interaction.tools.base import GeometryPreview
from pygeolab.interaction.tools.selection import SelectionTool
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style
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
        self._snap_engine = SnapEngine()
        self._snapping_options = SnappingOptions()
        self._snap_result: SnapResult | None = None
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
            "ray": RayTool(document, self.history, viewport),
            "vector": VectorTool(document, self.history, viewport),
            "perpendicular_bisector": PerpendicularBisectorTool(document, self.history, viewport),
            "angle_bisector": AngleBisectorTool(document, self.history, viewport),
            "projection": ProjectionTool(document, self.history, viewport),
            "point_on": PointOnObjectTool(document, self.history, viewport),
            "circle_radius": CircleRadiusTool(document, self.history, viewport),
            "circumcircle": CircumcircleTool(document, self.history, viewport),
            "distance": DistanceTool(document, self.history, viewport),
            "angle": AngleTool(document, self.history, viewport),
            "translate": TranslationTool(document, self.history, viewport),
            "rotate": RotationTool(document, self.history, viewport),
            "reflect_point": CentralReflectionTool(document, self.history, viewport),
            "reflect_line": AxialReflectionTool(document, self.history, viewport),
            "scale": ScaleTool(document, self.history, viewport),
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
    def snap_result(self) -> SnapResult | None:
        """Expose the active target for status feedback and the visual indicator."""
        return self._snap_result

    @property
    def snapping_options(self) -> SnappingOptions:
        """Return the current session snapping configuration."""
        return self._snapping_options

    def set_snapping_enabled(self, enabled: bool) -> None:
        """Enable or disable snapping globally for this interaction controller."""
        current = self._snapping_options
        self._snapping_options = SnappingOptions(
            enabled,
            current.threshold_px,
            current.points,
            current.grid,
            current.projections,
            current.intersections,
        )
        if not enabled:
            self._snap_result = None
        self._on_changed()

    def set_snapping_threshold(self, threshold_px: float) -> None:
        """Set the screen-space snap radius while preserving candidate options."""
        current = self._snapping_options
        self._snapping_options = SnappingOptions(
            current.enabled,
            threshold_px,
            current.points,
            current.grid,
            current.projections,
            current.intersections,
        )

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

    def pointer_press(
        self,
        x: float,
        y: float,
        shift: bool = False,
        suppress_snap: bool = False,
        ctrl: bool = False,
    ) -> None:
        """Forward a primary pointer press in screen coordinates."""
        self.active_tool.press(self._context(x, y, shift, suppress_snap, ctrl))
        self._on_changed()

    def pointer_move(
        self,
        x: float,
        y: float,
        shift: bool = False,
        suppress_snap: bool = False,
        ctrl: bool = False,
    ) -> None:
        """Forward pointer movement for previews and drag updates."""
        self.active_tool.move(self._context(x, y, shift, suppress_snap, ctrl))
        self._on_changed()

    def pointer_release(
        self,
        x: float,
        y: float,
        shift: bool = False,
        suppress_snap: bool = False,
        ctrl: bool = False,
    ) -> None:
        """Forward a primary pointer release."""
        self.active_tool.release(self._context(x, y, shift, suppress_snap, ctrl))
        self._on_changed()

    def cancel(self) -> None:
        """Cancel active transient construction or drag state."""
        self.active_tool.cancel()
        self._snap_result = None
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

    def clear_snap(self) -> None:
        """Clear stale feedback when camera navigation starts."""
        self._snap_result = None

    def select_all(self) -> None:
        """Select every object in document drawing order."""
        self.selection.replace_many(frozenset(self.document.objects))
        self._on_changed()

    def clear_selection(self) -> None:
        """Clear the current selection and notify connected views."""
        self.selection.clear()
        self._on_changed()

    def delete_selection(self) -> bool:
        """Delete the complete selection as one reversible command."""
        selected = self.selection.ids
        if not selected:
            return False
        self.history.execute(DeleteObjectsCommand(self.document, selected))
        self.selection.clear()
        self._on_changed()
        return True

    def set_selection_visibility(self, visible: bool) -> bool:
        """Apply one visibility state to all selected objects as one history entry."""
        commands = [
            ChangeVisibilityCommand(self.document, object_id, visible)
            for object_id in self.selection.ids
            if self.document.get(object_id).visible != visible
        ]
        return self._execute_group(commands)

    def set_selection_locked(self, locked: bool) -> bool:
        """Apply one editing lock state to all selected objects as one history entry."""
        commands = [
            ChangeLockCommand(self.document, object_id, locked)
            for object_id in self.selection.ids
            if self.document.get(object_id).locked != locked
        ]
        return self._execute_group(commands)

    def set_selection_style(self, style: Style) -> bool:
        """Apply one visual style to every selected object as one history entry."""
        commands = [
            ChangeStyleCommand(self.document, object_id, style)
            for object_id in self.selection.ids
            if self.document.get(object_id).style != style
        ]
        return self._execute_group(commands)

    def duplicate_selection(self) -> frozenset[str]:
        """Duplicate dependency-free selected definitions and select the copies."""
        existing_names = {obj.name for obj in self.document.objects.values()}
        duplicates: list[GeoObject] = []
        for obj in self.document.objects.values():
            if obj.id not in self.selection.ids or obj.dependencies:
                continue
            name = _unique_name(obj.name, existing_names)
            existing_names.add(name)
            params = dict(obj.params)
            if obj.kind == "point":
                x, y = params.get("x"), params.get("y")
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    params.update(x=float(x) + 0.25, y=float(y) - 0.25)
            duplicates.append(
                GeoObject(
                    obj.kind,
                    name,
                    params=params,
                    visible=obj.visible,
                    locked=obj.locked,
                    style=obj.style,
                )
            )
        if not duplicates:
            return frozenset()
        self.history.execute(CreateObjectsCommand(self.document, duplicates))
        created_ids = frozenset(obj.id for obj in duplicates)
        self.selection.replace_many(created_ids)
        self._on_changed()
        return created_ids

    def reorder_selection(self, *, to_front: bool) -> bool:
        """Move selected objects to the front or back while preserving relative order."""
        if not self.selection.ids:
            return False
        self.history.execute(
            ReorderObjectsCommand(self.document, self.selection.ids, to_front=to_front)
        )
        self._on_changed()
        return True

    def _context(
        self, x: float, y: float, shift: bool, suppress_snap: bool, ctrl: bool
    ) -> PointerContext:
        raw_world = self.viewport.screen_to_world(x, y)
        self._snap_result = self._snap_engine.snap(
            self.document,
            self.viewport,
            x,
            y,
            self._snapping_options,
            suppressed=suppress_snap,
            exclude_ids=self.active_tool.snap_excluded_ids,
        )
        world = raw_world if self._snap_result is None else self._snap_result.point
        return PointerContext(world, x, y, shift=shift, ctrl=ctrl, snap=self._snap_result)

    def _prune_selection(self) -> None:
        for object_id in tuple(self.selection.ids):
            if object_id not in self.document.objects:
                self.selection.toggle(object_id)

    def _execute_group(self, commands: Sequence[Command]) -> bool:
        if not commands:
            return False
        self.history.execute(CompositeCommand(commands))
        self._on_changed()
        return True


def _unique_name(base: str, reserved: set[str]) -> str:
    suffix = 1
    while f"{base}{suffix}" in reserved:
        suffix += 1
    return f"{base}{suffix}"
