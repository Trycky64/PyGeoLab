"""Validate that a release tag matches every user-visible project version."""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path


def main() -> int:
    """Return zero when the supplied tag exactly matches the project version."""
    root = Path(__file__).resolve().parents[1]
    if len(sys.argv) != 2:
        print("usage: check-release-tag.py v<version>", file=sys.stderr)
        return 2
    tag = sys.argv[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    version = str(project["project"]["version"])
    init_text = (root / "src" / "pygeolab" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"$', init_text, re.MULTILINE)
    if match is None or match.group(1) != version:
        print("pyproject.toml and pygeolab.__version__ differ", file=sys.stderr)
        return 1
    expected = f"v{version}"
    if tag != expected:
        print(f"release tag {tag!r} must be {expected!r}", file=sys.stderr)
        return 1
    print(f"Release metadata matches {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
