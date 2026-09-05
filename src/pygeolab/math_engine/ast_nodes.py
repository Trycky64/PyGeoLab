"""Immutable AST nodes for safe mathematical expressions."""

from __future__ import annotations

from dataclasses import dataclass


class Expr:
    """Marker base class for expression nodes."""


@dataclass(frozen=True, slots=True)
class Number(Expr):
    """Literal finite floating-point number."""

    value: float


@dataclass(frozen=True, slots=True)
class Variable(Expr):
    """Named variable or constant reference."""

    name: str


@dataclass(frozen=True, slots=True)
class Unary(Expr):
    """Unary arithmetic operator."""

    operator: str
    operand: Expr


@dataclass(frozen=True, slots=True)
class Binary(Expr):
    """Binary arithmetic operator."""

    operator: str
    left: Expr
    right: Expr


@dataclass(frozen=True, slots=True)
class Call(Expr):
    """Call to one whitelisted mathematical function."""

    name: str
    arguments: tuple[Expr, ...]
