"""Interactive Qt viewport connecting camera navigation to geometry interaction tools."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import (
    QContextMenuEvent,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import QMenu, QWidget

from pygeolab.commands import CommandHistory
from pygeolab.interaction import InteractionController
from pygeolab.model.document import Document
from pygeolab.rendering.hit_test import first_hit
from pygeolab.rendering.renderer import Renderer
from pygeolab.rendering.viewport import Viewport


class GeometryView(QWidget):
    """Display and edit one document with camera navigation and construction tools."""

    selectionChanged = Signal(object)
    cursorWorldChanged = Signal(float, float)
    interactionChanged = Signal()

    def __init__(self, document: Document | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("geometryView")
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._document = document or Document()
        self._viewport = Viewport(width=max(1, self.width()), height=max(1, self.height()))
        self._renderer = Renderer()
        self._pan_anchor: QPointF | None = None
        self._context_menu: QMenu | None = None
        self._last_selection: frozenset[str] = frozenset()
        self._unsubscribe: Callable[[], None] = self._document.subscribe(self._on_document_changed)
        self._interaction = InteractionController(
            self._document, self._viewport, on_changed=self._on_interaction_changed
        )

    @property
    def document(self) -> Document:
        """Return the document currently rendered and edited by this view."""
        return self._document

    @property
    def viewport(self) -> Viewport:
        """Return the immutable current camera state."""
        return self._viewport

    @property
    def interaction(self) -> InteractionController:
        """Return the controller used by toolbar actions and keyboard shortcuts."""
        return self._interaction

    @property
    def history(self) -> CommandHistory:
        """Return this document view's undo/redo history."""
        return self._interaction.history

    @property
    def selected_ids(self) -> frozenset[str]:
        """Return current interaction selection identities."""
        return self._interaction.selected_ids

    def set_document(self, document: Document) -> None:
        """Switch document subscriptions and start a fresh per-document command history."""
        if document is self._document:
            return
        self._unsubscribe()
        self._document = document
        self._unsubscribe = document.subscribe(self._on_document_changed)
        snapping = self._interaction.snapping_options
        self._interaction = InteractionController(
            document, self._viewport, on_changed=self._on_interaction_changed
        )
        self._interaction.set_snapping_enabled(snapping.enabled)
        self._interaction.set_snapping_threshold(snapping.threshold_px)
        self._renderer.invalidate_cache()
        self.update()

    def dispose(self) -> None:
        """Release the document subscription before the viewport is destroyed."""
        self._unsubscribe()

    def set_selected_ids(self, object_ids: set[str] | frozenset[str]) -> None:
        """Replace selection for external panels while preserving controller ownership."""
        self._interaction.selection.clear()
        for object_id in object_ids:
            if object_id in self._document.objects:
                self._interaction.selection.toggle(object_id)
        self._emit_selection_if_changed()
        self.update()

    def select_all(self) -> None:
        """Select every document object."""
        self._interaction.select_all()

    def clear_selection(self) -> None:
        """Clear every selected identity."""
        self._interaction.clear_selection()

    def delete_selection(self) -> bool:
        """Delete selected objects and descendants as one history command."""
        return self._interaction.delete_selection()

    def duplicate_selection(self) -> frozenset[str]:
        """Duplicate dependency-free selected objects."""
        return self._interaction.duplicate_selection()

    def activate_tool(self, name: str) -> None:
        """Activate one registered interaction tool by stable identifier."""
        self._interaction.activate(name)
        self.update()

    def set_snapping_enabled(self, enabled: bool) -> None:
        """Enable snapping for every tool and free-point drag in this view."""
        self._interaction.set_snapping_enabled(enabled)
        self.update()

    def set_function_sampling_quality(self, quality: str) -> None:
        """Persist the selected adaptive function sampling quality."""
        if quality not in {"low", "medium", "high"}:
            raise ValueError("Qualité de sampling inconnue")
        self._document.set_scene_option("function_sampling_quality", quality)

    def set_function_overlay(self, name: str, visible: bool) -> None:
        """Toggle one supported numerical function overlay in the scene."""
        if name not in {"roots", "extrema", "intersections", "derivative"}:
            raise ValueError("Couche d'analyse inconnue")
        self._document.set_scene_option(f"show_function_{name}", visible)

    def configure_display(self, *, grid: bool, axes: bool, labels: bool) -> None:
        """Apply non-document display preferences to the renderer."""
        self._renderer.configure_display(grid=grid, axes=axes, labels=labels)
        self.update()

    def reset_view(self) -> None:
        """Restore the default origin-centered camera while preserving widget size."""
        self._interaction.clear_snap()
        self._viewport = Viewport(width=max(1, self.width()), height=max(1, self.height()))
        self._sync_interaction_viewport()
        self._renderer.invalidate_cache()
        self.update()

    def pan_by_pixels(self, dx: float, dy: float) -> None:
        """Pan the camera by a screen displacement and request repaint."""
        self._interaction.clear_snap()
        self._viewport = self._viewport.panned_pixels(dx, dy)
        self._sync_interaction_viewport()
        self.update()

    def zoom_at(self, factor: float, x: float, y: float) -> None:
        """Zoom around a screen position and request repaint."""
        self._interaction.clear_snap()
        self._viewport = self._viewport.zoomed_at(factor, x, y)
        self._sync_interaction_viewport()
        self._renderer.invalidate_cache()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Render the current document, selection and active-tool preview."""
        del event
        painter = QPainter(self)
        try:
            self._renderer.render(
                painter,
                self._document,
                self._viewport,
                self.palette(),
                self._interaction.selected_ids,
            )
            self._renderer.render_preview(
                painter,
                self._document,
                self._viewport,
                self.palette(),
                self._interaction.preview,
            )
            snap = self._interaction.snap_result
            if snap is not None:
                self._renderer.render_snap_indicator(
                    painter, self._viewport, self.palette(), snap.point
                )
        finally:
            painter.end()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Keep screen dimensions synchronized with renderer and interaction viewport."""
        size = event.size()
        self._viewport = self._viewport.resized(size.width(), size.height())
        self._sync_interaction_viewport()
        self._renderer.invalidate_cache()
        super().resizeEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Apply exponential mouse-wheel zoom centered beneath the cursor."""
        steps = event.angleDelta().y() / 120.0
        if steps:
            self.zoom_at(1.2**steps, event.position().x(), event.position().y())
            event.accept()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start middle-button pan or forward primary presses to the active tool."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._interaction.clear_snap()
            self.update()
            self._pan_anchor = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus()
            self._interaction.pointer_press(
                event.position().x(),
                event.position().y(),
                bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier),
                bool(event.modifiers() & Qt.KeyboardModifier.AltModifier),
                bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier),
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Pan with middle drag or forward movement for previews and point dragging."""
        if self._pan_anchor is not None and event.buttons() & Qt.MouseButton.MiddleButton:
            position = event.position()
            delta = position - self._pan_anchor
            self._pan_anchor = position
            self.pan_by_pixels(delta.x(), delta.y())
            event.accept()
            return
        self._interaction.pointer_move(
            event.position().x(),
            event.position().y(),
            bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier),
            bool(event.modifiers() & Qt.KeyboardModifier.AltModifier),
            bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier),
        )
        raw_world = self._viewport.screen_to_world(event.position().x(), event.position().y())
        snap = self._interaction.snap_result
        world = raw_world if snap is None else snap.point
        self.cursorWorldChanged.emit(world.x, world.y)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finish viewport panning or one primary interaction gesture."""
        if event.button() == Qt.MouseButton.MiddleButton and self._pan_anchor is not None:
            self._pan_anchor = None
            self.unsetCursor()
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._interaction.pointer_release(
                event.position().x(),
                event.position().y(),
                bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier),
                bool(event.modifiers() & Qt.KeyboardModifier.AltModifier),
                bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier),
            )
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Cancel transient tool state with Escape."""
        if event.key() == Qt.Key.Key_Escape:
            self._interaction.cancel()
            event.accept()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Open non-blocking actions for the selection under the canvas pointer."""
        position = event.pos()
        obj = first_hit(self._document, self._viewport, position.x(), position.y())
        if obj is None:
            self.clear_selection()
            event.accept()
            return
        if obj.id not in self.selected_ids:
            self.set_selected_ids({obj.id})
        selected = [self._document.get(object_id) for object_id in self.selected_ids]
        menu = QMenu(self)
        visibility_target = not any(item.visible for item in selected)
        visibility = menu.addAction(self.tr("Afficher" if visibility_target else "Masquer"))
        visibility.triggered.connect(
            lambda: self._interaction.set_selection_visibility(visibility_target)
        )
        lock_target = not all(item.locked for item in selected)
        lock = menu.addAction(self.tr("Verrouiller" if lock_target else "Déverrouiller"))
        lock.triggered.connect(lambda: self._interaction.set_selection_locked(lock_target))
        menu.addSeparator()
        duplicate = menu.addAction(self.tr("Dupliquer"))
        duplicate.setEnabled(any(not item.dependencies for item in selected))
        duplicate.triggered.connect(self.duplicate_selection)
        front = menu.addAction(self.tr("Mettre au premier plan"))
        front.triggered.connect(lambda: self._interaction.reorder_selection(to_front=True))
        back = menu.addAction(self.tr("Mettre à l'arrière-plan"))
        back.triggered.connect(lambda: self._interaction.reorder_selection(to_front=False))
        menu.addSeparator()
        delete = menu.addAction(self.tr("Supprimer"))
        delete.triggered.connect(self.delete_selection)
        self._context_menu = menu
        menu.aboutToHide.connect(lambda: setattr(self, "_context_menu", None))
        menu.popup(event.globalPos())
        event.accept()

    def _sync_interaction_viewport(self) -> None:
        self._interaction.set_viewport(self._viewport)

    def _on_document_changed(self) -> None:
        """Repaint after a commit; revision-aware renderer caches update themselves."""
        self.update()

    def _on_interaction_changed(self) -> None:
        """Repaint transient state and notify shells about history/selection changes."""
        self._emit_selection_if_changed()
        self.interactionChanged.emit()
        self.update()

    def _emit_selection_if_changed(self) -> None:
        current = self._interaction.selected_ids
        if current != self._last_selection:
            self._last_selection = current
            self.selectionChanged.emit(current)
