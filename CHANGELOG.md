# Changelog

Toutes les modifications notables de PyGeoLab sont documentées ici.

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
