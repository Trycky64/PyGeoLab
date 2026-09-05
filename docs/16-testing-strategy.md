# 16 — Stratégie de tests

## Priorités

La logique mathématique doit être beaucoup plus testée que l'interface graphique.

## Tests unitaires

### Géométrie

Tester :

- distances ;
- intersections ;
- projections ;
- angles ;
- transformations ;
- polygones.

### Dépendances

Tester :

- ordre de recalcul ;
- propagation ;
- suppression ;
- invalidation ;
- cycles.

### Math

Tester :

- parsing ;
- priorité des opérateurs ;
- fonctions ;
- erreurs ;
- variables.

### Persistance

Tester :

- round-trip ;
- versions ;
- migrations ;
- fichiers invalides.

## Tests d'intégration

Scénarios complets.

Exemple :

1. créer A ;
2. créer B ;
3. créer AB ;
4. créer M milieu de AB ;
5. déplacer A ;
6. vérifier M.

## Tests UI

Limiter aux parcours essentiels :

- création document ;
- sélection ;
- action toolbar ;
- sauvegarde.

## Property-based testing

Hypothesis pourra vérifier des invariants.

Exemple :

```text
distance(A, B) == distance(B, A)
```

ou :

```text
projection(P, line) appartient à line
```

à tolérance numérique près.
