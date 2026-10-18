# PyGeoLab 1.3.0

**Français** · [English](RELEASE_NOTES.md)

PyGeoLab 1.3.0 est une version majeure introduisant les jeux de données numériques, les statistiques descriptives et bivariées, cinq modes de visualisations statistiques, un tableur léger interactif, le fitting de modèles non linéaires et l'intégration réactive au graphe de dépendances géométrique.

## Points forts

- **Jeux de données (`DatasetObject`)** : modèle de données tabulaire immuable avec validation numérique stricte, séries 1D et X/Y, et métadonnées ;
- **Statistiques descriptives** : calcul instantané de l'effectif, somme, moyenne, médiane, min, max, étendue, variance, écart-type, quartiles, IQR et barrières de Tukey pour les valeurs aberrantes ;
- **Statistiques bivariées** : covariance, corrélation de Pearson, droite de régression linéaire des moindres carrés (OLS), $R^2$, résidus et prédiction ;
- **Visualisations statistiques** : nuages de points, droites de régression ajustées, histogrammes, boîtes à moustaches et diagrammes en barres avec hit-testing, sélection et exports SVG/PNG ;
- **Tableur interactif (`DataTablePanel`)** : éditeur tabulaire dockable avec ajout/suppression de lignes et colonnes, navigation clavier, copier/coller TSV et protection en lecture seule pour les datasets calculés dynamiquement ;
- **Ajustements de courbes (Fitting)** : régressions polynomiales (degrés 1 à 5), exponentielles, logarithmiques et puissances générant des objets `FunctionObject` traçables sans aucun `eval()` ni `exec()` ;
- **Intégration au graphe de dépendances** : génération dynamique de datasets depuis des points mobiles du canevas, polygones, lieux géométriques, curseurs ou échantillonnages de fonctions ; dérivation réactive de points (point moyen) et de droites de régression ;
- **Import/Export CSV robuste** : détection automatique multi-lignes du délimiteur et de la virgule décimale, gestion UTF-8 avec ou sans BOM, chemins Unicode et politiques de valeurs manquantes (rejet, exclusion, substitution) ;
- **Projet de démonstration** : projet `examples/stats_modeling.pgl` illustrant la géométrie dynamique couplée aux statistiques en temps réel.

## Compatibilité et plateformes

- projets `.pgl` PyGeoLab 1.0, 1.1 et 1.2 compatibles sans conversion ;
- Python 3.12, 3.13 et 3.14 validés avec couverture de test supérieure à 85 % ;
- archives portables Windows x64 et Linux x64 testées au démarrage avant publication.

## Vérification rapide

1. lancer PyGeoLab ;
2. ouvrir `examples/stats_modeling.pgl` ;
3. déplacer le point `P1` ou `P2` sur le canevas : observer la mise à jour réactive du dataset `NuageMobile`, du barycentre `G_moyen` et de la droite de régression `Droite_OLS` ;
4. sélectionner `NuageMobile` et examiner les statistiques descriptives dans le panneau Propriétés ;
5. changer le mode de tracé statistique en Histogramme, Boîte à moustaches ou Barres dans le panneau Données ;
6. tester l'exportation et l'importation CSV ;
7. enregistrer et rouvrir le projet.

## Distribution

Le workflow GitHub `Release` produit :

- `PyGeoLab-Windows-x64.zip` ;
- `PyGeoLab-Linux-x64.tar.gz`.

Le tag `v1.3.0` déclenche les deux builds et publie automatiquement ces archives sur GitHub.
