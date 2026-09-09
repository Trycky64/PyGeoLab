"""Regression tests for release metadata and the bundled demonstration project."""

import re
from pathlib import Path

from PySide6.QtGui import QImage

from pygeolab import __version__
from pygeolab.persistence import load_project

ROOT = Path(__file__).resolve().parents[2]


def test_release_version_and_demo_project() -> None:
    assert __version__ == "1.0.0"
    demo = load_project(ROOT / "examples" / "demo.pgl")
    assert demo.name == "Démo PyGeoLab 1.1"
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
    assert {obj.kind for obj in demo.objects.values()} >= {
        "vector",
        "translate",
        "length",
        "area",
    }
    slider = next(obj for obj in demo.objects.values() if obj.name == "a")
    assert {"initial", "animation_speed", "ping_pong"} <= slider.params.keys()


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


def test_ci_release_gate_covers_supported_pythons_platforms_builds_and_artifacts() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert 'python: ["3.12", "3.13", "3.14"]' in workflow
    assert "os: [ubuntu-latest, windows-latest]" in workflow
    assert "python -m pytest" in workflow
    assert "python -m PyInstaller" in workflow
    assert "--smoke-test" in workflow
    assert "actions/upload-artifact@v4" in workflow


def test_v11_documentation_links_adrs_and_screenshot_are_coherent() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    local_links = re.findall(r"\[[^]]+\]\(([^)]+)\)", readme)
    assert local_links
    assert all((ROOT / link).exists() for link in local_links if "://" not in link)

    decisions = (ROOT / "docs" / "29-decisions.md").read_text(encoding="utf-8")
    numbers = [int(value) for value in re.findall(r"^## ADR-(\d{3})", decisions, re.MULTILINE)]
    assert numbers == list(range(1, len(numbers) + 1))
    assert numbers[-1] == 34

    guide = (ROOT / "docs" / "30-user-guide-v11.md").read_text(encoding="utf-8")
    assert all(
        topic.casefold() in guide.casefold()
        for topic in ("Magnétisme", "Fonctions et curseurs", "Autosave", "Préférences", "F1")
    )
    screenshot = QImage(str(ROOT / "docs" / "screenshots" / "workspace-v11.png"))
    assert not screenshot.isNull()
    assert screenshot.width() >= 1000 and screenshot.height() >= 700
