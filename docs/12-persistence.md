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

Fonction future.

Principe :

- sauvegarde périodique dans un fichier temporaire ;
- récupération après crash.
