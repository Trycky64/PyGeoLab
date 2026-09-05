# 26 — Extensions futures

## Calcul formel

Intégration possible avec SymPy pour :

- dérivées symboliques ;
- simplification ;
- factorisation ;
- résolution d'équations.

Cette intégration doit rester optionnelle au début.

## 3D

PyGeoLab 3D pourrait introduire :

- Point3D ;
- Vector3D ;
- Plane ;
- Sphere ;
- Camera3D ;
- projection perspective.

Cela nécessite un renderer distinct.

## Statistiques

- tableur simple ;
- séries ;
- moyenne ;
- médiane ;
- variance ;
- histogrammes ;
- régression.

## Animations

Les curseurs peuvent être animés.

Paramètres :

- vitesse ;
- boucle ;
- ping-pong.

## Locus

Créer la trajectoire d'un point dépendant lorsqu'un parent varie.

## Scripts

Un langage de commandes sécurisé pourrait être ajouté.

Exemple :

```text
A = Point(0, 0)
B = Point(2, 1)
d = Line(A, B)
```

Il ne s'agirait pas de Python brut.

## Plugins

Un système de plugins pourrait exposer une API stable.

À envisager uniquement après une architecture 1.x stabilisée.

## Cloud

Possibilités futures :

- partage ;
- galerie ;
- collaboration.

Hors objectif principal.
