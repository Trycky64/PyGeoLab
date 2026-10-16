# Décisions d'architecture — Version 1.2

## ADR-035 — Découpage préventif de l'interface : ActionRegistry, SelectionCoordinator et ProjectController

### Contexte
Pour préparer l'intégration des fonctionnalités de la version 1.2 (géométrie analytique, coniques, courbes paramétriques, polaires, lieux, timeline, tables de valeurs) sans transformer `MainWindow` ou `GeometryView` en God Objects, il est nécessaire de séparer les responsabilités transversales.

### Décision
Trois contrôleurs/services dédiés sont extraits dans `src/pygeolab/ui/` :

1. **`ActionRegistry`** (`pygeolab.ui.action_registry`) :
   Centralise la création, l'enregistrement, les raccourcis et la synchronisation d'état de l'ensemble des `QAction` (menus, barres d'outils, outils géométriques).
2. **`SelectionCoordinator`** (`pygeolab.ui.selection_coordinator`) :
   Gère la propagation non réentrante des identifiants d'objets sélectionnés entre la vue géométrique et les différents panneaux auxiliaires, éliminant les dépendances croisées directes.
3. **`ProjectController`** (`pygeolab.ui.project_controller`) :
   Isole le cycle de vie du document persistant, les ouvertures/sauvegardes, la sauvegarde automatique atomique et la restauration de crash hors du widget de fenêtre.

### Conséquences
- `MainWindow` reste un orchestrateur léger.
- Les dépendances circulaires entre panneaux sont supprimées grâce au `SelectionCoordinator`.
- L'ensemble des API publiques et propriétés de `MainWindow` sont intégralement conservées pour la compatibilité avec les tests et extensions existantes.
