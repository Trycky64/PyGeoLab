# 25 — Critères d'acceptation

## MVP

Le MVP est considéré fonctionnel lorsque :

- l'application démarre sans erreur ;
- le viewport supporte pan et zoom ;
- la grille s'adapte au zoom ;
- l'utilisateur crée des points ;
- les points libres sont déplaçables ;
- segments, droites et cercles existent ;
- les objets peuvent être sélectionnés et supprimés ;
- les coordonnées sont cohérentes avec le viewport.

## Géométrie dynamique

Accepté lorsque :

- un milieu dépend de deux points ;
- une intersection dépend de ses parents ;
- déplacer un parent actualise tous les descendants ;
- une construction impossible devient invalide sans crash ;
- elle redevient valide automatiquement lorsque possible.

## Fonctions

Accepté lorsque :

- `f(x)=sin(x)` est parsé ;
- la courbe se trace ;
- le zoom conserve un tracé correct ;
- les expressions invalides affichent une erreur ;
- aucune expression ne peut exécuter du code Python arbitraire.

## Sauvegarde

Accepté lorsque :

- une construction complexe est sauvegardée ;
- l'application est redémarrée ;
- le fichier est rouvert ;
- les objets, styles et dépendances sont identiques fonctionnellement.

## Release 1.0

La 1.0 doit :

- passer la CI ;
- ne contenir aucun bug bloquant connu ;
- disposer d'une documentation utilisateur minimale ;
- disposer de builds reproductibles ;
- proposer un exemple de construction ;
- être présentable dans un portfolio.
