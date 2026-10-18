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

