# 20 — Logging et debug

PyGeoLab utilise le module standard `logging` avec un `RotatingFileHandler` UTF-8 de 1 Mo et
trois sauvegardes. Les logs sont écrits dans `%LOCALAPPDATA%/PyGeoLab/logs` sous Windows et
`$XDG_STATE_HOME/pygeolab/logs` (ou `~/.local/state/pygeolab/logs`) sous Linux.

Sont journalisés : démarrage/version, ouvertures et sauvegardes, exports, erreurs de fichiers et
erreurs internes. Les événements souris et le contenu complet des documents ne sont jamais
journalisés à haute fréquence. `--debug` active le niveau DEBUG.

Les exceptions non gérées sont enregistrées avec traceback dans le log ; l'utilisateur reçoit
un message contextualisé indiquant le chemin du fichier, jamais un traceback brut.
