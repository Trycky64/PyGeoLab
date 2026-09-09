# 21 — Accessibilité et internationalisation

## Accessibilité 1.0

- navigation clavier via les widgets Qt natifs ;
- raccourcis cohérents pour fichier, historique et outils principaux ;
- noms accessibles explicites pour viewport, docks, toolbar, status bar et actions ;
- thèmes clair/sombre avec palettes à contraste élevé ;
- sélection signalée par une surépaisseur en plus de la couleur ;
- tailles de contrôles standard Qt et labels associés dans les formulaires.

Les informations importantes ne dépendent donc pas uniquement de la couleur.

## Accessibilité 1.1

- la liste des raccourcis est accessible par `F1` et ne bloque pas la fenêtre principale ;
- les collisions de raccourcis, noms et descriptions accessibles sont couvertes par les tests UI ;
- tous les contrôles focalisables participent à la chaîne de focus Qt ;
- boutons, champs et listes déroulantes ont une hauteur minimale de 28 pixels ;
- le focus clavier reçoit un contour de deux pixels utilisant la couleur de sélection ;
- les rapports de contraste du texte normal et sélectionné atteignent au moins 4,5:1 dans les
  thèmes clair et sombre ;
- la barre d'état verbalise les changements d'outil et de sélection.

## Internationalisation

Les chaînes UI passent par `tr()` dans les widgets principaux. Le format de stockage reste
invariant (`.` pour les nombres JSON) indépendamment de la locale. Une traduction anglaise
complète reste une extension future.
