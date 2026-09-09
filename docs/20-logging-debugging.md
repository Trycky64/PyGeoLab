# 20 — Logging et debug

PyGeoLab utilise le module standard `logging` avec un `RotatingFileHandler` UTF-8 de 1 Mo et
trois sauvegardes. Les logs sont écrits dans `%LOCALAPPDATA%/PyGeoLab/logs` sous Windows et
`$XDG_STATE_HOME/pygeolab/logs` (ou `~/.local/state/pygeolab/logs`) sous Linux.

Sont journalisés : démarrage/version, ouvertures et sauvegardes, exports, erreurs de fichiers et
erreurs internes. Les événements souris et le contenu complet des documents ne sont jamais
journalisés à haute fréquence. `--debug` active le niveau DEBUG.

Les exceptions non gérées sont enregistrées avec traceback dans le log ; l'utilisateur reçoit
un message contextualisé indiquant le chemin du fichier, jamais un traceback brut.

## Diagnostic 1.1

Chaque ligne inclut le PID et le thread. Le démarrage enregistre la version PyGeoLab,
l'identifiant de build injecté par `PYGEOLAB_BUILD_ID` ou `GITHUB_SHA`, Python, PySide6, Qt, le
système d'exploitation, l'architecture et l'exécutable. En développement, l'identifiant vaut
explicitement `development`.

Le menu **Aide** permet d'ouvrir le dossier des logs et de copier les mêmes informations système
dans le presse-papiers. Ce bloc omet les données du document et les chemins utilisateur ; il peut
être joint directement à un rapport d'anomalie.
