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

## ADR-036 — Édition analytique bidirectionnelle et validation des paramètres

### Contexte
La version 1.2 introduit l'édition directe des coordonnées et paramètres numériques des objets géométriques depuis le panneau Propriétés et le panneau Algèbre, tout en préservant l'intégrité du graphe de dépendances et l'atomicité de l'historique Undo/Redo.

### Décision
1. **Édition X/Y des points libres** : validation stricte via `parse_point_coordinates`, rejet de `NaN`/`Infinity`, mutation unifiée via `MovePointCommand`.
2. **Objets dépendants** : les coordonnées dérivées sont en lecture seule avec un tooltip explicatif (`Objet dépendant : calculé automatiquement`).
3. **Paramètres éditables de recettes** : édition de `radius`, `value`, `factor`, `angle` via `ChangeParametersCommand` avec contrôles stricts de domaine (rayons strictement positifs, bornes de curseurs respectées).

### Conséquences
- Synchronisation bidirectionnelle fluide entre canvas, panneau Algèbre et panneau Propriétés.
- Préservation absolue des invariants du domaine mathématique et de l'historique Undo/Redo.

## ADR-037 — Moteur de géométrie analytique pur et métriques dynamiques

### Contexte
La géométrie analytique requiert des calculs de représentations cartésiennes ($ax + by + c = 0$, $y = mx + p$), canoniques de cercle, métriques vectorielles (norme, produit scalaire, déterminant 2D, angles) et relations géométriques (parallélisme, orthogonalité, colinéarité), indépendamment de Qt et du système de rendu.

### Décision
1. **Module pur `pygeolab.geometry.analytical`** :
   Calculs vectoriels et métriques purs, sans dépendance Qt.
2. **Tolérances numériques documentées** :
   `EPSILON = 1e-9` pour les distances et coordonnées spatiales, `ANGLE_EPSILON = 1e-7` pour les angles en radians.
3. **Représentations canoniques et réduites** :
   Formatage cartésien propre, gestion des droites verticales ($x = k$) et horizontales ($y = p$), équations de cercle développées et canoniques.
4. **Intégration au panneau Propriétés** :
   Exposition interactive des propriétés analytiques pour 1, 2 ou 3 objets sélectionnés avec labels sélectionnables pour la copie (`TextSelectableByMouse`).

### Conséquences
- Calculs géométriques purs, testables à 100 % hors interface graphique.
- Ergonomie enrichie permettant aux étudiants et enseignants de visualiser et copier immédiatement les équations analytiques exactes.

