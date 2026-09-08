"""Dialog for creating a validated numeric slider variable."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QWidget,
)

from pygeolab.model.objects import GeoObject, JsonValue
from pygeolab.model.variables import numeric_variable, slider_initial, slider_spec


class SliderDialog(QDialog):
    """Collect slider name, current value, bounds and step."""

    def __init__(self, parent: QWidget | None = None, variable: GeoObject | None = None) -> None:
        super().__init__(parent)
        self._variable = variable
        self.setWindowTitle(self.tr("Modifier le curseur" if variable else "Nouveau curseur"))
        self.name_edit = QLineEdit(variable.name if variable else "a", self)
        self.value_spin = QDoubleSpinBox(self)
        self.minimum_spin = QDoubleSpinBox(self)
        self.maximum_spin = QDoubleSpinBox(self)
        self.step_spin = QDoubleSpinBox(self)
        for widget in (self.value_spin, self.minimum_spin, self.maximum_spin):
            widget.setRange(-1e9, 1e9)
            widget.setDecimals(6)
        self.step_spin.setRange(1e-9, 1e9)
        self.step_spin.setDecimals(9)
        self.minimum_spin.setValue(-10)
        self.maximum_spin.setValue(10)
        self.step_spin.setValue(0.1)
        if variable is not None:
            spec = slider_spec(variable)
            self.value_spin.setValue(spec.value)
            self.minimum_spin.setValue(spec.minimum)
            self.maximum_spin.setValue(spec.maximum)
            self.step_spin.setValue(spec.step)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form = QFormLayout(self)
        form.addRow(self.tr("Nom"), self.name_edit)
        form.addRow(self.tr("Valeur"), self.value_spin)
        form.addRow(self.tr("Minimum"), self.minimum_spin)
        form.addRow(self.tr("Maximum"), self.maximum_spin)
        form.addRow(self.tr("Pas"), self.step_spin)
        form.addRow(buttons)

    def variable(self) -> GeoObject:
        """Build the validated numeric variable represented by current controls."""
        return numeric_variable(
            self.name_edit.text(),
            self.value_spin.value(),
            self.minimum_spin.value(),
            self.maximum_spin.value(),
            self.step_spin.value(),
        )

    def definition(self) -> tuple[str, dict[str, JsonValue]]:
        """Return validated editable parameters while retaining animation preferences."""
        candidate = self.variable()
        params = dict(candidate.params)
        if self._variable is not None:
            params["initial"] = min(
                self.maximum_spin.value(),
                max(self.minimum_spin.value(), slider_initial(self._variable)),
            )
            params["animation_speed"] = self._variable.params.get("animation_speed", 1.0)
            params["ping_pong"] = self._variable.params.get("ping_pong", False)
        return candidate.name, params
