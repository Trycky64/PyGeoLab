# 16 — Stratégie de tests

La logique mathématique et métier est testée plus intensivement que l'UI.

Les suites couvrent : géométrie, intersections, transformations, dépendances, commandes,
parser/evaluator mathématique, analyse numérique, persistance, interaction et rendu. Les tests
d'intégration exercent création/déplacement/historique ; les tests UI utilisent pytest-qt pour
le démarrage, le viewport, les panneaux, le renderer et les exports.

`tests/unit/test_release_assets.py` charge le projet de démonstration comme fixture de
régression et vérifie les artefacts de release. `benchmarks/benchmark_core.py` fournit le jeu de
benchmarks essentiel sans ajouter une dépendance runtime. `tests/performance` applique les seuils
de régression, tandis que les tests de stabilité vérifient le cache de fonctions, le périmètre de
recalcul, les abonnements Qt, les timers de fermeture et l'absence de dialogue modal au démarrage.

## Release gate 1.1

La CI exécute toute la suite avec `QT_QPA_PLATFORM=offscreen` sur Windows et Linux pour Python
3.12, 3.13 et 3.14. Le job qualité exécute séparément `python -m ruff check .`,
`python -m ruff format --check .` et `python -m mypy src` sur Python 3.13.

Les smoke tests non interactifs couvrent le snapping, un outil avancé avec Undo, une fonction liée
à un slider animé, l'autosave/récupération et l'export d'une sélection. Un mode de démarrage
`python -m pygeolab --smoke-test` crée la vraie fenêtre, traite les événements puis la ferme avec
un code contrôlé.

Après les tests, la CI construit l'application PyInstaller sur Windows et Linux, lance chaque
exécutable en mode smoke, crée l'archive native et la publie comme artefact du workflow. Les scripts
locaux de build appliquent le même contrôle de démarrage avant compression.
