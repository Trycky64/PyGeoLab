"""Bound the five measured v1.1 performance scenarios."""

from benchmarks.benchmark_core import REGRESSION_LIMITS_MS, run_all


def test_release_gate_performance_scenarios_stay_below_regression_limits() -> None:
    results = run_all()

    assert REGRESSION_LIMITS_MS.keys() <= results.keys()
    regressions = {
        name: (results[name], limit)
        for name, limit in REGRESSION_LIMITS_MS.items()
        if results[name] >= limit
    }
    assert not regressions
