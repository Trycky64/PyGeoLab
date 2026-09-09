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

Les objets sont dessinés dans l'ordre persistant du document entre les axes et les labels. Les
actions **Mettre au premier plan** et **Mettre à l'arrière-plan** modifient cet ordre sans changer
les recettes géométriques. Le rendu complet suit donc :

1. fond ;
2. grille ;
3. axes ;
4. objets dans l'ordre du document ;
5. labels ;
6. surbrillance de sélection ;
7. outils temporaires.

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
discontinuités et clippe chaque segment au viewport. Les chemins échantillonnés sont mis en cache
pour une même révision de fonction et un même viewport ; le cache est borné afin de ne pas croître
indéfiniment. Une modification sans lien avec la fonction conserve donc son sampling. Le même
chemin de rendu est utilisé pour l'écran, le PNG et le SVG.

## Courbes de fonctions en 1.1

Chaque nouvelle courbe reçoit un style violet dédié, modifiable ensuite comme tout autre style.
Le nombre d'échantillons dépend de la largeur du viewport, du niveau de zoom et de la qualité
**basse**, **normale** ou **haute**. Il reste borné entre 120 et 4 000 pour conserver un coût
prévisible. Lorsque beaucoup de fonctions sont visibles, ce budget est réparti selon la racine
carrée de leur nombre. Chaque morceau continu est envoyé à Qt comme une seule polyligne. La
qualité et le nombre de fonctions font partie de la clé de cache.

Les marqueurs de racines, extrema et intersections sont dessinés après les objets. La dérivée est
représentée par une courbe pointillée. Une erreur numérique locale interrompt la couche concernée
sans empêcher le rendu du document.
