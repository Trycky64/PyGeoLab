# 07 — Moteur d'expressions mathématiques

## Objectif

Permettre des expressions telles que :

```text
sin(x)
x^2 + 3*x - 1
a * cos(x)
sqrt(x + 2)
```

## Sécurité

Interdiction absolue de faire :

```python
eval(user_input)
```

sur le texte brut de l'utilisateur.

## Grammaire minimale

Support :

- nombres ;
- variables ;
- parenthèses ;
- opérateurs `+ - * / ^` ;
- moins unaire ;
- appels de fonctions autorisées.

## Variables

Les variables peuvent provenir :

- d'un curseur ;
- d'une constante ;
- d'une mesure géométrique ;
- d'une autre expression.

## Fonctions intégrées

Liste initiale :

```text
sin cos tan
asin acos atan
sqrt abs
exp ln log10
floor ceil
min max
```

## Constantes

```text
pi
e
```

## AST interne

Une expression doit devenir un arbre interne.

Exemple :

```text
x^2 + 1
```

```text
Add
├── Pow
│   ├── Variable(x)
│   └── Number(2)
└── Number(1)
```

## Fonction

Une `FunctionObject` contient :

- nom ;
- variable principale ;
- expression AST ;
- dépendances externes ;
- domaine optionnel.

## Évaluation

API conceptuelle :

```text
evaluate(x=...)
```

## Sampling

Pour le tracé :

1. déterminer l'intervalle visible ;
2. générer des valeurs X ;
3. calculer Y ;
4. détecter les discontinuités ;
5. générer une polyline adaptée.

## Discontinuités

Le renderer ne doit pas tracer de segment à travers une asymptote.

Critères possibles :

- valeur non finie ;
- saut trop important ;
- erreur d'évaluation.

## Calcul numérique

La 1.0 implémente dans `math_engine/numerical.py` :

- dérivée numérique ;
- intégration numérique ;
- recherche de racines ;
- extrema ;
- intersections de fonctions.

Ces méthodes restent indépendantes de Qt et sont couvertes par des tests unitaires.

## Intégration au document en 1.0

Une fonction persistante est représentée par un `GeoObject(kind="function")`. Ses paramètres
conservent l'expression source, la variable principale et le domaine optionnel ; ses dépendances
UUID pointent vers les objets numériques utilisés comme variables externes. L'évaluation produit
un `FunctionObject` sûr, ce qui raccorde directement les sliders au recalcul des courbes.
