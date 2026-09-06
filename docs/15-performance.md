# 15 — Performance

## Objectif

L'application vise une interaction fluide avec plusieurs centaines d'objets simples.

## Optimisations présentes en 1.0

- recalcul incrémental par graphe de dépendances ;
- drag regroupé en une commande d'historique ;
- cache de grille dépendant du viewport ;
- cache de la liste des objets visibles ordonnés par `Document.revision` ;
- clipping des lignes, demi-droites et segments avant dessin ;
- sampling borné des fonctions et séparation des discontinuités.

Un index spatial (quadtree/R-tree) n'est pas justifié par les tailles ciblées en 1.0.

## Benchmarks

`benchmarks/benchmark_core.py` mesure l'insertion de 500 points et une mise à jour
incrémentale sans dépendance Qt. Il peut être exécuté avec `PYTHONPATH=src python
benchmarks/benchmark_core.py`. Les tests de régression vérifient en parallèle le périmètre de
recalcul plutôt qu'un seuil temporel fragile en CI.
