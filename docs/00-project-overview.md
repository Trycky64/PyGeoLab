# 00 — Vue d'ensemble du projet

## Nom

**PyGeoLab**

## Description

PyGeoLab est une application desktop de géométrie dynamique, de visualisation mathématique et de manipulation interactive d'objets géométriques.

L'utilisateur peut créer des points, segments, droites, cercles, polygones et constructions dérivées, puis déplacer les objets libres afin de voir toutes les dépendances se recalculer en temps réel.

PyGeoLab permet également de définir et tracer des fonctions mathématiques, manipuler des variables et curseurs, inspecter les propriétés des objets et sauvegarder une construction dans un fichier de projet.

## Vision

Créer un logiciel suffisamment intuitif pour être utilisé comme outil pédagogique, mais suffisamment structuré techniquement pour démontrer une architecture logicielle sérieuse.

Le projet n'a pas pour objectif initial de reproduire toutes les fonctionnalités de GeoGebra.

PyGeoLab doit d'abord exceller sur un noyau 2D solide.

## Principes

1. Interaction immédiate.
2. Recalcul déterministe.
3. Architecture modulaire.
4. Séparation claire entre modèle, rendu et interface.
5. Moteur mathématique indépendant de la GUI.
6. Tests automatisés sur toute la logique critique.
7. Aucune exécution arbitraire de code utilisateur.
8. Performances suffisantes pour plusieurs centaines d'objets.

## Utilisateurs cibles

- étudiants ;
- enseignants ;
- amateurs de mathématiques ;
- développeurs souhaitant explorer la géométrie computationnelle ;
- recruteurs évaluant le portfolio.

## Périmètre initial

### Inclus

- géométrie 2D ;
- coordonnées cartésiennes ;
- objets dynamiques ;
- tracé de fonctions ;
- variables numériques ;
- curseurs ;
- sauvegarde ;
- export image ;
- undo/redo ;
- propriétés d'objets ;
- grille et axes.

### Hors périmètre initial

- géométrie 3D ;
- calcul formel complet ;
- collaboration réseau ;
- synchronisation cloud ;
- application mobile ;
- compatibilité complète avec les fichiers GeoGebra ;
- solveur symbolique avancé.
