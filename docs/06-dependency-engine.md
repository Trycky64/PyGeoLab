# 06 — Moteur de dépendances

## But

PyGeoLab est un système de géométrie dynamique.

Les objets dépendants doivent être recalculés automatiquement.

Exemple :

```text
A ─┐
   ├─ Segment AB ──> Milieu M ──> Cercle C
B ─┘
```

Déplacer A doit mettre à jour :

1. AB ;
2. M ;
3. C.

## Graphe

Le moteur utilise un graphe orienté.

Une arête :

```text
A -> B
```

signifie que B dépend de A.

## Contraintes

Le graphe doit être acyclique pour les dépendances calculées classiques.

Une dépendance cyclique doit être refusée ou gérée explicitement.

## Mise à jour

Lorsqu'un objet racine change :

1. marquer ses descendants comme sales ;
2. déterminer l'ordre topologique ;
3. recalculer uniquement les objets affectés ;
4. notifier le renderer.

## Dirty flags

Chaque objet peut posséder :

- `geometry_dirty` ;
- `style_dirty` ;
- `visibility_dirty`.

## Recalcul

Les opérations doivent éviter un recalcul global du document.

## Objets invalides

Un objet dépendant peut devenir invalide.

Exemple :

```text
P = intersection(d1, d2)
```

Si `d1` et `d2` deviennent parallèles :

```text
P.valid = False
```

Ses descendants deviennent eux aussi potentiellement invalides.

## Cycles

Exemple interdit :

```text
A dépend de B
B dépend de A
```

Le moteur doit détecter cette situation au moment de la création de la relation.

## Suppression

Lorsqu'un objet parent est supprimé, deux stratégies sont possibles.

Décision initiale :

**suppression en cascade des descendants dépendants**, avec confirmation lorsqu'un nombre important d'objets sera supprimé.

Cette stratégie pourra évoluer.
