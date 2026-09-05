# 10 — UI / UX

## Layout principal

```text
┌─────────────────────────────────────────────────────┐
│ Menu                                                │
├─────────────────────────────────────────────────────┤
│ Toolbar                                             │
├──────────────┬───────────────────────┬──────────────┤
│ Algebra      │                       │ Properties   │
│ Panel        │    Geometry View      │ Panel        │
│              │                       │              │
├──────────────┴───────────────────────┴──────────────┤
│ Status Bar                                          │
└─────────────────────────────────────────────────────┘
```

## Panneau algébrique

Affiche les objets par catégorie.

Exemple :

```text
Points
A = (2.0, 1.0)
B = (4.5, 3.2)
M = midpoint(A, B)

Lines
d: through(A, B)

Functions
f(x) = sin(x)
```

## Propriétés

Permet d'éditer :

- nom ;
- visibilité ;
- couleur ;
- épaisseur ;
- taille ;
- type de ligne ;
- affichage du label.

## Barre d'état

Peut afficher :

- coordonnées du curseur ;
- outil actif ;
- aide contextuelle ;
- zoom.

## UX

Principes :

- réduire le nombre de clics ;
- fournir des previews ;
- messages d'erreur courts ;
- actions annulables ;
- aucun mode bloquant inutile.

## Thème

Prévoir :

- thème clair ;
- thème sombre.

Le thème ne doit pas être codé en dur dans le renderer.
