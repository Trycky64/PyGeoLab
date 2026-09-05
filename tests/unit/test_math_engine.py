"""Verify parsing, safe evaluation, dependencies and discontinuity-aware sampling."""

import math

import pytest

from pygeolab.math_engine import (
    EvaluationError,
    FunctionObject,
    ParseError,
    evaluate,
    parse,
    sample_function,
    tokenize,
)


def test_tokenizer_and_precedence() -> None:
    assert len(tokenize("2*x + 1")) == 6
    assert evaluate(parse("2 + 3*4^2")) == 50
    assert evaluate(parse("-2^2")) == -4
    assert evaluate(parse("2^-2")) == pytest.approx(0.25)


def test_functions_constants_and_variables() -> None:
    expression = parse("sin(pi/2) + a*cos(0) + max(2, 3)")
    assert evaluate(expression, {"a": 4}) == pytest.approx(8)


def test_function_object_extracts_external_dependencies() -> None:
    function = FunctionObject.from_source("f", "x", "a*x + b + pi")
    assert function.external_dependencies == frozenset({"a", "b"})
    assert function.evaluate(3, {"a": 2, "b": 1}) == pytest.approx(7 + math.pi)


@pytest.mark.parametrize("source", ["", "1;2", "x.__class__", "[1]", "lambda x:x", "sin("])
def test_parser_rejects_python_or_invalid_syntax(source: str) -> None:
    with pytest.raises((ParseError, ValueError)):
        parse(source)


def test_unknown_names_and_functions_are_never_executed() -> None:
    with pytest.raises(EvaluationError):
        evaluate(parse("__import__(x)"), {"x": 1})
    with pytest.raises(EvaluationError):
        evaluate(parse("secret + 1"))


def test_domain_and_invalid_operations_report_errors() -> None:
    function = FunctionObject.from_source("f", "x", "sqrt(x)", (0, 5))
    with pytest.raises(ValueError):
        function.evaluate(-1)
    with pytest.raises(EvaluationError):
        evaluate(parse("1/0"))


def test_sampling_splits_asymptote_and_domain() -> None:
    function = FunctionObject.from_source("f", "x", "1/x")
    sampled = sample_function(function, -1, 1, samples=201)
    assert len(sampled.segments) >= 2
    assert all(len(segment) >= 2 for segment in sampled.segments)
    bounded = FunctionObject.from_source("g", "x", "x^2", (-1, 1))
    points = [
        point
        for segment in sample_function(bounded, -5, 5, samples=21).segments
        for point in segment
    ]
    assert points and min(p.x for p in points) >= -1 and max(p.x for p in points) <= 1
