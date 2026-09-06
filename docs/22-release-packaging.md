# 22 — Packaging et releases

## Développement

Installation editable : `python -m pip install -e ".[dev]"` puis `python -m pygeolab`.

## Versioning

PyGeoLab suit Semantic Versioning. La version courante est **1.0.0**.

## Packaging 1.0

La stratégie retenue pour 1.0 est une application portable PyInstaller en mode dossier :

- Windows : `scripts/build-windows.ps1` produit `dist/PyGeoLab-Windows-x64.zip` ;
- Linux : `scripts/build-linux.sh` produit `dist/PyGeoLab-Linux-x64.tar.gz`.

Le fichier `packaging/pygeolab.spec` constitue la source de vérité du packaging. Il embarque
les ressources applicatives et masque la console pour l'application desktop.

Un installateur MSI/NSIS/AppImage n'est pas requis pour 1.0 et pourra être ajouté ultérieurement.

## CI et releases GitHub

`.github/workflows/ci.yml` valide lint, formatage, typage et tests sous Windows/Linux.
`.github/workflows/release.yml` se déclenche sur les tags `v*`, construit les deux plateformes,
upload les artefacts puis crée la GitHub Release avec des notes générées automatiquement.

## Checklist release

Une release doit inclure : changelog, notes, artefacts exécutables, icône, captures et projet de
démonstration. `CHANGELOG.md`, `assets/`, `docs/screenshots/` et `examples/demo.pgl` fournissent
ces éléments pour 1.0.0.
