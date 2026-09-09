"""Searchable algebra tree with inline, reversible document editing."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pygeolab.commands import (
    ChangeLockCommand,
    ChangeVisibilityCommand,
    Command,
    CompositeCommand,
    DeleteObjectsCommand,
    RenameObjectCommand,
)
from pygeolab.geometry import Circle2D, Line2D, Point2D, Polygon2D, Ray2D, Segment2D, Vector2D
from pygeolab.math_engine.functions import FunctionObject
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.ui.translations import translate_message


class AlgebraPanel(QWidget):
    """Present, filter, group, select and edit document objects."""

    selectionChanged = Signal(object)
    sliderCreationRequested = Signal()

    def __init__(
        self,
        document: Document,
        execute_command: Callable[[Command], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._execute_command = execute_command
        self._context_menu: QMenu | None = None
        self._selection_cache: frozenset[str] = frozenset()
        self._handling_item_change = False
        self._refresh_scheduled = False
        self._search = QLineEdit(self)
        self._search.setPlaceholderText(self.tr("Rechercher…"))
        self._sort = QComboBox(self)
        self._sort.addItem(self.tr("Ordre du document"), "document")
        self._sort.addItem(self.tr("Trier par nom"), "name")
        self._sort.addItem(self.tr("Trier par type"), "type")
        self._group = QComboBox(self)
        self._group.addItem(self.tr("Grouper par catégorie"), "category")
        self._group.addItem(self.tr("Grouper par type"), "type")
        self._group.addItem(self.tr("Sans regroupement"), "none")
        controls = QHBoxLayout()
        self._new_slider_button = QPushButton(self.tr("+ Curseur"), self)
        self._new_slider_button.clicked.connect(self.sliderCreationRequested)
        controls.addWidget(self._new_slider_button)
        controls.addWidget(self._search, 1)
        controls.addWidget(self._sort)
        controls.addWidget(self._group)
        self._tree = QTreeWidget(self)
        self._tree.setHeaderLabels(
            [self.tr("Objet"), self.tr("Valeur"), self.tr("Visible"), self.tr("Verrouillé")]
        )
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.itemSelectionChanged.connect(self._emit_selection)
        self._tree.itemChanged.connect(self._edit_item)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._search.textChanged.connect(self.refresh)
        self._sort.currentIndexChanged.connect(self.refresh)
        self._group.currentIndexChanged.connect(self.refresh)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controls)
        layout.addWidget(self._tree)
        self._unsubscribe = document.subscribe(self._document_changed)
        self.refresh()

    def set_document(self, document: Document) -> None:
        """Switch to another document and rebuild the object tree."""
        self._unsubscribe()
        self._document = document
        self._selection_cache = frozenset()
        self._unsubscribe = document.subscribe(self._document_changed)
        self.refresh()

    def dispose(self) -> None:
        """Release the document subscription before the widget is destroyed."""
        self._unsubscribe()

    def set_selected_ids(self, object_ids: frozenset[str] | set[str]) -> None:
        """Mirror selection coming from the canvas without changing document state."""
        self._selection_cache = frozenset(
            object_id for object_id in object_ids if object_id in self._document.objects
        )
        self._tree.blockSignals(True)
        try:
            self._tree.clearSelection()
            for item in self._iter_object_items():
                if item.data(0, Qt.ItemDataRole.UserRole) in self._selection_cache:
                    item.setSelected(True)
        finally:
            self._tree.blockSignals(False)

    def refresh(self) -> None:
        """Rebuild the filtered tree while preserving visible object selection."""
        self._selection_cache = frozenset(
            object_id for object_id in self._selection_cache if object_id in self._document.objects
        )
        selected = set(self._selection_cache)
        query = self._search.text().strip().casefold()
        objects = [obj for obj in self._document.objects.values() if self._matches(obj, query)]
        sort_mode = self._sort.currentData()
        if sort_mode == "name":
            objects.sort(key=lambda obj: (obj.name.casefold(), obj.kind, obj.id))
        elif sort_mode == "type":
            objects.sort(key=lambda obj: (obj.kind, obj.name.casefold(), obj.id))
        group_mode = self._group.currentData()
        self._tree.blockSignals(True)
        try:
            self._tree.clear()
            categories: dict[str, QTreeWidgetItem] = {}
            for obj in objects:
                item = self._object_item(obj)
                if group_mode == "none":
                    self._tree.addTopLevelItem(item)
                else:
                    category = obj.kind if group_mode == "type" else self._category(obj.geometry)
                    parent = categories.get(category)
                    if parent is None:
                        parent = QTreeWidgetItem([category, "", "", ""])
                        parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                        categories[category] = parent
                        self._tree.addTopLevelItem(parent)
                    parent.addChild(item)
                if obj.id in selected:
                    item.setSelected(True)
            self._tree.expandAll()
            for column in range(4):
                self._tree.resizeColumnToContents(column)
        finally:
            self._tree.blockSignals(False)

    def _object_item(self, obj: GeoObject) -> QTreeWidgetItem:
        item = QTreeWidgetItem([obj.name, self._format_value(obj), "", ""])
        item.setData(0, Qt.ItemDataRole.UserRole, obj.id)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(2, Qt.CheckState.Checked if obj.visible else Qt.CheckState.Unchecked)
        item.setCheckState(3, Qt.CheckState.Checked if obj.locked else Qt.CheckState.Unchecked)
        if not obj.valid:
            error_color = QColor("#dc2626")
            for column in range(4):
                item.setForeground(column, error_color)
                item.setToolTip(column, obj.error_state or self.tr("Construction indéfinie"))
        elif not obj.visible:
            for column in range(2):
                item.setForeground(column, self.palette().mid())
        return item

    def _emit_selection(self) -> None:
        self._selection_cache = self._selected_ids()
        self.selectionChanged.emit(self._selection_cache)

    def _edit_item(self, item: QTreeWidgetItem, column: int) -> None:
        object_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(object_id, str) or object_id not in self._document.objects:
            return
        obj = self._document.get(object_id)
        command: Command | None = None
        if column == 0:
            name = item.text(0).strip()
            if name and name != obj.name:
                command = RenameObjectCommand(self._document, object_id, name)
        elif column == 2:
            visible = item.checkState(2) == Qt.CheckState.Checked
            if visible != obj.visible:
                command = ChangeVisibilityCommand(self._document, object_id, visible)
        elif column == 3:
            locked = item.checkState(3) == Qt.CheckState.Checked
            if locked != obj.locked:
                command = ChangeLockCommand(self._document, object_id, locked)
        if command is not None:
            self._handling_item_change = True
            try:
                self._execute_command(command)
            finally:
                self._handling_item_change = False
        elif column == 1 or (column == 0 and item.text(0) != obj.name):
            self.refresh()

    def _show_context_menu(self, position: QPoint) -> None:
        item = self._tree.itemAt(position)
        if item is None:
            return
        object_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(object_id, str) or not object_id:
            return
        if object_id not in self._selected_ids():
            self.set_selected_ids({object_id})
            self._emit_selection()
        selected_ids = self._selected_ids()
        objects = [self._document.get(selected_id) for selected_id in selected_ids]
        menu = QMenu(self)
        visibility_target = not any(obj.visible for obj in objects)
        visibility = menu.addAction(self.tr("Afficher" if visibility_target else "Masquer"))
        visibility.triggered.connect(
            lambda: self._execute_commands(
                [
                    ChangeVisibilityCommand(self._document, obj.id, visibility_target)
                    for obj in objects
                    if obj.visible != visibility_target
                ]
            )
        )
        lock_target = not all(obj.locked for obj in objects)
        lock = menu.addAction(self.tr("Verrouiller" if lock_target else "Déverrouiller"))
        lock.triggered.connect(
            lambda: self._execute_commands(
                [
                    ChangeLockCommand(self._document, obj.id, lock_target)
                    for obj in objects
                    if obj.locked != lock_target
                ]
            )
        )
        menu.addSeparator()
        parents = menu.addAction(self.tr("Sélectionner les parents"))
        parent_ids = frozenset(parent_id for obj in objects for parent_id in obj.dependencies)
        parents.setEnabled(bool(parent_ids))
        parents.triggered.connect(lambda: self._request_selection(parent_ids))
        descendants = menu.addAction(self.tr("Sélectionner les descendants"))
        descendant_ids = self._document.descendants(selected_ids)
        descendants.setEnabled(bool(descendant_ids))
        descendants.triggered.connect(lambda: self._request_selection(descendant_ids))
        menu.addSeparator()
        delete = menu.addAction(self.tr("Supprimer"))
        delete.triggered.connect(
            lambda: self._execute_command(DeleteObjectsCommand(self._document, selected_ids))
        )
        self._context_menu = menu
        menu.aboutToHide.connect(lambda: setattr(self, "_context_menu", None))
        menu.popup(self._tree.viewport().mapToGlobal(position))

    def _execute_commands(self, commands: Sequence[Command]) -> None:
        if commands:
            self._execute_command(commands[0] if len(commands) == 1 else CompositeCommand(commands))

    def _selected_ids(self) -> frozenset[str]:
        return frozenset(
            object_id
            for item in self._tree.selectedItems()
            if isinstance((object_id := item.data(0, Qt.ItemDataRole.UserRole)), str)
        )

    def _request_selection(self, object_ids: frozenset[str]) -> None:
        self.set_selected_ids(object_ids)
        self.selectionChanged.emit(object_ids)

    def _document_changed(self) -> None:
        if not self._handling_item_change:
            self.refresh()
            return
        if not self._refresh_scheduled:
            self._refresh_scheduled = True
            QTimer.singleShot(0, self._run_scheduled_refresh)

    def _run_scheduled_refresh(self) -> None:
        self._refresh_scheduled = False
        self.refresh()

    def _iter_object_items(self) -> Iterator[QTreeWidgetItem]:
        for index in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(index)
            if item is None:
                continue
            if isinstance(item.data(0, Qt.ItemDataRole.UserRole), str):
                yield item
            for child_index in range(item.childCount()):
                child = item.child(child_index)
                if child is not None:
                    yield child

    def _matches(self, obj: GeoObject, query: str) -> bool:
        if not query:
            return True
        searchable = " ".join(
            (
                obj.name,
                obj.kind,
                self._category(obj.geometry),
                self._format_value(obj),
                obj.error_state or "",
            )
        ).casefold()
        return query in searchable

    def _category(self, geometry: object) -> str:
        if isinstance(geometry, Point2D):
            return self.tr("Points")
        if isinstance(geometry, (Line2D, Segment2D, Ray2D, Vector2D)):
            return self.tr("Lignes")
        if isinstance(geometry, Circle2D):
            return self.tr("Cercles")
        if isinstance(geometry, Polygon2D):
            return self.tr("Polygones")
        if isinstance(geometry, float):
            return self.tr("Nombres")
        if isinstance(geometry, FunctionObject):
            return self.tr("Fonctions")
        return self.tr("Objets")

    def _format_value(self, obj: GeoObject) -> str:
        geometry = obj.geometry
        if not obj.valid or geometry is None:
            if obj.error_state:
                return self.tr(f"indéfini — {translate_message(obj.error_state)}")
            return self.tr("indéfini")
        if isinstance(geometry, Point2D):
            return f"({geometry.x:.3g}, {geometry.y:.3g})"
        if isinstance(geometry, Segment2D):
            return self.tr(f"longueur {geometry.length:.3g}")
        if isinstance(geometry, Circle2D):
            return f"r = {geometry.radius:.3g}"
        if isinstance(geometry, Polygon2D):
            return f"aire = {geometry.area:.3g}"
        if isinstance(geometry, float):
            return f"{geometry:.6g}"
        if isinstance(geometry, FunctionObject):
            return f"{geometry.name}({geometry.variable})"
        return type(geometry).__name__.removesuffix("2D")
