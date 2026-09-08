"""Dialog for validated function recipes with optional display domains."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QWidget,
)

from pygeolab.math_engine.functions import FunctionObject
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject, JsonValue
from pygeolab.model.styles import Style


class FunctionDialog(QDialog):
    """Collect a function name, independent variable, expression and optional domain."""

    def __init__(
        self,
        document: Document,
        function: GeoObject | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._function = function
        self.setWindowTitle(self.tr("Modifier la fonction" if function else "Nouvelle fonction"))
        params = function.params if function is not None else {}
        self.name_edit = QLineEdit(function.name if function else "f", self)
        self.variable_edit = QLineEdit(str(params.get("variable", "x")), self)
        self.source_edit = QLineEdit(str(params.get("source", "sin(x)")), self)
        self.domain_check = QCheckBox(self.tr("Limiter le domaine"), self)
        self.domain_start = QDoubleSpinBox(self)
        self.domain_end = QDoubleSpinBox(self)
        for spin in (self.domain_start, self.domain_end):
            spin.setRange(-1e9, 1e9)
            spin.setDecimals(6)
        domain = params.get("domain")
        domain_start = domain[0] if isinstance(domain, tuple) and len(domain) == 2 else None
        domain_end = domain[1] if isinstance(domain, tuple) and len(domain) == 2 else None
        if (
            isinstance(domain_start, (int, float))
            and not isinstance(domain_start, bool)
            and isinstance(domain_end, (int, float))
            and not isinstance(domain_end, bool)
        ):
            self.domain_check.setChecked(True)
            self.domain_start.setValue(float(domain_start))
            self.domain_end.setValue(float(domain_end))
        else:
            self.domain_start.setValue(-10)
            self.domain_end.setValue(10)
        self.domain_check.toggled.connect(self.domain_start.setEnabled)
        self.domain_check.toggled.connect(self.domain_end.setEnabled)
        self.domain_start.setEnabled(self.domain_check.isChecked())
        self.domain_end.setEnabled(self.domain_check.isChecked())
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form = QFormLayout(self)
        form.addRow(self.tr("Nom"), self.name_edit)
        form.addRow(self.tr("Variable"), self.variable_edit)
        form.addRow(self.tr("Expression"), self.source_edit)
        form.addRow(self.domain_check)
        form.addRow(self.tr("Début"), self.domain_start)
        form.addRow(self.tr("Fin"), self.domain_end)
        form.addRow(buttons)

    def definition(self) -> tuple[str, tuple[str, ...], dict[str, JsonValue]]:
        """Validate syntax and resolve external names to numeric document objects."""
        name = self.name_edit.text().strip()
        variable = self.variable_edit.text().strip()
        source = self.source_edit.text().strip()
        domain = (
            (self.domain_start.value(), self.domain_end.value())
            if self.domain_check.isChecked()
            else None
        )
        parsed = FunctionObject.from_source(name, variable, source, domain)
        numeric_by_name = {
            obj.name: obj for obj in self._document.objects.values() if obj.kind == "number"
        }
        missing = sorted(parsed.external_dependencies.difference(numeric_by_name))
        if missing:
            raise ValueError(f"Curseurs numériques introuvables : {', '.join(missing)}")
        dependencies = tuple(
            numeric_by_name[dependency].id for dependency in sorted(parsed.external_dependencies)
        )
        params: dict[str, JsonValue] = {"variable": variable, "source": source}
        if domain is not None:
            params["domain"] = domain
        return name, dependencies, params

    def object_definition(self) -> GeoObject:
        """Create a new function object with its dedicated default curve style."""
        name, dependencies, params = self.definition()
        return GeoObject(
            "function",
            name,
            dependencies,
            params,
            style=Style(color="#9333ea", width=2.5, show_label=False),
        )
