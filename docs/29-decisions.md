# 29 — Journal des décisions d'architecture

## ADR-001 — PySide6

### Décision

Utiliser PySide6 pour l'application desktop.

### Raisons

- environnement Qt mature ;
- interface professionnelle ;
- outils adaptés aux applications complexes ;
- meilleur potentiel qu'un prototype Tkinter pour ce projet.

## ADR-002 — Domaine indépendant de Qt

### Décision

La géométrie et le moteur mathématique ne dépendent pas de PySide6.

### Raisons

- tests simples ;
- réutilisabilité ;
- séparation des responsabilités.

## ADR-003 — Graphe de dépendances explicite

### Décision

Les relations entre objets sont représentées explicitement.

### Raisons

- recalcul incrémental ;
- cycle detection ;
- debugging ;
- sérialisation claire.

## ADR-004 — Command pattern

### Décision

Les mutations utilisateur utilisent des commandes.

### Raisons

- undo/redo ;
- transactions ;
- historique cohérent.

## ADR-005 — JSON versionné pour `.pgl`

### Décision

Le premier format de fichier sera JSON.

### Raisons

- développement rapide ;
- inspectable ;
- testable ;
- migrable.

## ADR-006 — Pas de `eval`

### Décision

Les expressions utilisateur passent par un parser sécurisé.

### Raisons

- sécurité ;
- contrôle syntaxique ;
- dépendances détectables ;
- messages d'erreur de meilleure qualité.

## ADR-007 — 2D avant 3D

### Décision

La 1.0 cible exclusivement la géométrie 2D.

### Raisons

- maintenir un scope réaliste ;
- construire un noyau solide ;
- éviter de multiplier les moteurs de rendu trop tôt.

## ADR-008 — Invalidité dynamique

### Décision

Un objet géométriquement impossible peut rester dans le document en état invalide.

### Raisons

La géométrie dynamique implique que certaines constructions puissent devenir temporairement impossibles puis redevenir valides.
