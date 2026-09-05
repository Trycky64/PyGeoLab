"""Validated visual metadata, represented as plain values without Qt dependencies."""

import math
import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Style:
    """Portable object appearance using hexadecimal RGB colors and pixel sizes."""

    color: str = "#2563eb"
    width: float = 2.0
    point_size: float = 5.0
    line_style: str = "solid"
    show_label: bool = True
    fill_opacity: float = 0.12

    def __post_init__(self) -> None:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", self.color):
            raise ValueError("Couleur attendue au format #RRGGBB")
        if not math.isfinite(self.width) or not 0.5 <= self.width <= 20:
            raise ValueError("Épaisseur attendue entre 0.5 et 20")
        if not math.isfinite(self.point_size) or not 1 <= self.point_size <= 30:
            raise ValueError("Taille attendue entre 1 et 30")
        if self.line_style not in {"solid", "dash", "dot"}:
            raise ValueError("Style de ligne inconnu")
        if not math.isfinite(self.fill_opacity) or not 0 <= self.fill_opacity <= 1:
            raise ValueError("Opacité attendue entre 0 et 1")
