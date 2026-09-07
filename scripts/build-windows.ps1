$ErrorActionPreference = "Stop"
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m PyInstaller --clean --noconfirm packaging/pygeolab.spec
Compress-Archive -Path dist/PyGeoLab/* -DestinationPath dist/PyGeoLab-Windows-x64.zip -Force
