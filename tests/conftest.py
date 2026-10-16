"""Configure Qt's headless platform before tests import application widgets."""

import os
from collections.abc import Generator

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyside6")


@pytest.fixture(autouse=True)
def clean_recovery() -> Generator[None, None, None]:
    """Ensure no stale recovery files exist before or after tests."""
    from pygeolab.persistence.recovery import RecoveryManager

    r = RecoveryManager()
    if r.available:
        r.discard()
    yield
    if r.available:
        r.discard()
