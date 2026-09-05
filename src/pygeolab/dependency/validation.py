"""Structural validation for document objects before a mutation is committed."""

from collections.abc import Mapping

from pygeolab.dependency.graph import DependencyGraph
from pygeolab.model.objects import GeoObject


def validate_object_graph(objects: Mapping[str, GeoObject]) -> DependencyGraph:
    """Validate identities, names and dependencies and return the resulting DAG."""
    names: set[str] = set()
    dependencies: dict[str, tuple[str, ...]] = {}
    for key, obj in objects.items():
        if key != obj.id:
            raise ValueError("L'identité d'un objet ne peut pas changer")
        if not obj.name.strip() or obj.name in names:
            raise ValueError(f"Nom vide ou déjà utilisé : {obj.name}")
        names.add(obj.name)
        dependencies[key] = obj.dependencies
        for parent in obj.dependencies:
            if parent not in objects:
                raise ValueError(f"Dépendance introuvable : {parent}")

    graph = DependencyGraph.from_dependencies(dependencies)
    graph.topological_order()
    return graph
