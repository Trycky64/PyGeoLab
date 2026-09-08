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

## Édition et analyse visuelle en 1.1

Le menu **Objets > Nouvelle fonction** ouvre un éditeur pour le nom, la variable indépendante,
l'expression et un domaine facultatif. Les noms externes de l'expression sont résolus vers les
objets numériques de même nom ; une variable absente est signalée avant la création. La même
boîte modifie une fonction existante par une commande réversible unique.

Le sampling contrôle aussi le point milieu entre deux échantillons. Cette vérification sépare une
polyline lorsqu'une erreur, une croissance fortement non linéaire ou un changement de signe loin
de zéro révèle une asymptote située entre les positions échantillonnées.

Le menu **Affichage > Fonctions** propose trois qualités et quatre couches calculées à la demande :
racines, extrema, intersections et dérivées. Ces couches sont des options de scène persistantes et
ne créent aucun objet dans le document.

## Curseurs en 1.1

Le panneau Curseurs expose la valeur courante par glissière et saisie numérique. Les bornes et le
pas se modifient après création, tandis que **Reset** revient à la valeur initiale sérialisée. Les
anciens fichiers sans champ `initial` utilisent leur valeur chargée comme valeur de reset.

L'animation possède une vitesse en unités par seconde, une lecture cyclique ou aller-retour et une
commande lecture/pause. Elle conserve une position continue entre les frames avant d'appliquer le
pas configuré, afin qu'un petit déplacement finisse toujours par produire une nouvelle valeur.
Chaque frame appelle le recalcul incrémental du document sans ajouter de commande Undo.

## Panneau d'analyse numérique en 1.1

Le panneau Analyse numérique exécute dérivée, intégrale, recherche de racines, extrema et
intersections sur les fonctions valides du document. L'utilisateur choisit l'intervalle, la
tolérance et un nombre d'échantillons borné de 32 à 10 000. Les résultats et les erreurs restent
dans le panneau et ne modifient pas le document.

Une racine ou intersection obtenue après dichotomie n'est conservée que si le résidu final est
proche de zéro. L'intégration vérifie au préalable que le sampling couvre l'intervalle en une seule
polyline ; une asymptote ou une portion hors domaine produit ainsi une erreur lisible au lieu d'un
résultat trompeur.
