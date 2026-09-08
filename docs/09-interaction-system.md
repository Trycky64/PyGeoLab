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

## Outils avancés 1.1

Les outils avancés réutilisent le hit-testing, le snapping et les points implicites du système
d'interaction. Une construction incomplète reste transitoire. Le dernier clic crée sa recette et
ses éventuels points implicites dans une seule commande ; `Escape` abandonne l'ensemble sans
modifier le document.

Les séquences de clics sont les suivantes :

- demi-droite, vecteur et médiatrice : deux points ;
- bissectrice et angle : un point sur le premier côté, le sommet, puis un point sur le second côté ;
- projection orthogonale : un point, puis une droite, un segment ou une demi-droite ;
- point sur objet : une droite, un segment, une demi-droite ou un cercle sous le curseur ;
- cercle centre-rayon : le centre, puis une position qui fixe un rayon numérique ;
- cercle circonscrit : trois points non alignés ;
- distance : un point, puis un autre point ou un support linéaire ;
- translation : un point existant, puis un vecteur existant ;
- symétrie centrale : le point à transformer, puis le centre ;
- symétrie axiale : le point à transformer, puis l'axe linéaire ;
- rotation : le point à transformer, le centre, puis une direction cible qui fixe l'angle signé ;
- homothétie : le point à transformer, le centre, puis une position dont la projection sur l'axe
  centre-source fixe le rapport signé.

La distance et l'angle produisent des valeurs numériques dynamiques visibles dans la catégorie
**Nombres** du panneau Algèbre. Les transformations produisent des points dépendants. Les paramètres
de rotation, d'homothétie et de cercle centre-rayon sont enregistrés comme valeurs numériques dans
la recette ; les autres résultats suivent leurs objets parents lors du recalcul.

Chaque outil affiche une prévisualisation dès que ses données temporaires suffisent : support,
segments auxiliaires, cercle ou point résultat selon la construction. Aucune boîte de dialogue
modale n'est nécessaire pendant ces interactions.
