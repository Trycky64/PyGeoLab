# Changelog

**Français** · [English](CHANGELOG.md)

Toutes les modifications notables de PyGeoLab sont documentées ici.

## 1.3.0 — 2026-10-18

### Ajouté

- modèle métier tabulaire immuable `DatasetObject` avec validation numérique stricte, représentations 1D et bivariées (X/Y) et métadonnées ;
- moteur de statistiques descriptives complet (effectif, somme, moyenne, médiane, min, max, étendue, variances population et échantillon, écart-type, quartiles $Q_1$/$Q_3$, intervalle interquartile, centiles et détection des valeurs aberrantes de Tukey) ;
- moteur de statistiques bivariées (covariance, corrélation linéaire de Pearson, régression linéaire OLS, $R^2$, résidus et prédictions) ;
- visualisations statistiques intégrées au moteur de rendu : nuage de points, droite de régression, histogramme, boîte à moustaches et diagramme en barres, avec hit-testing, sélection et export PNG/SVG ;
- tableur léger `DataTablePanel` tabifié avec la Timeline et la Table de valeurs, supportant l'ajout/suppression dynamique de lignes/colonnes, la navigation clavier et le copier/coller TSV ;
- moteur d'ajustement non-linéaire (polynômes de degrés 1 à 5 par élimination de Gauss à pivot partiel, régressions exponentielles, logarithmiques et puissances) produisant des instances `FunctionObject` sûres sans `eval()` ni `exec()` ;
- intégration complète au graphe de dépendances : génération réactive de datasets depuis des points du canevas, polygones, lieux géométriques, curseurs et échantillonnage de fonctions, avec dérivation de points (barycentre, ligne) et de droites de régression ;
- importation et exportation CSV robustes avec détection automatique multi-lignes du délimiteur et de la virgule décimale, support UTF-8 avec ou sans BOM, chemins Unicode, gestion des valeurs manquantes (rejet, exclusion, remplissage) et plafonds de taille sécurisés ;
- projet exemple `examples/stats_modeling.pgl` et guides utilisateurs complets en français et anglais.

## 1.2.0 — 2026-10-17

### Ajouté

- coniques euclidiennes : ellipses (foyers + point, centre + axes), paraboles (foyer + directrice) et hyperboles (foyers + point/paramètre) avec intégration au graphe de dépendances, bounding boxes, échantillonnage adaptatif et métriques analytiques (excentricité, périmètre, aire, paramètre focal, directrice, asymptotes) ;
- courbes paramétriques $x(t), y(t)$ avec parsing sécurisé, détection des curseurs dépendants, échantillonnage adaptatif, isolation des discontinuités et dialogue dédié ;
- courbes polaires $r(\theta)$ avec choix d'unité angulaire (radians/degrés), conversions automatiques, repliement périodique et dialogue dédié ;
- édition analytique directe et inspection interactive des équations dans les panneaux Propriétés et Algèbre avec copie souris ;
- lieux géométriques (`Locus2D`) par sous-graphe isolé, persistance légère recalculable et traces transitoires à l'écran ;
- timeline multi-curseurs globale avec barre de transport (Play/Pause/Stop), scrubbing fluide, modes boucle/aller-retour, durée et FPS configurables ;
- panneau de table de valeurs (`ValueTablePanel`) avec affichage tabulaire virtualisé, navigation clavier, copie presse-papiers et export CSV UTF-8 ;
- compatibilité descendante validée pour les fichiers `.pgl` versions 1.0 et 1.1.

## 1.1.1 — 2026-09-09

### Ajouté

- catalogue anglais complet avec sélection automatique selon la langue du système ;
- préférence persistante Système, English ou Français ;
- README, guide utilisateur, changelog et notes de release en anglais et en français ;
- métadonnées publiques et fins de ligne normalisées entre plateformes.

### Modifié

- la documentation publique utilise désormais l'anglais comme langue d'entrée ;
- les archives Windows et Linux incluent les documents dans les deux langues.

### Supprimé

- checklist interne terminée, anciennes maquettes SVG et notes de préparation portfolio.

## 1.1.0 — 2026-09-09

### Ajouté

- snapping configurable sur grille, points, projections et intersections ;
- outils avancés : demi-droite, vecteur, médiatrice, bissectrice, projection, point sur objet,
  cercles, transformations et mesures dynamiques ;
- sélection rectangulaire et multiple, édition groupée, duplication et gestion de l'ordre ;
- recherche, tri, regroupement et édition directe dans les panneaux Algèbre et Propriétés ;
- création et édition de fonctions avec sampling adaptatif, dérivée, racines, extrema et
  intersections optionnels ;
- curseurs éditables et animables avec lecture aller-retour sans pollution de l'historique ;
- panneau d'analyse numérique pour dérivées, intégrales, racines, extrema et intersections ;
- fichiers récents, autosave atomique et récupération après incident ;
- préférences centralisées, thèmes, accessibilité clavier et aide des raccourcis ;
- exports du document ou de la sélection en PNG/SVG et copie vers le presse-papiers ;
- diagnostics système, erreurs contextualisées et ouverture du dossier de logs.

### Amélioré

- rendu des fonctions mis en cache et accéléré pour les scènes chargées ;
- hit-testing des objets superposés et cycle de sélection ;
- détection des discontinuités et suppression des segments à travers les asymptotes ;
- tests de stabilité jusqu'à 10 000 objets et nettoyage des ressources Qt à la fermeture ;
- documentation utilisateur, captures, démonstration et décisions architecturales.

### Distribution

- validation sous Python 3.12, 3.13 et 3.14 sur Windows et Linux ;
- smoke test des exécutables PyInstaller avant archivage ;
- métadonnées Windows et Linux, icônes, licence et notes incluses dans les paquets ;
- compatibilité vérifiée avec les projets `.pgl` créés par PyGeoLab 1.0.

## 1.0.0 — 2026-09-05

### Ajouté

- moteur de géométrie euclidienne immutable et robuste ;
- graphe de dépendances avec recalcul incrémental et invalidité récupérable ;
- viewport 2D avec grille adaptative, pan, zoom et rendu Qt ;
- outils de construction, sélection, déplacement et previews ;
- historique Undo/Redo basé sur le Command Pattern ;
- panneaux Algèbre, Propriétés et Curseurs ;
- parser mathématique sécurisé sans `eval` ni `exec` ;
- analyse numérique : dérivée, intégrale, racines, extrema et intersections ;
- format projet `.pgl` JSON versionné avec migration et validation ;
- export PNG et SVG, résolution configurable et fond transparent ;
- thèmes clair/sombre, préférences persistantes, logs rotatifs et gestion globale des erreurs ;
- builds PyInstaller Windows/Linux et workflow de release GitHub Actions.
