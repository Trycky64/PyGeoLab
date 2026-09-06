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

    @classmethod
    def load(cls) -> Preferences:
        """Read preferences and safely coerce values from QSettings."""
        settings = QSettings()
        scale = float(settings.value("export/scale", 1.0))
        return cls(
            dark_theme=settings.value("appearance/dark_theme", False, type=bool),
            export_scale=min(8.0, max(0.25, scale)),
            transparent_export=settings.value("export/transparent", False, type=bool),
        )

    def save(self) -> None:
        """Persist all preferences atomically through Qt's settings backend."""
        settings = QSettings()
        settings.setValue("appearance/dark_theme", self.dark_theme)
        settings.setValue("export/scale", self.export_scale)
        settings.setValue("export/transparent", self.transparent_export)
        settings.sync()
