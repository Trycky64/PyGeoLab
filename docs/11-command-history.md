# 11 — Commandes, Undo et Redo

## Principe

Les mutations importantes du document passent par des commandes.

Interface conceptuelle :

```text
execute()
undo()
redo()
```

## Commandes

Exemples :

- CreateObjectCommand ;
- DeleteObjectCommand ;
- MovePointCommand ;
- RenameObjectCommand ;
- ChangeStyleCommand ;
- ChangeVisibilityCommand ;
- ChangeLockCommand ;
- ChangeParametersCommand ;
- DeleteObjectsCommand ;
- ReorderObjectsCommand ;
- SetVariableCommand.

## Historique

Deux piles :

```text
undo_stack
redo_stack
```

Après une nouvelle commande :

- push dans undo ;
- vider redo.

## Drag

Un drag continu ne doit pas créer une commande par pixel.

Stratégie :

- capturer position initiale ;
- permettre mises à jour interactives ;
- créer une unique commande finale.

## Transactions

Des commandes composées doivent pouvoir regrouper plusieurs modifications.

Exemple :

- création automatique de deux points + segment.
- visibilité, verrouillage ou style d'une sélection multiple ;
- suppression de plusieurs racines avec leurs descendants ;
- changement d'ordre d'affichage d'un groupe.

La suppression groupée restaure sur Undo les définitions, leurs dépendances et l'ordre exact du
document. La duplication de plusieurs objets indépendants utilise également une seule commande de
création groupée.
