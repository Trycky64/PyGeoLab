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

## ADR-038 — Modèles euclidiens de coniques, évaluation dynamique et rendu adaptatif

### Contexte
L'introduction des coniques (ellipses, paraboles, hyperboles) en version 1.2 nécessite de véritables modèles euclidiens géométriques dans le domaine, intégrés au graphe de dépendances incrémental, avec hit-testing réactif, styles, persistance, Undo/Redo, métriques analytiques et export sans dégrader les performances du canvas.

### Décision
1. **Modèles euclidiens immuables purs** (`pygeolab.geometry.conics`) :
   - `Ellipse2D` : définie par centre, demi-axes $a \ge b > 0$, rotation $\theta$ ; calculs de foyers, excentricité, périmètre de Ramanujan, aire $\pi a b$ et bounding box orientée.
   - `Parabola2D` : définie par foyer $F$ et directrice $D$ ; calcul de sommet $V$, paramètre focal $p = d(F, D)$, axe et tangente de sommet.
   - `Hyperbola2D` : définie par deux foyers $F_1, F_2$ et demi-axe $0 < a < c$ ; calcul de centre, demi-axe conjugué $b = \sqrt{c^2 - a^2}$, sommets et asymptotes.
   - Rejet immédiat de toute configuration dégénérée (points colinéaires, foyer sur directrice, $2a \ge 2c$) via renvoi de `None` dans les méthodes de fabrique.
2. **Évaluation incrémentale dans le document** :
   - Recettes : `ellipse` (2 foyers + point), `ellipse_center` (centre + direction grand axe + demi-axe $b$), `parabola` (foyer + directrice), `hyperbola` (2 foyers + point ou paramètre $a$).
   - Propagation naturelle des invalidations et recalculs lorsque les points ou droites supports sont déplacés.
3. **Hit-testing et rendu adaptatif** :
   - Bounding boxes pour élimination rapide.
   - Évaluation de distance euclidienne / écart quadratique pour hit-testing précis à la tolérance de clic.
   - Rendu `QPainter.drawEllipse` avec rotation pour ellipses ; échantillonnage adaptatif borné au viewport pour les branches infinies de paraboles et hyperboles.
4. **Persistance et Undo/Redo** :
   - Sérialisation transparente des types `ellipse`, `ellipse_center`, `parabola`, `hyperbola` dans le schéma .pgl standard.
   - Commandes Undo/Redo standard (`CreateObjectsCommand`, `ChangeParametersCommand`, `MovePointCommand`).
5. **Panneaux Propriétés et Algèbre** :
   - Catégorisation "Coniques" dans l'arbre d'algèbre avec affichage des paramètres caractéristiques.
   - Restitution complète des propriétés analytiques dans le panneau Propriétés (équations, foyers, directrice, asymptotes, excentricité, sommets, paramètre).

### Conséquences
- Architecture propre et découplée, exempte de hacks à base de polylines persistées.
- Fluidité de rendu optimale même lors de zooms et pans sur des branches ouvertes.
- Compatibilité descendante et ascendante complète des documents .pgl.

## ADR-039 — Modèle dédié de courbes paramétriques x(t), y(t), sampling adaptatif et discontinuités

### Contexte
La version 1.2 introduit les courbes planes définies paramétriquement sous la forme $(x(t), y(t))$ pour $t \in [t_{min}, t_{max}]$. Ces objets requièrent une gestion sécurisée des expressions, la détection des variables externes (curseurs), un échantillonnage préservant la fidélité visuelle sans lier artificiellement les branches disjointes lors de singularités, et une intégration complète avec l'UI, le rendu, l'export et la persistance.

### Décision
1. **Modèle explicite `ParametricFunctionObject`** (`pygeolab.math_engine.functions`) :
   - Objet immuable distinct de `FunctionObject` stockant les deux arbres d'expressions syntaxiques $x(t)$ et $y(t)$, le nom du paramètre $t$ et les bornes fermées $[t_{min}, t_{max}]$.
   - Extraction automatique des dépendances externes vers les curseurs : $\text{deps} = (\text{vars}(x) \cup \text{vars}(y)) \setminus \{t\}$.
   - Évaluation sécurisée via le moteur d'expressions sans `eval()` ni `exec()`.
2. **Échantillonnage et coupure sur discontinuité** (`pygeolab.math_engine.sampling`) :
   - Fonction `sample_parametric` évaluant la trajectoire par pas régulier de paramètre.
   - Détection des singularités par analyse de distance euclidienne et écart non-linéaire au point médian, isolant les asymptotes en polylignes disjointes (`SampledFunction`).
3. **Persistance et Undo/Redo** :
   - Type d'objet `parametric` dans `GeoObject` et `KINDS`.
   - Compatibilité totale avec `CreateObjectCommand` et `ChangeFunctionCommand`.
4. **Interface utilisateur** :
   - Dialogue dédié `ParametricFunctionDialog` pour la saisie et modification des expressions et du domaine.
   - Entrées dans le menu Objets, section "Courbes paramétriques" dans le panneau Algèbre et restitution analytique dans le panneau Propriétés.

### Conséquences
- Modèle mathématique robuste et explicite, découplé du moteur de rendu.
- Visualisation fidèle des spirales, cycloïdes, courbes de Lissajous et coniques paramétrées sans artefacts visuels.
- Respect absolu des contraintes de sécurité et de persistance versionnée .pgl.


