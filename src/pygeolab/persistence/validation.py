"""Validate untrusted project mappings before model reconstruction."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from pygeolab.model.objects import KINDS
from pygeolab.model.styles import Style
from pygeolab.persistence.serializer import CURRENT_VERSION, FORMAT_NAME


def validate_project(data: object) -> dict[str, Any]:
    """Return a typed shallow copy after strict structural validation."""
    if not isinstance(data, dict):
        raise ValueError("Le projet doit être un objet JSON")
    if data.get("format") != FORMAT_NAME or data.get("version") != CURRENT_VERSION:
        raise ValueError("Format ou version .pgl invalide")
    document = data.get("document")
    if not isinstance(document, dict):
        raise ValueError("Section document manquante")
    name = document.get("name")
    objects = document.get("objects")
    metadata = document.get("metadata", {})
    scene = document.get("scene", {})
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Nom de document invalide")
    if not isinstance(objects, list):
        raise ValueError("Liste d'objets invalide")
    if not isinstance(metadata, dict) or not isinstance(scene, dict):
        raise ValueError("Métadonnées de document invalides")
    seen: set[str] = set()
    for raw in objects:
        _validate_object(raw, seen)
    known = set(seen)
    for raw in objects:
        assert isinstance(raw, dict)
        dependencies = raw.get("dependencies", [])
        if any(dependency not in known for dependency in dependencies):
            raise ValueError("Une dépendance référence un objet absent")
    return data


def _validate_object(raw: object, seen: set[str]) -> None:
    if not isinstance(raw, dict):
        raise ValueError("Définition d'objet invalide")
    object_id = raw.get("id")
    kind = raw.get("kind")
    name = raw.get("name")
    dependencies = raw.get("dependencies", [])
    params = raw.get("params", {})
    style = raw.get("style", {})
    if not isinstance(object_id, str):
        raise ValueError("Identifiant d'objet invalide")
    try:
        UUID(object_id)
    except ValueError as exc:
        raise ValueError("Identifiant UUID invalide") from exc
    if object_id in seen:
        raise ValueError("Identifiant d'objet dupliqué")
    seen.add(object_id)
    if kind not in KINDS or not isinstance(name, str):
        raise ValueError("Type ou nom d'objet invalide")
    if not isinstance(dependencies, list) or not all(
        isinstance(item, str) for item in dependencies
    ):
        raise ValueError("Dépendances invalides")
    if not isinstance(params, dict) or not _json_value(params):
        raise ValueError("Paramètres invalides")
    if not isinstance(raw.get("visible", True), bool) or not isinstance(
        raw.get("locked", False), bool
    ):
        raise ValueError("Drapeaux d'objet invalides")
    if not isinstance(style, dict):
        raise ValueError("Style invalide")
    try:
        Style(**style)
    except (TypeError, ValueError) as exc:
        raise ValueError("Style invalide") from exc


def _json_value(value: object) -> bool:
    if value is None or isinstance(value, (bool, int, str)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_json_value(item) for item in value)
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and _json_value(item) for key, item in value.items())
    return False
