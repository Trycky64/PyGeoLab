# 15 — Performance

## Objectifs

Le MVP doit rester fluide avec plusieurs centaines d'objets simples.

## Budget

Cible :

- interaction visuelle proche de 60 FPS sur une machine desktop classique.

Cette valeur est un objectif, pas une garantie contractuelle.

## Optimisations prioritaires

1. recalcul incrémental ;
2. limitation des allocations pendant le drag ;
3. hit-testing spatial ;
4. caching des fonctions ;
5. batching du rendu ;
6. invalidation partielle.

## Spatial index

Pour les gros documents, utiliser potentiellement :

- quadtree ;
- grille spatiale ;
- R-tree.

Pas nécessaire dans la première implémentation.

## Fonctions

Éviter un sampling excessif.

Le nombre de points dépend :

- de la largeur écran ;
- du zoom ;
- de la courbure.

## Profiling

Outils possibles :

- `cProfile` ;
- `py-spy` ;
- profiling Qt ;
- benchmarks pytest.
