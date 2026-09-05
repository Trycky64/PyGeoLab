"""Editable property panel for the currently selected document object."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from pygeolab.commands import (
    ChangeStyleCommand,
    ChangeVisibilityCommand,
    Command,
    RenameObjectCommand,
)
from pygeolab.model.document import Document
from pygeolab.model.styles import Style


class PropertiesPanel(QWidget):
    """Edit common object metadata using reversible history commands."""

    def __init__(
        self,
        document: Document,
        execute_command: Callable[[Command], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._execute_command = execute_command
        self._object_id: str | None = None
        self._updating = False
        self._empty = QLabel(self.tr("Sélectionnez un objet"), self)
        self._name = QLineEdit(self)
        self._visible = QCheckBox(self)
        self._color = QPushButton(self.tr("Choisir…"), self)
        self._width = QDoubleSpinBox(self)
        self._width.setRange(0.5, 20)
        self._width.setSingleStep(0.5)
        self._point_size = QDoubleSpinBox(self)
        self._point_size.setRange(1, 30)
        self._line_style = QComboBox(self)
        self._line_style.addItems(["solid", "dash", "dot"])
        self._label = QCheckBox(self)
        self._opacity = QDoubleSpinBox(self)
        self._opacity.setRange(0, 1)
        self._opacity.setSingleStep(0.05)
        form = QFormLayout(self)
        form.addRow(self._empty)
        form.addRow(self.tr("Nom"), self._name)
        form.addRow(self.tr("Visible"), self._visible)
        form.addRow(self.tr("Couleur"), self._color)
        form.addRow(self.tr("Épaisseur"), self._width)
        form.addRow(self.tr("Taille du point"), self._point_size)
        form.addRow(self.tr("Style de ligne"), self._line_style)
        form.addRow(self.tr("Afficher le label"), self._label)
        form.addRow(self.tr("Opacité du remplissage"), self._opacity)
        self._name.editingFinished.connect(self._rename)
        self._visible.toggled.connect(self._change_visibility)
        self._color.clicked.connect(self._choose_color)
        self._width.valueChanged.connect(self._change_style)
        self._point_size.valueChanged.connect(self._change_style)
        self._line_style.currentTextChanged.connect(self._change_style)
        self._label.toggled.connect(self._change_style)
        self._opacity.valueChanged.connect(self._change_style)
        self._unsubscribe = document.subscribe(self.refresh)
        self.refresh()

    def set_document(self, document: Document) -> None:
        """Switch document subscriptions and clear stale selection."""
        self._unsubscribe()
        self._document = document
        self._object_id = None
        self._unsubscribe = document.subscribe(self.refresh)
        self.refresh()

    def set_selection(self, object_ids: frozenset[str] | set[str]) -> None:
        """Inspect exactly one selected object; multiple selections show no editor."""
        self._object_id = next(iter(object_ids)) if len(object_ids) == 1 else None
        self.refresh()

    def refresh(self) -> None:
        """Synchronize controls from the immutable current object value."""
        obj = self._document.objects.get(self._object_id or "")
        enabled = obj is not None
        self._empty.setVisible(not enabled)
        widgets = (
            self._name,
            self._visible,
            self._color,
            self._width,
            self._point_size,
            self._line_style,
            self._label,
            self._opacity,
        )
        for widget in widgets:
            widget.setEnabled(enabled)
        if obj is None:
            return
        self._updating = True
        try:
            self._name.setText(obj.name)
            self._visible.setChecked(obj.visible)
            self._width.setValue(obj.style.width)
            self._point_size.setValue(obj.style.point_size)
            self._line_style.setCurrentText(obj.style.line_style)
            self._label.setChecked(obj.style.show_label)
            self._opacity.setValue(obj.style.fill_opacity)
            self._color.setText(obj.style.color)
        finally:
            self._updating = False

    def _rename(self) -> None:
        if self._updating or self._object_id is None:
            return
        obj = self._document.get(self._object_id)
        name = self._name.text().strip()
        if name and name != obj.name:
            self._execute_command(RenameObjectCommand(self._document, obj.id, name))

    def _change_visibility(self, visible: bool) -> None:
        if self._updating or self._object_id is None:
            return
        obj = self._document.get(self._object_id)
        if visible != obj.visible:
            command = ChangeVisibilityCommand(self._document, obj.id, visible)
            self._execute_command(command)

    def _choose_color(self) -> None:
        if self._object_id is None:
            return
        obj = self._document.get(self._object_id)
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            style = self._style(color=color.name())
            self._execute_command(ChangeStyleCommand(self._document, obj.id, style))

    def _change_style(self, *args: object) -> None:
        del args
        if self._updating or self._object_id is None:
            return
        obj = self._document.get(self._object_id)
        style = self._style()
        if style != obj.style:
            self._execute_command(ChangeStyleCommand(self._document, obj.id, style))

    def _style(self, color: str | None = None) -> Style:
        obj = self._document.get(self._object_id or "")
        return Style(
            color=color or obj.style.color,
            width=self._width.value(),
            point_size=self._point_size.value(),
            line_style=self._line_style.currentText(),
            show_label=self._label.isChecked(),
            fill_opacity=self._opacity.value(),
        )
