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

## ADR-009 — Primitives immuables et normales unitaires

Les primitives scalaires sont regroupées dans `geometry/primitives.py` et exposées
par `geometry`. Les intersections et transformations restent des modules séparés.
Cette organisation limite les imports circulaires entre petits types fortement liés.
Les droites normalisent leurs coefficients pour que les distances et tolérances
ne dépendent pas du facteur utilisé dans leur équation. Les fabriques renvoient
`None` pour une construction sans direction ; les intersections distinguent zéro,
un, deux points et les objets confondus. NaN, infini et rayons négatifs sont refusés.
Les calculs scalaires ne requièrent pas NumPy ; son ajout reste possible si des
mesures de performance justifient une vectorisation.

## ADR-010 — Définitions d'objets immuables

`GeoObject` est une valeur figée portant UUID, type, paramètres, parents et style.
Les paramètres sont copiés et figés récursivement ; le registre expose une vue
en lecture seule. Le document remplace l'objet lors d'une mutation et notifie
ses abonnés sans dépendre de Qt. Les recettes sont évaluées dans
`model/constructions.py`. Les caches de géométrie et d'invalidité sont reconstruits
à partir des recettes, et ne constituent pas l'identité de l'objet.

La revue du modèle a également révélé un cas numérique : une intersection très
éloignée peut avoir un résidu supérieur à la tolérance absolue malgré une solution
analytique correcte. Le filtrage après résolution vérifie les bornes des segments
et demi-droites, sans rejeter une droite infinie à cause de ce résidu.
