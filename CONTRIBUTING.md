# Contributing to PyGeoLab

## English

Use Python 3.12 or newer, create a virtual environment, and install `.[dev]`. Keep changes focused and include tests for behavior that can regress.

Before opening a pull request, run:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

Write commit messages in imperative English. Explain the problem, resulting behavior, validation, and any compatibility impact in the pull request. User-facing changes must keep both English and French documentation or translations coherent.

## Français

Utilisez Python 3.12 ou plus récent, créez un environnement virtuel et installez `.[dev]`. Gardez les changements ciblés et ajoutez des tests pour les comportements susceptibles de régresser.

Avant d'ouvrir une pull request, exécutez les quatre commandes du release gate ci-dessus. Rédigez les commits en anglais à l'impératif et décrivez le problème, le résultat, la validation et l'impact de compatibilité. Toute modification visible doit maintenir la cohérence des traductions ou documentations anglaises et françaises.
