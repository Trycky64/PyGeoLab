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

Avec plusieurs objets sélectionnés, le nom reste désactivé tandis que visibilité, verrouillage et
champs de style s'appliquent au groupe dans une seule entrée Undo/Redo.

## Barre d'état

Peut afficher :

- coordonnées du curseur ;
- coordonnées aimantées lorsqu'une cible de snapping est active ;
- outil actif ;
- aide contextuelle ;
- zoom.

## Précision de construction

Un viseur entouré d'un cercle matérialise la cible de snapping. Le magnétisme est activé par
défaut, basculable avec `M`, et suspendu tant que `Alt` est maintenu. Le seuil reste exprimé en
pixels pour fournir le même geste au clavier et à la souris, quel que soit le zoom.

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
