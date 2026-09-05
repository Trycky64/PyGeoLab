# 21 — Accessibilité et internationalisation

## Accessibilité

Objectifs :

- navigation clavier ;
- raccourcis cohérents ;
- contraste suffisant ;
- labels accessibles ;
- tailles d'UI raisonnables.

## Daltonisme

Les informations importantes ne doivent pas dépendre uniquement de la couleur.

## Internationalisation

L'architecture doit permettre l'i18n.

Langues initiales potentielles :

- français ;
- anglais.

Les chaînes visibles ne doivent pas être dispersées arbitrairement dans le code métier.

## Nombres

Attention aux différences :

```text
1.5
1,5
```

Le format interne doit rester invariant.

L'UI peut localiser l'affichage.
