# 15 — Performance

## Objectif

L'application vise une interaction fluide avec plusieurs centaines d'objets simples.

## Optimisations présentes en 1.0

- recalcul incrémental par graphe de dépendances ;
- drag regroupé en une commande d'historique ;
- cache de grille dépendant du viewport ;
- cache de la liste des objets visibles ordonnés par `Document.revision` ;
- clipping des lignes, demi-droites et segments avant dessin ;
- sampling borné des fonctions et séparation des discontinuités.

Un index spatial (quadtree/R-tree) n'est pas justifié par les tailles ciblées en 1.0.

## Mesures et optimisations 1.1

`python -m benchmarks.benchmark_core` mesure le chargement et le rendu de 1 000 puis 10 000 objets,
le hit-testing parmi 10 000 objets, une chaîne de 1 000 dépendances, 100 fonctions et une frame de
50 curseurs animés. Le test de performance exécute les mêmes scénarios avec des plafonds assez
larges pour les runners CI partagés et assez bas pour détecter une régression d'un ordre de
grandeur.

La mesure locale de référence donne environ 76 ms pour 10 000 points et 2,7 ms pour leur
hit-testing. Un cache de hit-testing ou un index spatial ajouterait donc de la complexité sans
bénéfice mesuré et n'est pas retenu. Le premier rendu de 100 fonctions atteignait environ 900 ms :
le regroupement des segments en polylignes, le budget adaptatif multi-courbes et un cache fondé sur
la révision de chaque fonction le ramènent autour de 80 ms sur la même machine.

Le modèle publie le nombre d'observateurs uniquement à des fins de diagnostic. La fermeture de la
fenêtre arrête les timers et libère explicitement les six abonnements UI, ce qui évite de retenir
des widgets Qt après leur fermeture.
