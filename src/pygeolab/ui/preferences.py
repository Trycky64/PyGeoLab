"""Persistent desktop preferences backed by Qt's platform-native settings store."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings


@dataclass(frozen=True, slots=True)
class Preferences:
    """Small stable set of user preferences used by the desktop shell."""

    dark_theme: bool = False
    export_scale: float = 1.0
    transparent_export: bool = False
    autosave_enabled: bool = True
    autosave_interval_minutes: int = 2

    @classmethod
    def load(cls) -> Preferences:
        """Read preferences and safely coerce values from QSettings."""
        settings = QSettings()
        scale_value = settings.value("export/scale", 1.0)
        if isinstance(scale_value, bool) or not isinstance(scale_value, (int, float, str)):
            scale = 1.0
        else:
            try:
                scale = float(scale_value)
            except ValueError:
                scale = 1.0
        return cls(
            dark_theme=_read_bool(settings, "appearance/dark_theme", False),
            export_scale=min(8.0, max(0.25, scale)),
            transparent_export=_read_bool(settings, "export/transparent", False),
            autosave_enabled=_read_bool(settings, "files/autosave_enabled", True),
            autosave_interval_minutes=_read_int(
                settings, "files/autosave_interval_minutes", 2, 1, 60
            ),
        )

    def save(self) -> None:
        """Persist all preferences atomically through Qt's settings backend."""
        settings = QSettings()
        settings.setValue("appearance/dark_theme", self.dark_theme)
        settings.setValue("export/scale", self.export_scale)
        settings.setValue("export/transparent", self.transparent_export)
        settings.setValue("files/autosave_enabled", self.autosave_enabled)
        settings.setValue("files/autosave_interval_minutes", self.autosave_interval_minutes)
        settings.sync()


def _read_bool(settings: QSettings, key: str, default: bool) -> bool:
    """Read a boolean QSettings value without relying on loosely typed Qt stubs."""
    value = settings.value(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _read_int(settings: QSettings, key: str, default: int, minimum: int, maximum: int) -> int:
    """Read and clamp one integer preference."""
    value = settings.value(key, default)
    try:
        parsed = (
            int(value)
            if isinstance(value, (int, float, str)) and not isinstance(value, bool)
            else default
        )
    except (TypeError, ValueError):
        parsed = default
    return min(maximum, max(minimum, parsed))
