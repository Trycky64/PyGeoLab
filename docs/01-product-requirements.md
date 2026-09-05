# 01 — Exigences produit

## Fenêtre principale

L'application doit fournir :

- une barre de menus ;
- une barre d'outils ;
- une vue géométrique centrale ;
- un panneau algébrique ;
- un panneau de propriétés ;
- une barre d'état.

## Navigation

Le viewport doit supporter :

- déplacement de la caméra ;
- zoom avant/arrière ;
- recentrage ;
- réinitialisation du zoom ;
- affichage ou masquage de la grille ;
- affichage ou masquage des axes.

## Objets géométriques

### Point

Types :

- point libre ;
- point dépendant ;
- point d'intersection ;
- milieu ;
- point sur objet.

### Segment

Défini par deux points.

Propriétés :

- longueur ;
- visibilité ;
- style ;
- label.

### Droite

Définie par :

- deux points ;
- un point et une direction ;
- parallèle à une droite ;
- perpendiculaire à une droite.

### Demi-droite

Définie par une origine et un second point.

### Cercle

Modes :

- centre + rayon ;
- centre + point ;
- trois points.

### Polygone

Défini par N sommets.

Propriétés :

- aire ;
- périmètre ;
- orientation.

### Vecteur

Défini par deux points ou par composantes.

## Constructions

PyGeoLab doit supporter :

- milieu ;
- intersection droite-droite ;
- intersection droite-cercle ;
- intersection cercle-cercle ;
- parallèle ;
- perpendiculaire ;
- médiatrice ;
- bissectrice ;
- projection orthogonale ;
- distance ;
- angle ;
- translation ;
- rotation ;
- symétrie centrale ;
- symétrie axiale.

## Fonctions

L'utilisateur doit pouvoir créer une fonction telle que :

```text
f(x) = sin(x) + x^2 / 4
```

Fonctions natives minimales :

- sin ;
- cos ;
- tan ;
- asin ;
- acos ;
- atan ;
- sqrt ;
- abs ;
- exp ;
- ln ;
- log10 ;
- floor ;
- ceil.

Constantes :

- pi ;
- e.

## Analyse numérique

Fonctionnalités cibles :

- valeur d'une fonction ;
- zéros numériques ;
- extrema locaux ;
- dérivée numérique ;
- intégrale numérique ;
- intersection de fonctions.

## Curseurs

Un curseur possède :

- nom ;
- valeur ;
- minimum ;
- maximum ;
- pas.

Toute modification doit déclencher le recalcul des objets dépendants.

## Sélection

L'utilisateur doit pouvoir :

- cliquer un objet ;
- sélectionner plusieurs objets ;
- supprimer ;
- déplacer ;
- ouvrir ses propriétés ;
- masquer ;
- renommer.

## Sauvegarde

L'application doit pouvoir :

- créer un nouveau projet ;
- ouvrir un projet ;
- enregistrer ;
- enregistrer sous ;
- détecter les modifications non enregistrées.

## Historique

Toutes les modifications utilisateur pertinentes doivent être annulables et rétablissables.

## Export

Au minimum :

- PNG ;
- SVG.

## Raccourcis

Cibles :

- `Ctrl+N` : nouveau ;
- `Ctrl+O` : ouvrir ;
- `Ctrl+S` : enregistrer ;
- `Ctrl+Shift+S` : enregistrer sous ;
- `Ctrl+Z` : annuler ;
- `Ctrl+Y` : rétablir ;
- `Delete` : supprimer ;
- `Escape` : annuler l'outil actif.
