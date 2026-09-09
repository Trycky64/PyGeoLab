# 13 — Import et export

## Import

Le format de projet initial est `.pgl`, JSON versionné et validé avant reconstruction.

## Export PNG

**Fichier → Exporter → Image PNG** propose le viewport, le document complet ajusté à son contenu
ou la sélection uniquement. La largeur et la hauteur sont configurables jusqu'à 20 000 pixels,
puis le facteur de résolution de 0,25× à 8× s'applique. Le fond peut être opaque ou transparent.
Cette échelle constitue le réglage persistant de qualité d'export. Le PNG porte le nom du document
et l'identifiant logiciel dans ses métadonnées textuelles.

## Export SVG

**Fichier → Exporter → Image SVG** utilise `QSvgGenerator` et le renderer commun. Segments,
droites et demi-droites clippées, cercles, polygones, points et labels restent vectoriels.
Le fond peut être omis pour produire un SVG transparent.

Le SVG utilise les mêmes zones, dimensions et facteur de résolution que le PNG. Son `viewBox`
contraint toutes les droites et demi-droites après clipping. Son titre reprend le nom du document ;
les labels et les courbes restent des éléments vectoriels.

## Presse-papiers

Les actions **Copier le viewport en PNG** et **Copier le viewport en SVG** placent respectivement
une image Qt et des données MIME `image/svg+xml` dans le presse-papiers. Elles ne créent aucun
fichier temporaire.

## Export de données

CSV de points et JSON simplifié restent des extensions futures.

## Compatibilité GeoGebra

Aucun objectif de compatibilité complète pour 1.0.
