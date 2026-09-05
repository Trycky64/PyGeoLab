# 09 — Système d'interaction

## Outils

Un seul outil principal est actif à la fois.

Exemples :

- sélection ;
- point ;
- segment ;
- droite ;
- cercle ;
- polygone ;
- intersection ;
- milieu ;
- parallèle ;
- perpendiculaire.

## Machine à états

Chaque outil complexe utilise une petite machine à états.

Exemple outil Segment :

```text
WAIT_FIRST_POINT
↓ clic
WAIT_SECOND_POINT
↓ clic
CREATE_SEGMENT
↓
WAIT_FIRST_POINT
```

## Hit-testing

Le hit-testing détermine l'objet situé sous le curseur.

Il doit tenir compte :

- de la distance écran ;
- du type d'objet ;
- du niveau de priorité.

Priorité suggérée :

1. point ;
2. poignée ;
3. segment ;
4. cercle ;
5. droite ;
6. courbe.

## Drag

Seuls les objets déplaçables peuvent être drag.

Un point calculé n'est pas directement libre.

## Snapping

Cibles futures :

- grille ;
- point existant ;
- intersection ;
- axe.

Le snapping doit être désactivable.

## Sélection multiple

Support futur ou MVP avancé :

- `Shift+clic` ;
- rectangle de sélection.

## Aperçu

Un outil peut afficher une prévisualisation avant validation.

Exemple :

- cercle temporaire durant le mouvement de la souris.
