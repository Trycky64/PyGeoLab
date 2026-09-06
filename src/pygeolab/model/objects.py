"""Stable logical object identities and serializable construction definitions.

Definitions reference parents by UUID, never by their display name. Computed
geometry and validity are replaceable caches and are excluded from persistence.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from uuid import UUID, uuid4

from pygeolab.geometry import Circle2D, Line2D, Point2D, Polygon2D, Ray2D, Segment2D, Vector2D
from pygeolab.math_engine.functions import FunctionObject
from pygeolab.model.styles import Style

type JsonValue = (
    None
    | bool
    | int
    | float
    | str
    | list[JsonValue]
    | tuple[JsonValue, ...]
    | Mapping[str, JsonValue]
)
type Geometry = (
    Point2D
    | Vector2D
    | Line2D
    | Segment2D
    | Ray2D
    | Circle2D
    | Polygon2D
    | FunctionObject
    | float
)

KINDS = frozenset(
    {
        "point",
        "segment",
        "line",
        "ray",
        "vector",
        "circle",
        "circle_radius",
        "circumcircle",
        "polygon",
        "midpoint",
        "intersection",
        "parallel",
        "perpendicular",
        "perpendicular_bisector",
        "angle_bisector",
        "projection",
        "distance",
        "angle",
        "translate",
        "rotate",
        "reflect_point",
        "reflect_line",
        "scale",
        "point_on",
        "number",
        "function",
    }
)


@dataclass(frozen=True, slots=True)
class GeoObject:
    """A construction definition with stable UUID and transient evaluated state.

    The document replaces values after edits. Parameters are recursively frozen
    so every edit must go through Document.update and notify dependents and views.
    """

    kind: str
    name: str
    dependencies: tuple[str, ...] = ()
    params: Mapping[str, JsonValue] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    visible: bool = True
    locked: bool = False
    style: Style = field(default_factory=Style)
    valid: bool = True
    error_state: str | None = None
    geometry: Geometry | None = None
    revision: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "params",
            MappingProxyType({key: freeze_json(value) for key, value in self.params.items()}),
        )
        UUID(self.id)
        if self.kind not in KINDS:
            raise ValueError(f"Type d'objet inconnu : {self.kind}")
        if not self.name.strip() or len(self.name) > 100:
            raise ValueError("Le nom doit contenir entre 1 et 100 caractères")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("Une dépendance ne peut être répétée")

    @property
    def movable(self) -> bool:
        """Only unlocked free points may follow a mouse drag."""
        return self.kind == "point" and not self.dependencies and not self.locked


def freeze_json(value: JsonValue) -> JsonValue:
    """Copy and recursively freeze JSON containers while preserving scalar values."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze_json(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(freeze_json(item) for item in value)
    return value


def number(params: Mapping[str, JsonValue], key: str, default: float | None = None) -> float:
    """Read a finite scalar without accepting JSON booleans as numbers."""
    import math

    value = params.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Paramètre numérique invalide : {key}")
    return float(value)
