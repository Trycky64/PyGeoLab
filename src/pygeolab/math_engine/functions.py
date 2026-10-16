"""Function definitions backed by the safe expression AST."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from pygeolab.geometry.primitives import Point2D
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
        if domain is not None and (
            not all(math.isfinite(value) for value in domain) or domain[0] >= domain[1]
        ):
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


@dataclass(frozen=True, slots=True)
class ParametricFunctionObject:
    """Named parametric curve defined by x(t) and y(t) with closed parameter interval."""

    name: str
    parameter: str
    x_source: str
    y_source: str
    x_expression: Expr
    y_expression: Expr
    external_dependencies: frozenset[str]
    t_min: float
    t_max: float

    @classmethod
    def from_source(
        cls,
        name: str,
        parameter: str,
        x_source: str,
        y_source: str,
        t_min: float,
        t_max: float,
    ) -> ParametricFunctionObject:
        """Parse coordinate expressions and derive external variable dependencies."""
        if not name.strip() or not parameter.isidentifier():
            raise ValueError("Nom de courbe ou paramètre invalide")
        if not math.isfinite(t_min) or not math.isfinite(t_max) or t_min >= t_max:
            raise ValueError(
                "Domaine paramétrique invalide : t_min doit être strictement inférieur à t_max"
            )
        x_expr = parse(x_source)
        y_expr = parse(y_source)
        external = (dependencies(x_expr) | dependencies(y_expr)) - {parameter}
        return cls(
            name=name,
            parameter=parameter,
            x_source=x_source,
            y_source=y_source,
            x_expression=x_expr,
            y_expression=y_expr,
            external_dependencies=frozenset(external),
            t_min=float(t_min),
            t_max=float(t_max),
        )

    def evaluate(self, t: float, variables: Mapping[str, float] | None = None) -> Point2D:
        """Evaluate (x(t), y(t)) at one parameter value."""
        if not math.isfinite(t):
            raise ValueError("Le paramètre t doit être fini")
        if not (self.t_min - 1e-9 <= t <= self.t_max + 1e-9):
            raise ValueError("Paramètre t hors de l'intervalle défini")
        scope = dict(variables or {})
        scope[self.parameter] = t
        x = evaluate(self.x_expression, scope)
        y = evaluate(self.y_expression, scope)
        return Point2D(x, y)
