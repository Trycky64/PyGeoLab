# 23 — Roadmap

## Milestone 0 — Fondation

Objectif : repository propre et application vide fonctionnelle.

Livrables :

- pyproject ;
- src layout ;
- PySide6 ;
- fenêtre principale ;
- CI ;
- lint ;
- tests.

## Milestone 1 — Viewport 2D

- canvas ;
- coordonnées monde-écran ;
- zoom ;
- pan ;
- grille ;
- axes ;
- labels de graduation.

## Milestone 2 — Points et sélection

- point libre ;
- création à la souris ;
- sélection ;
- drag ;
- propriétés ;
- suppression.

## Milestone 3 — Géométrie de base

- segments ;
- droites ;
- demi-droites ;
- cercles ;
- polygones ;
- vecteurs.

## Milestone 4 — Dépendances

- graphe ;
- objets calculés ;
- milieu ;
- parallèles ;
- perpendiculaires ;
- intersections ;
- propagation dynamique.

## Milestone 5 — Commandes

- undo ;
- redo ;
- transactions ;
- raccourcis.

## Milestone 6 — Panneaux

- panneau algébrique ;
- propriétés ;
- visibilité ;
- renommage ;
- styles.

## Milestone 7 — Math engine

- tokenizer ;
- parser ;
- AST ;
- evaluator ;
- variables ;
- fonctions ;
- tracé.

## Milestone 8 — Persistance

- `.pgl` ;
- save/load ;
- validation ;
- migrations ;
- fichiers récents *(livré en 1.1, section 8)*.

## Milestone 9 — Analyse mathématique

- racines ;
- dérivée ;
- intégrale ;
- extrema ;
- intersection de courbes.

## Milestone 10 — Export et finition

- PNG ;
- SVG ;
- thème sombre ;
- préférences ;
- packaging.

## Milestone 11 — Release 1.0

Critères :

- stabilité ;
- documentation ;
- tutoriel ;
- tests ;
- builds Windows/Linux ;
- démo portfolio.


## État 1.0.0

Les milestones 0 à 11 sont réalisés pour le périmètre 1.0. Les éléments explicitement laissés
au backlog (snapping, édition directe des coordonnées, saisie de fonctions dédiée, fichiers
récents, autosave, vidéo portfolio) ne bloquent pas la release et restent identifiés dans
`docs/24-todo.md`.

## Version 1.1 — Précision et constructions avancées

- Section 1 terminée : snapping sur points, grille, projections et intersections, avec contrôle
  global, suspension par `Alt` et indicateur visuel.
- Section 2 terminée : outils demi-droite, vecteur, médiatrice, bissectrice, projection, point sur
  objet, cercles avancés, mesures et transformations, avec previews, annulation et Undo/Redo.
- Section 3 terminée : sélection rectangulaire et multiple, édition groupée, duplication, ordre
  d'affichage, cycle des objets superposés et menu contextuel du canvas.
- Section 4 terminée : panneau Algèbre filtrable, triable et éditable, états invalides détaillés,
  paramètres numériques et navigation dans le graphe depuis Propriétés.
- Section 5 terminée : éditeur de fonctions lié aux sliders, sampling adaptatif, détection renforcée
  des asymptotes et couches optionnelles de racines, extrema, intersections et dérivées.
- Section 6 terminée : création depuis Algèbre, édition complète, saisie et reset, contrôle clavier
  et animation configurable avec recalcul incrémental sans historique par frame.
- Section 7 terminée : panneau d'analyse numérique borné, gestion des domaines et discontinuités,
  résultats intégrés à l'UI et mesures dynamiques de longueur, aire et angle.
- Section 8 terminée : fichiers récents auto-nettoyés, autosave atomique configurable et
  restauration de crash dans un fichier séparé compatible avec le format v1.
- Section 9 terminée : préférences centralisées pour thème, affichage, snapping, styles, export et
  autosave, avec restauration des valeurs par défaut et round-trip QSettings.
- Section 10 terminée : export viewport, document ou sélection en PNG/SVG, dimensions et résolution
  personnalisées, transparence, métadonnées et presse-papiers Qt.
- Section 11 terminée : raccourcis sans collision et consultables, contrôles nommés et dimensionnés,
  focus clavier visible, palettes contrastées et retours d'état explicites.
- Section 12 terminée : profils reproductibles jusqu'à 10 000 objets, rendu multi-fonctions
  optimisé, seuils de régression et nettoyage explicite des ressources Qt.
- Section 13 terminée : diagnostics de build et de plateforme, erreurs fichier/export contextualisées,
  copie des informations système et conservation atomique du document courant.
- Section 14 terminée : smoke tests V1.1, matrice Windows/Linux sur Python 3.12 à 3.14, gate
  Ruff/mypy et builds PyInstaller lancés avant publication des artefacts.
- Section 15 terminée : guide utilisateur V1.1, README, captures, démonstration et registre ADR
  ont été synchronisés avec le produit livré.
- Section 16 terminée : version 1.1.0, métadonnées, compatibilité `.pgl` V1.0, paquets portables,
  release gate et publication GitHub ont été validés.
