"""Function definitions backed by the safe expression AST."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from pygeolab.math_engine.ast_nodes import Expr
from pygeolab.math_engine.evaluator import dependencies, evaluate
from pygeolab.math_engine.parser import parse


@dataclass(frozen=True, slots=True)
class FunctionObject:
    """Named single-variable mathematical function with optional closed domain."""

    name: str
    variable: str
    expression: Expr
    external_dependencies: frozenset[str]
    domain: tuple[float, float] | None = None

    @classmethod
    def from_source(
        cls, name: str, variable: str, source: str, domain: tuple[float, float] | None = None
    ) -> FunctionObject:
        """Parse source and derive external variable dependencies."""
        if not name.strip() or not variable.isidentifier():
            raise ValueError("Nom de fonction ou variable invalide")
        if domain is not None and (not all(math.isfinite(v) for v in domain) or domain[0] >= domain[1]):
            raise ValueError("Domaine invalide")
        expression = parse(source)
        return cls(name, variable, expression, dependencies(expression) - {variable}, domain)

    def evaluate(self, value: float, variables: Mapping[str, float] | None = None) -> float:
        """Evaluate the function at one finite primary-variable value."""
        if not math.isfinite(value):
            raise ValueError("La variable principale doit être finie")
        if self.domain is not None and not self.domain[0] <= value <= self.domain[1]:
            raise ValueError("Valeur hors du domaine de la fonction")
        scope = dict(variables or {})
        scope[self.variable] = value
        return evaluate(self.expression, scope)
