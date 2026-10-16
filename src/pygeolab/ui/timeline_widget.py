"""Multi-slider timeline control widget with transport bar, scrubbing slider, and range markers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from pygeolab.model.document import Document
from pygeolab.ui.timeline_controller import TimelineController

if TYPE_CHECKING:
    from pygeolab.ui.preferences import Preferences


class TimelineWidget(QWidget):
    """Transport and scrubbing interface for TimelineController."""

    def __init__(
        self,
        document: Document,
        preferences: Preferences | None = None,
        controller: TimelineController | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._controller = (
            controller
            if controller is not None
            else TimelineController(document, preferences=preferences, parent=self)
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(4)

        # Row 1: Transport buttons & Status
        transport_layout = QHBoxLayout()
        self.play_button = QPushButton(self.tr("Lecture"), self)
        self.stop_button = QPushButton(self.tr("Arrêter"), self)
        self.time_label = QLabel("0.00s / 10.00s", self)
        transport_layout.addWidget(self.play_button)
        transport_layout.addWidget(self.stop_button)
        transport_layout.addWidget(self.time_label)
        transport_layout.addStretch()

        self.loop_check = QCheckBox(self.tr("Boucle"), self)
        self.loop_check.setChecked(self._controller.loop)
        self.ping_pong_check = QCheckBox(self.tr("Aller-retour"), self)
        self.ping_pong_check.setChecked(self._controller.ping_pong)
        self.restore_check = QCheckBox(self.tr("Restaurer l'état initial à l'arrêt"), self)

        transport_layout.addWidget(self.loop_check)
        transport_layout.addWidget(self.ping_pong_check)
        transport_layout.addWidget(self.restore_check)
        main_layout.addLayout(transport_layout)

        # Row 2: Scrubbing slider (1000 steps)
        scrub_layout = QHBoxLayout()
        self.scrub_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.scrub_slider.setRange(0, 1000)
        self.scrub_slider.setValue(0)
        scrub_layout.addWidget(self.scrub_slider)
        main_layout.addLayout(scrub_layout)

        # Row 3: Markers & parameters
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel(self.tr("Début :"), self))
        self.start_spin = QDoubleSpinBox(self)
        self.start_spin.setRange(0.0, 1.0)
        self.start_spin.setSingleStep(0.05)
        self.start_spin.setDecimals(2)
        self.start_spin.setValue(self._controller.start_marker)
        params_layout.addWidget(self.start_spin)

        params_layout.addWidget(QLabel(self.tr("Fin :"), self))
        self.end_spin = QDoubleSpinBox(self)
        self.end_spin.setRange(0.0, 1.0)
        self.end_spin.setSingleStep(0.05)
        self.end_spin.setDecimals(2)
        self.end_spin.setValue(self._controller.end_marker)
        params_layout.addWidget(self.end_spin)

        params_layout.addWidget(QLabel(self.tr("Durée :"), self))
        self.duration_spin = QDoubleSpinBox(self)
        self.duration_spin.setRange(0.5, 3600.0)
        self.duration_spin.setSingleStep(1.0)
        self.duration_spin.setDecimals(1)
        self.duration_spin.setSuffix(" s")
        self.duration_spin.setValue(self._controller.duration)
        params_layout.addWidget(self.duration_spin)

        params_layout.addWidget(QLabel(self.tr("Vitesse :"), self))
        self.speed_spin = QDoubleSpinBox(self)
        self.speed_spin.setRange(0.1, 10.0)
        self.speed_spin.setSingleStep(0.1)
        self.speed_spin.setDecimals(2)
        self.speed_spin.setSuffix("×")
        self.speed_spin.setValue(self._controller.global_speed)
        params_layout.addWidget(self.speed_spin)

        params_layout.addStretch()
        main_layout.addLayout(params_layout)

        # Connect signals
        self.play_button.clicked.connect(self._controller.toggle_play)
        self.stop_button.clicked.connect(
            lambda: self._controller.stop(restore_initial=self.restore_check.isChecked())
        )
        self.loop_check.toggled.connect(self._controller.set_loop)
        self.ping_pong_check.toggled.connect(self._controller.set_ping_pong)

        self.start_spin.valueChanged.connect(self._on_markers_changed)
        self.end_spin.valueChanged.connect(self._on_markers_changed)
        self.duration_spin.valueChanged.connect(self._controller.set_duration)
        self.speed_spin.valueChanged.connect(self._controller.set_global_speed)

        self.scrub_slider.sliderMoved.connect(self._on_slider_scrubbing)
        self.scrub_slider.valueChanged.connect(
            lambda val: self._on_slider_scrubbing(val) if self.scrub_slider.isSliderDown() else None
        )

        self._controller.stateChanged.connect(self._on_state_changed)
        self._controller.timeChanged.connect(self._on_time_changed)
        self._controller.durationChanged.connect(self._on_duration_changed)

    @property
    def controller(self) -> TimelineController:
        """Expose the underlying TimelineController."""
        return self._controller

    def set_document(self, document: Document) -> None:
        """Switch the active document for the timeline widget and controller."""
        self._document = document
        self._controller.set_document(document)

    def _on_state_changed(self, is_playing: bool) -> None:
        self.play_button.setText(self.tr("Pause" if is_playing else "Lecture"))

    def _on_time_changed(self, norm_t: float) -> None:
        if not self.scrub_slider.isSliderDown():
            self.scrub_slider.blockSignals(True)
            self.scrub_slider.setValue(round(norm_t * 1000))
            self.scrub_slider.blockSignals(False)
        curr_s = self._controller.current_time
        dur_s = self._controller.duration
        self.time_label.setText(f"{curr_s:.2f}s / {dur_s:.2f}s")

    def _on_duration_changed(self, duration: float) -> None:
        self.duration_spin.blockSignals(True)
        self.duration_spin.setValue(duration)
        self.duration_spin.blockSignals(False)
        self._on_time_changed(self._controller.normalized_time)

    def _on_slider_scrubbing(self, slider_pos: int) -> None:
        norm_t = slider_pos / 1000.0
        self._controller.set_normalized_time(norm_t)

    def _on_markers_changed(self) -> None:
        s = self.start_spin.value()
        e = self.end_spin.value()
        self._controller.set_markers(s, e)
