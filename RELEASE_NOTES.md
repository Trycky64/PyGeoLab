# PyGeoLab 1.1.0

PyGeoLab 1.1 enrichit la géométrie dynamique, le tracé de fonctions et le travail quotidien sur
des documents complexes. Cette version conserve le format `.pgl` version 1 et ouvre directement
les projets enregistrés avec PyGeoLab 1.0.

## Points forts

- snapping sur la grille, les points, les projections et les intersections ;
- nouveaux outils de construction, transformations et mesures dynamiques ;
- sélection multiple et rectangulaire avec commandes groupées et Undo/Redo ;
- panneaux Algèbre et Propriétés filtrables, triables et éditables ;
- fonctions éditables, courbes adaptatives et couches d'analyse optionnelles ;
- curseurs animés et panneau d'analyse numérique ;
- fichiers récents, autosave, récupération et préférences centralisées ;
- exports PNG/SVG du document complet ou de la sélection ;
- raccourcis documentés, navigation clavier et diagnostics enrichis.

## Compatibilité et plateformes

- projets `.pgl` PyGeoLab 1.0 compatibles sans conversion ;
- Python 3.12, 3.13 et 3.14 validés ;
- archives portables Windows x64 et Linux x64 testées au démarrage avant publication.

## Vérification rapide

1. lancer PyGeoLab ;
2. ouvrir `examples/demo.pgl` ;
3. déplacer A/B/C ou animer le curseur `a` ;
4. vérifier le recalcul des objets, mesures et courbes ;
5. tester la sélection multiple puis Undo/Redo ;
6. exporter la sélection en PNG puis le document en SVG ;
7. enregistrer et rouvrir le projet.

## Distribution

Le workflow GitHub `Release` produit :

- `PyGeoLab-Windows-x64.zip` ;
- `PyGeoLab-Linux-x64.tar.gz`.

Le tag `v1.1.0` déclenche les deux builds et publie automatiquement ces archives sur GitHub.
