$ErrorActionPreference = "Stop"
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m PyInstaller --clean --noconfirm packaging/pygeolab.spec
$env:QT_QPA_PLATFORM = "offscreen"
$smoke = Start-Process -FilePath (Resolve-Path "dist/PyGeoLab/PyGeoLab.exe") -ArgumentList "--smoke-test" -WindowStyle Hidden -Wait -PassThru
if ($smoke.ExitCode -ne 0) {
    throw "PyGeoLab executable smoke test failed with exit code $($smoke.ExitCode)"
}
Compress-Archive -Path dist/PyGeoLab/* -DestinationPath dist/PyGeoLab-Windows-x64.zip -Force
