# 14 — Gestion des erreurs

## Catégories

### Erreur utilisateur

Exemple :

- expression invalide ;
- nom déjà utilisé ;
- rayon négatif.

Doit produire un retour clair dans l'UI.

### Configuration géométrique invalide

Exemple :

- intersection impossible.

Ne doit pas nécessairement lever une exception.

L'objet peut devenir temporairement invalide.

### Erreur de fichier

Exemple :

- JSON corrompu ;
- version non supportée.

Doit empêcher l'ouverture proprement.

### Erreur interne

Doit être journalisée.

Une boîte de dialogue peut proposer :

- détails ;
- copie du traceback ;
- emplacement des logs.

## Philosophie

Ne jamais masquer silencieusement une erreur critique.

Ne jamais montrer un traceback brut à un utilisateur standard sans contexte.
