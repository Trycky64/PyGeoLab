# PyGeoLab

PyGeoLab 1.1 est une application desktop de **géométrie dynamique** et de **visualisation mathématique** écrite en Python et PySide6. Elle combine constructions dépendantes, fonctions paramétrées, analyse numérique et projets `.pgl` versionnés dans une interface utilisable à la souris comme au clavier.

![Espace de travail PyGeoLab 1.1](docs/screenshots/workspace-v11.png)

## Nouveautés 1.1

- magnétisme sur la grille, les points, projections et intersections, suspendu avec `Alt` ;
- quinze outils avancés : demi-droite, vecteur, médiatrice, bissectrice, projections, cercles, mesures et transformations ;
- sélection rectangulaire et multiple, édition groupée, duplication, ordre d'affichage et cycle des objets superposés ;
- panneau Algèbre filtrable et triable, propriétés numériques, dépendances et descendants ;
- création et édition de fonctions, sampling adaptatif, racines, extrema, intersections et dérivée ;
- curseurs éditables et animés avec vitesse, aller-retour, pause et reset ;
- dérivée, intégrale, racines, extrema, intersections et mesures dynamiques ;
- fichiers récents, autosave atomique et récupération après incident ;
- préférences centralisées, thèmes contrastés, raccourcis consultables avec `F1` ;
- export du viewport, du document ou de la sélection en PNG/SVG, plus copie presse-papiers ;
- diagnostics partageables et release gate Windows/Linux sur Python 3.12, 3.13 et 3.14.

Le [guide utilisateur V1.1](docs/30-user-guide-v11.md) décrit les outils, fonctions, curseurs, raccourcis, préférences, fichiers et exports.

## Installation développeur

Python 3.12 à 3.14 est pris en charge.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pygeolab
```

Sous Linux :

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pygeolab
```

## Vérifications

```powershell
py -m pytest
py -m ruff check .
py -m ruff format --check .
py -m mypy src
```

La suite compte plus de 340 tests non interactifs. La CI les exécute avec Qt offscreen sur Windows et Linux pour Python 3.12, 3.13 et 3.14. Elle construit ensuite les deux applications PyInstaller, lance chaque exécutable avec `--smoke-test` et publie les archives du commit.

## Projet de démonstration

Ouvrez [`examples/demo.pgl`](examples/demo.pgl) avec **Fichier > Ouvrir**. Le projet V1.1 présente un triangle, un cercle, un milieu, un vecteur, une translation, des mesures dynamiques, le curseur animé `a` et la fonction `f(x) = sin(x) + a`.

## Builds desktop

Windows PowerShell 5+ :

```powershell
.\scripts\build-windows.ps1
```

Linux :

```bash
./scripts/build-linux.sh
```

Chaque script exécute le release gate, construit le dossier portable, vérifie son démarrage hors écran et produit l'archive de plateforme. Les tags `v*` déclenchent aussi [le workflow de release](.github/workflows/release.yml).

## Architecture et sécurité

La [documentation d'architecture](docs/README.md) couvre le modèle, le graphe de dépendances, le rendu, la persistance, les tests et les ADR. Le format `.pgl` est validé avant reconstruction et une ouverture invalide conserve le document courant. Le moteur mathématique utilise un parser fermé et n'appelle jamais `eval` ou `exec`.

## Licence

MIT — voir [LICENSE](LICENSE).
