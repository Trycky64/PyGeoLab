# 02 — Stack technique

## Langage

Python 3.12+.

La version minimale pourra être ajustée avant la première release stable.

## Interface graphique

### Choix principal

**PySide6**

Raisons :

- Qt moderne ;
- widgets riches ;
- système d'événements mature ;
- menus, docks et raccourcis ;
- rendu personnalisé ;
- packaging desktop réaliste ;
- bon potentiel portfolio.

## Calcul numérique

### NumPy

Utilisation prévue :

- vecteurs ;
- tableaux numériques ;
- calculs géométriques ;
- sampling de fonctions.

NumPy ne doit pas être une dépendance du modèle métier lorsque de simples opérations scalaires suffisent.

## Parsing mathématique

Le parser doit être développé autour de l'AST Python ou d'un parser dédié.

L'utilisation de `eval()` sur du texte utilisateur est interdite.

## Tests

- pytest ;
- pytest-qt pour l'interface si nécessaire ;
- hypothesis optionnel pour les propriétés géométriques.

## Qualité

- Ruff ;
- Black ou Ruff formatter ;
- mypy ou Pyright ;
- pre-commit.

## Packaging

Cibles possibles :

- PyInstaller ;
- Nuitka.

La décision finale doit être prise après validation du prototype.
