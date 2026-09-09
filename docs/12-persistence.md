# 12 — Persistance

## Extension

Extension proposée :

```text
.pgl
```

## Format

Format initial recommandé :

**JSON versionné**.

Avantages :

- lisible ;
- facile à debugger ;
- simple à migrer ;
- naturel en Python.

## Structure

Exemple conceptuel :

```json
{
  "format": "pygeolab",
  "version": 1,
  "document": {
    "name": "Triangle",
    "objects": []
  }
}
```

## Sérialisation

Sauvegarder :

- identifiant ;
- type ;
- propriétés ;
- dépendances ;
- style ;
- métadonnées.

## Ne pas sauvegarder

Les données purement dérivées peuvent être recalculées.

Exemple :

- bounding boxes ;
- cache de rendu ;
- ordre topologique ;
- cache de sampling.

## Validation

Un fichier doit être validé avant de reconstruire le document.

## Migration

Chaque version du format doit disposer si nécessaire d'une migration :

```text
v1 -> v2
v2 -> v3
```

## Autosave

Depuis la 1.1, l'autosave est configurable entre 1 et 60 minutes et activé par défaut toutes les
deux minutes. Il écrit atomiquement un fichier `autosave-recovery.pgl` dans le dossier de données
de l'application. Il ne remplace jamais le chemin choisi par l'utilisateur.

Au démarrage, une récupération disponible est proposée avec les choix restaurer ou ignorer. Le
document restauré reste non enregistré. Une sauvegarde normale, l'ouverture d'un autre projet ou
la création d'un nouveau document nettoie le fichier de récupération.

## Fichiers récents

Les dix derniers `.pgl` ouverts ou enregistrés sont stockés dans `QSettings`. Le menu Fichier les
présente du plus récent au plus ancien, retire les chemins qui n'existent plus et propose une action
d'effacement complet.

Le format courant reste la version 1. Les nouvelles options utilisent les mappings extensibles de
scène et de paramètres ; les fichiers PyGeoLab 1.0 restent lisibles. La migration historique v0
vers v1 demeure appliquée avant validation.
