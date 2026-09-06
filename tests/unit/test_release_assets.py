"""Regression tests for release metadata and the bundled demonstration project."""

from pathlib import Path

from pygeolab import __version__
from pygeolab.persistence import load_project

ROOT = Path(__file__).resolve().parents[2]


def test_release_version_and_demo_project() -> None:
    assert __version__ == "1.0.0"
    demo = load_project(ROOT / "examples" / "demo.pgl")
    assert demo.name == "Démo PyGeoLab 1.0"
    assert {obj.name for obj in demo.objects.values()} >= {
        "A",
        "B",
        "C",
        "Triangle",
        "M",
        "c",
        "a",
        "f",
    }
    function = next(obj for obj in demo.objects.values() if obj.name == "f")
    assert function.valid


def test_release_build_assets_are_present() -> None:
    required = (
        ROOT / "packaging" / "pygeolab.spec",
        ROOT / "scripts" / "build-windows.ps1",
        ROOT / "scripts" / "build-linux.sh",
        ROOT / "assets" / "pygeolab.ico",
        ROOT / "assets" / "pygeolab.png",
        ROOT / ".github" / "workflows" / "release.yml",
        ROOT / "CHANGELOG.md",
    )
    assert all(path.is_file() and path.stat().st_size > 0 for path in required)
