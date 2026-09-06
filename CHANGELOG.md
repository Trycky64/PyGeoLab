# Changelog

Toutes les modifications notables de PyGeoLab sont documentées ici.

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
