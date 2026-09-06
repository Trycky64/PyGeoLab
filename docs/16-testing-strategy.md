# 16 — Stratégie de tests

La logique mathématique et métier est testée plus intensivement que l'UI.

Les suites couvrent : géométrie, intersections, transformations, dépendances, commandes,
parser/evaluator mathématique, analyse numérique, persistance, interaction et rendu. Les tests
d'intégration exercent création/déplacement/historique ; les tests UI utilisent pytest-qt pour
le démarrage, le viewport, les panneaux, le renderer et les exports.

`tests/unit/test_release_assets.py` charge le projet de démonstration comme fixture de
régression et vérifie les artefacts de release. `benchmarks/benchmark_core.py` fournit le jeu de
benchmarks essentiel sans ajouter une dépendance runtime.

La CI exécute `pytest`, Ruff et mypy sur Python 3.13. Les tests Qt utilisent
`QT_QPA_PLATFORM=offscreen`.
