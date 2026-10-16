"""Dialog for defining and editing geometric locus recipes."""

from __future__ import annotations

import math

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QWidget,
)

from pygeolab.geometry.primitives import Point2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject, JsonValue


class LocusDialog(QDialog):
    """Collect a locus name, target point, driver object, sweep range, and sample count."""

    def __init__(
        self,
        document: Document,
        locus: GeoObject | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._locus = locus
        title = "Modifier le lieu géométrique" if locus else "Nouveau lieu géométrique"
        self.setWindowTitle(self.tr(title))

        params = locus.params if locus is not None else {}
        self.name_edit = QLineEdit(locus.name if locus else document.unique_name("Lieu"), self)

        # Candidates for target: points that have dependencies
        self.target_combo = QComboBox(self)
        for obj in document.objects.values():
            if isinstance(obj.geometry, Point2D) and obj.dependencies:
                self.target_combo.addItem(f"{obj.name} ({obj.kind})", obj.id)

        # Candidates for driver: number sliders or point_on
        self.driver_combo = QComboBox(self)
        for obj in document.objects.values():
            if obj.kind in {"number", "point_on"}:
                self.driver_combo.addItem(f"{obj.name} ({obj.kind})", obj.id)

        self.start_spin = QDoubleSpinBox(self)
        self.start_spin.setRange(-1e9, 1e9)
        self.start_spin.setDecimals(4)

        self.end_spin = QDoubleSpinBox(self)
        self.end_spin.setRange(-1e9, 1e9)
        self.end_spin.setDecimals(4)

        self.samples_spin = QSpinBox(self)
        self.samples_spin.setRange(10, 500)
        self.samples_spin.setSingleStep(10)
        raw_samples = params.get("samples", 150)
        samples_val = int(raw_samples) if isinstance(raw_samples, (int, float, str)) else 150
        self.samples_spin.setValue(samples_val)

        # Pre-select existing or sensible defaults
        if locus is not None and len(locus.dependencies) >= 2:
            target_id, driver_id = locus.dependencies[0], locus.dependencies[1]
            idx_t = self.target_combo.findData(target_id)
            if idx_t >= 0:
                self.target_combo.setCurrentIndex(idx_t)
            idx_d = self.driver_combo.findData(driver_id)
            if idx_d >= 0:
                self.driver_combo.setCurrentIndex(idx_d)
            raw_start = params.get("start", 0.0)
            raw_end = params.get("end", 1.0)
            start_val = float(raw_start) if isinstance(raw_start, (int, float, str)) else 0.0
            end_val = float(raw_end) if isinstance(raw_end, (int, float, str)) else 1.0
            self.start_spin.setValue(start_val)
            self.end_spin.setValue(end_val)
        else:
            if self.target_combo.count() > 0 and self.driver_combo.count() > 0:
                # If the first items happen to be the same object, pick another driver or target
                if self.target_combo.itemData(0) == self.driver_combo.itemData(0):
                    if self.target_combo.count() > 1:
                        self.target_combo.setCurrentIndex(1)
                    elif self.driver_combo.count() > 1:
                        self.driver_combo.setCurrentIndex(1)
            self._update_default_range()

        self.driver_combo.currentIndexChanged.connect(self._on_driver_changed)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout(self)
        layout.addRow(self.tr("Nom :"), self.name_edit)
        layout.addRow(self.tr("Point cible :"), self.target_combo)
        layout.addRow(self.tr("Variable pilote :"), self.driver_combo)
        layout.addRow(self.tr("Début :"), self.start_spin)
        layout.addRow(self.tr("Fin :"), self.end_spin)
        layout.addRow(self.tr("Échantillons :"), self.samples_spin)
        layout.addRow(buttons)

    def _on_driver_changed(self) -> None:
        self._update_default_range()

    def _update_default_range(self) -> None:
        driver_id = self.driver_combo.currentData()
        if not driver_id or driver_id not in self._document.objects:
            return
        driver = self._document.get(driver_id)
        if driver.kind == "number":
            min_val = driver.params.get("minimum", -5.0)
            max_val = driver.params.get("maximum", 5.0)
            self.start_spin.setValue(float(min_val) if isinstance(min_val, (int, float)) else -5.0)
            self.end_spin.setValue(float(max_val) if isinstance(max_val, (int, float)) else 5.0)
        elif driver.kind == "point_on":
            # If point is on a circle, sweep 0 to 2pi; if on segment, 0 to 1
            support_id = driver.dependencies[0] if driver.dependencies else None
            support = self._document.objects.get(support_id) if support_id else None
            if support and support.kind in {"circle", "circumcircle", "circle_radius"}:
                self.start_spin.setValue(0.0)
                self.end_spin.setValue(2.0 * math.pi)
            else:
                self.start_spin.setValue(0.0)
                self.end_spin.setValue(1.0)

    def definition(self) -> tuple[str, tuple[str, ...], dict[str, JsonValue]]:
        """Return (name, dependencies, params) for creating or updating a locus."""
        name = self.name_edit.text().strip()
        if not name:
            raise ValueError("Le nom du lieu géométrique ne peut pas être vide")

        target_id = self.target_combo.currentData()
        driver_id = self.driver_combo.currentData()
        if not target_id or not driver_id:
            raise ValueError("Point cible et variable pilote requis")
        if target_id == driver_id:
            raise ValueError("La cible et le pilote doivent être distincts")

        start = self.start_spin.value()
        end = self.end_spin.value()
        if math.isclose(start, end, abs_tol=1e-12):
            raise ValueError("L'intervalle de balayage ne peut pas être nul")

        samples = self.samples_spin.value()
        params: dict[str, JsonValue] = {
            "start": start,
            "end": end,
            "samples": samples,
        }
        return name, (target_id, driver_id), params

    def object_definition(self) -> GeoObject:
        """Build a new GeoObject ready for insertion into the document."""
        name, dependencies, params = self.definition()
        return GeoObject(
            kind="locus",
            name=name,
            dependencies=dependencies,
            params=params,
            style=self._document.default_style,
        )
