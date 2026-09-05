# 04 — Modèle métier

## Document

Le `Document` représente une construction PyGeoLab.

Il contient :

- metadata ;
- paramètres de scène ;
- objets ;
- variables ;
- historique logique ;
- configuration de visibilité.

## BaseObject

Chaque objet logique dérive conceptuellement de `GeoObject`.

Propriétés communes :

- `id` ;
- `name` ;
- `visible` ;
- `locked` ;
- `style` ;
- `dependencies` ;
- `valid` ;
- `error_state`.

## Identifiants

Les identifiants doivent être :

- uniques ;
- immuables ;
- indépendants du nom utilisateur.

UUID recommandé.

## Noms

Les noms visibles peuvent être :

- `A`, `B`, `C` ;
- `d`, `e` ;
- `c1` ;
- `f` ;
- noms personnalisés.

Le nom n'est jamais utilisé comme identité interne.

## État valide/invalide

Une construction peut être temporairement impossible.

Exemple :

- intersection de deux droites parallèles.

L'objet doit rester présent mais être marqué comme invalide.

Il peut redevenir valide automatiquement lorsque ses dépendances changent.
