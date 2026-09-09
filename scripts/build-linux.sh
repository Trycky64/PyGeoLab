#!/usr/bin/env bash
set -euo pipefail
python -m pip install -e '.[dev]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m PyInstaller --clean --noconfirm packaging/pygeolab.spec
QT_QPA_PLATFORM=offscreen ./dist/PyGeoLab/PyGeoLab --smoke-test
tar -C dist -czf dist/PyGeoLab-Linux-x64.tar.gz PyGeoLab
