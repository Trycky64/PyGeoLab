"""Safe evaluator and dependency extraction for PyGeoLab expression ASTs."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping

from pygeolab.math_engine.ast_nodes import Binary, Call, Expr, Number, Unary, Variable

_ALLOWED_FUNCTIONS: Mapping[str, Callable[..., float]] = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sqrt": math.sqrt,
    "abs": abs,
    "exp": math.exp,
    "ln": math.log,
    "log10": math.log10,
    "floor": math.floor,
    "ceil": math.ceil,
    "min": min,
    "max": max,
}
CONSTANTS: Mapping[str, float] = {"pi": math.pi, "e": math.e}


class EvaluationError(ValueError):
    """Raised for unknown names, invalid operations or non-finite results."""


def evaluate(expression: Expr, variables: Mapping[str, float] | None = None) -> float:
    """Evaluate only internal AST nodes and whitelisted mathematical operations."""
    scope = variables or {}
    try:
        result = _evaluate(expression, scope)
    except EvaluationError:
        raise
    except (ArithmeticError, ValueError, OverflowError) as exc:
        raise EvaluationError(str(exc) or "Erreur d'évaluation") from exc
    if not math.isfinite(result):
        raise EvaluationError("Le résultat n'est pas fini")
    return float(result)


def _evaluate(expression: Expr, variables: Mapping[str, float]) -> float:
    if isinstance(expression, Number):
        return expression.value
    if isinstance(expression, Variable):
        if expression.name in variables:
            value = variables[expression.name]
        elif expression.name in CONSTANTS:
            value = CONSTANTS[expression.name]
        else:
            raise EvaluationError(f"Variable inconnue : {expression.name}")
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise EvaluationError(f"Valeur invalide pour {expression.name}")
        return float(value)
    if isinstance(expression, Unary):
        value = _evaluate(expression.operand, variables)
        return value if expression.operator == "+" else -value
    if isinstance(expression, Binary):
        left = _evaluate(expression.left, variables)
        right = _evaluate(expression.right, variables)
        if expression.operator == "+":
            return left + right
        if expression.operator == "-":
            return left - right
        if expression.operator == "*":
            return left * right
        if expression.operator == "/":
            return left / right
        if expression.operator == "^":
            return float(left**right)
        raise EvaluationError(f"Opérateur inconnu : {expression.operator}")
    if isinstance(expression, Call):
        function = _ALLOWED_FUNCTIONS.get(expression.name)
        if function is None:
            raise EvaluationError(f"Fonction interdite ou inconnue : {expression.name}")
        arguments = tuple(_evaluate(argument, variables) for argument in expression.arguments)
        try:
            return float(function(*arguments))
        except TypeError as exc:
            raise EvaluationError(f"Arguments invalides pour {expression.name}") from exc
    raise EvaluationError("Nœud d'expression inconnu")


def dependencies(expression: Expr) -> frozenset[str]:
    """Return variable names referenced by an AST, excluding built-in constants."""
    result: set[str] = set()
    stack = [expression]
    while stack:
        node = stack.pop()
        if isinstance(node, Variable):
            if node.name not in CONSTANTS:
                result.add(node.name)
        elif isinstance(node, Unary):
            stack.append(node.operand)
        elif isinstance(node, Binary):
            stack.extend((node.left, node.right))
        elif isinstance(node, Call):
            stack.extend(node.arguments)
    return frozenset(result)
