# 30 — Protocole d'inspection du Debug Bridge et Sérialisation

Ce document spécifie le protocole JSON-RPC 2.0 utilisé par le Debug Bridge IPC de PyGeoLab (`src/pygeolab/debug/`), les schémas de données échangés, les politiques de pagination, de troncature et les codes d'erreur.

---

## 1. Principes Généraux et Sécurité

- **Transport local sécurisé** : Named Pipe sous Windows (`\\.\pipe\pygeolab-debug-<PID>-<nonce>`) avec DACL stricte owner-only, ou socket UNIX local (`0600`) dans répertoire privé (`0700`) sous Linux.
- **Framing borné** : Maximum de 1 Mo (1 048 576 octets) par trame, délimité par saut de ligne `\n`.
- **Authentification** : Token de 32 octets aléatoires transmis via le fichier de session privé lors du handshake initial.
- **Lecture seule absolue** : L'inspecteur n'appelle aucune méthode mutatrice sur le `Document` ou la `MainWindow`.
- **Déterminisme et isolation** : Aucun recours à `eval`, `exec` ou `repr()` non sécurisé.

---

## 2. Opérations IPC

### A. `handshake`
- **Paramètres** :
  - `token` (`str`) : Token d'authentification.
  - `version` (`str`) : Version du protocole client (ex: `"1.0.0"`).
- **Résultat** :
  - `status` (`str`) : `"authenticated"`
  - `pygeolab_version` (`str`) : Version de PyGeoLab.
  - `protocol_version` (`str`) : `"1.0.0"`
  - `pid` (`int`) : Identifiant du processus serveur.

### B. `runtime_snapshot`
- **Paramètres** : aucun.
- **Résultat** :
  - `schema_version` (`str`) : `"1.0.0"`
  - `version` (`str`) : Version de PyGeoLab.
  - `pid` (`int`) : PID serveur.
  - `uptime_s` (`float`) : Temps de fonctionnement en secondes.
  - `connected` (`bool`) : Statut de connexion.
  - `document` (`dict`) : `{name: str | null, dirty: bool | null, objects_count: int | null}`
  - `selection` (`dict`) : `{selected_ids: list[str] | null, count: int | null, truncated: bool}`
  - `tool` (`dict`) : `{active: str | null}`
  - `viewport` (`dict | null`) : Coordonnées, dimensions et échelle de la caméra.
  - `recent_errors` (`list[dict]`) : FIFO bornée des 20 dernières erreurs applicatives.

### C. `list_objects`
Liste paginée et déterministe des objets du document courant.

- **Paramètres** :
  - `limit` (`int`, optionnel) : Entier strict entre 1 et 100 (défaut : 50). Tout type non-int (y compris bool) retourne `INVALID_PARAMS`.
  - `cursor` (`str`, optionnel) : Curseur opaque (base64url) encodant l'état du document et le décalage.
  - `kind` (`str`, optionnel) : Filtre sur le type d'objet (ex: `"point"`, `"circle"`). Doit appartenir aux `KINDS` autorisés.

- **Structure du Curseur Opaque** :
  Le curseur lie de façon inviolable :
  - `dn` : Nom du document.
  - `dp` : Identifiant mémoire de l'instance du document (`id(doc)`).
  - `sig` : Empreinte cryptographique de 16 caractères hexadécimaux de l'ensemble des identifiants et révisions des objets filtrés.
  - `k` : Filtre `kind` actif.
  - `off` : Décalage entier non négatif.

- **Détection des Mutations Concolores** :
  Si le document est modifié (ajout, suppression, déplacement, édition de paramètre), si un nouveau document est ouvert, ou si le filtre `kind` est modifié entre deux pages, le serveur rejette la requête avec `DOCUMENT_REVISION_MISMATCH` (-32005) ou `INVALID_PARAMS` (-32602).

- **Résultat** :
  - `schema_version` : `"1.0.0"`
  - `document_id` : Nom du document ou identifiant stable.
  - `document_revision` : Entier de révision du document.
  - `items` : Liste ordonnée canoniquement (par identifiant UUID).
    - `id` : UUID stable de l'objet.
    - `name` : Nom d'affichage de l'objet (borné à 1000 caractères).
    - `kind` : Type de l'objet (ex: `"point"`, `"segment"`).
    - `valid` : Booléen de validité géométrique.
    - `visible` : Booléen de visibilité.
    - `selected` : Booléen indiquant si l'objet est sélectionné.
  - `returned_count` : Nombre d'éléments retournés sur la page courante.
  - `total_count` : Nombre total d'éléments correspondant au filtre.
  - `next_cursor` : Curseur opaque pour la page suivante, ou `null` si fin de liste.
  - `truncated` : Booléen indiquant si des éléments supplémentaires existent (`next_cursor != null`).

### D. `inspect_object`
Inspection détaillée et sécurisée d'un objet géométrique unique.

- **Paramètres** :
  - `object_id` (`str`) : UUID de l'objet (longueur 1 à 128 caractères).

- **Résultat** :
  - `schema_version` : `"1.0.0"`
  - `id` : UUID de l'objet.
  - `name` : Nom de l'objet (borné).
  - `kind` : Type de l'objet.
  - `parameters` : Dictionnaire des paramètres de construction, sanitisés et bornés.
  - `computed_geometry` : Géométrie calculée sérialisée selon le type concret, ou `null`.
  - `validity` : `"valid"`, `"invalid"` ou `"empty"`.
  - `visible` : Booléen.
  - `selected` : Booléen.
  - `errors` : Liste de messages d'erreurs textuels explicites.
  - `warnings` : Liste d'avertissements (troncatures, références cycliques, etc.).

---

## 3. Politiques de Bornage et Troncature

Pour garantir le respect du budget IPC de 1 Mo et éviter tout gel du thread principal Qt :
1. **Profondeur de récursion maximale** : 5 niveaux (`MAX_RECURSION_DEPTH = 5`). Au-delà, un marqueur `{"_truncated": true, "reason": "max_depth_exceeded"}` est inséré et un warning est consigné.
2. **Nombre d'éléments par collection** : 100 éléments (`MAX_COLLECTION_ITEMS = 100`). Au-delà, la liste est tronquée et annotée par `{"_truncated": true, "total_elements": n}`.
3. **Nombre de clés par dictionnaire** : 50 clés (`MAX_PARAMS_KEYS = 50`). Au-delà, `_truncated: true` et `_total_keys: n` sont ajoutés.
4. **Longueur maximale des chaînes** : 1000 caractères (`MAX_STRING_LENGTH = 1000`). Au-delà, la chaîne est tronquée avec suffixe `"... [truncated]"`.
5. **Sommets de polygone** : Maximum 100 sommets (`MAX_POLYGON_VERTICES = 100`).
6. **Échantillons de lieu géométrique** : Maximum 100 points (`MAX_LOCUS_SAMPLES = 100`).
7. **Colonnes de dataset** : Maximum 50 colonnes (`MAX_DATASET_COLS = 50`).
8. **Détection des cycles** : Tout objet déjà visité dans la pile de sérialisation retourne `{"_cyclic_ref": true, "type": "..."}` sans boucle infinie.
9. **Objets Python non reconnus** : Retourne `{"_unserializable": true, "type": "..."}` sans exposer `repr()` ou `str()`.

---

## 4. Représentation des Valeurs Invalides et Non-Finies

- Les valeurs absentes sont représentées par `null`.
- **NaN et Infinity** : Strictement interdits dans la sortie JSON standard. Toute valeur non-finie (`math.isnan` ou `math.isinf`) est remplacée par `null` et consignée dans `errors` ou `warnings` sous forme de message structuré (ex: `"Non-finite value 'nan' in 'Point2D.x' replaced by null"`).

---

## 5. Exemples Authentiques

### Exemple 1 : Point valide (`Point2D`)
```json
{
  "schema_version": "1.0.0",
  "id": "e83792c8-8df0-4b24-9b24-5d9c24098901",
  "name": "A",
  "kind": "point",
  "parameters": {
    "x": 3.0,
    "y": 4.5
  },
  "computed_geometry": {
    "type": "point",
    "x": 3.0,
    "y": 4.5
  },
  "validity": "valid",
  "visible": true,
  "selected": false,
  "errors": [],
  "warnings": []
}
```

### Exemple 2 : Cercle valide (`Circle2D`)
```json
{
  "schema_version": "1.0.0",
  "id": "c194a822-4467-4638-b7a4-846399a9a3b2",
  "name": "c1",
  "kind": "circle",
  "parameters": {},
  "computed_geometry": {
    "type": "circle",
    "center": {
      "x": 0.0,
      "y": 0.0
    },
    "radius": 5.0
  },
  "validity": "valid",
  "visible": true,
  "selected": true,
  "errors": [],
  "warnings": []
}
```

### Exemple 3 : Objet invalide (Point avec coordonnées non finies)
```json
{
  "schema_version": "1.0.0",
  "id": "f51276a0-5b1b-4899-b13c-0e2410651234",
  "name": "P_invalid",
  "kind": "point",
  "parameters": {
    "x": null,
    "y": 2.0
  },
  "computed_geometry": {
    "type": "point",
    "x": null,
    "y": 2.0
  },
  "validity": "invalid",
  "visible": true,
  "selected": false,
  "errors": [
    "Non-finite value 'nan' in 'Point2D.x' replaced by null"
  ],
  "warnings": []
}
```

---

## 6. Table des Codes d'Erreur JSON-RPC

| Code | Constante | Description |
| :--- | :--- | :--- |
| `-32700` | `PARSE_ERROR` | Tissu JSON invalide ou malformé sur le stream IPC |
| `-32600` | `INVALID_REQUEST` | Structure JSON-RPC non conforme (ex: `jsonrpc != "2.0"`) |
| `-32601` | `METHOD_NOT_FOUND` | Méthode inconnue |
| `-32602` | `INVALID_PARAMS` | Paramètre invalide (type incorrect, borne dépassée, filtre erroné, curseur forgé) |
| `-32603` | `INTERNAL_ERROR` | Erreur interne serveur masquée sans fuite de traceback |
| `-32000` | `AUTH_FAILED` | Échec du handshake d'authentification par token |
| `-32001` | `PROTOCOL_MISMATCH` | Incompatibilité de version de protocole |
| `-32002` | `PAYLOAD_TOO_LARGE` | Trame dépassant le budget de 1 Mo |
| `-32003` | `SERVER_STOPPING` | Serveur en cours d'arrêt propre |
| `-32004` | `OBJECT_NOT_FOUND` | Identifiant d'objet introuvable dans le document |
| `-32005` | `DOCUMENT_REVISION_MISMATCH` | Mutation ou changement de document survenu pendant la pagination |
