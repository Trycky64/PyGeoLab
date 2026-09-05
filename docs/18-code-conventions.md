# 18 — Conventions de code

## Style

PEP 8 avec formatter automatique.

## Typage

Type hints obligatoires sur :

- API publiques ;
- fonctions métier ;
- structures de données.

## Nommage

Classes :

```text
PascalCase
```

Fonctions et variables :

```text
snake_case
```

Constantes :

```text
UPPER_SNAKE_CASE
```

## Dataclasses

Utiliser `dataclass` pour les valeurs simples lorsque pertinent.

## Exceptions

Créer des exceptions spécialisées uniquement pour des erreurs réellement exceptionnelles.

## Docstrings

Documenter :

- classes publiques ;
- algorithmes non triviaux ;
- choix numériques ;
- comportements subtils.

## Imports

Ordre :

1. standard library ;
2. dépendances tierces ;
3. imports PyGeoLab.

## Couplage

Éviter les imports circulaires.

Préférer :

- interfaces ;
- protocoles ;
- événements ;
- inversion de dépendance.
