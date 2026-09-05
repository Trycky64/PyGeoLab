"""Interactive Qt viewport widget responsible for pan, zoom and document painting."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent, QPainter, QPaintEvent, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QWidget

from pygeolab.model.document import Document
from pygeolab.rendering.renderer import Renderer
from pygeolab.rendering.viewport import Viewport


class GeometryView(QWidget):
    """Display one document through a camera, with middle-button pan and wheel zoom."""

    def __init__(self, document: Document | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("geometryView")
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._document = document or Document()
        self._viewport = Viewport(width=max(1, self.width()), height=max(1, self.height()))
        self._renderer = Renderer()
        self._selected_ids: set[str] = set()
        self._pan_anchor: QPointF | None = None
        self._unsubscribe: Callable[[], None] = self._document.subscribe(self._on_document_changed)

    @property
    def document(self) -> Document:
        """Return the document currently rendered by this view."""
        return self._document

    @property
    def viewport(self) -> Viewport:
        """Return the immutable current camera state."""
        return self._viewport

    @property
    def selected_ids(self) -> frozenset[str]:
        """Return selection identities used only for visual highlighting."""
        return frozenset(self._selected_ids)

    def set_document(self, document: Document) -> None:
        """Switch document subscriptions without transferring ownership of model state."""
        if document is self._document:
            return
        self._unsubscribe()
        self._document = document
        self._unsubscribe = document.subscribe(self._on_document_changed)
        self._renderer.invalidate_cache()
        self.update()

    def set_selected_ids(self, object_ids: set[str]) -> None:
        """Set IDs highlighted by the renderer; interaction policy lives elsewhere."""
        self._selected_ids = set(object_ids)
        self.update()

    def reset_view(self) -> None:
        """Restore the default origin-centered camera while preserving widget size."""
        self._viewport = Viewport(width=max(1, self.width()), height=max(1, self.height()))
        self._renderer.invalidate_cache()
        self.update()

    def pan_by_pixels(self, dx: float, dy: float) -> None:
        """Pan the camera by a screen displacement and request repaint."""
        self._viewport = self._viewport.panned_pixels(dx, dy)
        self.update()

    def zoom_at(self, factor: float, x: float, y: float) -> None:
        """Zoom around a screen position and request repaint."""
        self._viewport = self._viewport.zoomed_at(factor, x, y)
        self._renderer.invalidate_cache()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Render the current document using this widget's palette and dimensions."""
        del event
        painter = QPainter(self)
        try:
            self._renderer.render(
                painter,
                self._document,
                self._viewport,
                self.palette(),
                self._selected_ids,
            )
        finally:
            painter.end()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Keep screen dimensions synchronized with the renderer viewport."""
        size = event.size()
        self._viewport = self._viewport.resized(size.width(), size.height())
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
        """Start viewport panning with the middle mouse button."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_anchor = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Pan continuously while a middle-button drag is active."""
        if self._pan_anchor is not None and event.buttons() & Qt.MouseButton.MiddleButton:
            position = event.position()
            delta = position - self._pan_anchor
            self._pan_anchor = position
            self.pan_by_pixels(delta.x(), delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finish middle-button panning and restore the normal cursor."""
        if event.button() == Qt.MouseButton.MiddleButton and self._pan_anchor is not None:
            self._pan_anchor = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _on_document_changed(self) -> None:
        """Invalidate visual caches and repaint after one committed document edit."""
        self._renderer.invalidate_cache()
        self.update()
