"""Pure world/screen coordinate transforms used by rendering and interaction."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from pygeolab.geometry import Point2D

MIN_SCALE = 1e-4
MAX_SCALE = 1e7


@dataclass(frozen=True, slots=True)
class Viewport:
    """Describe a 2D camera with a world center and pixels-per-world-unit scale."""

    center: Point2D = Point2D(0.0, 0.0)
    scale: float = 80.0
    width: int = 1
    height: int = 1

    def __post_init__(self) -> None:
        if not math.isfinite(self.scale) or not MIN_SCALE <= self.scale <= MAX_SCALE:
            raise ValueError("Zoom de viewport invalide")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Le viewport nécessite des dimensions positives")

    def world_to_screen(self, point: Point2D) -> tuple[float, float]:
        """Convert mathematical coordinates to screen pixels with an inverted Y axis."""
        return (
            self.width / 2 + (point.x - self.center.x) * self.scale,
            self.height / 2 - (point.y - self.center.y) * self.scale,
        )

    def screen_to_world(self, x: float, y: float) -> Point2D:
        """Convert screen pixels back to mathematical world coordinates."""
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("Les coordonnées écran doivent être finies")
        return Point2D(
            self.center.x + (x - self.width / 2) / self.scale,
            self.center.y - (y - self.height / 2) / self.scale,
        )

    @property
    def world_bounds(self) -> tuple[float, float, float, float]:
        """Return visible left, bottom, right and top world coordinates."""
        half_width = self.width / (2 * self.scale)
        half_height = self.height / (2 * self.scale)
        return (
            self.center.x - half_width,
            self.center.y - half_height,
            self.center.x + half_width,
            self.center.y + half_height,
        )

    def resized(self, width: int, height: int) -> Viewport:
        """Return the same camera using new positive screen dimensions."""
        return replace(self, width=max(1, width), height=max(1, height))

    def panned_pixels(self, dx: float, dy: float) -> Viewport:
        """Pan as if the scene were dragged by a screen-space displacement."""
        if not math.isfinite(dx) or not math.isfinite(dy):
            raise ValueError("Le déplacement écran doit être fini")
        return replace(
            self,
            center=Point2D(self.center.x - dx / self.scale, self.center.y + dy / self.scale),
        )

    def zoomed_at(self, factor: float, screen_x: float, screen_y: float) -> Viewport:
        """Zoom around one cursor position while preserving the world point beneath it."""
        if not math.isfinite(factor) or factor <= 0:
            raise ValueError("Le facteur de zoom doit être positif et fini")
        anchor = self.screen_to_world(screen_x, screen_y)
        new_scale = min(MAX_SCALE, max(MIN_SCALE, self.scale * factor))
        center = Point2D(
            anchor.x - (screen_x - self.width / 2) / new_scale,
            anchor.y + (screen_y - self.height / 2) / new_scale,
        )
        return replace(self, center=center, scale=new_scale)
