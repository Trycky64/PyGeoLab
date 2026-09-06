"""Preferences dialog for appearance and export defaults."""

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QWidget,
)

from pygeolab.ui.preferences import Preferences


class PreferencesDialog(QDialog):
    """Edit the intentionally small set of persistent user preferences."""

    def __init__(self, preferences: Preferences, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Préférences"))
        self.setAccessibleName(self.tr("Préférences de PyGeoLab"))
        self._dark = QCheckBox(self.tr("Utiliser le thème sombre"), self)
        self._dark.setChecked(preferences.dark_theme)
        self._transparent = QCheckBox(self.tr("Fond transparent par défaut"), self)
        self._transparent.setChecked(preferences.transparent_export)
        self._scale = QDoubleSpinBox(self)
        self._scale.setRange(0.25, 8.0)
        self._scale.setSingleStep(0.25)
        self._scale.setSuffix("×")
        self._scale.setValue(preferences.export_scale)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QFormLayout(self)
        layout.addRow(self._dark)
        layout.addRow(self.tr("Résolution export"), self._scale)
        layout.addRow(self._transparent)
        layout.addRow(buttons)

    def preferences(self) -> Preferences:
        """Return the validated preference values currently displayed."""
        return Preferences(
            self._dark.isChecked(),
            self._scale.value(),
            self._transparent.isChecked(),
        )
