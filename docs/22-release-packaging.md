# 22 — Packaging et releases

## Développement

Installation editable :

```bash
pip install -e .
```

## Entrée

Commande cible :

```bash
pygeolab
```

ou :

```bash
python -m pygeolab
```

## Builds

Produire des exécutables desktop.

Priorité :

1. Windows ;
2. Linux ;
3. macOS.

## Versioning

Semantic Versioning :

```text
MAJOR.MINOR.PATCH
```

Exemples :

```text
0.1.0
0.2.0
1.0.0
```

## Releases

Chaque release doit inclure :

- changelog ;
- notes de version ;
- artefact exécutable ;
- checksum éventuellement ;
- captures d'écran.

## CI

Pipeline cible :

1. lint ;
2. type checking ;
3. tests ;
4. build ;
5. package.

## GitHub

Prévoir :

- issue templates ;
- pull request template ;
- workflows CI ;
- releases automatiques ou semi-automatiques.
