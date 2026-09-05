# 20 — Logging et debug

## Logging

Utiliser le module standard `logging`.

## Niveaux

- DEBUG ;
- INFO ;
- WARNING ;
- ERROR ;
- CRITICAL.

## Contenu

Les logs peuvent contenir :

- démarrage ;
- version ;
- ouverture/sauvegarde ;
- erreurs de parsing ;
- erreurs internes ;
- migrations ;
- statistiques de performance en debug.

## Ne pas logger

Éviter :

- données inutiles à haute fréquence ;
- chaque événement souris ;
- contenu complet d'un document à chaque frame.

## Mode développeur

Une option de debug pourra afficher :

- FPS ;
- objets rendus ;
- objets recalculés ;
- temps de frame ;
- bounding boxes ;
- graphe de dépendances.
