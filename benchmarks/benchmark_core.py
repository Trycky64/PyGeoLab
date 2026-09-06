"""Small repeatable core benchmarks runnable without pytest-benchmark or Qt."""

from __future__ import annotations

import time

from pygeolab.geometry import Point2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject


def benchmark_document(size: int = 500) -> dict[str, float]:
    """Measure bulk insertion and one incremental point update in milliseconds."""
    document = Document("Benchmark")
    points = tuple(
        GeoObject("point", f"P{index}", params={"x": float(index), "y": 0.0})
        for index in range(size)
    )
    started = time.perf_counter()
    document.restore(points)
    restore_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    document.move_point(points[0].id, Point2D(-1.0, 1.0))
    update_ms = (time.perf_counter() - started) * 1000
    return {"restore_ms": restore_ms, "incremental_update_ms": update_ms}


if __name__ == "__main__":
    for key, value in benchmark_document().items():
        print(f"{key}: {value:.3f} ms")
