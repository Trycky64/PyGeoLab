"""Numeric variable definitions backed by document number objects."""

from __future__ import annotations

import math
from dataclasses import dataclass

from pygeolab.model.objects import GeoObject, JsonValue, number


@dataclass(frozen=True, slots=True)
class SliderSpec:
    """Validated numeric slider bounds, value and increment."""

    value: float
    minimum: float
    maximum: float
    step: float

    def __post_init__(self) -> None:
        values = (self.value, self.minimum, self.maximum, self.step)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Les valeurs du curseur doivent être finies")
        if self.minimum >= self.maximum:
            raise ValueError("Le minimum doit être inférieur au maximum")
        if self.step <= 0:
            raise ValueError("Le pas doit être strictement positif")
        if not self.minimum <= self.value <= self.maximum:
            raise ValueError("La valeur doit appartenir aux bornes du curseur")

    def snapped(self, value: float) -> float:
        """Clamp and snap a candidate value to the nearest configured step."""
        if not math.isfinite(value):
            raise ValueError("La valeur doit être finie")
        clamped = min(self.maximum, max(self.minimum, value))
        index = round((clamped - self.minimum) / self.step)
        snapped = self.minimum + index * self.step
        return min(self.maximum, max(self.minimum, snapped))


def numeric_variable(
    name: str,
    value: float = 0.0,
    minimum: float = -10.0,
    maximum: float = 10.0,
    step: float = 0.1,
) -> GeoObject:
    """Create a serializable number object carrying slider metadata."""
    spec = SliderSpec(value, minimum, maximum, step)
    return GeoObject(
        "number",
        name,
        params={
            "value": spec.value,
            "minimum": spec.minimum,
            "maximum": spec.maximum,
            "step": spec.step,
        },
    )


def slider_spec(obj: GeoObject) -> SliderSpec:
    """Read slider metadata from a number object and validate it."""
    if obj.kind != "number":
        raise ValueError("Un objet numérique est attendu")
    return SliderSpec(
        number(obj.params, "value"),
        number(obj.params, "minimum", -10.0),
        number(obj.params, "maximum", 10.0),
        number(obj.params, "step", 0.1),
    )


def slider_params(obj: GeoObject, value: float) -> dict[str, JsonValue]:
    """Return complete updated number parameters after clamping and snapping value."""
    spec = slider_spec(obj)
    params = dict(obj.params)
    params["value"] = spec.snapped(value)
    return params
