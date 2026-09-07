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

Le snapping de la version 1.1 recherche, dans cet ordre de priorité :

- les points existants ;
- les intersections finies de droites, segments, demi-droites et cercles ;
- la projection la plus proche sur une droite, un segment, une demi-droite, un cercle ou le
  bord d'un polygone ;
- la grille adaptative visible.

Le seuil est mesuré en pixels écran (10 px par défaut), donc sa taille visuelle reste constante
pendant le zoom et le pan. Les objets masqués ou invalides sont ignorés. Le point en cours de
déplacement est exclu des candidats pour ne pas rester aimanté à son ancienne position.

Le menu **Affichage → Magnétisme** et la touche `M` activent ou désactivent globalement le
snapping pour la session. Maintenir `Alt` pendant une interaction le suspend temporairement.
Un viseur coloré indique la cible active. La position résolue est transmise au même
`PointerContext` que les outils utilisent déjà : previews, points implicites et drag bénéficient
ainsi du snapping sans modifier le modèle métier ni l'historique de commandes.

## Sélection multiple

Support futur ou MVP avancé :

- `Shift+clic` ;
- rectangle de sélection.

## Aperçu

Un outil peut afficher une prévisualisation avant validation.

Exemple :

- cercle temporaire durant le mouvement de la souris.
