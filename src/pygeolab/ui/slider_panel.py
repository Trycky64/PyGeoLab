"""Dock panel exposing document numeric variables as live sliders."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSlider, QVBoxLayout, QWidget

from pygeolab.commands import ChangeNumberValueCommand, Command
from pygeolab.model.document import Document
from pygeolab.model.variables import slider_spec


class SliderPanel(QWidget):
    """Render one horizontal slider for every number object in the current document."""

    def __init__(
        self,
        document: Document,
        execute_command: Callable[[Command], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._execute_command = execute_command
        self._layout = QVBoxLayout(self)
        self._unsubscribe = document.subscribe(self.refresh)
        self.refresh()

    def set_document(self, document: Document) -> None:
        """Switch to another document and rebuild slider controls."""
        self._unsubscribe()
        self._document = document
        self._unsubscribe = document.subscribe(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        """Rebuild sliders from immutable number definitions."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        found = False
        for obj in self._document.objects.values():
            if obj.kind != "number":
                continue
            found = True
            spec = slider_spec(obj)
            label = QLabel(f"{obj.name} = {spec.value:.6g}", self)
            slider = QSlider(Qt.Orientation.Horizontal, self)
            steps = max(1, round((spec.maximum - spec.minimum) / spec.step))
            slider.setRange(0, min(steps, 1_000_000))
            index = round((spec.value - spec.minimum) / spec.step)
            position = round(index / steps * slider.maximum())
            slider.setValue(min(slider.maximum(), max(0, position)))
            slider.setProperty("logical_steps", steps)
            slider.setProperty("object_id", obj.id)
            slider.sliderReleased.connect(lambda control=slider: self._commit(control))
            self._layout.addWidget(label)
            self._layout.addWidget(slider)
        if not found:
            self._layout.addWidget(QLabel(self.tr("Aucun curseur"), self))
        self._layout.addStretch(1)

    def _commit(self, slider: QSlider) -> None:
        object_id = slider.property("object_id")
        if not isinstance(object_id, str) or object_id not in self._document.objects:
            return
        spec = slider_spec(self._document.get(object_id))
        steps = slider.property("logical_steps")
        if not isinstance(steps, int) or steps <= 0:
            return
        index = round(slider.value() / max(1, slider.maximum()) * steps)
        value = spec.minimum + index * spec.step
        self._execute_command(ChangeNumberValueCommand(self._document, object_id, value))
