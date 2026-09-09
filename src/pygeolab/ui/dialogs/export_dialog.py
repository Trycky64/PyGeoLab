"""Shared export options for raster and vector output."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QSpinBox,
    QWidget,
)


@dataclass(frozen=True, slots=True)
class ExportOptions:
    """Validated UI export choices."""

    area: str
    transparent: bool
    scale: float
    width: int
    height: int


class ExportDialog(QDialog):
    """Choose viewport/document/selection extent and output dimensions."""

    def __init__(
        self,
        width: int,
        height: int,
        scale: float,
        transparent: bool,
        has_selection: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Options d'export"))
        self.area = QComboBox(self)
        self.area.addItem(self.tr("Viewport actuel"), "viewport")
        self.area.addItem(self.tr("Document complet"), "document")
        self.area.addItem(self.tr("Sélection uniquement"), "selection")
        model_item = self.area.model().index(2, 0)
        self.area.model().setData(model_item, has_selection, 0x0100 - 1)
        self.transparent = QCheckBox(self.tr("Fond transparent"), self)
        self.transparent.setChecked(transparent)
        self.scale = QDoubleSpinBox(self)
        self.scale.setRange(0.25, 8)
        self.scale.setSingleStep(0.25)
        self.scale.setSuffix("×")
        self.scale.setValue(scale)
        self.width_spin = QSpinBox(self)
        self.height_spin = QSpinBox(self)
        for control, value in ((self.width_spin, width), (self.height_spin, height)):
            control.setRange(1, 20_000)
            control.setValue(value)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QFormLayout(self)
        layout.addRow(self.tr("Zone"), self.area)
        layout.addRow(self.tr("Largeur"), self.width_spin)
        layout.addRow(self.tr("Hauteur"), self.height_spin)
        layout.addRow(self.tr("Résolution"), self.scale)
        layout.addRow(self.transparent)
        layout.addRow(buttons)

    def options(self) -> ExportOptions:
        """Return current options after widget-level validation."""
        return ExportOptions(
            str(self.area.currentData()),
            self.transparent.isChecked(),
            self.scale.value(),
            self.width_spin.value(),
            self.height_spin.value(),
        )
