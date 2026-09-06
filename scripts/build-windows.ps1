$ErrorActionPreference = "Stop"
py -m pip install -e ".[dev]"
py -m pytest
py -m ruff check .
py -m ruff format --check .
py -m mypy src
pyinstaller --clean --noconfirm packaging/pygeolab.spec
Compress-Archive -Path dist/PyGeoLab/* -DestinationPath dist/PyGeoLab-Windows-x64.zip -Force
