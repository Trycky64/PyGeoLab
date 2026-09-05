# 05 — Moteur géométrique

## Objectif

Le moteur géométrique fournit des calculs purs et testables.

Il ne connaît :

- ni la souris ;
- ni Qt ;
- ni le renderer ;
- ni les fichiers projet.

## Coordonnées

Toutes les coordonnées métier utilisent des `float`.

## Point

```text
Point2D(x, y)
```

## Vecteur

Opérations :

- addition ;
- soustraction ;
- norme ;
- normalisation ;
- produit scalaire ;
- produit vectoriel 2D ;
- rotation.

## Droite

Représentation recommandée :

```text
ax + by + c = 0
```

Cette représentation facilite :

- distances ;
- intersections ;
- parallélisme ;
- perpendicularité.

## Segment

Défini par deux points.

Calculs :

- longueur ;
- point le plus proche ;
- appartenance ;
- bounding box.

## Cercle

```text
center
radius
```

Le rayon doit toujours être positif ou nul.

## Tolérances

Les comparaisons flottantes ne doivent jamais utiliser l'égalité stricte lorsque la géométrie est concernée.

Constante de base :

```text
EPSILON
```

Les tolérances peuvent dépendre du type de calcul.

## Intersections

### Droite-droite

Cas :

- intersection unique ;
- parallèles ;
- confondues.

### Droite-cercle

Cas :

- aucune intersection ;
- tangence ;
- deux intersections.

### Cercle-cercle

Cas :

- séparés ;
- tangents ;
- deux intersections ;
- confondus ;
- cercle intérieur sans intersection.

## Projection

Projection orthogonale d'un point sur :

- droite ;
- segment.

## Angles

Les angles internes utilisent les radians.

L'affichage utilisateur peut choisir degrés ou radians.

## Polygones

Calculs :

- aire signée ;
- aire absolue ;
- périmètre ;
- centroïde ;
- orientation ;
- point dans polygone.

## Transformations

- translation ;
- rotation ;
- homothétie ;
- réflexion.

## Robustesse

Les fonctions géométriques doivent retourner des types explicites plutôt que lever des exceptions pour les configurations géométriques normales.

Exemple :

```text
IntersectionResult.NONE
IntersectionResult.ONE
IntersectionResult.TWO
IntersectionResult.COINCIDENT
```
