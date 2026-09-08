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

Affiche les objets avec une recherche textuelle, un tri par nom ou type et un regroupement
configurable par catégorie, type ou sans groupe. La sélection est conservée lorsqu'un filtre la
masque temporairement.

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

Le nom se modifie directement dans l'arbre. Deux colonnes à cases à cocher pilotent la visibilité
et le verrouillage avec Undo/Redo. Une construction invalide apparaît en rouge ; sa valeur et son
infobulle donnent le message d'erreur calculé. Le menu contextuel permet aussi de sélectionner les
parents directs ou tous les descendants.

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

Pour une sélection unique, le panneau affiche les parents directs et tous les descendants, avec
des boutons permettant de transférer cette relation vers la sélection du workspace. Il expose les
paramètres numériques directement éditables des points libres, nombres, cercles à rayon littéral,
intersections, points sur objet, rotations et homothéties. Une modification remplace la recette via
une commande et déclenche le recalcul normal du graphe.

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

## Fonctions en 1.1

Le menu **Objets** crée et modifie les fonctions. L'éditeur valide immédiatement la syntaxe, le
domaine et les références aux sliders. La suppression utilise l'action globale de sélection et
reste groupée avec ses descendants dans l'historique.

Le sous-menu **Affichage > Fonctions** contient le réglage de qualité du tracé et les bascules des
racines, extrema, intersections et dérivées. Les fonctions valides apparaissent dans Algèbre comme
les autres objets ; une expression invalide y conserve sa ligne en rouge avec le détail de
l'erreur.
