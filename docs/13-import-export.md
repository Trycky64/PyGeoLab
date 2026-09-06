# 13 — Import et export

## Import

Le format de projet initial est `.pgl`, JSON versionné et validé avant reconstruction.

## Export PNG

**Fichier → Exporter → Image PNG** rend la zone visible courante. Le facteur de résolution
est configurable de 0,25× à 8× dans les préférences. Le fond peut être opaque ou transparent.

## Export SVG

**Fichier → Exporter → Image SVG** utilise `QSvgGenerator` et le renderer commun. Segments,
droites et demi-droites clippées, cercles, polygones, points et labels restent vectoriels.
Le fond peut être omis pour produire un SVG transparent.

## Export de données

CSV de points et JSON simplifié restent des extensions futures.

## Compatibilité GeoGebra

Aucun objectif de compatibilité complète pour 1.0.
