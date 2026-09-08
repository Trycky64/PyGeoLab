"""Non-modal numerical analysis controls for document functions."""

from __future__ import annotations

import math
from collections.abc import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pygeolab.math_engine.functions import FunctionObject
from pygeolab.math_engine.numerical import derivative, extrema, find_roots, integrate, intersections
from pygeolab.model.document import Document


class NumericalPanel(QWidget):
    """Calculate bounded numerical results and display them without mutating the document."""

    MAX_RESULTS = 500

    def __init__(self, document: Document, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._document = document
        self.operation = QComboBox(self)
        for label, name in (
            (self.tr("Dérivée en x"), "derivative"),
            (self.tr("Intégrale"), "integral"),
            (self.tr("Racines"), "roots"),
            (self.tr("Extrema"), "extrema"),
            (self.tr("Intersections"), "intersections"),
        ):
            self.operation.addItem(label, name)
        self.first_function = QComboBox(self)
        self.second_function = QComboBox(self)
        self.start = QDoubleSpinBox(self)
        self.end = QDoubleSpinBox(self)
        for spin, value in ((self.start, -10.0), (self.end, 10.0)):
            spin.setRange(-1e9, 1e9)
            spin.setDecimals(9)
            spin.setValue(value)
        self.tolerance = QDoubleSpinBox(self)
        self.tolerance.setDecimals(12)
        self.tolerance.setRange(1e-12, 1e-2)
        self.tolerance.setValue(1e-8)
        self.samples = QSpinBox(self)
        self.samples.setRange(32, 10_000)
        self.samples.setValue(512)
        self.calculate_button = QPushButton(self.tr("Calculer"), self)
        self.message = QLabel(self)
        self.results = QListWidget(self)
        form = QFormLayout()
        form.addRow(self.tr("Opération"), self.operation)
        form.addRow(self.tr("Fonction"), self.first_function)
        form.addRow(self.tr("Deuxième fonction"), self.second_function)
        form.addRow(self.tr("x / début"), self.start)
        form.addRow(self.tr("Fin"), self.end)
        form.addRow(self.tr("Tolérance"), self.tolerance)
        form.addRow(self.tr("Échantillons"), self.samples)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.calculate_button)
        layout.addWidget(self.message)
        layout.addWidget(self.results, 1)
        self.operation.currentIndexChanged.connect(self._sync_operation)
        self.calculate_button.clicked.connect(self.calculate)
        self._unsubscribe: Callable[[], None] = document.subscribe(self.refresh)
        self.refresh()
        self._sync_operation()

    def set_document(self, document: Document) -> None:
        """Switch the observed document and clear stale results."""
        self._unsubscribe()
        self._document = document
        self._unsubscribe = document.subscribe(self.refresh)
        self.results.clear()
        self.refresh()

    def refresh(self) -> None:
        """Keep valid function choices synchronized by stable UUID."""
        first_id = self.first_function.currentData()
        second_id = self.second_function.currentData()
        functions = [
            obj
            for obj in self._document.objects.values()
            if obj.valid and isinstance(obj.geometry, FunctionObject)
        ]
        for combo, selected_id in (
            (self.first_function, first_id),
            (self.second_function, second_id),
        ):
            combo.blockSignals(True)
            combo.clear()
            for obj in functions:
                combo.addItem(obj.name, obj.id)
            index = combo.findData(selected_id)
            if index >= 0:
                combo.setCurrentIndex(index)
            combo.blockSignals(False)
        self.calculate_button.setEnabled(bool(functions))
        if not functions:
            self.message.setText(self.tr("Aucune fonction valide"))

    def _sync_operation(self) -> None:
        operation = self.operation.currentData()
        self.second_function.setVisible(operation == "intersections")
        self.end.setEnabled(operation != "derivative")
        self.samples.setEnabled(operation != "derivative")

    def calculate(self) -> None:
        """Run the chosen bounded algorithm and present errors inline."""
        self.results.clear()
        self.message.clear()
        try:
            function, variables = self._selected_function(self.first_function)
            operation = self.operation.currentData()
            tolerance = self.tolerance.value()
            samples = self.samples.value()
            start, end = self.start.value(), self.end.value()
            if operation == "derivative":
                values: tuple[str, ...] = (
                    f"f'({self._format(start)}) = "
                    f"{self._format(derivative(function, start, variables, step=tolerance))}",
                )
            elif operation == "integral":
                values = (
                    f"∫ f(x) dx = "
                    f"{self._format(integrate(function, start, end, variables, samples))}",
                )
            elif operation == "roots":
                values = tuple(
                    f"x = {self._format(x)}"
                    for x in find_roots(function, start, end, variables, samples, tolerance)
                )
            elif operation == "extrema":
                values = tuple(
                    f"{point.kind}: ({self._format(point.x)}, {self._format(point.y)})"
                    for point in extrema(function, start, end, variables, samples)
                )
            elif operation == "intersections":
                other, other_variables = self._selected_function(self.second_function)
                values = tuple(
                    f"({self._format(x)}, {self._format(y)})"
                    for x, y in intersections(
                        function,
                        other,
                        start,
                        end,
                        {**variables, **other_variables},
                        samples,
                        tolerance,
                    )
                )
            else:
                raise ValueError("Opération numérique inconnue")
            for value in values[: self.MAX_RESULTS]:
                self.results.addItem(value)
            if not values:
                self.message.setText(self.tr("Aucun résultat sur cet intervalle"))
            elif len(values) > self.MAX_RESULTS:
                self.message.setText(self.tr("Résultats limités aux 500 premiers"))
            else:
                self.message.setText(self.tr(f"{len(values)} résultat(s)"))
        except (ValueError, ArithmeticError, IndexError, KeyError) as exc:
            self.message.setText(self.tr(f"Erreur : {exc}"))

    def _selected_function(self, combo: QComboBox) -> tuple[FunctionObject, dict[str, float]]:
        object_id = combo.currentData()
        if not isinstance(object_id, str):
            raise ValueError("Sélectionnez une fonction valide")
        obj = self._document.get(object_id)
        if not isinstance(obj.geometry, FunctionObject):
            raise ValueError("La fonction sélectionnée est invalide")
        variables = {
            parent.name: parent.geometry
            for dependency_id in obj.dependencies
            if isinstance((parent := self._document.get(dependency_id)).geometry, float)
        }
        return obj.geometry, variables

    def _format(self, value: float) -> str:
        decimals = min(12, max(3, math.ceil(-math.log10(self.tolerance.value()))))
        return f"{value:.{decimals}g}"
