# 03 — Architecture logicielle

## Objectif

Séparer fortement :

- logique géométrique ;
- moteur de dépendances ;
- état du document ;
- rendu ;
- interaction ;
- interface graphique ;
- persistance.

## Couches

```text
UI
↓
Interaction / Commands
↓
Document / Scene
↓
Geometry + Math + Dependency Engine
↓
Persistence / Serialization
```

Le renderer lit le document mais ne possède pas les objets métier.

## Modules principaux

### `geometry`

Contient les primitives et algorithmes géométriques.

Aucune dépendance vers PySide6.

### `math_engine`

Expressions, fonctions, variables, évaluations numériques.

### `model`

Objets du document et métadonnées.

### `dependency`

Graphe de dépendances et propagation des mises à jour.

### `commands`

Actions utilisateur atomiques.

### `rendering`

Transformation monde-écran, dessin, clipping et style.

### `interaction`

Outils actifs, hit-testing, drag, sélection.

### `ui`

Fenêtres, panneaux et widgets Qt.

### `persistence`

Sérialisation, validation, migrations de format.

## Règles

Le domaine ne doit jamais importer l'UI.

Le renderer ne doit jamais modifier le document.

Toute action modifiant le document doit idéalement passer par une commande.

Les objets doivent disposer d'identifiants uniques stables.

Les calculs ne doivent pas dépendre du nombre de pixels ou du zoom.
