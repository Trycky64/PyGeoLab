#!/usr/bin/env bash
set -euo pipefail
python -m pip install -e '.[dev]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m PyInstaller --clean --noconfirm packaging/pygeolab.spec
QT_QPA_PLATFORM=offscreen ./dist/PyGeoLab/PyGeoLab --smoke-test
cp LICENSE README.md CHANGELOG.md RELEASE_NOTES.md dist/PyGeoLab/
mkdir -p dist/PyGeoLab/assets \
  dist/PyGeoLab/share/applications \
  dist/PyGeoLab/share/icons/hicolor/256x256/apps \
  dist/PyGeoLab/share/metainfo
cp assets/pygeolab.ico assets/pygeolab.png dist/PyGeoLab/assets/
cp packaging/pygeolab.desktop dist/PyGeoLab/share/applications/
cp assets/pygeolab.png dist/PyGeoLab/share/icons/hicolor/256x256/apps/pygeolab.png
cp packaging/io.github.trycky64.PyGeoLab.metainfo.xml dist/PyGeoLab/share/metainfo/
tar -C dist -czf dist/PyGeoLab-Linux-x64.tar.gz PyGeoLab
