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

## Chemins récupérables en 1.1

Les erreurs d'ouverture, d'enregistrement, d'export et de presse-papiers passent par un format
commun : une explication de l'opération, le détail technique court et le chemin du journal. Le log
ajoute le nom et la révision du document ainsi que le chemin cible. Les erreurs attendues ne
quittent jamais la boucle Qt.

`ProjectSession.open` construit et sérialise entièrement le nouveau document avant de remplacer la
session. Un JSON corrompu, une version inconnue ou une dépendance invalide conserve donc le
document, le chemin et le snapshot courants. Les sauvegardes restent atomiques et l'export SVG
vérifie qu'un fichier non vide a réellement été créé.
