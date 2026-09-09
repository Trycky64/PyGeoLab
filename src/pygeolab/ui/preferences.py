"""Central persistent desktop preferences backed by QSettings."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor


@dataclass(frozen=True, slots=True)
class Preferences:
    """Validated settings for appearance, interaction, creation, export and recovery."""

    theme_mode: str = "system"
    show_grid: bool = True
    show_axes: bool = True
    show_labels: bool = True
    snapping_enabled: bool = True
    snap_threshold_px: float = 10.0
    default_width: float = 2.0
    default_point_size: float = 5.0
    default_color: str = "#2563eb"
    export_scale: float = 1.0
    transparent_export: bool = False
    autosave_enabled: bool = True
    autosave_interval_minutes: int = 2

    def __post_init__(self) -> None:
        if self.theme_mode not in {"system", "light", "dark"}:
            raise ValueError("Thème inconnu")
        if not 1 <= self.snap_threshold_px <= 100:
            raise ValueError("Taille de snap invalide")
        if not 0.25 <= self.default_width <= 20:
            raise ValueError("Épaisseur par défaut invalide")
        if not 1 <= self.default_point_size <= 40:
            raise ValueError("Taille de point par défaut invalide")
        if not QColor(self.default_color).isValid():
            raise ValueError("Couleur par défaut invalide")
        if not 0.25 <= self.export_scale <= 8:
            raise ValueError("Qualité d'export invalide")
        if not 1 <= self.autosave_interval_minutes <= 60:
            raise ValueError("Intervalle d'autosave invalide")

    @property
    def dark_theme(self) -> bool:
        """Retain the former read-only convenience flag for callers."""
        return self.theme_mode == "dark"

    @classmethod
    def load(cls, settings: QSettings | None = None) -> Preferences:
        """Read every setting with bounded fallbacks and legacy-theme migration."""
        store = settings if settings is not None else QSettings()
        legacy_dark = _read_bool(store, "appearance/dark_theme", False)
        theme = store.value("appearance/theme", "dark" if legacy_dark else "system")
        theme_mode = (
            theme if isinstance(theme, str) and theme in {"system", "light", "dark"} else "system"
        )
        color = store.value("creation/color", "#2563eb")
        default_color = color if isinstance(color, str) and QColor(color).isValid() else "#2563eb"
        return cls(
            theme_mode=theme_mode,
            show_grid=_read_bool(store, "display/grid", True),
            show_axes=_read_bool(store, "display/axes", True),
            show_labels=_read_bool(store, "display/labels", True),
            snapping_enabled=_read_bool(store, "interaction/snapping", True),
            snap_threshold_px=_read_float(store, "interaction/snap_threshold_px", 10, 1, 100),
            default_width=_read_float(store, "creation/width", 2, 0.25, 20),
            default_point_size=_read_float(store, "creation/point_size", 5, 1, 40),
            default_color=default_color,
            export_scale=_read_float(store, "export/scale", 1, 0.25, 8),
            transparent_export=_read_bool(store, "export/transparent", False),
            autosave_enabled=_read_bool(store, "files/autosave_enabled", True),
            autosave_interval_minutes=_read_int(store, "files/autosave_interval_minutes", 2, 1, 60),
        )

    def save(self, settings: QSettings | None = None) -> None:
        """Persist the complete preference set through one settings store."""
        store = settings if settings is not None else QSettings()
        values: dict[str, object] = {
            "appearance/theme": self.theme_mode,
            "display/grid": self.show_grid,
            "display/axes": self.show_axes,
            "display/labels": self.show_labels,
            "interaction/snapping": self.snapping_enabled,
            "interaction/snap_threshold_px": self.snap_threshold_px,
            "creation/width": self.default_width,
            "creation/point_size": self.default_point_size,
            "creation/color": self.default_color,
            "export/scale": self.export_scale,
            "export/transparent": self.transparent_export,
            "files/autosave_enabled": self.autosave_enabled,
            "files/autosave_interval_minutes": self.autosave_interval_minutes,
        }
        for key, value in values.items():
            store.setValue(key, value)
        store.sync()

    @classmethod
    def reset(cls, settings: QSettings | None = None) -> Preferences:
        """Restore and persist all documented defaults."""
        preferences = cls()
        preferences.save(settings)
        return preferences


def _read_bool(settings: QSettings, key: str, default: bool) -> bool:
    value = settings.value(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.strip().lower() in {"1", "true", "yes", "on"}:
            return True
        if value.strip().lower() in {"0", "false", "no", "off"}:
            return False
    return default


def _read_float(
    settings: QSettings, key: str, default: float, minimum: float, maximum: float
) -> float:
    value = settings.value(key, default)
    try:
        parsed = (
            float(value)
            if isinstance(value, (int, float, str)) and not isinstance(value, bool)
            else default
        )
    except ValueError:
        parsed = default
    return min(maximum, max(minimum, parsed))


def _read_int(settings: QSettings, key: str, default: int, minimum: int, maximum: int) -> int:
    return round(_read_float(settings, key, default, minimum, maximum))
