"""Dialog for validated polar curve recipes with r(theta) and angular domain."""

from __future__ import annotations

import math

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QWidget,
)

from pygeolab.math_engine.functions import PolarFunctionObject
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject, JsonValue
from pygeolab.model.styles import Style


class PolarFunctionDialog(QDialog):
    """Collect a polar curve name, angle parameter, radius expression, and domain."""

    def __init__(
        self,
        document: Document,
        polar: GeoObject | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._polar = polar
        title = "Modifier la courbe polaire" if polar else "Nouvelle courbe polaire"
        self.setWindowTitle(self.tr(title))
        params = polar.params if polar is not None else {}
        self.name_edit = QLineEdit(polar.name if polar else "r", self)
        self.param_edit = QLineEdit(str(params.get("parameter", "theta")), self)
        self.r_edit = QLineEdit(str(params.get("r_source", "1 + cos(theta)")), self)

        self.degree_mode_checkbox = QCheckBox(self.tr("Saisir / afficher en degrés"), self)
        use_degrees = bool(params.get("use_degrees", False))
        self.degree_mode_checkbox.setChecked(use_degrees)

        self.theta_min_spin = QDoubleSpinBox(self)
        self.theta_max_spin = QDoubleSpinBox(self)
        for spin in (self.theta_min_spin, self.theta_max_spin):
            spin.setRange(-1e9, 1e9)
            spin.setDecimals(6)

        theta_min_val = params.get("theta_min", 0.0)
        theta_max_val = params.get("theta_max", 2.0 * math.pi)

        initial_min = float(theta_min_val) if isinstance(theta_min_val, (int, float)) else 0.0
        initial_max = (
            float(theta_max_val) if isinstance(theta_max_val, (int, float)) else 2.0 * math.pi
        )

        if use_degrees:
            self.theta_min_spin.setValue(math.degrees(initial_min))
            self.theta_max_spin.setValue(math.degrees(initial_max))
            self.theta_min_spin.setSuffix("°")
            self.theta_max_spin.setSuffix("°")
            self.theta_min_spin.setSingleStep(15.0)
            self.theta_max_spin.setSingleStep(15.0)
        else:
            self.theta_min_spin.setValue(initial_min)
            self.theta_max_spin.setValue(initial_max)
            self.theta_min_spin.setSuffix(" rad")
            self.theta_max_spin.setSuffix(" rad")
            self.theta_min_spin.setSingleStep(0.1)
            self.theta_max_spin.setSingleStep(0.1)

        self.degree_mode_checkbox.toggled.connect(self._on_degree_mode_toggled)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout(self)
        form.addRow(self.tr("Nom"), self.name_edit)
        form.addRow(self.tr("Paramètre angulaire"), self.param_edit)
        form.addRow(self.tr("Expression r(θ)"), self.r_edit)
        form.addRow(self.degree_mode_checkbox)
        form.addRow(self.tr("θ min"), self.theta_min_spin)
        form.addRow(self.tr("θ max"), self.theta_max_spin)
        form.addRow(buttons)

    def _on_degree_mode_toggled(self, checked: bool) -> None:
        min_val = self.theta_min_spin.value()
        max_val = self.theta_max_spin.value()
        if checked:
            self.theta_min_spin.setValue(math.degrees(min_val))
            self.theta_max_spin.setValue(math.degrees(max_val))
            self.theta_min_spin.setSuffix("°")
            self.theta_max_spin.setSuffix("°")
            self.theta_min_spin.setSingleStep(15.0)
            self.theta_max_spin.setSingleStep(15.0)
        else:
            self.theta_min_spin.setValue(math.radians(min_val))
            self.theta_max_spin.setValue(math.radians(max_val))
            self.theta_min_spin.setSuffix(" rad")
            self.theta_max_spin.setSuffix(" rad")
            self.theta_min_spin.setSingleStep(0.1)
            self.theta_max_spin.setSingleStep(0.1)

    def definition(self) -> tuple[str, tuple[str, ...], dict[str, JsonValue]]:
        """Validate syntax, domain, and resolve external slider dependencies."""
        name = self.name_edit.text().strip()
        parameter = self.param_edit.text().strip()
        r_source = self.r_edit.text().strip()
        use_degrees = self.degree_mode_checkbox.isChecked()
        theta_min_raw = self.theta_min_spin.value()
        theta_max_raw = self.theta_max_spin.value()

        if use_degrees:
            theta_min = math.radians(theta_min_raw)
            theta_max = math.radians(theta_max_raw)
        else:
            theta_min = theta_min_raw
            theta_max = theta_max_raw

        parsed = PolarFunctionObject.from_source(
            name, parameter, r_source, theta_min, theta_max, use_degrees=use_degrees
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
            "r_source": r_source,
            "theta_min": theta_min,
            "theta_max": theta_max,
            "use_degrees": use_degrees,
        }
        return name, dependencies, params

    def object_definition(self) -> GeoObject:
        """Create a new polar curve object with its default style."""
        name, dependencies, params = self.definition()
        return GeoObject(
            "polar",
            name,
            dependencies,
            params,
            style=Style(color="#8b5cf6", width=2.5, show_label=False),
        )
