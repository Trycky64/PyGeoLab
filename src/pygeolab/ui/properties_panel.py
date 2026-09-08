"""Editable property panel for the currently selected document object."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace

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
    ChangeLockCommand,
    ChangeStyleCommand,
    ChangeVisibilityCommand,
    Command,
    CompositeCommand,
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
        self._object_ids: frozenset[str] = frozenset()
        self._updating = False
        self._empty = QLabel(self.tr("Sélectionnez un objet"), self)
        self._name = QLineEdit(self)
        self._visible = QCheckBox(self)
        self._locked = QCheckBox(self)
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
        form.addRow(self.tr("Verrouillé"), self._locked)
        form.addRow(self.tr("Couleur"), self._color)
        form.addRow(self.tr("Épaisseur"), self._width)
        form.addRow(self.tr("Taille du point"), self._point_size)
        form.addRow(self.tr("Style de ligne"), self._line_style)
        form.addRow(self.tr("Afficher le label"), self._label)
        form.addRow(self.tr("Opacité du remplissage"), self._opacity)
        self._name.editingFinished.connect(self._rename)
        self._visible.toggled.connect(self._change_visibility)
        self._locked.toggled.connect(self._change_locked)
        self._color.clicked.connect(self._choose_color)
        self._width.valueChanged.connect(lambda _value: self._change_style("width"))
        self._point_size.valueChanged.connect(lambda _value: self._change_style("point_size"))
        self._line_style.currentTextChanged.connect(lambda _value: self._change_style("line_style"))
        self._label.toggled.connect(lambda _value: self._change_style("show_label"))
        self._opacity.valueChanged.connect(lambda _value: self._change_style("fill_opacity"))
        self._unsubscribe = document.subscribe(self.refresh)
        self.refresh()

    def set_document(self, document: Document) -> None:
        """Switch document subscriptions and clear stale selection."""
        self._unsubscribe()
        self._document = document
        self._object_id = None
        self._object_ids = frozenset()
        self._unsubscribe = document.subscribe(self.refresh)
        self.refresh()

    def set_selection(self, object_ids: frozenset[str] | set[str]) -> None:
        """Inspect one object or expose common style controls for multiple objects."""
        self._object_ids = frozenset(
            object_id for object_id in object_ids if object_id in self._document.objects
        )
        self._object_id = next(iter(self._object_ids)) if len(self._object_ids) == 1 else None
        self.refresh()

    def refresh(self) -> None:
        """Synchronize controls from the immutable current object value."""
        objects = [
            self._document.get(object_id)
            for object_id in self._object_ids
            if object_id in self._document.objects
        ]
        obj = objects[0] if objects else None
        enabled = bool(objects)
        single = len(objects) == 1
        self._empty.setText(
            self.tr("Sélectionnez un objet")
            if not objects
            else self.tr(f"{len(objects)} objets sélectionnés")
        )
        self._empty.setVisible(not single)
        widgets = (
            self._visible,
            self._locked,
            self._color,
            self._width,
            self._point_size,
            self._line_style,
            self._label,
            self._opacity,
        )
        for widget in widgets:
            widget.setEnabled(enabled)
        self._name.setEnabled(single)
        if obj is None:
            return
        self._updating = True
        try:
            self._name.setText(obj.name)
            self._visible.setChecked(obj.visible)
            self._locked.setChecked(obj.locked)
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
        if self._updating or not self._object_ids:
            return
        commands = [
            ChangeVisibilityCommand(self._document, object_id, visible)
            for object_id in self._object_ids
            if self._document.get(object_id).visible != visible
        ]
        self._execute_commands(commands)

    def _change_locked(self, locked: bool) -> None:
        if self._updating or not self._object_ids:
            return
        commands = [
            ChangeLockCommand(self._document, object_id, locked)
            for object_id in self._object_ids
            if self._document.get(object_id).locked != locked
        ]
        self._execute_commands(commands)

    def _choose_color(self) -> None:
        if not self._object_ids:
            return
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self._apply_style_value("color", color.name())

    def _change_style(self, field: str) -> None:
        if self._updating or not self._object_ids:
            return
        values: dict[str, str | float | bool] = {
            "width": self._width.value(),
            "point_size": self._point_size.value(),
            "line_style": self._line_style.currentText(),
            "show_label": self._label.isChecked(),
            "fill_opacity": self._opacity.value(),
        }
        self._apply_style_value(field, values[field])

    def _apply_style_value(self, field: str, value: str | float | bool) -> None:
        commands: list[Command] = []
        for object_id in self._object_ids:
            obj = self._document.get(object_id)
            style = _replace_style_value(obj.style, field, value)
            if style != obj.style:
                commands.append(ChangeStyleCommand(self._document, object_id, style))
        self._execute_commands(commands)

    def _execute_commands(self, commands: Sequence[Command]) -> None:
        if not commands:
            return
        self._execute_command(commands[0] if len(commands) == 1 else CompositeCommand(commands))


def _replace_style_value(style: Style, field: str, value: str | float | bool) -> Style:
    if field == "color" and isinstance(value, str):
        return replace(style, color=value)
    if field == "line_style" and isinstance(value, str):
        return replace(style, line_style=value)
    if field == "show_label" and isinstance(value, bool):
        return replace(style, show_label=value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric = float(value)
        if field == "width":
            return replace(style, width=numeric)
        if field == "point_size":
            return replace(style, point_size=numeric)
        if field == "fill_opacity":
            return replace(style, fill_opacity=numeric)
    raise ValueError(f"Propriété de style invalide : {field}")
