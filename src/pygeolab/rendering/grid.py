"""Adaptive world-grid layout independent of Qt painting details."""

from __future__ import annotations

import math
from dataclasses import dataclass

from pygeolab.rendering.viewport import Viewport


@dataclass(frozen=True, slots=True)
class GridLayout:
    """World coordinates of visible minor grid lines plus the selected step."""

    step: float
    vertical: tuple[float, ...]
    horizontal: tuple[float, ...]


def adaptive_step(scale: float, target_pixels: float = 80.0) -> float:
    """Choose a 1/2/5 × 10^n step whose screen spacing is near the target."""
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("L'échelle doit être positive et finie")
    if not math.isfinite(target_pixels) or target_pixels <= 0:
        raise ValueError("L'espacement cible doit être positif et fini")
    raw = target_pixels / scale
    exponent = math.floor(math.log10(raw))
    base = 10.0**exponent
    normalized = raw / base
    if normalized <= 1.0:
        multiplier = 1.0
    elif normalized <= 2.0:
        multiplier = 2.0
    elif normalized <= 5.0:
        multiplier = 5.0
    else:
        multiplier = 10.0
    return multiplier * base


def adaptive_grid(viewport: Viewport, target_pixels: float = 80.0) -> GridLayout:
    """Generate all visible grid coordinates at an adaptive stable decimal step."""
    step = adaptive_step(viewport.scale, target_pixels)
    left, bottom, right, top = viewport.world_bounds
    first_x = math.ceil(left / step)
    last_x = math.floor(right / step)
    first_y = math.ceil(bottom / step)
    last_y = math.floor(top / step)
    vertical = tuple(index * step for index in range(first_x, last_x + 1))
    horizontal = tuple(index * step for index in range(first_y, last_y + 1))
    return GridLayout(step=step, vertical=vertical, horizontal=horizontal)


class GridCache:
    """Cache adaptive grid geometry until camera dimensions, center or scale changes."""

    def __init__(self) -> None:
        self._key: tuple[float, float, float, int, int] | None = None
        self._layout: GridLayout | None = None

    def get(self, viewport: Viewport) -> GridLayout:
        """Return a cached layout for an identical viewport or compute a new one."""
        key = (
            viewport.center.x,
            viewport.center.y,
            viewport.scale,
            viewport.width,
            viewport.height,
        )
        if self._key != key or self._layout is None:
            self._key = key
            self._layout = adaptive_grid(viewport)
        return self._layout

    def clear(self) -> None:
        """Invalidate any stored grid geometry."""
        self._key = None
        self._layout = None
