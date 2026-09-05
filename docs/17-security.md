# 17 — Sécurité

## Expressions utilisateur

La principale surface de sécurité vient du moteur d'expressions.

Interdictions :

- `eval()` brut ;
- `exec()` ;
- imports ;
- accès attribut arbitraire ;
- appels de fonctions Python non autorisées ;
- accès au système de fichiers depuis une expression.

## Fichiers

Un fichier `.pgl` est traité comme donnée non fiable.

Le loader doit :

- vérifier les types ;
- limiter les tailles extrêmes ;
- refuser les structures inconnues dangereuses ;
- gérer proprement les références invalides.

## Export

Les chemins d'export sont choisis par l'utilisateur.

## Plugins

Aucun système de plugins exécutables dans le MVP.

Un éventuel système futur devra être conçu séparément avec un modèle de confiance explicite.
