"""Regression tests for release metadata and the bundled demonstration project."""

import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

from PySide6.QtGui import QImage

from pygeolab import __version__
from pygeolab.persistence import load_project

ROOT = Path(__file__).resolve().parents[2]


def test_release_version_and_demo_project() -> None:
    assert __version__ == "1.1.1"
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
        ROOT / "RELEASE_NOTES.md",
        ROOT / "README.fr.md",
        ROOT / "CHANGELOG.fr.md",
        ROOT / "RELEASE_NOTES.fr.md",
        ROOT / "packaging" / "io.github.trycky64.PyGeoLab.metainfo.xml",
        ROOT / "tests" / "fixtures" / "v1_0_project.pgl",
    )
    assert all(path.is_file() and path.stat().st_size > 0 for path in required)


def test_release_metadata_is_consistently_versioned() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == __version__ == "1.1.1"

    windows = (ROOT / "packaging" / "version_info.txt").read_text(encoding="utf-8")
    assert "filevers=(1, 1, 1, 0)" in windows
    assert "prodvers=(1, 1, 1, 0)" in windows
    assert windows.count("'1.1.1'") == 2

    metainfo_path = ROOT / "packaging" / "io.github.trycky64.PyGeoLab.metainfo.xml"
    metainfo = ET.parse(metainfo_path).getroot()
    assert metainfo.findtext("id") == "io.github.trycky64.PyGeoLab"
    assert metainfo.find("./releases/release").attrib["version"] == "1.1.1"

    assert "## 1.1.1 — 2026-09-09" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert (ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8").startswith("# PyGeoLab 1.1.1")


def test_release_tag_validator_accepts_only_the_project_version() -> None:
    script = ROOT / "scripts" / "check-release-tag.py"
    valid = subprocess.run(
        [sys.executable, str(script), "v1.1.1"], capture_output=True, text=True, check=False
    )
    invalid = subprocess.run(
        [sys.executable, str(script), "v9.9.9"], capture_output=True, text=True, check=False
    )

    assert valid.returncode == 0 and "matches v1.1.1" in valid.stdout
    assert invalid.returncode == 1 and "must be 'v1.1.1'" in invalid.stderr


def test_release_workflow_and_archives_use_stable_names_and_contents() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    windows_script = (ROOT / "scripts" / "build-windows.ps1").read_text(encoding="utf-8")
    linux_script = (ROOT / "scripts" / "build-linux.sh").read_text(encoding="utf-8")

    assert 'tags: ["v*"]' in workflow
    assert "check-release-tag.py" in workflow
    assert "PYGEOLAB_BUILD_ID: ${{ github.sha }}" in workflow
    assert "PyGeoLab-Windows-x64.zip" in workflow
    assert "PyGeoLab-Linux-x64.tar.gz" in workflow
    assert "body_path: RELEASE_NOTES.md" in workflow
    for required in (
        "LICENSE",
        "README.md",
        "README.fr.md",
        "CHANGELOG.md",
        "CHANGELOG.fr.md",
        "RELEASE_NOTES.md",
        "RELEASE_NOTES.fr.md",
    ):
        assert required in windows_script
        assert required in linux_script
    assert "pygeolab.ico" in windows_script
    assert "pygeolab.desktop" in linux_script
    assert "io.github.trycky64.PyGeoLab.metainfo.xml" in linux_script


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

    guide = (ROOT / "docs" / "user-guide.fr.md").read_text(encoding="utf-8")
    assert all(
        topic.casefold() in guide.casefold()
        for topic in ("Magnétisme", "Fonctions et curseurs", "Autosave", "Préférences", "F1")
    )
    screenshot = QImage(str(ROOT / "docs" / "screenshots" / "workspace-v11.png"))
    assert not screenshot.isNull()
    assert screenshot.width() >= 1000 and screenshot.height() >= 700


def test_public_documentation_is_available_in_english_and_french() -> None:
    pairs = (
        (ROOT / "README.md", ROOT / "README.fr.md"),
        (ROOT / "CHANGELOG.md", ROOT / "CHANGELOG.fr.md"),
        (ROOT / "RELEASE_NOTES.md", ROOT / "RELEASE_NOTES.fr.md"),
        (ROOT / "docs" / "user-guide.md", ROOT / "docs" / "user-guide.fr.md"),
    )
    assert all(english.is_file() and french.is_file() for english, french in pairs)
    assert "English user guide" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "guide utilisateur" in (ROOT / "README.fr.md").read_text(encoding="utf-8")
    assert not (ROOT / "docs" / "24-todo.md").exists()
