"""Directed acyclic graph utilities for stable object dependency identities."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping


class DependencyGraph:
    """Store parent/child relations and provide deterministic graph traversals."""

    def __init__(self, nodes: Iterable[str] = ()) -> None:
        self._parents: dict[str, set[str]] = {}
        self._children: dict[str, set[str]] = {}
        for node in nodes:
            self.add_node(node)

    @classmethod
    def from_dependencies(cls, dependencies: Mapping[str, Iterable[str]]) -> DependencyGraph:
        """Build a graph where each mapping value lists the parents of its key."""
        graph = cls(dependencies)
        for child, parents in dependencies.items():
            for parent in parents:
                if parent not in graph:
                    graph.add_node(parent)
                graph.add_dependency(child, parent)
        return graph

    def __contains__(self, node: object) -> bool:
        return isinstance(node, str) and node in self._parents

    def __len__(self) -> int:
        return len(self._parents)

    @property
    def nodes(self) -> tuple[str, ...]:
        """Return graph identities in insertion order."""
        return tuple(self._parents)

    def add_node(self, node: str) -> None:
        """Register a node when absent without altering existing relations."""
        self._parents.setdefault(node, set())
        self._children.setdefault(node, set())

    def remove_node(self, node: str) -> None:
        """Remove one node and every incident edge."""
        if node not in self._parents:
            raise KeyError(node)
        for parent in tuple(self._parents[node]):
            self._children[parent].remove(node)
        for child in tuple(self._children[node]):
            self._parents[child].remove(node)
        del self._parents[node]
        del self._children[node]

    def add_dependency(self, child: str, parent: str) -> None:
        """Add parent -> child, refusing missing nodes, duplicates and cycles."""
        if child not in self._parents or parent not in self._parents:
            missing = child if child not in self._parents else parent
            raise KeyError(missing)
        if child == parent or child in self.ancestors(parent):
            raise ValueError("Une dépendance cyclique est interdite")
        self._parents[child].add(parent)
        self._children[parent].add(child)

    def remove_dependency(self, child: str, parent: str) -> None:
        """Remove an existing parent -> child relation."""
        if child not in self._parents or parent not in self._parents:
            missing = child if child not in self._parents else parent
            raise KeyError(missing)
        if parent not in self._parents[child]:
            raise ValueError("La dépendance demandée n'existe pas")
        self._parents[child].remove(parent)
        self._children[parent].remove(child)

    def parents_of(self, node: str) -> frozenset[str]:
        """Return the direct parents of a registered node."""
        return frozenset(self._parents[node])

    def children_of(self, node: str) -> frozenset[str]:
        """Return the direct children of a registered node."""
        return frozenset(self._children[node])

    def descendants(self, roots: Iterable[str], *, include_roots: bool = True) -> set[str]:
        """Return every node reachable through child edges from the supplied roots."""
        root_set = set(roots)
        unknown = root_set.difference(self._parents)
        if unknown:
            raise KeyError(next(iter(unknown)))
        result = set(root_set) if include_roots else set()
        seen = set(root_set)
        pending = list(root_set)
        while pending:
            current = pending.pop()
            for child in self._children[current]:
                if child not in seen:
                    seen.add(child)
                    result.add(child)
                    pending.append(child)
        return result

    def ancestors(self, roots: str | Iterable[str], *, include_roots: bool = False) -> set[str]:
        """Return every node reachable through parent edges from one or more roots."""
        root_set = {roots} if isinstance(roots, str) else set(roots)
        unknown = root_set.difference(self._parents)
        if unknown:
            raise KeyError(next(iter(unknown)))
        result = set(root_set) if include_roots else set()
        seen = set(root_set)
        pending = list(root_set)
        while pending:
            current = pending.pop()
            for parent in self._parents[current]:
                if parent not in seen:
                    seen.add(parent)
                    result.add(parent)
                    pending.append(parent)
        return result

    def topological_order(self, subset: Iterable[str] | None = None) -> tuple[str, ...]:
        """Return a deterministic topological order, optionally restricted to a subset."""
        selected = set(self._parents) if subset is None else set(subset)
        unknown = selected.difference(self._parents)
        if unknown:
            raise KeyError(next(iter(unknown)))
        indegree = {
            node: sum(parent in selected for parent in self._parents[node]) for node in selected
        }
        pending = deque(node for node in self._parents if node in selected and indegree[node] == 0)
        ordered: list[str] = []
        while pending:
            node = pending.popleft()
            ordered.append(node)
            for child in self._children[node]:
                if child not in selected:
                    continue
                indegree[child] -= 1
                if indegree[child] == 0:
                    pending.append(child)
        if len(ordered) != len(selected):
            raise ValueError("Une dépendance cyclique est interdite")
        return tuple(ordered)
