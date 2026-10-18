# Décisions d'architecture — PyGeoLab 1.3

Ce document consigne les Décisions d'Architecture (ADR) spécifiques au cycle de développement de PyGeoLab 1.3 (Données, statistiques et modélisation).

---

## ADR-044 : Modèle métier immuable DatasetObject et découplage des données tabulaires

### Contexte
La version 1.3 introduit les données, les statistiques et la modélisation dans PyGeoLab. Les données doivent pouvoir représenter des séries unidimensionnelles (1D), des séries bivariées appariées (X/Y) ou des tables multivariées à $N$ colonnes. Pour respecter l'architecture du domaine, les jeux de données doivent être immuables, strictement validés, indépendants de toute dépendance à Qt, sérialisables sans perte dans le format `.pgl`, compatibles avec les commandes Undo/Redo et intégrables dans le graphe de dépendances.

### Décisions d'architecture
1. **Modèle de données métier `DatasetObject`** (`pygeolab.data.dataset`) :
   - Structure immuable `@dataclass(frozen=True, slots=True)` encapsulant :
     - `name`: nom du jeu de données (chaîne non vide) ;
     - `column_names`: tuple de noms de colonnes uniques et non vides ;
     - `rows`: tuple de tuples de réels finis (`float`), chaque ligne possédant exactement la même arité que `column_names` ;
     - `metadata`: dictionnaire en lecture seule (`MappingProxyType`) pour stocker unités, source, horodatage ou contexte d'acquisition.
   - Rejet strict à l'instanciation de toute valeur non numérique, `NaN` ou infinie (`math.isfinite`).
   - Méthodes et propriétés utilitaires :
     - `row_count`, `col_count`, `is_empty`, `is_1d`, `is_2d` ;
     - Extraction de colonne `column(index_or_name)` ;
     - Séries numériques `x_values` et `y_values` ;
     - Extraction géométrique `points -> tuple[Point2D, ...]` permettant la compatibilité avec les nuages de points et le rendu canvas ;
     - Méthodes de copie non destructive `with_rows` et `with_metadata`.
2. **Couche I/O CSV robuste et sécurisée** (`pygeolab.data.csv_io`) :
   - Détection heuristique automatique du délimiteur (`,`, `;`, `\t`, espace) et du séparateur décimal (point ou virgule).
   - Prise en charge des fichiers UTF-8 avec ou sans BOM (`utf-8-sig`).
   - Contrôle strict du volume (`max_rows` paramétrable, par défaut 100 000 lignes) pour prévenir les attaques par déni de service mémoire.
   - Messages d'erreur contextualisés indiquant le numéro de ligne, la colonne et le motif de rejet.
3. **Intégration au modèle Document et persistance** :
   - Ajout du type `"dataset"` dans `KINDS` et inclusion de `DatasetObject` dans l'union `Geometry` (`pygeolab.model.objects`).
   - Évaluation et résolution pure dans `eval_object` (`pygeolab.model.constructions`).
   - Persistance transparente dans `.pgl` via la méthode `to_dict()` sans altération du schéma 1.0/1.1/1.2.
   - Intégration complète dans `CommandHistory` : création (`CreateObjectCommand`) et mise à jour (`ChangeParametersCommand`) avec Undo/Redo instantané.
4. **Intégration UI et Traduction** :
   - Catégorisation sous "Jeux de données" / "Datasets" dans `AlgebraPanel` avec affichage du format `N cols, M lignes`.
   - Carte analytique dédiée dans `PropertiesPanel` affichant dimensions, noms de colonnes et métadonnées associées.
   - Traduction complète en français et en anglais dans `pygeolab.ui.translations`.

### Conséquences
- Architecture statistique totalement découplée de Qt et facilement testable par de simples tests unitaires rapides.
- Élimination des régressions sur la manipulation du graphe de dépendances et la persistance.
- Base solide pour les calculs de statistiques descriptives, bivariées et régressions (sections suivantes).

---

## ADR-045 : Moteur de statistiques descriptives déterministe et haute précision

### Contexte
La version 1.3 nécessite le calcul de résumés statistiques descriptifs complets sur les séries numériques (effectif, somme, moyenne, médiane, extrêmes, étendue, variance de population et d'échantillon, écarts-types, quartiles, écart interquartile IQR, percentiles quelconques et détection des valeurs aberrantes). Ces opérations doivent être mathématiquement rigoureuses, déterministes, sans dépendance tierce complexe, et tolérantes aux cas limites (série vide, singleton, valeurs constantes).

### Décisions d'architecture
1. **Module métier `pygeolab.data.statistics`** :
   - Fonctions pures et déterministes :
     - `percentile(values, p)` : calcul de percentile par interpolation linéaire continue standard (équivalent NumPy `linear` / Excel `PERCENTILE.INC`).
     - `quartiles(values)` : retourne $(Q_1, Q_2, Q_3)$ via `percentile` à 25%, 50% et 75%.
     - `detect_outliers(values, k=1.5)` : identification des valeurs aberrantes selon les barrières de Tukey ($x < Q_1 - k \cdot \text{IQR}$ ou $x > Q_3 + k \cdot \text{IQR}$).
     - `compute_descriptive_stats(values)` : calcule l'ensemble des grandeurs et retourne un conteneur immuable `@dataclass(frozen=True) DescriptiveStats`.
2. **Gestion rigoureuse des cas limites** :
   - Ensemble vide : levée explicite de `ValueError` descriptive.
   - Singleton ($N = 1$) : moyenne = médiane = min = max = valeur, étendue = 0, variance population = 0, variance échantillon = `None` ($N-1 = 0$), aucun outlier.
   - Série constante : variance population = variance échantillon = étendue = IQR = 0.
   - Rejet immédiat de toute valeur non finie (`NaN`, $\pm\infty$) avec indication de l'indice en faute.
3. **Intégration au modèle `DatasetObject` et aux panneaux UI** :
   - Méthode `DatasetObject.descriptive_stats(col=0)` permettant une extraction directe des métriques de n'importe quelle colonne par index ou nom.
   - Affichage synthétique automatique dans le panneau Propriétés (`PropertiesPanel`) dès qu'un dataset contenant des lignes est sélectionné.

---

## ADR-046 : Statistiques bivariées, corrélation de Pearson et régression linéaire OLS

### Contexte
La version 1.3 apporte l'analyse bivariée de séries appariées : covariance de population et d'échantillon, coefficient de corrélation linéaire de Pearson ($r$), régression par moindres carrés ordinaires ($y = ax + b$), coefficient de détermination ($R^2$), analyse des résidus et prédiction sur de nouvelles abscisses.

### Décisions d'architecture
1. **Module métier déterministe `pygeolab.data.bivariate`** :
   - Structure immuable `@dataclass(frozen=True) LinearRegressionResult` contenant `slope`, `intercept`, `r`, `r_squared`, `covariance`, `residuals`, et `count`.
   - Méthode d'évaluation `predict(x)` validant strictement la finitude de la variable explicative.
   - Fonction `covariance(x, y, sample=True)` calculant la covariance non biaisée (ou de population).
   - Fonction `pearson_correlation(x, y)` avec clamp strict dans $[-1.0, 1.0]$.
   - Fonction `linear_regression(x, y)` calculant les paramètres OLS, le vecteur des résidus $e_i = y_i - (\hat{a} x_i + \hat{b})$ et la variance expliquée $R^2$.
2. **Robustesse et validation stricte** :
   - Séries de tailles différentes ou vides : rejet immédiat avec exception explicite `ValueError`.
   - Série $X$ à variance nulle (droite verticale) : levée d'erreur car pente infinie.
   - Série $Y$ à variance nulle (droite horizontale) : pente $= 0$, ordonnée $= \bar{y}$, $r = 0$, $R^2 = 1.0$.
3. **Intégration au domaine et à l'interface** :
   - Méthodes directes sur `DatasetObject` : `covariance(col_x, col_y)`, `correlation(col_x, col_y)`, `linear_regression(col_x, col_y)`.
   - Affichage synthétique automatique de la covariance, de la corrélation, du $R^2$ et de l'équation de la droite dans `PropertiesPanel` pour les jeux de données 2D comportant au moins 2 lignes.

---

## ADR-047 : Rendu graphique des visualisations statistiques et hit-testing

### Contexte
Les séries statistiques et jeux de données tabulaires doivent pouvoir être représentés visuellement dans le plan de travail géométrique selon différents modes graphiques d'analyse de données :
- Nuage de points (*Scatter plot*)
- Droite de régression linéaire avec nuage de points
- Histogramme par classes automatiques (règle de la racine carrée)
- Boîte à moustaches (*Box plot* avec quartiles et barrières de Tukey pour les valeurs aberrantes)
- Diagramme en barres (*Bar chart*)

Ces représentations graphiques doivent respecter la séparation stricte Modèle / Rendu, être compatibles avec les styles (couleur, épaisseur, opacité de remplissage, taille de point), le hit-testing sous le curseur, la sélection interactive, et l'export PNG/SVG.

### Décisions d'architecture
1. **Attribut de mode de tracé `plot_kind` sur `DatasetObject`** :
   - Valeurs supportées : `"scatter"`, `"regression"`, `"histogram"`, `"boxplot"`, `"bar"`.
   - Sérialisation et désérialisation sans perte dans `.to_dict()` et `.from_dict()`.
   - Méthode immuable `.with_plot_kind(mode)` pour mise à jour sans mutation d'état.
2. **Moteur de rendu `Renderer._draw_dataset`** :
   - Mode `scatter` : tracé de disques de rayon paramétré avec bordure et remplissage translucide.
   - Mode `regression` : superposition des points d'observations et de la droite d'ajustement OLS découpée aux limites de la fenêtre mathématique active.
   - Mode `histogram` : découpage automatique en intervalles $[x_i, x_{i+1}]$ avec comptage des effectifs et tracé des rectangles d'effectifs sur l'axe des abscisses.
   - Mode `boxplot` : tracé de la boîte $[Q_1, Q_3]$, de la barre médiane, des moustaches raccordées aux extrêmes bornés par $1.5 \times \text{IQR}$, et des points d'outliers isolés.
   - Mode `bar` : tracé de colonnes d'amplitudes $y_i$ centrées sur les abscisses $x_i$.
3. **Hit-testing et sélection interactive (`hit_test.py`)** :
   - Intégration de `DatasetObject` dans `_PRIORITY` (priorité 1, juste après `Point2D`).
   - Calcul de distance minimale aux points du jeu de données dans `_distance_px`.
   - Détection d'intersection rectangulaire dans `_intersects_bounds` pour le lasso/boîte de sélection.
   - Ancrage d'étiquette sur le premier point de la série dans `Renderer._label_anchor`.

---

## ADR-048 : Tableur de données léger et interactif (DataTablePanel)

### Contexte
La manipulation manuelle ou tabulaire des jeux de données requiert une interface de type tableur permettant l'édition directe de cellules, l'insertion et la suppression dynamique de lignes et de colonnes, le copier-coller tabulaire via le presse-papiers, l'importation et l'exportation CSV, tout en s'intégrant au système Undo/Redo et en validant la nature strictement numérique des données.

### Décisions d'architecture
1. **Modèle de données Qt `DatasetTableModel`** (`pygeolab.ui.data_table_panel`) :
   - Sous-classe de `QAbstractTableModel` avec état de travail local modifiable.
   - Édition directe en cellule avec conversion stricte des séparateurs décimaux (virgule convertie en point).
   - Rejet immédiat de toute valeur non numérique ou non finie (`NaN`, $\pm\infty$).
   - Opérations de structure dynamiques : `add_row`, `remove_rows`, `add_column`, `remove_column` émettant les signaux de layout Qt appropriés.
   - Méthode de conversion déterministe `to_dataset(name, plot_kind)` produisant un `DatasetObject` immuable.
2. **Composant UI `DataTablePanel`** :
   - Sélecteur de dataset actif et sélecteur de mode de tracé statistique.
   - `QTableView` avec `QHeaderView.Stretch`, sélection étendue et navigation au clavier (Tab, touches fléchées).
   - Boutons de barre d'outils : ajout/suppression de lignes et colonnes, copie de plage sélectionnée vers le presse-papiers (format TSV), collage multi-lignes/colonnes avec extension automatique des dimensions de la table.
   - Importation et exportation de fichiers CSV avec dialogues natifs et gestion robuste des erreurs d'I/O.
3. **Intégration Document et Undo/Redo** :
   - Propagation des modifications par émission de `ChangeParametersCommand` vers l'historique d'actions de l'application.
   - Dockable dans `MainWindow` au bas de l'écran, tabifié aux côtés de la Timeline et de la Table de valeurs.

---

## ADR-049 : Moteur d'ajustements et de régressions (Curve Fitting Engine)

### Contexte
La modélisation de séries bivariées nécessite d'ajuster des modèles mathématiques continus au-delà de la droite linéaire OLS :
- Régressions polynomiales de degré $n \in [1, 5]$
- Régressions exponentielles $y = a \cdot e^{b \cdot x}$
- Régressions logarithmiques $y = a + b \cdot \ln(x)$
- Régressions puissances $y = a \cdot x^b$

Le moteur de calcul doit être indépendant de Qt, ne dépendre d'aucune bibliothèque externe (pur Python standard), valider rigoureusement les domaines de définition, calculer les métriques de qualité ($R^2$, résidus), et permettre de créer des objets de fonction mathématique (`FunctionObject`) injectables dans l'environnement géométrique sans aucun `eval()` / `exec()`.

### Décisions d'architecture
1. **Module `pygeolab.data.fitting`** :
   - `FitResult` : conteneur immuable (`dataclass(frozen=True)`) regroupant le type de modèle, les paramètres numériques ajustés, l'expression formelle sûre (compatible avec le parseur AST de PyGeoLab), le coefficient $R^2$, les résidus d'observation et la taille de l'échantillon.
   - Méthode `predict(x)` pour évaluer ponctuellement le modèle avec validation stricte de finitude et de domaine.
   - Méthode `to_function(name)` instanciant un `FunctionObject` prêt à être tracé ou référencé dans les expressions du document.
2. **Algorithmes de résolution numériques purs** :
   - `_solve_linear_system(matrix, vector)` : résolution matricielle $A \cdot x = b$ par élimination de Gauss-Jordan avec pivot partiel pour prévenir l'amplification d'erreurs d'arrondi sur les puissances élevées des équations normales.
   - `fit_polynomial(x, y, degree)` : formulation des équations normales $\left(X^T X\right) c = X^T y$ jusqu'au degré 5 avec validation $N > \text{degree}$.
   - `fit_exponential(x, y)` : linéarisation par transformation logarithmique $\ln(y) = \ln(a) + b \cdot x$ avec validation stricte $y_i > 0$.
   - `fit_logarithmic(x, y)` : ajustement linéaire sur la variable transformée $u = \ln(x)$ avec validation stricte $x_i > 0$.
3. **Intégration métier et UI** :
   - Méthodes directes sur `DatasetObject` : `fit_polynomial(degree)`, `fit_exponential()`, `fit_logarithmic()`.
   - Affichage synthétique du modèle quadratique et de son $R^2$ dans `PropertiesPanel` lorsque le dataset comporte au moins 3 points d'observation distincts.

---

## ADR-050 : Intégration des jeux de données au graphe de dépendances géométrique

### Contexte
La géométrie dynamique implique que les jeux de données ne doivent pas être cantonnés à des valeurs statiques. Ils doivent pouvoir être alimentés de manière réactive par des objets géométriques parents (points mobiles du canevas, sommets de polygones, trajectoires de lieux géométriques, curseurs/sliders ou échantillonnage régulier de fonctions mathématiques). Réciproquement, des objets géométriques doivent pouvoir être dérivés des jeux de données (points de coordonnées, point moyen/barycentre $(\bar{x}, \bar{y})$, droite de régression linéaire dynamique).

### Décisions d'architecture
1. **Évaluation réactive bidirectionnelle (`constructions.py`)** :
   - `kind == "dataset"` : extraction automatique des observations selon les types de parents reçus :
     - Parents `Point2D` : chaque point fournit une ligne $(x_i, y_i)$.
     - Parent `Polygon2D` : extraction des sommets dans l'ordre trigonométrique.
     - Parent `Locus2D` : extraction de l'échantillonnage de la trajectoire échantillonnée.
     - Parents scalaires/curseurs `float` : série 1D ou paires $(x_i, y_i)$ réévaluées à chaque pas de timeline/scrubbing.
     - Parent `FunctionObject` : discrétisation régulière sur un intervalle $[x_{\min}, x_{\max}]$ paramétrable.
   - `kind == "point"` : extraction réactive depuis un `DatasetObject` parent :
     - Mode `row` (défaut) : sélection de la ligne $i$.
     - Mode `mean` : calcul automatique du centre de gravité $(\bar{x}, \bar{y})$ via les statistiques descriptives du dataset.
   - `kind == "line"` : droite d'ajustement linéaire OLS dynamique calculée automatiquement sur le dataset parent.
2. **Propriétés de lecture seule et ergonomie UI (`data_table_panel.py`)** :
   - Lorsqu'un `DatasetObject` possède des dépendances (`obj.dependencies` non vide), le tableur passe automatiquement en mode lecture seule (`_read_only = True`), désactivant l'édition manuelle de cellules et les boutons d'ajout/suppression de lignes/colonnes tout en maintenant la sélection, la copie TSV et l'exportation CSV.
3. **Robustesse et invalidation fine** :
   - Le graphe de dépendances (`DependencyGraph`) détecte et interdit strictement tout cycle orienté (`CycleDetectedError` / `ValueError`), empêchant par exemple un point de dépendre d'un dataset qui dépendrait de ce même point.
   - Le recalcul incrémental document (`Document._commit`) n'invalide et ne réévalue que le sous-graphe des descendants directs et indirects, préservant intactes les constructions géométriques indépendantes.

---

## ADR-051 : Importation et exportation de données tabulaires robustes (CSV I/O Engine)

### Contexte
L'échange de données statistiques nécessite de pouvoir importer et exporter des fichiers CSV provenant d'environnements hétérogènes (Excel français avec séparateur point-virgule et virgule décimale, outils scientifiques anglo-saxons avec virgule et point décimal, TSV, fichiers avec ou sans BOM UTF-8, chemins Unicode). L'importation doit détecter automatiquement les séparateurs, valider strictement la nature numérique des données, gérer les politiques de valeurs manquantes et imposer des limites de dimensionnement sécurisées.

### Décisions d'architecture
1. **Module `pygeolab.data.csv_io`** :
   - `detect_delimiter(sample)` : analyse de cohérence multi-lignes des fréquences d'apparition des séparateurs candidats (`;`, `\t`, `,`, ` `) avec priorisation de `;` et `\t` face aux virgules numériques.
   - `detect_decimal_separator(sample, delimiter)` : détermination automatique du point ou de la virgule décimale selon les fréquences observées dans les jetons numériques.
   - Décodage Unicode sécurisé avec gestion du BOM (`utf-8-sig`) et repli gracieux (`latin-1`).
2. **Politique explicite des valeurs manquantes (`missing_policy`)** :
   - Détection des jetons standards : `""`, `"NA"`, `"N/A"`, `"NaN"`, `"null"`, `"?"`, `"-"`, `"none"`.
   - Trois politiques au choix :
     - `"error"` (défaut) : rejet immédiat avec indication précise de la ligne, colonne et valeur fautive.
     - `"skip"` : exclusion de la ligne incomplète.
     - `"fill"` : substitution par une valeur numérique de repli (`fill_value`, défaut $0.0$).
3. **Limites de sécurité et messages descriptifs** :
   - Plafonds par défaut de $100\,000$ lignes et $1\,000$ colonnes configurables.
   - Messages d'erreur explicites précisant le numéro de ligne 1-indexé, le nom de colonne et le texte non analysable.
4. **Méthodes d'accès sur `DatasetObject`** :
   - `DatasetObject.from_csv(source, ...)` pour l'instanciation directe depuis une chaîne ou un chemin de fichier `Path`.
   - `DatasetObject.to_csv(...)` et `DatasetObject.to_csv_file(path, ...)` pour la sérialisation avec contrôle du délimiteur, de la virgule décimale et de l'en-tête.




