# PyGeoLab 1.0.0

Première release stable de PyGeoLab.

## Points forts

- géométrie dynamique avec dépendances et recalcul incrémental ;
- viewport 2D interactif, outils de construction et Undo/Redo ;
- moteur d'expressions mathématiques sécurisé ;
- curseurs numériques et analyse numérique ;
- projets `.pgl` versionnés et validés ;
- export PNG/SVG ;
- thèmes clair/sombre, préférences et logs ;
- archives desktop Windows et Linux construites avec PyInstaller.

## Vérification rapide

1. lancer PyGeoLab ;
2. ouvrir `examples/demo.pgl` ;
3. déplacer A/B/C ou modifier le curseur `a` ;
4. vérifier le recalcul des objets et de la fonction ;
5. tester Undo/Redo ;
6. exporter en PNG puis SVG ;
7. enregistrer et rouvrir le projet.

## Distribution

Le workflow GitHub `Release` produit :

- `PyGeoLab-Windows-x64.zip` ;
- `PyGeoLab-Linux-x64.tar.gz`.

Créer le tag `v1.0.0` après validation de la CI pour publier la release.
