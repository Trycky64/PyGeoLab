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

## ADR-011 — Graphe et résolution séparés du Document

Le graphe orienté, sa validation structurelle et le recalcul incrémental vivent
dans `dependency/`. `Document` reste propriétaire de l'état et des transactions,
mais délègue les parcours, cycles, ordres topologiques et dirty recomputations.
Les dirty flags distinguent géométrie, style et visibilité afin que les couches
de rendu puissent invalider uniquement ce qui est nécessaire.

## ADR-012 — Viewport pur et renderer Qt sans propriété métier

Les transformations monde/écran et le calcul de grille restent indépendants de Qt.
Le renderer reçoit un `QPainter`, lit le document sans le modifier et utilise la
palette du widget pour les éléments d'interface (fond, grille, axes, sélection).
Les droites et demi-droites infinies sont clippées dans l'espace monde avant dessin.
`GeometryView` possède uniquement l'état de caméra et les caches visuels ; les outils
de création, sélection et hit-testing restent réservés à la couche interaction.


## ADR-013 — Outils d'interaction purs et constructions transitoires

Le contrôleur d'interaction et les outils restent indépendants de Qt. Les événements
d'écran sont convertis en coordonnées monde par `GeometryView`, puis transmis sous
forme de contexte de pointeur. Une construction incomplète conserve ses points et sa
géométrie en état transitoire : aucun objet n'est ajouté au `Document` avant validation.
`Escape` peut ainsi annuler sans laisser de définitions orphelines. Le hit-testing est
exprimé en distance écran afin de garder une tolérance stable quel que soit le zoom.

## ADR-014 — Historique par commandes et drag coalescé

Les mutations utilisateur importantes passent par `commands/` et `CommandHistory`.
Une commande nouvelle vide la pile redo ; les commandes composées regroupent une
opération logique et annulent les membres déjà exécutés en cas d'échec. Pendant un
drag, le point libre est déplacé directement pour conserver un retour dynamique et
recalculer ses descendants. Au relâchement, une seule `MovePointCommand` déjà appliquée
est enregistrée dans l'historique, ce qui évite une entrée Undo par mouvement de souris.

## ADR-015 — Panneaux pilotés par les commandes et thème au niveau application

Les panneaux Algèbre et Propriétés observent le `Document`, mais toute édition utilisateur
passe par le même `CommandHistory` que le canvas. La sélection est synchronisée par signaux
Qt sans devenir un état métier persistant. Les palettes clair/sombre sont appliquées au
niveau de `QApplication` ; le renderer continue uniquement à consommer la palette reçue.

## ADR-016 — Parser mathématique dédié et AST fermé

Les expressions utilisateur sont tokenisées puis analysées par un parser descendant récursif
dédié. L'AST interne n'expose que nombres, variables, opérateurs documentés et appels de
fonctions autorisées. Aucun `eval`, `exec`, attribut Python, indexation ou construction de code
n'est accepté. L'évaluateur reçoit explicitement les variables et le sampling sépare ses
polylines lorsqu'une évaluation échoue ou lorsqu'un saut numérique indique une discontinuité.

## ADR-013 — Curseurs comme objets numériques du document

Les curseurs utilisent le type sérialisable `number` du modèle métier avec les paramètres
`value`, `minimum`, `maximum` et `step`. Une variation passe par `Document.update`, ce qui
réutilise le graphe de dépendances, les dirty flags et le recalcul incrémental existants au lieu
d'introduire un second système de variables réactives.

## ADR-014 — Analyse numérique déterministe sans dépendance scientifique obligatoire

La dérivée utilise une différence centrée, l'intégration la méthode de Simpson composite,
les racines un balayage suivi de dichotomie, les extrema un voisinage échantillonné avec
raffinement parabolique et les intersections la recherche de racines de `f-g`. Ces algorithmes
restent indépendants de Qt et de NumPy/SciPy afin de conserver un socle léger et testable.

## ADR-015 — Persistance `.pgl` validée avant adoption par l'UI

Le format courant est le JSON versionné v1 documenté dans `docs/12-persistence.md`. Les
fichiers sont migrés puis validés comme données non fiables avant reconstruction. Les caches
dérivés ne sont pas sérialisés. `ProjectSession` compare le contenu sérialisable courant à la
dernière sauvegarde afin que l'indicateur de modifications non enregistrées reflète le contenu
et pas seulement un compteur de révision.

## ADR-015 — Export piloté par le renderer et builds desktop reproductibles

Les exports PNG et SVG réutilisent le même `Renderer` et le même `Viewport` que l'affichage,
avec un facteur de résolution indépendant et un fond optionnellement transparent. Cela évite
une seconde implémentation géométrique dédiée à l'export et garantit que lignes clippées,
objets vectoriels et labels suivent les mêmes règles que le canvas.

Les préférences utilisateur sont stockées avec `QSettings`; elles ne font pas partie du fichier
`.pgl`. Les erreurs internes non gérées sont journalisées dans un fichier rotatif puis présentées
avec un message contextualisé, sans traceback brut dans l'interface standard.

La release 1.0 adopte PyInstaller en mode dossier portable. Les builds Windows et Linux sont
produits nativement par GitHub Actions à partir d'un même fichier `packaging/pygeolab.spec`.
Un installateur système reste une évolution future : la 1.0 distribue des archives portables.

## ADR-017 — Snapping pur avec seuil écran

Le calcul des cibles vit dans `interaction/snapping.py` et ne dépend pas de Qt. Il reçoit le
`Document` et le `Viewport`, classe les points, intersections, projections et positions de grille,
puis compare leur distance en pixels. Le contrôleur remplace uniquement la coordonnée monde du
`PointerContext`; les outils, previews et commandes existants conservent ainsi leur architecture.

Le point déplacé est exclu des candidats. `Alt` suspend le calcul pour l'événement courant et une
option du contrôleur l'active globalement. Le renderer ne connaît que la position finale du viseur,
ce qui maintient la séparation entre décision d'interaction et dessin Qt. Les intersections sont
calculées à la demande ; un index ou cache ne sera ajouté qu'après mesure dans la section
performance de la version 1.1.

## ADR-018 — Outils avancés fondés sur les recettes existantes

Les outils de construction 1.1 vivent dans `interaction/tools/advanced.py` et créent les types de
recettes déjà pris en charge par le modèle. Ils partagent les primitives d'interaction de
`construction.py` pour le hit-testing, les points implicites et l'exécution de commandes. Chaque
geste final exécute une unique `CreateObjectsCommand`, tandis que ses clics intermédiaires et sa
prévisualisation restent hors du document.

La rotation et l'homothétie utilisent trois clics : source, centre et direction ou position cible.
Ce choix fournit une prévisualisation continue, évite une boîte de dialogue modale et enregistre un
angle ou un rapport signé dans la recette. Le cercle centre-rayon enregistre de même la distance du
second clic comme rayon littéral. Ces valeurs sont des paramètres JSON ordinaires ; tous les types
de recettes existaient déjà dans le format `.pgl` version 1, donc la section 2 ne change ni le
schéma ni son numéro de version et ne nécessite aucune migration.

## ADR-019 — Sélection avancée et ordre portés par le document existant

La sélection multiple reste un état d'interaction non sérialisé. Le rectangle est converti en
bornes monde pour interroger les géométries visibles, tandis que le hit-testing ponctuel conserve
sa priorité sémantique et départage les égalités avec l'ordre d'affichage. Des clics répétés
parcourent la pile complète sans modifier le document.

L'ordre d'affichage correspond à l'ordre des définitions déjà sérialisées dans `.pgl`. Le déplacer
ne demande donc aucun nouveau champ ni migration. `Document.set_order` valide une permutation
complète et les commandes d'ordre la restaurent exactement sur Undo. Les mutations d'une sélection
utilisent une commande composée ou une commande groupée spécialisée ; elles occupent une seule
entrée d'historique même lorsqu'elles concernent plusieurs objets ou descendants.

## ADR-020 — Panneaux comme projections éditables du document

Le panneau Algèbre reconstruit une projection filtrée, triée et regroupée des objets sans copier
leur état métier. Il mémorise seulement les UUID sélectionnés afin qu'un filtre temporaire ne les
perde pas. Les cellules éditables créent des commandes de nom, visibilité ou verrouillage ; les
messages d'invalidité proviennent directement de `GeoObject.error_state`.

Le panneau Propriétés demande les descendants au `Document`, qui expose une vue en lecture seule du
graphe interne. Les paramètres numériques modifiables sont limités aux clés dont la recette et le
contrôle UI ont une sémantique claire. `ChangeParametersCommand` remplace le mapping complet, ce qui
préserve l'immutabilité de `GeoObject` et le recalcul incrémental existant. L'éditeur dédié aux
fonctions et celui des bornes de curseur restent dans leurs sections respectives.

## ADR-021 — Fonctions éditées comme recettes et analyses comme couches de scène

L'éditeur de fonction transforme la saisie validée en recette `GeoObject(kind="function")`. Les
variables externes sont résolues par nom vers des UUID d'objets numériques avant la commande ; le
graphe conserve ainsi ses références stables. `ChangeFunctionCommand` remplace ensemble le nom,
les dépendances et les paramètres, ce qui rend une modification entièrement annulable.

La qualité du sampling et les analyses visibles appartiennent à `Document.scene`, déjà sérialisé
par le format v1. Le renderer ajuste le nombre de points à la largeur et au zoom, puis dessine les
résultats numériques sans modifier le modèle. Ce choix ne change pas le schéma `.pgl` et conserve
la compatibilité avec les documents 1.0.

## ADR-022 — Animation des curseurs hors de l'historique de commandes

Les paramètres durables d'un curseur, notamment sa valeur initiale, sa vitesse et son mode
aller-retour, restent dans sa recette sérialisable. Une édition explicite passe par une commande et
reste annulable. Le timer d'animation applique en revanche les valeurs de frame directement au
`Document`, car chacune est un état transitoire d'une même lecture et ne doit pas remplir la pile
Undo.

Le panneau conserve une position continue séparée de la valeur alignée sur le pas. Le document ne
reçoit que les changements de valeur effectifs et son graphe recalcule alors le curseur et ses seuls
descendants. L'état lecture/pause et le sens courant restent des états UI non sérialisés.

## ADR-023 — Résultats numériques transitoires et mesures persistantes

Les calculs ponctuels de dérivée, intégrale, racines, extrema et intersections sont présentés dans
un panneau dédié. Ils dépendent de bornes et d'une tolérance choisies pour une demande précise ; ils
restent donc des résultats UI transitoires et ne chargent ni le graphe ni l'historique.

Les longueurs et aires destinées à suivre une construction sont au contraire des `GeoObject`
persistants. Leurs dépendances passent par le graphe normal et leur valeur est recalculée comme les
mesures de distance et d'angle existantes. Ces deux nouveaux types utilisent la structure ouverte
des recettes v1 et ne demandent aucune migration du format.

## ADR-024 — Récupération atomique séparée et récents dans QSettings

L'autosave réutilise le sérialiseur et l'écriture atomique `.pgl`, mais vise un chemin de
récupération propre à l'application. Il ne change ni le chemin ni le snapshot enregistré de la
session utilisateur. Une restauration adopte un document validé comme projet non enregistré ; une
erreur de lecture laisse la session courante intacte.

La liste MRU contient uniquement des chemins et relève des préférences de poste. Elle reste donc
dans `QSettings`, se borne à dix entrées et élimine les fichiers absents à chaque lecture. Aucun de
ces ajouts ne modifie la version 1 du schéma de document.

## ADR-025 — Préférences globales typées et styles par défaut tardifs

Une dataclass `Preferences` validée constitue l'unique représentation des réglages persistants.
Elle lit et écrit toutes ses valeurs dans `QSettings`, migre l'ancien booléen de thème et borne les
valeurs numériques avant usage. Les options d'affichage configurent le renderer et le contrôleur
d'interaction sans modifier la scène sérialisée.

Le `Document` reçoit le style de création après son chargement. Il l'applique uniquement aux
nouvelles définitions encore à leur révision initiale et portant le style neutre. Les styles d'un
fichier existant sont donc reconstruits avant l'application des préférences et restent fidèles au
projet enregistré.

## ADR-026 — Une caméra d'export calculée, un filtre d'objets et un renderer commun

L'export de document ou de sélection calcule un `Viewport` ajusté aux bornes finies des objets,
indépendamment de la caméra du canvas. Les fonctions bornées contribuent par leur sampling ; les
fonctions sans domaine utilisent l'étendue finie disponible ou l'intervalle `[-10, 10]`. Les
objets infinis sont ensuite clippés par le renderer à cette caméra.

La sélection est transmise comme filtre d'UUID au même renderer, qui conserve l'accès au document
complet pour résoudre les dépendances. PNG, SVG et presse-papiers réutilisent ainsi les mêmes
règles de dessin, de labels et de courbes sans dupliquer le moteur géométrique.

## ADR-027 — Accessibilité appliquée à l'arbre de widgets et raccourcis issus des actions

La fenêtre principale complète les métadonnées accessibles de chaque contrôle focalisable après
la construction de ses docks et barres d'outils. La même passe impose la taille minimale des
contrôles de saisie et un contour de focus fondé sur la palette, ce qui couvre aussi les panneaux
composés sans répéter ces règles dans chaque classe.

La fenêtre d'aide reçoit directement les `QAction` de l'application et affiche leurs séquences
effectives. La documentation visible ne peut ainsi pas diverger des raccourcis configurés. Les
tests contrôlent leur unicité, la chaîne de focus, les métadonnées accessibles et le contraste des
deux palettes.

## ADR-028 — Optimiser le rendu multi-fonctions après mesure

Les profils 1.1 montrent que le rendu initial de nombreuses fonctions domine les autres scénarios.
Le renderer envoie désormais chaque morceau continu en une polyligne Qt et répartit le sampling
selon le nombre de fonctions visibles. Sa clé utilise la révision de l'objet fonction plutôt que la
révision globale du document, afin qu'une modification indépendante ne recalcule pas sa courbe.

Le hit-testing de 10 000 objets reste de l'ordre de quelques millisecondes sur la machine de
référence. Aucun index spatial ni cache de hit-testing n'est donc ajouté. Les seuils automatisés
laissent une marge importante aux runners partagés et visent les régressions d'un ordre de
grandeur, pas les fluctuations ordinaires de charge.

## ADR-029 — Diagnostic partageable et adoption atomique des documents

Le diagnostic système est produit par une fonction pure commune au log de démarrage et au
presse-papiers. L'identifiant de build vient de l'environnement de packaging ou de CI, avec une
valeur de développement explicite. Le format de log ajoute processus et thread ; les opérations de
fichier ajoutent document, révision et cible sans enregistrer le contenu utilisateur.

Une session ne publie un document chargé qu'après validation et création de son snapshot. Les
erreurs récupérables utilisent un message UI commun avec résumé, détail court et chemin du journal.
Cette frontière laisse les exceptions internes au gestionnaire global avec traceback, tout en
gardant les échecs attendus dans le flux normal de l'application.

## ADR-030 — Même mode smoke pour les sources et les exécutables

L'option `--smoke-test` emprunte le démarrage normal jusqu'à la création de `MainWindow`, traite une
itération d'événements puis exige une fermeture propre. Elle désactive seulement la proposition de
récupération, qui rendrait un démarrage automatisé dépendant de l'état du poste. Le même point
d'entrée sert aux tests Python et aux dossiers PyInstaller sur Windows et Linux.

La matrice de compatibilité teste chaque combinaison des trois versions Python supportées et des
deux systèmes. Les builds restent sur Python 3.13 pour produire deux artefacts déterministes après
la réussite de toute la matrice ; chaque exécutable doit réussir le smoke avant son archivage.
