"""Lightweight spreadsheet panel for viewing and editing numerical datasets.

Provides a dedicated QTableView with:
- Row/column insertion and deletion
- Real-time cell editing with strict floating-point validation
- Copy selected range and paste from clipboard (tab/comma-delimited)
- Direct CSV import and export
- Integration with Command Pattern (ChangeParametersCommand) for complete Undo/Redo
- Keyboard navigation (arrows, Enter, Tab)
"""

from __future__ import annotations

import csv
import io
import math
from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from pygeolab.commands import ChangeParametersCommand, Command
from pygeolab.data.dataset import DatasetObject
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject

if TYPE_CHECKING:
    pass


class DatasetTableModel(QAbstractTableModel):
    """Editable Qt table model backed by a DatasetObject."""

    dataChangedSignal = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._column_names: list[str] = ["x", "y"]
        self._rows: list[list[float]] = []
        self._read_only: bool = False

    def set_read_only(self, read_only: bool) -> None:
        """Mark table model as editable or read-only."""
        self._read_only = read_only

    def set_dataset(self, dataset: DatasetObject) -> None:
        """Reset internal table contents to match the given dataset."""
        self.beginResetModel()
        self._column_names = list(dataset.column_names)
        self._rows = [list(row) for row in dataset.rows]
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        """Return the total number of table rows."""
        return 0 if parent is not None and parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        """Return the total number of table columns."""
        return 0 if parent is not None and parent.isValid() else len(self._column_names)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        """Return horizontal column names or vertical 1-based row numbers."""
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._column_names):
                return self._column_names[section]
            return f"Col {section + 1}"
        return str(section + 1)

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        """Return item flags enabling selection and optional in-place editing."""
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        fl = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if not self._read_only:
            fl |= Qt.ItemFlag.ItemIsEditable
        return fl

    def data(
        self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> str | None:
        """Retrieve formatted numeric string for display or exact representation for editing."""
        if not index.isValid() or role not in (
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.EditRole,
        ):
            return None
        row, col = index.row(), index.column()
        if 0 <= row < len(self._rows) and 0 <= col < len(self._rows[row]):
            val = self._rows[row][col]
            if role == Qt.ItemDataRole.EditRole:
                return str(val)
            return f"{val:.6g}" if abs(val) < 1e5 else f"{val:.4e}"
        return ""

    def setData(
        self,
        index: QModelIndex | QPersistentModelIndex,
        value: str,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        """Parse and update table cell with strict float validation."""
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False
        row, col = index.row(), index.column()
        if not (0 <= row < len(self._rows) and 0 <= col < len(self._column_names)):
            return False

        try:
            # Parse localized decimal separator
            clean_str = str(value).strip().replace(",", ".")
            num = float(clean_str)
            if not math.isfinite(num):
                return False
        except ValueError:
            return False

        self._rows[row][col] = num
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        self.dataChangedSignal.emit()
        return True

    def add_row(self, values: list[float] | None = None) -> None:
        """Insert a row at the end."""
        pos = len(self._rows)
        self.beginInsertRows(QModelIndex(), pos, pos)
        if values is not None and len(values) == len(self._column_names):
            self._rows.append(list(values))
        else:
            self._rows.append([0.0] * len(self._column_names))
        self.endInsertRows()
        self.dataChangedSignal.emit()

    def remove_rows(self, row_indices: list[int]) -> None:
        """Remove specified row indices."""
        for r in sorted(row_indices, reverse=True):
            if 0 <= r < len(self._rows):
                self.beginRemoveRows(QModelIndex(), r, r)
                del self._rows[r]
                self.endRemoveRows()
        self.dataChangedSignal.emit()

    def add_column(self, name: str | None = None) -> None:
        """Insert a column at the end."""
        pos = len(self._column_names)
        col_name = name or f"col_{pos + 1}"
        if col_name in self._column_names:
            col_name = f"{col_name}_{pos + 1}"
        self.beginInsertColumns(QModelIndex(), pos, pos)
        self._column_names.append(col_name)
        for row in self._rows:
            row.append(0.0)
        self.endInsertColumns()
        self.dataChangedSignal.emit()

    def remove_column(self, col_index: int) -> None:
        """Remove a column if more than one remains."""
        if len(self._column_names) <= 1:
            return
        if 0 <= col_index < len(self._column_names):
            self.beginRemoveColumns(QModelIndex(), col_index, col_index)
            del self._column_names[col_index]
            for row in self._rows:
                if col_index < len(row):
                    del row[col_index]
            self.endRemoveColumns()
            self.dataChangedSignal.emit()

    def to_dataset(self, name: str, plot_kind: str = "scatter") -> DatasetObject:
        """Convert current model data into an immutable DatasetObject."""
        return DatasetObject.from_rows(
            column_names=self._column_names,
            rows=self._rows,
            name=name,
            plot_kind=plot_kind,
        )


class DataTablePanel(QWidget):
    """Dedicated interactive spreadsheet panel for dataset manipulation."""

    def __init__(
        self,
        document: Document,
        execute_command: Callable[[Command], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._execute_command = execute_command
        self._active_object_id: str | None = None
        self._updating = False

        self._model = DatasetTableModel(self)
        self._model.dataChangedSignal.connect(self._on_table_data_edited)

        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Header controls: Dataset selector and plot kind
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel(self.tr("Jeu de données :")))
        self._dataset_combo = QComboBox(self)
        self._dataset_combo.currentIndexChanged.connect(self._on_dataset_selected)
        top_bar.addWidget(self._dataset_combo, 1)

        top_bar.addWidget(QLabel(self.tr("Mode de tracé :")))
        self._plot_kind_combo = QComboBox(self)
        self._plot_kind_combo.addItem(self.tr("Nuage de points"), "scatter")
        self._plot_kind_combo.addItem(self.tr("Droite de régression"), "regression")
        self._plot_kind_combo.addItem(self.tr("Histogramme"), "histogram")
        self._plot_kind_combo.addItem(self.tr("Boîte à moustaches"), "boxplot")
        self._plot_kind_combo.addItem(self.tr("Diagramme en barres"), "bar")
        self._plot_kind_combo.currentIndexChanged.connect(self._on_plot_kind_changed)
        top_bar.addWidget(self._plot_kind_combo)

        layout.addLayout(top_bar)

        # Spreadsheet Table View
        self._table_view = QTableView(self)
        self._table_view.setModel(self._model)
        self._table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table_view.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self._table_view.setTabKeyNavigation(True)
        layout.addWidget(self._table_view, 1)

        # Toolbar buttons
        btn_bar = QHBoxLayout()
        self._btn_add_row = QPushButton(self.tr("+ Ligne"), self)
        self._btn_add_row.clicked.connect(self._add_row)
        btn_bar.addWidget(self._btn_add_row)

        self._btn_del_row = QPushButton(self.tr("- Ligne"), self)
        self._btn_del_row.clicked.connect(self._delete_selected_rows)
        btn_bar.addWidget(self._btn_del_row)

        self._btn_add_col = QPushButton(self.tr("+ Colonne"), self)
        self._btn_add_col.clicked.connect(self._add_column)
        btn_bar.addWidget(self._btn_add_col)

        self._btn_del_col = QPushButton(self.tr("- Colonne"), self)
        self._btn_del_col.clicked.connect(self._delete_current_column)
        btn_bar.addWidget(self._btn_del_col)

        btn_bar.addSpacing(10)

        self._btn_copy = QPushButton(self.tr("Copier plage"), self)
        self._btn_copy.clicked.connect(self.copy_selection)
        btn_bar.addWidget(self._btn_copy)

        self._btn_paste = QPushButton(self.tr("Coller"), self)
        self._btn_paste.clicked.connect(self.paste_clipboard)
        btn_bar.addWidget(self._btn_paste)

        btn_bar.addSpacing(10)

        self._btn_import_csv = QPushButton(self.tr("Importer CSV…"), self)
        self._btn_import_csv.clicked.connect(self._import_csv)
        btn_bar.addWidget(self._btn_import_csv)

        self._btn_export_csv = QPushButton(self.tr("Exporter CSV…"), self)
        self._btn_export_csv.clicked.connect(self._export_csv)
        btn_bar.addWidget(self._btn_export_csv)

        layout.addLayout(btn_bar)

        # Keyboard shortcuts
        QShortcut(QKeySequence.StandardKey.Copy, self._table_view, self.copy_selection)
        QShortcut(QKeySequence.StandardKey.Paste, self._table_view, self.paste_clipboard)

    def refresh(self) -> None:
        """Refresh datasets list from document."""
        self._updating = True
        try:
            self._dataset_combo.clear()
            datasets = [
                obj
                for obj in self._document.objects.values()
                if obj.kind == "dataset" and isinstance(obj.geometry, DatasetObject)
            ]
            for obj in datasets:
                self._dataset_combo.addItem(obj.name, obj.id)

            if datasets:
                existing_ids = [d.id for d in datasets]
                target_id = (
                    self._active_object_id
                    if self._active_object_id in existing_ids
                    else datasets[0].id
                )
                idx = self._dataset_combo.findData(target_id)
                if idx >= 0:
                    self._dataset_combo.setCurrentIndex(idx)
                self._load_active_dataset(target_id)
            else:
                self._active_object_id = None
                self._model.set_dataset(
                    DatasetObject(name="Vide", column_names=("x", "y"), rows=())
                )
        finally:
            self._updating = False

    def _on_dataset_selected(self, index: int) -> None:
        if self._updating or index < 0:
            return
        obj_id = self._dataset_combo.itemData(index)
        if isinstance(obj_id, str):
            self._load_active_dataset(obj_id)

    def _load_active_dataset(self, object_id: str) -> None:
        self._active_object_id = object_id
        obj = self._document.get(object_id)
        if obj is not None and isinstance(obj.geometry, DatasetObject):
            ds = obj.geometry
            is_dependent = bool(obj.dependencies)
            self._model.set_read_only(is_dependent)
            self._model.set_dataset(ds)
            # Update plot_kind combo
            pk_idx = self._plot_kind_combo.findData(ds.plot_kind)
            if pk_idx >= 0:
                self._plot_kind_combo.setCurrentIndex(pk_idx)
            self._btn_add_row.setEnabled(not is_dependent)
            self._btn_del_row.setEnabled(not is_dependent)
            self._btn_add_col.setEnabled(not is_dependent)
            self._btn_del_col.setEnabled(not is_dependent)
            self._btn_paste.setEnabled(not is_dependent)

    def _on_plot_kind_changed(self, index: int) -> None:
        if self._updating or not self._active_object_id or index < 0:
            return
        plot_kind = self._plot_kind_combo.itemData(index)
        if not isinstance(plot_kind, str):
            return
        obj = self._document.get(self._active_object_id)
        if obj is not None and isinstance(obj.geometry, DatasetObject):
            new_ds = obj.geometry.with_plot_kind(plot_kind)
            self._apply_dataset_update(new_ds)

    def _on_table_data_edited(self) -> None:
        if self._updating or not self._active_object_id:
            return
        obj = self._document.get(self._active_object_id)
        if obj is not None and isinstance(obj.geometry, DatasetObject):
            new_ds = self._model.to_dataset(obj.name, plot_kind=obj.geometry.plot_kind)
            self._apply_dataset_update(new_ds)

    def _apply_dataset_update(self, new_dataset: DatasetObject) -> None:
        if not self._active_object_id:
            return
        if self._execute_command:
            cmd = ChangeParametersCommand(
                self._document, self._active_object_id, new_dataset.to_dict()
            )
            self._execute_command(cmd)
        else:
            obj = self._document.get(self._active_object_id)
            updated = GeoObject(
                id=obj.id,
                name=obj.name,
                kind=obj.kind,
                dependencies=obj.dependencies,
                params=new_dataset.to_dict(),
                visible=obj.visible,
                locked=obj.locked,
                style=obj.style,
                geometry=new_dataset,
            )
            self._document.add(updated)

    def _add_row(self) -> None:
        self._model.add_row()

    def _delete_selected_rows(self) -> None:
        selection = self._table_view.selectionModel()
        if not selection or not selection.hasSelection():
            return
        selected_rows = {index.row() for index in selection.selectedIndexes()}
        self._model.remove_rows(list(selected_rows))

    def _add_column(self) -> None:
        self._model.add_column()

    def _delete_current_column(self) -> None:
        col = self._table_view.currentIndex().column()
        if col >= 0:
            self._model.remove_column(col)

    def copy_selection(self) -> None:
        """Copy selected table cells to the clipboard as tab-separated values."""
        selection = self._table_view.selectionModel()
        if not selection or not selection.hasSelection():
            return
        indexes = selection.selectedIndexes()
        rows = sorted({idx.row() for idx in indexes})
        cols = sorted({idx.column() for idx in indexes})

        output = io.StringIO()
        writer = csv.writer(output, delimiter="\t")
        for r in rows:
            row_data = [self._model.data(self._model.index(r, c)) or "" for c in cols]
            writer.writerow(row_data)

        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(output.getvalue())

    def paste_clipboard(self) -> None:
        """Paste tab/comma-separated clipboard text into selected cells."""
        clipboard = QApplication.clipboard()
        if not clipboard:
            return
        text = clipboard.text().strip()
        if not text:
            return

        # Determine delimiter
        delimiter = "\t" if "\t" in text else (";" if ";" in text else ",")
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)

        start_row = self._table_view.currentIndex().row()
        start_col = self._table_view.currentIndex().column()
        if start_row < 0:
            start_row = 0
        if start_col < 0:
            start_col = 0

        for r_offset, row in enumerate(reader):
            target_r = start_row + r_offset
            while target_r >= self._model.rowCount():
                self._model.add_row()
            for c_offset, cell in enumerate(row):
                target_c = start_col + c_offset
                while target_c >= self._model.columnCount():
                    self._model.add_column()
                clean_val = cell.strip()
                if clean_val:
                    self._model.setData(self._model.index(target_r, target_c), clean_val)

    def _import_csv(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Importer un jeu de données CSV"),
            "",
            self.tr("Fichiers CSV (*.csv);;Tous les fichiers (*.*)"),
        )
        if not file_path:
            return
        try:
            name = self._dataset_combo.currentText() or "Dataset"
            ds = DatasetObject.from_csv(file_path, name=name)
            self._model.set_dataset(ds)
            self._apply_dataset_update(ds)
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur d'importation"), str(e))

    def _export_csv(self) -> None:
        if self._model.rowCount() == 0:
            QMessageBox.warning(self, self.tr("Tableur"), self.tr("Aucune donnée à exporter."))
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Exporter le jeu de données en CSV"),
            "dataset.csv",
            self.tr("Fichiers CSV (*.csv)"),
        )
        if not file_path:
            return
        try:
            name = self._dataset_combo.currentText() or "Dataset"
            ds = self._model.to_dataset(name)
            csv_str = ds.to_csv()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(csv_str)
            QMessageBox.information(
                self, self.tr("Tableur"), self.tr("Jeu de données exporté avec succès.")
            )
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur d'exportation"), str(e))
