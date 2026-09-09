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
Copy-Item LICENSE, README.md, README.fr.md, CHANGELOG.md, CHANGELOG.fr.md, RELEASE_NOTES.md, RELEASE_NOTES.fr.md -Destination dist/PyGeoLab
New-Item -ItemType Directory -Force -Path dist/PyGeoLab/assets | Out-Null
Copy-Item assets/pygeolab.ico, assets/pygeolab.png -Destination dist/PyGeoLab/assets
Compress-Archive -Path dist/PyGeoLab/* -DestinationPath dist/PyGeoLab-Windows-x64.zip -Force
