# Guide utilisateur — PyGeoLab 1.1

**Français** · [English](user-guide.md)

## Espace de travail

Le canvas occupe le centre. **Algèbre** recherche, trie, regroupe et sélectionne les objets ; **Propriétés** modifie la sélection et affiche parents et descendants ; **Curseurs** pilote les variables numériques ; **Analyse numérique** exécute les calculs bornés. Les docks se masquent depuis **Affichage**.

## Outils de construction

Choisissez un outil dans la barre, puis cliquez les objets ou positions demandés. Un clic sur une zone vide crée automatiquement un point libre lorsque la construction l'accepte. `Escape` annule toute construction incomplète.

| Outil | Séquence |
|---|---|
| Point | une position |
| Segment, droite, demi-droite, vecteur | deux points |
| Cercle | centre puis point du cercle |
| Polygone | sommets, puis clic sur le premier sommet |
| Milieu | deux points ou un segment |
| Intersection | deux objets compatibles |
| Parallèle, perpendiculaire | point puis support linéaire |
| Médiatrice | deux points |
| Bissectrice, angle | côté, sommet, autre côté |
| Projection | point puis support linéaire |
| Point sur objet | support linéaire ou cercle |
| Cercle centre-rayon | centre puis position du rayon |
| Cercle circonscrit | trois points non alignés |
| Distance | point puis point ou support linéaire |
| Translation | point puis vecteur |
| Symétrie centrale | point puis centre |
| Symétrie axiale | point puis axe |
| Rotation | point, centre, direction cible |
| Homothétie | point, centre, position du rapport |

Les previews et le viseur de magnétisme montrent le résultat avant validation. Une construction terminée forme une seule commande Undo.

## Sélection et édition

Un clic remplace la sélection. `Shift` ajoute, `Ctrl` bascule et un glisser depuis le vide trace un rectangle. Des clics répétés au même emplacement parcourent les objets superposés. Le menu contextuel du canvas applique visibilité, verrouillage, duplication, ordre d'affichage ou suppression au groupe.

Dans **Propriétés**, couleur, épaisseur, taille, trait, label, visibilité et verrouillage s'appliquent à tous les objets sélectionnés dans une seule commande. Le panneau Algèbre permet aussi de renommer et de modifier directement visibilité ou verrouillage.

## Magnétisme

Le snapping recherche les points, intersections, projections sur objets puis la grille. Son rayon est exprimé en pixels et reste stable au zoom. `M` l'active ou le désactive ; maintenez `Alt` pour le suspendre pendant un geste. **Préférences** règle son état et son rayon de 1 à 100 px.

## Coniques euclidiennes

Le menu **Objets** et la barre d'outils permettent de tracer :
- **Ellipse** : par deux foyers et un point, ou par centre et demi-axes ;
- **Parabole** : par foyer et droite directrice ;
- **Hyperbole** : par deux foyers et un point (ou paramètre $a$).

Le panneau Propriétés affiche les fiches analytiques des coniques (équation cartésienne exacte, coordonnées des foyers, directrice, asymptotes, excentricité, périmètre et aire) avec copie directe au clic.

## Courbes paramétriques et polaires

**Objets > Nouvelle courbe paramétrique** trace des trajectoires $(x(t), y(t))$ sur $[t_{min}, t_{max}]$ avec détection automatique des curseurs dépendants.

**Objets > Nouvelle courbe polaire** évalue $r(\theta)$ en radians ou en degrés. Les singularités et discontinuités sont automatiquement isolées pour éviter les segments d'asymptote parasites.

## Lieux géométriques et traces

**Objets > Nouveau lieu** génère le lieu d'un point cible piloté par un curseur ou un point sur courbe. Le calcul s'exécute sur un sous-graphe isolé sans ralentir le document.

Un clic droit sur un point permet d'activer la **Trace temporaire** pour suivre son mouvement en direct sans alourdir le fichier sauvegardé. **Affichage > Effacer les traces** réinitialise le canvas.

## Timeline et animation multi-curseurs

Le dock inférieur **Timeline** synchronise l'ensemble des curseurs animés du document. Il propose lecture, pause, stop, scrubbing par curseur temporel, vitesse, modes boucle et aller-retour. Raccourcis : `Espace` pour lecture/pause, `Échap` pour arrêt.

## Table de valeurs

Le dock **Table de valeurs** tabule les fonctions cartésiennes, paramétriques ou polaires sur une plage $[start, end]$ avec un pas paramétrable. Il supporte jusqu'à 50 000 lignes avec virtualisation, copie presse-papiers et export direct au format CSV UTF-8.

## Fonctions et curseurs

**Objets > Nouveau curseur** crée une variable avec valeur, minimum, maximum et pas. Le panneau Curseurs permet la saisie directe, le reset, l'édition, la vitesse d'animation, la lecture en boucle ou aller-retour et pause/reprise. Une animation recalcule seulement ses descendants et ne remplit pas l'historique Undo.

**Objets > Nouvelle fonction** accepte une expression, une variable indépendante et un domaine optionnel. Les autres identifiants de l'expression sont reliés automatiquement aux curseurs de même nom. Les erreurs restent visibles dans la boîte et dans Algèbre. **Affichage > Fonctions** règle la qualité du sampling et les couches racines, extrema, intersections et dérivée.

## Données, statistiques et modélisation

PyGeoLab 1.3 intègre une suite complète d'outils statistiques et de gestion de données tabulaires :

### Jeux de données (`DatasetObject`) et Tableur
- **Tableau de données** : Le panneau ancrable *Données* (tabifié au bas de la fenêtre) permet de visualiser et d'éditer les observations sous forme de tableur. Vous pouvez ajouter/supprimer des lignes et colonnes, copier/coller des plages de cellules au format tabulaire (TSV/CSV) et ajuster le mode de rendu graphique.
- **Importation et exportation CSV** : Détection automatique des séparateurs (virgule, point-virgule, tabulation, espace), gestion des encodages UTF-8 avec ou sans BOM, détection de la virgule décimale locale et politiques configurables pour les valeurs manquantes (rejet, exclusion ou remplissage).

### Statistiques descriptives et bivariées
- **Métriques univariées** : Dès qu'un jeu de données est sélectionné, le panneau *Propriétés* affiche instantanément l'effectif total, la moyenne, la médiane, le minimum, le maximum, l'étendue, la variance (population et échantillon), l'écart-type, les quartiles $Q_1$, $Q_3$, l'intervalle interquartile (IQR) et les valeurs aberrantes selon les barrières de Tukey ($1.5 \times \text{IQR}$).
- **Métriques bivariées** : Pour les séries $(X, Y)$, calcul automatique de la covariance, du coefficient de corrélation de Pearson $r$, du coefficient de détermination $R^2$, ainsi que de la pente et de l'ordonnée à l'origine de la droite de régression des moindres carrés (OLS).

### Visualisations statistiques
Plusieurs modes de tracé sont disponibles via le sélecteur du panneau Données ou dans Propriétés :
- **Nuage de points (*Scatter plot*)** : Représentation ponctuelle classique avec taille, couleur et transparence de remplissage éditables.
- **Droite de régression** : Superposition des points d'observation et de la droite d'ajustement linéaire calculée.
- **Histogramme** : Répartition des fréquences en classes d'amplitudes régulières tracées le long de l'axe des abscisses.
- **Boîte à moustaches (*Box plot*)** : Tracé du rectangle $[Q_1, Q_3]$, de la ligne médiane, des moustaches raccordées aux valeurs extrêmes non aberrantes, et mise en évidence des outliers isolés.
- **Diagramme en barres (*Bar chart*)** : Colonnes discrètes proportionnelles aux amplitudes des observations.

### Modélisation et ajustements (Fitting)
- **Régressions non-linéaires** : Ajustement de polynômes de degré 1 à 5, modèles exponentiels ($y = a \cdot e^{b \cdot x}$), logarithmiques ($y = a + b \cdot \ln(x)$) et puissances.
- **Création de fonctions dynamiques** : Tout modèle ajusté peut être converti directement en objet `FunctionObject` traçable et réutilisable dans le moteur d'expressions sans code arbitraire (`eval` / `exec`).

### Intégration géométrique et dépendances
- **Génération depuis des objets géométriques** : Un dataset peut dépendre directement d'un groupe de points du canevas, des sommets d'un polygone, des échantillons d'un lieu géométrique ou de curseurs de la timeline.
- **Objets dépendants de données** : Des points peuvent être dérivés d'un dataset (par exemple le point moyen $(\bar{x}, \bar{y})$ ou un point d'indice donné), ainsi que la droite de régression linéaire qui se met à jour en temps réel dès qu'un point parent est déplacé.

## Analyse et mesures

Le dock Analyse numérique propose dérivée en un point, intégrale sur un intervalle, racines, extrema et intersections. Choisissez les bornes, la tolérance et le nombre d'échantillons. Les domaines invalides et discontinuités produisent un message dans le panneau.

Distance et angle créent des nombres dynamiques. **Objets > Mesurer la longueur sélectionnée** accepte un segment ou vecteur ; **Mesurer l'aire sélectionnée** accepte un polygone. Ces résultats suivent leurs dépendances.

## Fichiers, autosave et récupération

**Fichier > Fichiers récents** conserve jusqu'à dix chemins existants et peut vider la liste. Une sauvegarde écrit le `.pgl` atomiquement. L'autosave écrit un fichier de récupération séparé toutes les deux minutes par défaut, sans remplacer le projet utilisateur. Au prochain démarrage, PyGeoLab propose de le restaurer ou de l'ignorer ; une sauvegarde normale le nettoie.

Le format demeure en version 1 et lit les projets PyGeoLab 1.0. Un fichier corrompu affiche son erreur sans remplacer le document ouvert.

## Préférences

**Édition > Préférences** centralise :

- langue système, anglaise ou française (appliquée au redémarrage) ;
- thème système, clair ou sombre ;
- grille, axes et labels ;
- magnétisme et rayon ;
- couleur, épaisseur et taille des nouveaux objets ;
- facteur et transparence d'export ;
- autosave et intervalle.

**Restaurer les valeurs par défaut** remet puis enregistre toutes les valeurs initiales.

## Export et diagnostic

L'export PNG/SVG cible le viewport, le document complet ou la sélection, avec dimensions, facteur de résolution et transparence. Les commandes de copie placent le viewport en PNG ou SVG dans le presse-papiers.

**Aide > Ouvrir le dossier des logs** ouvre les journaux rotatifs. **Copier les informations système** copie versions PyGeoLab/build/Python/PySide6/Qt et OS pour un rapport d'erreur.

## Raccourcis

| Action | Raccourci |
|---|---|
| Nouveau, ouvrir, enregistrer, enregistrer sous | raccourcis système `Ctrl+N`, `Ctrl+O`, `Ctrl+S`, `Ctrl+Shift+S` |
| Annuler / rétablir | `Ctrl+Z` / `Ctrl+Y` selon la plateforme |
| Supprimer | `Delete` |
| Tout sélectionner / effacer | `Ctrl+A` / `Ctrl+Shift+A` |
| Dupliquer | `Ctrl+D` |
| Nouvelle fonction | `Ctrl+F` |
| Réinitialiser la vue | `Home` |
| Magnétisme | `M` |
| Sélection, point, segment, droite, cercle, polygone | `S`, `P`, `G`, `D`, `C`, `Y` |
| Suspendre temporairement le snapping | maintenir `Alt` |
| Annuler un geste | `Escape` |
| Liste dynamique des raccourcis | `F1` |

La fenêtre `F1` reste la référence exacte car elle est construite depuis les actions actives de l'application.
