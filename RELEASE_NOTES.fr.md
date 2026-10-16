# PyGeoLab 1.2.0

**Français** · [English](RELEASE_NOTES.md)

PyGeoLab 1.2.0 est une version majeure introduisant les coniques euclidiennes, les courbes paramétriques et polaires, l'édition analytique directe d'équations, les lieux géométriques avec traces transitoires, une timeline d'animation multi-curseurs et un panneau de tables de valeurs virtualisé.

## Points forts

- **Coniques** : ellipses, paraboles et hyperboles avec modèles géométriques stricts, directrices, asymptotes, excentricité et fiches analytiques ;
- **Courbes paramétriques** : $(x(t), y(t))$ avec parsing sécurisé, échantillonnage adaptatif, isolation des singularités et liaison aux curseurs ;
- **Courbes polaires** : $r(\theta)$ avec prise en charge des radians et degrés, repliement périodique et dialogue dédié ;
- **Édition analytique** : modification d'équations en temps réel et inspection des propriétés analytiques avec copie souris ;
- **Lieux géométriques et traces** : calcul de lieux par sous-graphe isolé, persistance allégée sans sérialisation superflue de points, et traces transitoires ;
- **Timeline multi-curseurs** : barre de transport (Lecture/Pause/Stop), scrubbing fluide, durée, vitesse, modes boucle et aller-retour ;
- **Tables de valeurs** : tableur virtualisé haute performance pour fonctions cartésiennes, paramétriques et polaires, avec export CSV UTF-8 et copie presse-papiers ;
- **Snapping, mesures et transformations** : continuité complète des transformations euclidiennes, analyse numérique, mesures dynamiques et exports SVG/PNG.

## Compatibilité et plateformes

- projets `.pgl` PyGeoLab 1.0 et 1.1 compatibles sans conversion ;
- Python 3.12, 3.13 et 3.14 validés avec couverture de test supérieure à 85 % ;
- archives portables Windows x64 et Linux x64 testées au démarrage avant publication.

## Vérification rapide

1. lancer PyGeoLab ;
2. ouvrir `examples/demo.pgl` ;
3. animer la timeline ou jouer les curseurs avec `Espace` ;
4. vérifier le recalcul interactif des coniques, courbes paramétriques, rosaces et lieux ;
5. afficher le panneau Table de valeurs et exporter en CSV ;
6. tester la sélection multiple puis Undo/Redo ;
7. exporter en PNG puis en SVG ;
8. enregistrer et rouvrir le projet.

## Distribution

Le workflow GitHub `Release` produit :

- `PyGeoLab-Windows-x64.zip` ;
- `PyGeoLab-Linux-x64.tar.gz`.

Le tag `v1.2.0` déclenche les deux builds et publie automatiquement ces archives sur GitHub.
