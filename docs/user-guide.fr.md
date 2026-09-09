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

## Fonctions et curseurs

**Objets > Nouveau curseur** crée une variable avec valeur, minimum, maximum et pas. Le panneau Curseurs permet la saisie directe, le reset, l'édition, la vitesse d'animation, la lecture en boucle ou aller-retour et pause/reprise. Une animation recalcule seulement ses descendants et ne remplit pas l'historique Undo.

**Objets > Nouvelle fonction** accepte une expression, une variable indépendante et un domaine optionnel. Les autres identifiants de l'expression sont reliés automatiquement aux curseurs de même nom. Les erreurs restent visibles dans la boîte et dans Algèbre. **Affichage > Fonctions** règle la qualité du sampling et les couches racines, extrema, intersections et dérivée.

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
