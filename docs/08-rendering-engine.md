# 08 — Moteur de rendu 2D

## Responsabilité

Transformer l'état logique du document en représentation visuelle.

## Coordonnées

Deux espaces :

### Monde

Coordonnées mathématiques.

### Écran

Coordonnées en pixels.

## Viewport

Le viewport définit :

- centre monde ;
- zoom ;
- dimensions écran ;
- transformation monde-écran.

## Transformation

Exemple conceptuel :

```text
screen_x = width / 2 + (world_x - camera_x) * scale
screen_y = height / 2 - (world_y - camera_y) * scale
```

L'axe Y écran est inversé.

## Zoom

Le zoom à la molette doit être centré sur la position du curseur.

Le point monde sous le curseur doit rester stable visuellement.

## Grille

La grille doit adapter automatiquement son pas selon le zoom.

Exemples de pas :

```text
0.01
0.02
0.05
0.1
0.2
0.5
1
2
5
10
20
50
...
```

## Axes

Afficher :

- X ;
- Y ;
- graduations ;
- valeurs.

## Ordre de rendu

Proposition :

1. fond ;
2. grille ;
3. axes ;
4. surfaces ;
5. courbes ;
6. lignes ;
7. segments ;
8. cercles ;
9. points ;
10. labels ;
11. sélection ;
12. outils temporaires.

## Clipping

Les objets très grands ou infinis doivent être coupés au viewport.

## Cache

Le rendu peut mettre en cache :

- grille ;
- textes ;
- paths de fonctions.

Le cache doit être invalidé proprement lors du zoom ou d'une modification.

## Courbes de fonctions en 1.0

Le renderer échantillonne les `FunctionObject` sur l'intervalle X visible, sépare les
discontinuités et clippe chaque segment au viewport. Les chemins échantillonnés sont mis en
cache pour une même révision du document et un même viewport ; le cache est borné afin de ne
pas croître indéfiniment. Le même chemin de rendu est utilisé pour l'écran, le PNG et le SVG.
