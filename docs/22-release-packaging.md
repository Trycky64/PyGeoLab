# 22 — Packaging et releases

## Développement

Installation editable : `python -m pip install -e ".[dev]"` puis `python -m pygeolab`.

## Versioning

PyGeoLab suit Semantic Versioning. La version courante est **1.1.1**.

## Packaging 1.0

La stratégie retenue pour 1.0 est une application portable PyInstaller en mode dossier :

- Windows : `scripts/build-windows.ps1` produit `dist/PyGeoLab-Windows-x64.zip` ;
- Linux : `scripts/build-linux.sh` produit `dist/PyGeoLab-Linux-x64.tar.gz`.

Le fichier `packaging/pygeolab.spec` constitue la source de vérité du packaging. Il embarque
les ressources applicatives et masque la console pour l'application desktop.

Un installateur MSI/NSIS/AppImage n'est pas requis pour 1.0 et pourra être ajouté ultérieurement.

## Gate de packaging 1.1

Chaque build lance `PyGeoLab --smoke-test` avec Qt offscreen avant de créer l'archive. Le workflow
CI produit ainsi `PyGeoLab-Windows-x64.zip` et `PyGeoLab-Linux-x64.tar.gz` depuis les mêmes sources
que la matrice de tests, puis conserve ces deux fichiers comme artefacts associés au commit.

## CI et releases GitHub

`.github/workflows/ci.yml` valide lint, formatage, typage et tests sous Windows/Linux.
`.github/workflows/release.yml` se déclenche sur les tags `v*`, vérifie que le tag correspond à
la version du projet, construit les deux plateformes, charge les artefacts puis crée la GitHub
Release avec `RELEASE_NOTES.md`.

## Checklist release

Une release doit inclure : changelog, notes, artefacts exécutables, icône, captures et projet de
démonstration. `CHANGELOG.md`, `assets/`, `docs/screenshots/` et `examples/demo.pgl` fournissent
ces éléments pour 1.1.1. Les archives contiennent également la licence, le changelog, les notes
de release et les icônes. Le paquet Linux fournit les fichiers desktop et AppStream.
