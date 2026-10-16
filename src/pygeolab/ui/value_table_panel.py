"""Panel presenting a tabbed, virtualized spreadsheet table of values for functions and curves."""

from __future__ import annotations

import csv
import io
import math
from typing import TYPE_CHECKING

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
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

from pygeolab.math_engine.functions import (
    FunctionObject,
    ParametricFunctionObject,
    PolarFunctionObject,
)
from pygeolab.model.document import Document
from pygeolab.model.variables import slider_spec

if TYPE_CHECKING:
    pass


class ValueTableModel(QAbstractTableModel):
    """Memory-efficient virtualized model displaying tabulated coordinates and values."""

    def __init__(
        self,
        headers: list[str],
        rows: list[list[str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._headers = headers
        self._rows = rows

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        """Return number of rows."""
        return 0 if parent is not None and parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        """Return number of columns."""
        return 0 if parent is not None and parent.isValid() else len(self._headers)

    def data(
        self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object:
        """Retrieve cell text for display."""
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        row, col = index.row(), index.column()
        if 0 <= row < len(self._rows) and 0 <= col < len(self._rows[row]):
            return self._rows[row][col]
        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> object:
        """Provide horizontal header labels or vertical row numbers."""
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal and 0 <= section < len(self._headers):
            return self._headers[section]
        if orientation == Qt.Orientation.Vertical:
            return str(section + 1)
        return None


class ValueTablePanel(QWidget):
    """Panel for computing, inspecting, copying, and exporting function/curve value tables."""

    MAX_POINTS: int = 50_000

    def __init__(
        self,
        document: Document,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._headers: list[str] = ["x", "f(x)"]
        self._rows: list[list[str]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Controls row
        ctrl_layout = QHBoxLayout()
        ctrl_layout.addWidget(QLabel(self.tr("Fonction :"), self))
        self.function_combo = QComboBox(self)
        ctrl_layout.addWidget(self.function_combo)

        ctrl_layout.addWidget(QLabel(self.tr("Début :"), self))
        self.start_spin = QDoubleSpinBox(self)
        self.start_spin.setRange(-1e9, 1e9)
        self.start_spin.setDecimals(4)
        self.start_spin.setValue(-5.0)
        ctrl_layout.addWidget(self.start_spin)

        ctrl_layout.addWidget(QLabel(self.tr("Fin :"), self))
        self.end_spin = QDoubleSpinBox(self)
        self.end_spin.setRange(-1e9, 1e9)
        self.end_spin.setDecimals(4)
        self.end_spin.setValue(5.0)
        ctrl_layout.addWidget(self.end_spin)

        ctrl_layout.addWidget(QLabel(self.tr("Pas :"), self))
        self.step_spin = QDoubleSpinBox(self)
        self.step_spin.setRange(1e-6, 1000.0)
        self.step_spin.setDecimals(4)
        self.step_spin.setValue(1.0)
        ctrl_layout.addWidget(self.step_spin)

        self.compute_button = QPushButton(self.tr("Calculer la table"), self)
        ctrl_layout.addWidget(self.compute_button)
        ctrl_layout.addStretch()

        self.copy_button = QPushButton(self.tr("Copier la table"), self)
        self.export_button = QPushButton(self.tr("Exporter CSV…"), self)
        ctrl_layout.addWidget(self.copy_button)
        ctrl_layout.addWidget(self.export_button)
        layout.addLayout(ctrl_layout)

        # Table View
        self.table_view = QTableView(self)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._model = ValueTableModel(self._headers, self._rows, self)
        self.table_view.setModel(self._model)
        layout.addWidget(self.table_view)

        # Signals
        self.function_combo.currentIndexChanged.connect(self._on_function_selected)
        self.compute_button.clicked.connect(self.compute_table)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.export_button.clicked.connect(self.export_csv)

        self._unsubscribe = document.subscribe(self.refresh_functions)
        self.refresh_functions()

    def set_document(self, document: Document) -> None:
        """Adopt new document and refresh function selector."""
        self._unsubscribe()
        self._document = document
        self._unsubscribe = document.subscribe(self.refresh_functions)
        self.refresh_functions()

    def dispose(self) -> None:
        """Release subscription."""
        self._unsubscribe()

    def refresh_functions(self) -> None:
        """Populate combo box with valid functions, parametric, and polar curves."""
        current_id = self.function_combo.currentData()
        self.function_combo.blockSignals(True)
        self.function_combo.clear()

        for obj in self._document.objects.values():
            if obj.kind in {"function", "parametric", "polar"}:
                self.function_combo.addItem(f"{obj.name} ({obj.kind})", obj.id)

        idx = self.function_combo.findData(current_id) if current_id else -1
        if idx >= 0:
            self.function_combo.setCurrentIndex(idx)
        elif self.function_combo.count() > 0:
            self.function_combo.setCurrentIndex(0)
            self._update_default_bounds()
        self.function_combo.blockSignals(False)

        has_functions = self.function_combo.count() > 0
        self.compute_button.setEnabled(has_functions)
        self.copy_button.setEnabled(has_functions and len(self._rows) > 0)
        self.export_button.setEnabled(has_functions and len(self._rows) > 0)

    def _on_function_selected(self) -> None:
        self._update_default_bounds()

    def _update_default_bounds(self) -> None:
        obj_id = self.function_combo.currentData()
        if not obj_id or obj_id not in self._document.objects:
            return
        obj = self._document.get(obj_id)
        if obj.kind == "function":
            dom = obj.params.get("domain")
            if (
                isinstance(dom, (list, tuple))
                and len(dom) == 2
                and isinstance(dom[0], (int, float, str))
                and isinstance(dom[1], (int, float, str))
            ):
                self.start_spin.setValue(float(dom[0]))
                self.end_spin.setValue(float(dom[1]))
            else:
                self.start_spin.setValue(-5.0)
                self.end_spin.setValue(5.0)
            self.step_spin.setValue(1.0)
        elif obj.kind == "parametric":
            t_min = float(obj.params.get("t_min", -5.0))  # type: ignore[arg-type]
            t_max = float(obj.params.get("t_max", 5.0))  # type: ignore[arg-type]
            self.start_spin.setValue(t_min)
            self.end_spin.setValue(t_max)
            span = max(1.0, t_max - t_min)
            self.step_spin.setValue(span / 10.0)
        elif obj.kind == "polar":
            th_min = float(obj.params.get("theta_min", 0.0))  # type: ignore[arg-type]
            th_max = float(obj.params.get("theta_max", 2.0 * math.pi))  # type: ignore[arg-type]
            self.start_spin.setValue(th_min)
            self.end_spin.setValue(th_max)
            span = max(0.1, th_max - th_min)
            self.step_spin.setValue(span / 10.0)

    def compute_table(self) -> None:
        """Compute the rows and headers for the selected function over [start, end] with step."""
        obj_id = self.function_combo.currentData()
        if not obj_id or obj_id not in self._document.objects:
            return
        obj = self._document.get(obj_id)

        start = self.start_spin.value()
        end = self.end_spin.value()
        step = self.step_spin.value()

        if step <= 0:
            QMessageBox.warning(
                self,
                self.tr("Pas d'échantillonnage invalide"),
                self.tr("Le pas doit être strictement positif"),
            )
            return

        if start > end:
            QMessageBox.warning(
                self,
                self.tr("Intervalle de table invalide"),
                self.tr("Début doit être inférieur ou égal à Fin"),
            )
            return

        steps_count = int(math.floor((end - start) / step)) + 1
        if steps_count > self.MAX_POINTS:
            QMessageBox.warning(
                self,
                self.tr("Intervalle de table invalide"),
                self.tr("Nombre de points limité à 50 000"),
            )
            return

        # Prepare variable scope from sliders
        scope = {
            o.name: slider_spec(o).value
            for o in self._document.objects.values()
            if o.kind == "number"
        }

        headers: list[str] = []
        rows: list[list[str]] = []

        if obj.kind == "function":
            var_name = str(obj.params.get("variable", "x"))
            func_name = obj.name
            headers = [var_name, f"{func_name}({var_name})"]
            try:
                fn_obj = FunctionObject.from_source(
                    obj.name,
                    var_name,
                    str(obj.params.get("source", "")),
                )
            except Exception:
                fn_obj = None

            for i in range(steps_count):
                x = start + i * step
                if x > end + 1e-9:
                    break
                val_str = self.tr("indéfini")
                if fn_obj is not None:
                    try:
                        y = fn_obj.evaluate(x, scope)
                        val_str = f"{y:.6g}" if math.isfinite(y) else self.tr("indéfini")
                    except Exception:
                        val_str = self.tr("indéfini")
                rows.append([f"{x:.6g}", val_str])

        elif obj.kind == "parametric":
            p_name = str(obj.params.get("parameter", "t"))
            headers = [p_name, f"x({p_name})", f"y({p_name})"]
            try:
                p_obj = ParametricFunctionObject.from_source(
                    obj.name,
                    p_name,
                    str(obj.params.get("x_source", "")),
                    str(obj.params.get("y_source", "")),
                    float(obj.params.get("t_min", start)),  # type: ignore[arg-type]
                    float(obj.params.get("t_max", end)),  # type: ignore[arg-type]
                )
            except Exception:
                p_obj = None

            for i in range(steps_count):
                t = start + i * step
                if t > end + 1e-9:
                    break
                x_str, y_str = self.tr("indéfini"), self.tr("indéfini")
                if p_obj is not None:
                    try:
                        pt = p_obj.evaluate(t, scope)
                        x_str = f"{pt.x:.6g}" if math.isfinite(pt.x) else self.tr("indéfini")
                        y_str = f"{pt.y:.6g}" if math.isfinite(pt.y) else self.tr("indéfini")
                    except Exception:
                        pass
                rows.append([f"{t:.6g}", x_str, y_str])

        elif obj.kind == "polar":
            p_name = str(obj.params.get("parameter", "θ"))
            headers = [p_name, f"r({p_name})", "x", "y"]
            try:
                pol_obj = PolarFunctionObject.from_source(
                    obj.name,
                    p_name,
                    str(obj.params.get("r_source", "")),
                    float(obj.params.get("theta_min", start)),  # type: ignore[arg-type]
                    float(obj.params.get("theta_max", end)),  # type: ignore[arg-type]
                    use_degrees=bool(obj.params.get("use_degrees", False)),
                )
            except Exception:
                pol_obj = None

            for i in range(steps_count):
                theta = start + i * step
                if theta > end + 1e-9:
                    break
                r_str, x_str, y_str = (
                    self.tr("indéfini"),
                    self.tr("indéfini"),
                    self.tr("indéfini"),
                )
                if pol_obj is not None:
                    try:
                        # evaluate radius expression
                        from pygeolab.math_engine.evaluator import evaluate

                        scope_theta = dict(scope)
                        scope_theta[p_name] = theta
                        r = evaluate(pol_obj.r_expression, scope_theta)
                        pt = pol_obj.evaluate(theta, scope)
                        r_str = f"{r:.6g}" if math.isfinite(r) else self.tr("indéfini")
                        x_str = f"{pt.x:.6g}" if math.isfinite(pt.x) else self.tr("indéfini")
                        y_str = f"{pt.y:.6g}" if math.isfinite(pt.y) else self.tr("indéfini")
                    except Exception:
                        pass
                rows.append([f"{theta:.6g}", r_str, x_str, y_str])

        self._headers = headers
        self._rows = rows
        self._model = ValueTableModel(self._headers, self._rows, self)
        self.table_view.setModel(self._model)

        self.copy_button.setEnabled(len(rows) > 0)
        self.export_button.setEnabled(len(rows) > 0)

    def to_csv_string(self) -> str:
        """Serialize current table content to CSV text."""
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(self._headers)
        writer.writerows(self._rows)
        return buf.getvalue()

    def copy_to_clipboard(self) -> None:
        """Copy table formatted as TSV/CSV to system clipboard."""
        if not self._rows:
            return
        lines = ["\t".join(self._headers)]
        for row in self._rows:
            lines.append("\t".join(row))
        text = "\n".join(lines)
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)

    def export_csv(self) -> None:
        """Save table content to a CSV file on disk."""
        if not self._rows:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Exporter CSV…"),
            "table_valeurs.csv",
            self.tr("Fichier CSV (*.csv)"),
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(self.to_csv_string())
