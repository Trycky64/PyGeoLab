"""Dialog for the centralized application preference set."""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from pygeolab.ui.preferences import Preferences


class PreferencesDialog(QDialog):
    """Edit appearance, construction, interaction, export and autosave defaults."""

    def __init__(self, preferences: Preferences, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Préférences"))
        self.setAccessibleName(self.tr("Préférences de PyGeoLab"))
        self._language = QComboBox(self)
        self._language.addItem(self.tr("Système"), "system")
        self._language.addItem("English", "en")
        self._language.addItem("Français", "fr")
        self._theme = QComboBox(self)
        self._theme.addItem(self.tr("Système"), "system")
        self._theme.addItem(self.tr("Clair"), "light")
        self._theme.addItem(self.tr("Sombre"), "dark")
        self._grid = QCheckBox(self.tr("Afficher la grille"), self)
        self._axes = QCheckBox(self.tr("Afficher les axes"), self)
        self._labels = QCheckBox(self.tr("Afficher les labels"), self)
        self._snapping = QCheckBox(self.tr("Activer le snapping"), self)
        self._snap_size = QDoubleSpinBox(self)
        self._snap_size.setRange(1, 100)
        self._snap_size.setSuffix(self.tr(" px"))
        self._width = QDoubleSpinBox(self)
        self._width.setRange(0.25, 20)
        self._point_size = QDoubleSpinBox(self)
        self._point_size.setRange(1, 40)
        self._color = QLineEdit(self)
        self._transparent = QCheckBox(self.tr("Fond transparent par défaut"), self)
        self._scale = QDoubleSpinBox(self)
        self._scale.setRange(0.25, 8.0)
        self._scale.setSingleStep(0.25)
        self._scale.setSuffix("×")
        self._autosave = QCheckBox(self.tr("Activer la sauvegarde automatique"), self)
        self._autosave_interval = QSpinBox(self)
        self._autosave_interval.setRange(1, 60)
        self._autosave_interval.setSuffix(self.tr(" min"))
        self._snapping.toggled.connect(self._snap_size.setEnabled)
        self._autosave.toggled.connect(self._autosave_interval.setEnabled)
        self._defaults = QPushButton(self.tr("Restaurer les valeurs par défaut"), self)
        self._defaults.clicked.connect(lambda: self._load(Preferences()))
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QFormLayout(self)
        layout.addRow(self.tr("Langue"), self._language)
        layout.addRow(self.tr("Thème"), self._theme)
        layout.addRow(self._grid)
        layout.addRow(self._axes)
        layout.addRow(self._labels)
        layout.addRow(self._snapping)
        layout.addRow(self.tr("Taille du snap"), self._snap_size)
        layout.addRow(self.tr("Épaisseur par défaut"), self._width)
        layout.addRow(self.tr("Taille de point par défaut"), self._point_size)
        layout.addRow(self.tr("Couleur par défaut"), self._color)
        layout.addRow(self.tr("Qualité d'export"), self._scale)
        layout.addRow(self._transparent)
        layout.addRow(self._autosave)
        layout.addRow(self.tr("Intervalle autosave"), self._autosave_interval)
        layout.addRow(self._defaults)
        layout.addRow(buttons)
        self._load(preferences)

    def _load(self, preferences: Preferences) -> None:
        self._language.setCurrentIndex(self._language.findData(preferences.language))
        self._theme.setCurrentIndex(self._theme.findData(preferences.theme_mode))
        self._grid.setChecked(preferences.show_grid)
        self._axes.setChecked(preferences.show_axes)
        self._labels.setChecked(preferences.show_labels)
        self._snapping.setChecked(preferences.snapping_enabled)
        self._snap_size.setValue(preferences.snap_threshold_px)
        self._width.setValue(preferences.default_width)
        self._point_size.setValue(preferences.default_point_size)
        self._color.setText(preferences.default_color)
        self._scale.setValue(preferences.export_scale)
        self._transparent.setChecked(preferences.transparent_export)
        self._autosave.setChecked(preferences.autosave_enabled)
        self._autosave_interval.setValue(preferences.autosave_interval_minutes)
        self._snap_size.setEnabled(self._snapping.isChecked())
        self._autosave_interval.setEnabled(self._autosave.isChecked())

    def preferences(self) -> Preferences:
        """Return validated values currently displayed."""
        return Preferences(
            theme_mode=str(self._theme.currentData()),
            language=str(self._language.currentData()),
            show_grid=self._grid.isChecked(),
            show_axes=self._axes.isChecked(),
            show_labels=self._labels.isChecked(),
            snapping_enabled=self._snapping.isChecked(),
            snap_threshold_px=self._snap_size.value(),
            default_width=self._width.value(),
            default_point_size=self._point_size.value(),
            default_color=self._color.text().strip(),
            export_scale=self._scale.value(),
            transparent_export=self._transparent.isChecked(),
            autosave_enabled=self._autosave.isChecked(),
            autosave_interval_minutes=self._autosave_interval.value(),
        )
