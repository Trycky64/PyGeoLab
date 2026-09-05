"""Load, validate and reconstruct versioned PyGeoLab projects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject
from pygeolab.model.styles import Style
from pygeolab.persistence.migrations import migrate
from pygeolab.persistence.serializer import serialize_document
from pygeolab.persistence.validation import validate_project


def document_from_mapping(raw: dict[str, Any]) -> Document:
    """Validate and reconstruct a complete document with dependencies restored atomically."""
    data = validate_project(migrate(raw))
    payload = data["document"]
    document = Document(payload["name"])
    document.metadata = dict(payload.get("metadata", {}))
    document.scene = dict(payload.get("scene", {}))
    objects = []
    for item in payload["objects"]:
        style = Style(**item.get("style", {}))
        objects.append(
            GeoObject(
                item["kind"],
                item["name"],
                tuple(item.get("dependencies", [])),
                item.get("params", {}),
                item["id"],
                item.get("visible", True),
                item.get("locked", False),
                style,
            )
        )
    document.restore(objects)
    return document


def load_project(path: str | Path) -> Document:
    """Read UTF-8 JSON from disk and reconstruct a validated document."""
    project_path = Path(path)
    try:
        raw = json.loads(project_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Impossible de lire le projet : {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("Le projet doit être un objet JSON")
    return document_from_mapping(raw)


def save_project(document: Document, path: str | Path) -> Path:
    """Write canonical pretty UTF-8 JSON atomically using a sibling temporary file."""
    project_path = Path(path)
    if project_path.suffix.lower() != ".pgl":
        project_path = project_path.with_suffix(".pgl")
    project_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = project_path.with_suffix(project_path.suffix + ".tmp")
    text = json.dumps(serialize_document(document), ensure_ascii=False, indent=2, sort_keys=True)
    try:
        temporary.write_text(text + "\n", encoding="utf-8")
        temporary.replace(project_path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise ValueError(f"Impossible d'enregistrer le projet : {exc}") from exc
    return project_path
