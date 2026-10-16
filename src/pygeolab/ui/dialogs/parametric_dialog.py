"""Dialog for validated parametric curve recipes with x(t), y(t) and parameter domain."""

from __future__ import annotations

import math

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QWidget,
)

from pygeolab.math_engine.functions import ParametricFunctionObject
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject, JsonValue
from pygeolab.model.styles import Style


class ParametricFunctionDialog(QDialog):
    """Collect a parametric curve name, parameter variable, coordinate expressions, and domain."""

    def __init__(
        self,
        document: Document,
        parametric: GeoObject | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._parametric = parametric
        title = "Modifier la courbe paramétrique" if parametric else "Nouvelle courbe paramétrique"
        self.setWindowTitle(self.tr(title))
        params = parametric.params if parametric is not None else {}
        self.name_edit = QLineEdit(parametric.name if parametric else "c", self)
        self.param_edit = QLineEdit(str(params.get("parameter", "t")), self)
        self.x_edit = QLineEdit(str(params.get("x_source", "cos(t)")), self)
        self.y_edit = QLineEdit(str(params.get("y_source", "sin(t)")), self)

        self.t_min_spin = QDoubleSpinBox(self)
        self.t_max_spin = QDoubleSpinBox(self)
        for spin in (self.t_min_spin, self.t_max_spin):
            spin.setRange(-1e9, 1e9)
            spin.setDecimals(6)

        t_min_val = params.get("t_min", 0.0)
        t_max_val = params.get("t_max", 2.0 * math.pi)
        if isinstance(t_min_val, (int, float)) and not isinstance(t_min_val, bool):
            self.t_min_spin.setValue(float(t_min_val))
        else:
            self.t_min_spin.setValue(0.0)

        if isinstance(t_max_val, (int, float)) and not isinstance(t_max_val, bool):
            self.t_max_spin.setValue(float(t_max_val))
        else:
            self.t_max_spin.setValue(2.0 * math.pi)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout(self)
        form.addRow(self.tr("Nom"), self.name_edit)
        form.addRow(self.tr("Paramètre"), self.param_edit)
        form.addRow(self.tr("Expression x(t)"), self.x_edit)
        form.addRow(self.tr("Expression y(t)"), self.y_edit)
        form.addRow(self.tr("t min"), self.t_min_spin)
        form.addRow(self.tr("t max"), self.t_max_spin)
        form.addRow(buttons)

    def definition(self) -> tuple[str, tuple[str, ...], dict[str, JsonValue]]:
        """Validate syntax, domain, and resolve external slider dependencies."""
        name = self.name_edit.text().strip()
        parameter = self.param_edit.text().strip()
        x_source = self.x_edit.text().strip()
        y_source = self.y_edit.text().strip()
        t_min = self.t_min_spin.value()
        t_max = self.t_max_spin.value()

        parsed = ParametricFunctionObject.from_source(
            name, parameter, x_source, y_source, t_min, t_max
        )
        numeric_by_name = {
            obj.name: obj for obj in self._document.objects.values() if obj.kind == "number"
        }
        missing = sorted(parsed.external_dependencies.difference(numeric_by_name))
        if missing:
            raise ValueError(f"Curseurs numériques introuvables : {', '.join(missing)}")
        dependencies = tuple(
            numeric_by_name[dep].id for dep in sorted(parsed.external_dependencies)
        )
        params: dict[str, JsonValue] = {
            "parameter": parameter,
            "x_source": x_source,
            "y_source": y_source,
            "t_min": t_min,
            "t_max": t_max,
        }
        return name, dependencies, params

    def object_definition(self) -> GeoObject:
        """Create a new parametric curve object with its default style."""
        name, dependencies, params = self.definition()
        return GeoObject(
            "parametric",
            name,
            dependencies,
            params,
            style=Style(color="#059669", width=2.5, show_label=False),
        )
