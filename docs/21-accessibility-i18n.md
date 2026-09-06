# 21 — Accessibilité et internationalisation

## Accessibilité 1.0

- navigation clavier via les widgets Qt natifs ;
- raccourcis cohérents pour fichier, historique et outils principaux ;
- noms accessibles explicites pour viewport, docks, toolbar, status bar et actions ;
- thèmes clair/sombre avec palettes à contraste élevé ;
- sélection signalée par une surépaisseur en plus de la couleur ;
- tailles de contrôles standard Qt et labels associés dans les formulaires.

Les informations importantes ne dépendent donc pas uniquement de la couleur.

## Internationalisation

Les chaînes UI passent par `tr()` dans les widgets principaux. Le format de stockage reste
invariant (`.` pour les nombres JSON) indépendamment de la locale. Une traduction anglaise
complète reste une extension future.
