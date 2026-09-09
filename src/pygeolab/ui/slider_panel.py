"""Editable, keyboard-accessible and animatable numeric-variable controls."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from pygeolab.commands import (
    ChangeNumberValueCommand,
    ChangeParametersCommand,
    Command,
    CompositeCommand,
    RenameObjectCommand,
)
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.variables import slider_initial, slider_params, slider_spec
from pygeolab.ui.dialogs.slider_dialog import SliderDialog
from pygeolab.ui.translations import translate_message


@dataclass(slots=True)
class _SliderControls:
    container: QWidget
    label: QLabel
    slider: QSlider
    value: QDoubleSpinBox
    reset: QPushButton
    edit: QPushButton
    play: QPushButton
    speed: QDoubleSpinBox
    ping_pong: QCheckBox


class SliderPanel(QWidget):
    """Render persistent numeric controls and animate them outside Undo history."""

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
        self._rows: dict[str, _SliderControls] = {}
        self._empty_label = QLabel(self.tr("Aucun curseur"), self)
        self._layout.addWidget(self._empty_label)
        self._layout.addStretch(1)
        self._active: set[str] = set()
        self._directions: dict[str, int] = {}
        self._animation_values: dict[str, float] = {}
        self._last_tick = monotonic()
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._animate_tick)
        self._unsubscribe = document.subscribe(self.refresh)
        self.refresh()

    @property
    def active_animation_ids(self) -> frozenset[str]:
        """Expose active animations for status and deterministic tests."""
        return frozenset(self._active)

    def set_document(self, document: Document) -> None:
        """Switch document, stop animations and rebuild numeric controls."""
        self._unsubscribe()
        self._active.clear()
        self._directions.clear()
        self._animation_values.clear()
        self._timer.stop()
        for controls in self._rows.values():
            controls.container.deleteLater()
        self._rows.clear()
        self._document = document
        self._unsubscribe = document.subscribe(self.refresh)
        self.refresh()

    def dispose(self) -> None:
        """Stop animation and release the document subscription."""
        self._active.clear()
        self._timer.stop()
        self._unsubscribe()

    def refresh(self) -> None:
        """Synchronize controls without replacing widgets during their Qt signals."""
        objects = {obj.id: obj for obj in self._document.objects.values() if obj.kind == "number"}
        for object_id in tuple(self._rows):
            if object_id not in objects:
                self._active.discard(object_id)
                self._rows.pop(object_id).container.deleteLater()
        for object_id, obj in objects.items():
            controls = self._rows.get(object_id)
            if controls is None:
                controls = self._create_row(obj)
                self._rows[object_id] = controls
                self._layout.insertWidget(self._layout.count() - 1, controls.container)
            self._sync_row(obj, controls)
        self._empty_label.setVisible(not objects)
        if not self._active:
            self._timer.stop()

    def _create_row(self, obj: GeoObject) -> _SliderControls:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(container)
        slider = QSlider(Qt.Orientation.Horizontal, container)
        value = QDoubleSpinBox(container)
        value.setDecimals(9)
        reset = QPushButton(self.tr("Reset"), container)
        edit = QPushButton(self.tr("Modifier"), container)
        play = QPushButton(self.tr("▶"), container)
        speed = QDoubleSpinBox(container)
        speed.setRange(0.01, 1000.0)
        speed.setDecimals(2)
        speed.setSuffix(self.tr(" u/s"))
        ping_pong = QCheckBox(self.tr("↔"), container)
        for widget in (label, slider, value, reset, edit, play, speed, ping_pong):
            layout.addWidget(widget)
        controls = _SliderControls(
            container, label, slider, value, reset, edit, play, speed, ping_pong
        )
        slider.sliderReleased.connect(lambda oid=obj.id: self._commit_slider(oid))
        slider.valueChanged.connect(
            lambda _value, oid=obj.id: (
                self._commit_slider(oid) if not self._rows[oid].slider.isSliderDown() else None
            )
        )
        value.editingFinished.connect(lambda oid=obj.id: self._commit_value(oid))
        reset.clicked.connect(lambda _checked=False, oid=obj.id: self._reset(oid))
        edit.clicked.connect(lambda _checked=False, oid=obj.id: self._edit(oid))
        play.clicked.connect(lambda _checked=False, oid=obj.id: self.toggle_animation(oid))
        speed.editingFinished.connect(lambda oid=obj.id: self._commit_animation_options(oid))
        ping_pong.toggled.connect(lambda _checked, oid=obj.id: self._commit_animation_options(oid))
        return controls

    def _sync_row(self, obj: GeoObject, controls: _SliderControls) -> None:
        spec = slider_spec(obj)
        controls.label.setText(f"{obj.name} = {spec.value:.6g}")
        steps = max(1, round((spec.maximum - spec.minimum) / spec.step))
        maximum = min(steps, 1_000_000)
        position = round((spec.value - spec.minimum) / (spec.maximum - spec.minimum) * maximum)
        for widget in (controls.slider, controls.value, controls.speed, controls.ping_pong):
            widget.blockSignals(True)
        controls.slider.setRange(0, maximum)
        controls.slider.setProperty("logical_steps", steps)
        controls.slider.setValue(min(maximum, max(0, position)))
        controls.value.setRange(spec.minimum, spec.maximum)
        controls.value.setSingleStep(spec.step)
        controls.value.setValue(spec.value)
        speed = obj.params.get("animation_speed", 1.0)
        controls.speed.setValue(float(speed) if isinstance(speed, (int, float)) else 1.0)
        controls.ping_pong.setChecked(obj.params.get("ping_pong", False) is True)
        for widget in (controls.slider, controls.value, controls.speed, controls.ping_pong):
            widget.blockSignals(False)
        controls.play.setText(self.tr("⏸" if obj.id in self._active else "▶"))

    def _commit_slider(self, object_id: str) -> None:
        if object_id not in self._rows or object_id not in self._document.objects:
            return
        controls = self._rows[object_id]
        spec = slider_spec(self._document.get(object_id))
        fraction = controls.slider.value() / max(1, controls.slider.maximum())
        self._set_value(object_id, spec.minimum + fraction * (spec.maximum - spec.minimum))

    def _commit_value(self, object_id: str) -> None:
        if object_id in self._rows:
            self._set_value(object_id, self._rows[object_id].value.value())

    def _set_value(self, object_id: str, value: float) -> None:
        obj = self._document.get(object_id)
        spec = slider_spec(obj)
        snapped = spec.snapped(value)
        if snapped != spec.value:
            self._execute_command(ChangeNumberValueCommand(self._document, object_id, snapped))

    def _reset(self, object_id: str) -> None:
        self._set_value(object_id, slider_initial(self._document.get(object_id)))

    def _edit(self, object_id: str) -> None:
        obj = self._document.get(object_id)
        dialog = SliderDialog(self, obj)
        if dialog.exec() != SliderDialog.DialogCode.Accepted:
            return
        try:
            name, params = dialog.definition()
            commands: list[Command] = [ChangeParametersCommand(self._document, object_id, params)]
            if name != obj.name:
                commands.insert(0, RenameObjectCommand(self._document, object_id, name))
            self._execute_command(commands[0] if len(commands) == 1 else CompositeCommand(commands))
        except ValueError as exc:
            QMessageBox.warning(self, self.tr("Curseur invalide"), translate_message(str(exc)))

    def _commit_animation_options(self, object_id: str) -> None:
        if object_id not in self._rows or object_id not in self._document.objects:
            return
        controls = self._rows[object_id]
        obj = self._document.get(object_id)
        params = dict(obj.params)
        params["animation_speed"] = controls.speed.value()
        params["ping_pong"] = controls.ping_pong.isChecked()
        if params != dict(obj.params):
            self._execute_command(ChangeParametersCommand(self._document, object_id, params))

    def toggle_animation(self, object_id: str) -> None:
        """Start or pause one slider while preserving its playback direction."""
        if object_id in self._active:
            self._active.remove(object_id)
        elif object_id in self._document.objects:
            self._active.add(object_id)
            self._directions.setdefault(object_id, 1)
            self._animation_values[object_id] = slider_spec(self._document.get(object_id)).value
            self._last_tick = monotonic()
            self._timer.start()
        self.refresh()

    def _animate_tick(self, elapsed: float | None = None) -> None:
        now = monotonic()
        delta = min(0.25, max(0.0, elapsed if elapsed is not None else now - self._last_tick))
        self._last_tick = now
        for object_id in tuple(self._active):
            if object_id not in self._document.objects:
                self._active.discard(object_id)
                continue
            obj = self._document.get(object_id)
            spec = slider_spec(obj)
            raw_speed = obj.params.get("animation_speed", 1.0)
            speed = float(raw_speed) if isinstance(raw_speed, (int, float)) else 1.0
            if not math.isfinite(speed) or speed <= 0:
                speed = 1.0
            direction = self._directions.get(object_id, 1)
            candidate = (
                self._animation_values.get(object_id, spec.value) + direction * speed * delta
            )
            if obj.params.get("ping_pong", False) is True:
                span = spec.maximum - spec.minimum
                if candidate > spec.maximum:
                    overflow = (candidate - spec.maximum) % (2 * span)
                    if overflow <= span:
                        candidate, direction = spec.maximum - overflow, -1
                    else:
                        candidate, direction = spec.minimum + overflow - span, 1
                elif candidate < spec.minimum:
                    overflow = (spec.minimum - candidate) % (2 * span)
                    if overflow <= span:
                        candidate, direction = spec.minimum + overflow, 1
                    else:
                        candidate, direction = spec.maximum - overflow + span, -1
                self._directions[object_id] = direction
            else:
                span = spec.maximum - spec.minimum
                candidate = spec.minimum + (candidate - spec.minimum) % span
            self._animation_values[object_id] = candidate
            params = slider_params(obj, candidate)
            value = params.get("value")
            if isinstance(value, (int, float)) and not math.isclose(float(value), spec.value):
                self._document.update(object_id, params=params)
        if not self._active:
            self._timer.stop()
