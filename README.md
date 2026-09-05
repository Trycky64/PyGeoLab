# PyGeoLab

Application desktop de géométrie dynamique et de visualisation mathématique, en Python et PySide6.

## Installation de développement

Python 3.12 ou supérieur est requis.

```sh
python -m venv .venv
# Windows : .venv\Scripts\activate
# Linux : source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pygeolab
```

La commande `pygeolab` démarre également l'application.

## Vérifications

```sh
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

Pour les tests sans affichage, définir `QT_QPA_PLATFORM=offscreen`.
L'architecture et le cahier des charges sont conservés dans [docs](docs/README.md).

## Licence

MIT, voir [LICENSE](LICENSE).
