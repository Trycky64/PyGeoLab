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


## ADR-040 — Modèle dédié de courbes polaires r(θ), conversion angulaire et affichage en degrés

### Contexte
La version 1.2 introduit les courbes définies en coordonnées polaires sous la forme $r(\theta)$ pour $\theta \in [\theta_{min}, \theta_{max}]$. Le domaine géométrique impose une représentation angulaire unifiée en radians en interne, tout en autorisant optionnellement la saisie et l'affichage en degrés pour le confort de l'utilisateur.

### Décision
1. **Modèle `PolarFunctionObject`** (`pygeolab.math_engine.functions`) :
   - Stockage immuable de l'expression $r(\theta)$, du paramètre angulaire (ex. `theta`), des bornes $[\theta_{min}, \theta_{max}]$ en radians, et d'un indicateur `use_degrees: bool` pour l'affichage UI.
   - Conversion cartésienne dynamique : $\text{evaluate}(\theta) \to (r \cos\theta, r \sin\theta)$.
   - Dépendances externes vers les curseurs : $\text{deps} = \text{vars}(r) \setminus \{\theta\}$.
2. **Échantillonnage et coupures singulières** (`pygeolab.math_engine.sampling`) :
   - Fonction `sample_polar` avec pas régulier angulaire et détection robuste des asymptotes et pôles ($r \to \infty$ ou discontinuités de signe/amplitude).
3. **Persistance et Undo/Redo** :
   - Type d'objet `polar` dans `GeoObject` et `KINDS`.
   - Compatibilité totale avec `CreateObjectCommand` et `ChangeFunctionCommand`.
4. **Interface utilisateur et panneaux** :
   - Dialogue dédié `PolarFunctionDialog` avec bascule dynamique temps réel entre radians et degrés, validation des curseurs et aperçu de style.
   - Catégorie "Courbes polaires" dans le panneau Algèbre et restitution analytique de l'équation et de l'intervalle angulaire dans le panneau Propriétés.

### Conséquences
- Modélisation mathématique rigoureuse (radians canoniques en interne, zéro ambiguïté dimensionnelle).
- Tracé fluide et précis des cardioïdes, limaçons de Pascal, roses géométriques et spirales d'Archimède.
- Parfaite cohérence avec le graphe de dépendances, le hit-testing et l'export vectoriel.

## ADR-041 : Lieux géométriques et traces dynamiques (Section 7)

### Contexte
Dans les logiciels de géométrie dynamique avancés (ex. GeoGebra, Cabri), les utilisateurs ont besoin d'étudier la trajectoire d'un point géométrique dépendant lorsqu'un point support ou un paramètre (curseur) varie de manière continue. Deux mécanismes distincts répondent à ce besoin :
1. Les **lieux géométriques persistants** (`Locus2D` / `kind="locus"`), objets mathématiques du domaine définis par un point cible $T$ et une variable pilote $P$, recalculés dynamiquement selon un sous-graphe topologique de dépendances.
2. Les **traces éphémères** (canvas traces), activées à la volée sur un point quelconque pour visualiser sa trajectoire lors des manipulations interactives à la souris ou des animations, sans alourdir le modèle persistant.

### Décisions d'architecture
1. **Modèle de domaine Locus2D & Persistance allégée** :
   - `Locus2D` encapsule une séquence ordonnée de polylignes continues (`tuple[tuple[Point2D, ...], ...]`), les identifiants de cible et de pilote, ainsi que les bornes et le nombre d'échantillons.
   - Les points échantillonnés ne sont **pas** persistés dans le fichier `.pgl` ; seuls la recette géométrique et les paramètres (`start`, `end`, `samples`) sont sauvegardés. Le document recalcule le lieu à l'ouverture et lors de la modification des ancêtres.
2. **Échantillonnage en sous-graphe isolé** (`pygeolab.geometry.locus.sample_locus`) :
   - Pour chaque valeur du pilote dans $[start, end]$, le sous-graphe des dépendances entre le pilote et la cible est évalué sur un clone d'état léger sans polluer le document principal.
   - Rejet automatique des discontinuités (sauts de distance excessifs ou singularités) en créant de nouveaux segments disjoints.
3. **Traces transitoires hors modèle** :
   - Gérées au niveau de `GeometryView` dans une table `_transient_traces` indexée par identifiant d'objet.
   - Aucune modification de l'historique Undo/Redo lors du traçage à l'écran, effacement instantané via l'action dédiée et le menu contextuel.
4. **Intégration UI & Rendu** :
   - Dialogue `LocusDialog` avec sélection guidée des cibles valides et pilotes disponibles.
   - Prise en charge dans `AlgebraPanel` (catégorie dédiée "Lieux géométriques"), `PropertiesPanel` (édition interactive de `start`, `end`, `samples`), `Renderer` (rendu vectoriel anti-aliasé), `HitTest` et export de vue (`fitted_viewport`).

## ADR-042 : Timeline et animation multi-sliders synchronisée (Section 8)

### Contexte
L'animation indépendante slider par slider ne permettait pas de synchroniser des constructions complexes (ex. mécanismes articulés avec plusieurs degrés de liberté, visualisations physiques temporelles, balayages paramétriques conjoints). Une timeline globale avec barre de transport (Play, Pause, Stop), scrubbing instantané, marqueurs de boucle et interpolation déterministe était requise.

### Décisions d'architecture
1. **Contrôleur métier découplé `TimelineController`** :
   - Encapsule l'état d'animation temporel : durée, tête de lecture (`current_time` / `normalized_time`), FPS, vitesse globale, mode boucle, mode ping-pong, marqueurs de début et de fin.
   - Fournit une méthode `advance(delta_seconds)` pure et déterministe pour des tests unitaires rapides et fiables sans dépendance temporelle aux timers Qt.
   - Gère la capture d'état initial (`save_initial_state`) et la restauration optionnelle sans pollution de l'historique Undo/Redo.
2. **Interface utilisateur `TimelineWidget` et Dock dédié** :
   - Panneau dockable en bas de l'écran avec boutons de transport, affichage numérique du temps ($s$), slider de scrubbing fluide (1 000 crans), cases à cocher pour boucle et aller-retour, et spinboxes de précision pour marqueurs, durée et vitesse.
   - Raccourcis clavier globaux : `Space` pour Lecture / Pause, `Escape` pour Arrêter l'animation.
3. **Préférences applicatives et configuration centralisée** :
   - Nouveaux paramètres persistants `timeline_fps` (10 à 120 FPS) et `timeline_speed` (0.1× à 10.0×), configurables via `PreferencesDialog` et restaurables par défaut.

## ADR-043 : Panneau de tables de valeurs avec modèle tabulaire virtualisé (Section 9)

### Contexte
L'étude des fonctions analytiques cartésiennes, paramétriques et polaires nécessite un outil tabulaire d'évaluation discrète permettant de calculer des valeurs à pas régulier, d'afficher les indéterminations ou erreurs d'évaluation proprement sans blocage, de copier les données ou de les exporter vers des tableurs au format CSV.

### Décisions d'architecture
1. **Modèle de données tabulaire `ValueTableModel` (`QAbstractTableModel`)** :
   - Prise en charge universelle des fonctions cartésiennes ($x \mapsto f(x)$), courbes paramétriques ($t \mapsto (x(t), y(t))$) et polaires ($\theta \mapsto r(\theta)$ ou $(\theta, x, y)$).
   - Génération dynamique et virtualisée jusqu'à 50 000 lignes (`MAX_ROWS`) à partir des paramètres de début, fin et pas.
   - Formatage adaptatif des nombres réels et affichage clair des singularités (`ND`, `NaN`, `Inf`, `Div/0`).
2. **Interface utilisateur `ValueTablePanel` et Docking** :
   - Intégration en dock inférieur tabifié avec la Timeline (`value_table_dock`).
   - Commandes interactives pour définir la plage ($start$, $end$, $step$) avec validation en direct (rejet des pas nuls ou bornes inversées).
   - Copie presse-papiers tabulée compatible tableurs (Excel, LibreOffice Calc) et export direct en fichier `.csv` encodé en UTF-8.
   - Nettoyage propre lors de la fermeture ou du changement de document (`dispose`).






