"""Timeline controller for multi-slider playback and deterministic animations."""

from __future__ import annotations

import math
from time import monotonic
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Signal

from pygeolab.model.document import Document
from pygeolab.model.variables import slider_params, slider_spec

if TYPE_CHECKING:
    from pygeolab.ui.preferences import Preferences


class TimelineController(QObject):
    """Orchestrates synchronized multi-slider animation, scrubbing, and timeline state."""

    stateChanged = Signal(bool)  # is_playing
    timeChanged = Signal(float)  # current normalized time in [0, 1] or seconds
    durationChanged = Signal(float)  # duration in seconds

    def __init__(
        self,
        document: Document,
        preferences: Preferences | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._document = document
        self._duration: float = 10.0  # Timeline duration in seconds
        self._current_time: float = 0.0  # Current playhead in [0, duration]
        self._fps: int = 30
        self._global_speed: float = 1.0
        self._loop: bool = True
        self._ping_pong: bool = False
        self._reverse: bool = False
        self._is_playing: bool = False
        self._start_marker: float = 0.0  # normalized [0, 1]
        self._end_marker: float = 1.0  # normalized [0, 1]

        # Initial values saved before playback for optional restore
        self._initial_states: dict[str, float] = {}
        # Sliders that participate in the timeline (default empty -> all sliders participate)
        self._active_slider_ids: set[str] = set()

        self._timer = QTimer(self)
        self._update_timer_interval()
        self._timer.timeout.connect(self._on_timer_tick)
        self._last_tick_time = monotonic()

        if preferences is not None:
            self.set_fps(preferences.timeline_fps)
            self.set_global_speed(preferences.timeline_speed)

    @property
    def is_playing(self) -> bool:
        """Return True if the animation is currently running."""
        return self._is_playing

    @property
    def duration(self) -> float:
        """Return timeline duration in seconds."""
        return self._duration

    def set_duration(self, duration: float) -> None:
        """Set the duration of the timeline in seconds."""
        clamped = max(0.5, min(3600.0, float(duration)))
        if not math.isclose(clamped, self._duration):
            self._duration = clamped
            self.durationChanged.emit(self._duration)
            self.set_time(self._current_time)

    @property
    def current_time(self) -> float:
        """Return current playhead time in seconds."""
        return self._current_time

    @property
    def normalized_time(self) -> float:
        """Return normalized playhead in [0, 1]."""
        return self._current_time / max(0.001, self._duration)

    @property
    def fps(self) -> int:
        """Return animation timer target FPS."""
        return self._fps

    def set_fps(self, fps: int) -> None:
        """Set animation timer target FPS."""
        self._fps = max(10, min(120, int(fps)))
        self._update_timer_interval()

    @property
    def global_speed(self) -> float:
        """Return playback speed multiplier."""
        return self._global_speed

    def set_global_speed(self, speed: float) -> None:
        """Set playback speed multiplier."""
        if math.isfinite(speed) and speed > 0:
            self._global_speed = max(0.1, min(10.0, float(speed)))

    @property
    def loop(self) -> bool:
        """Return True if playback loops continuously."""
        return self._loop

    def set_loop(self, loop: bool) -> None:
        """Enable or disable continuous looping."""
        self._loop = bool(loop)

    @property
    def ping_pong(self) -> bool:
        """Return True if playback bounces forward and backward."""
        return self._ping_pong

    def set_ping_pong(self, ping_pong: bool) -> None:
        """Enable or disable ping-pong oscillation."""
        self._ping_pong = bool(ping_pong)

    @property
    def start_marker(self) -> float:
        """Return normalized start marker [0, 1]."""
        return self._start_marker

    @property
    def end_marker(self) -> float:
        """Return normalized end marker [0, 1]."""
        return self._end_marker

    def set_markers(self, start: float, end: float) -> None:
        """Set start and end playback range markers in [0, 1]."""
        s = max(0.0, min(1.0, float(start)))
        e = max(0.0, min(1.0, float(end)))
        if s > e:
            s, e = e, s
        if math.isclose(s, e, abs_tol=1e-5):
            e = min(1.0, s + 0.01)
        self._start_marker = s
        self._end_marker = e

    @property
    def active_slider_ids(self) -> frozenset[str]:
        """Return the subset of slider IDs participating in timeline animation."""
        return frozenset(self._active_slider_ids)

    def set_active_slider_ids(self, ids: set[str] | frozenset[str]) -> None:
        """Set the subset of slider IDs participating in timeline animation."""
        self._active_slider_ids = set(ids)

    def set_document(self, document: Document) -> None:
        """Adopt a new document and reset timeline playback."""
        self.stop(restore_initial=False)
        self._document = document
        self._initial_states.clear()
        self._active_slider_ids.clear()
        self._current_time = 0.0
        self.timeChanged.emit(0.0)

    def _update_timer_interval(self) -> None:
        interval_ms = max(1, round(1000.0 / self._fps))
        self._timer.setInterval(interval_ms)

    def save_initial_state(self) -> None:
        """Capture current values of all numeric sliders."""
        self._initial_states = {
            obj.id: slider_spec(obj).value
            for obj in self._document.objects.values()
            if obj.kind == "number"
        }

    def restore_initial_state(self) -> None:
        """Restore all sliders to their saved initial state without adding undo entries."""
        for object_id, value in self._initial_states.items():
            if object_id in self._document.objects:
                obj = self._document.get(object_id)
                params = slider_params(obj, value)
                self._document.update(object_id, params=params)
        self.set_time(0.0)

    def play(self) -> None:
        """Start or resume playback."""
        if self._is_playing:
            return
        if not self._initial_states:
            self.save_initial_state()
        self._is_playing = True
        self._last_tick_time = monotonic()
        self._timer.start()
        self.stateChanged.emit(True)

    def pause(self) -> None:
        """Pause playback at current playhead."""
        if not self._is_playing:
            return
        self._is_playing = False
        self._timer.stop()
        self.stateChanged.emit(False)

    def toggle_play(self) -> None:
        """Toggle between play and pause states."""
        if self._is_playing:
            self.pause()
        else:
            self.play()

    def stop(self, restore_initial: bool = False) -> None:
        """Stop playback and rewind to start marker (optionally restoring initial values)."""
        self.pause()
        if restore_initial and self._initial_states:
            self.restore_initial_state()
        else:
            self.set_time(self._start_marker * self._duration)

    def set_time(self, time_s: float) -> None:
        """Scrub playhead to specific time in seconds and update all participating sliders."""
        time_s = max(0.0, min(self._duration, float(time_s)))
        self._current_time = time_s
        self._apply_sliders_at_time(self.normalized_time)
        self.timeChanged.emit(self.normalized_time)

    def set_normalized_time(self, t: float) -> None:
        """Scrub playhead using normalized fraction [0, 1]."""
        self.set_time(max(0.0, min(1.0, float(t))) * self._duration)

    def advance(self, delta_seconds: float) -> None:
        """Deterministic frame advance, usable directly in unit tests without Qt timers."""
        if self._duration <= 0:
            return

        effective_delta = delta_seconds * self._global_speed
        if self._reverse:
            effective_delta = -effective_delta

        new_time = self._current_time + effective_delta
        min_time = self._start_marker * self._duration
        max_time = self._end_marker * self._duration
        span = max_time - min_time

        if span <= 1e-6:
            self.set_time(min_time)
            return

        if self._ping_pong:
            if new_time >= max_time:
                overflow = (new_time - max_time) % (2 * span)
                if overflow <= span:
                    new_time = max_time - overflow
                    self._reverse = True
                else:
                    new_time = min_time + overflow - span
                    self._reverse = False
            elif new_time <= min_time:
                overflow = (min_time - new_time) % (2 * span)
                if overflow <= span:
                    new_time = min_time + overflow
                    self._reverse = False
                else:
                    new_time = max_time - overflow + span
                    self._reverse = True
        elif self._loop:
            if new_time > max_time:
                new_time = min_time + ((new_time - min_time) % span)
            elif new_time < min_time:
                new_time = max_time - ((min_time - new_time) % span)
        else:
            if new_time >= max_time:
                new_time = max_time
                self.pause()
            elif new_time <= min_time:
                new_time = min_time

        self.set_time(new_time)

    def _on_timer_tick(self) -> None:
        now = monotonic()
        delta = now - self._last_tick_time
        self._last_tick_time = now
        # Bound delta to prevent large jumps on UI stalls
        clamped_delta = min(0.2, max(0.0, delta))
        self.advance(clamped_delta)

    def _apply_sliders_at_time(self, norm_t: float) -> None:
        """Interpolate all eligible sliders at normalized timeline position norm_t."""
        all_sliders = [obj for obj in self._document.objects.values() if obj.kind == "number"]
        if not all_sliders:
            return

        target_sliders = (
            [obj for obj in all_sliders if obj.id in self._active_slider_ids]
            if self._active_slider_ids
            else all_sliders
        )

        for obj in target_sliders:
            spec = slider_spec(obj)
            # Evaluate slider fraction based on slider individual ping-pong/speed if desired,
            # or sweep linearly across its [minimum, maximum] range across markers
            span = max(1e-9, self._end_marker - self._start_marker)
            relative_t = max(0.0, min(1.0, (norm_t - self._start_marker) / span))

            # If slider has individual ping_pong param, ping-pong its fraction
            is_ping_pong = obj.params.get("ping_pong", False) is True
            fraction = relative_t
            if is_ping_pong:
                # 0 -> 1 -> 0
                fraction = 2.0 * relative_t if relative_t <= 0.5 else 2.0 * (1.0 - relative_t)

            val = spec.minimum + fraction * (spec.maximum - spec.minimum)
            snapped = spec.snapped(val)
            if not math.isclose(snapped, spec.value, abs_tol=1e-9):
                params = slider_params(obj, snapped)
                self._document.update(obj.id, params=params)
