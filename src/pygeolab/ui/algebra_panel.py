"""Algebra dock widget listing document objects by category and value."""

from __future__ import annotations

from collections.abc import Callable, Iterator

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QMenu, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from pygeolab.commands import ChangeVisibilityCommand, Command, DeleteObjectCommand
from pygeolab.geometry import Circle2D, Line2D, Point2D, Polygon2D, Ray2D, Segment2D, Vector2D
from pygeolab.model.document import Document


class AlgebraPanel(QWidget):
    """Present objects grouped by geometry category and expose selection/context actions."""

    selectionChanged = Signal(object)

    def __init__(
        self,
        document: Document,
        execute_command: Callable[[Command], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._execute_command = execute_command
        self._tree = QTreeWidget(self)
        self._tree.setHeaderLabels([self.tr("Objet"), self.tr("Valeur")])
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.itemSelectionChanged.connect(self._emit_selection)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tree)
        self._unsubscribe = document.subscribe(self.refresh)
        self.refresh()

    def set_document(self, document: Document) -> None:
        """Switch to another document and rebuild the object tree."""
        self._unsubscribe()
        self._document = document
        self._unsubscribe = document.subscribe(self.refresh)
        self.refresh()

    def set_selected_ids(self, object_ids: frozenset[str] | set[str]) -> None:
        """Mirror selection coming from the canvas without changing document state."""
        self._tree.blockSignals(True)
        try:
            self._tree.clearSelection()
            for item in self._iter_object_items():
                if item.data(0, Qt.ItemDataRole.UserRole) in object_ids:
                    item.setSelected(True)
        finally:
            self._tree.blockSignals(False)

    def refresh(self) -> None:
        """Rebuild categories and human-readable values from current document objects."""
        selected = {
            item.data(0, Qt.ItemDataRole.UserRole) for item in self._tree.selectedItems()
        }
        self._tree.blockSignals(True)
        try:
            self._tree.clear()
            categories: dict[str, QTreeWidgetItem] = {}
            for obj in self._document.objects.values():
                category = self._category(obj.geometry)
                parent = categories.get(category)
                if parent is None:
                    parent = QTreeWidgetItem([category, ""])
                    parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                    categories[category] = parent
                    self._tree.addTopLevelItem(parent)
                item = QTreeWidgetItem([obj.name, self._format_value(obj.geometry, obj.valid)])
                item.setData(0, Qt.ItemDataRole.UserRole, obj.id)
                if not obj.visible:
                    item.setForeground(0, self.palette().mid())
                parent.addChild(item)
                if obj.id in selected:
                    item.setSelected(True)
            self._tree.expandAll()
        finally:
            self._tree.blockSignals(False)

    def _emit_selection(self) -> None:
        ids = {
            item.data(0, Qt.ItemDataRole.UserRole)
            for item in self._tree.selectedItems()
            if item.data(0, Qt.ItemDataRole.UserRole)
        }
        self.selectionChanged.emit(frozenset(ids))

    def _show_context_menu(self, position: QPoint) -> None:
        item = self._tree.itemAt(position)
        if item is None:
            return
        object_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(object_id, str) or not object_id:
            return
        obj = self._document.get(object_id)
        menu = QMenu(self)
        visibility = menu.addAction(self.tr("Masquer") if obj.visible else self.tr("Afficher"))
        delete = menu.addAction(self.tr("Supprimer"))
        chosen = menu.exec(self._tree.viewport().mapToGlobal(position))
        if chosen is visibility:
            command = ChangeVisibilityCommand(self._document, object_id, not obj.visible)
            self._execute_command(command)
        elif chosen is delete:
            self._execute_command(DeleteObjectCommand(self._document, object_id))

    def _iter_object_items(self) -> Iterator[QTreeWidgetItem]:
        for index in range(self._tree.topLevelItemCount()):
            parent = self._tree.topLevelItem(index)
            if parent is None:
                continue
            for child_index in range(parent.childCount()):
                child = parent.child(child_index)
                if child is not None:
                    yield child

    @staticmethod
    def _category(geometry: object) -> str:
        if isinstance(geometry, Point2D):
            return "Points"
        if isinstance(geometry, (Line2D, Segment2D, Ray2D, Vector2D)):
            return "Lignes"
        if isinstance(geometry, Circle2D):
            return "Cercles"
        if isinstance(geometry, Polygon2D):
            return "Polygones"
        if isinstance(geometry, float):
            return "Nombres"
        return "Objets"

    @staticmethod
    def _format_value(geometry: object, valid: bool) -> str:
        if not valid or geometry is None:
            return "indéfini"
        if isinstance(geometry, Point2D):
            return f"({geometry.x:.3g}, {geometry.y:.3g})"
        if isinstance(geometry, Segment2D):
            return f"longueur {geometry.length:.3g}"
        if isinstance(geometry, Circle2D):
            return f"r = {geometry.radius:.3g}"
        if isinstance(geometry, Polygon2D):
            return f"aire = {geometry.area:.3g}"
        if isinstance(geometry, float):
            return f"{geometry:.6g}"
        return type(geometry).__name__.removesuffix("2D")
