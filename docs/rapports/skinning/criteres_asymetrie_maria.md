# Critère d'asymétrie pour Maria (fixé avant mesure)

Date de fixation : 2026-11-05, avant toute exécution du script `symetrie_percentile.py`.

## Pourquoi un critère séparé
Le maillage de repos de Maria n'est pas symétrique (écart miroir p99 = 10,8 mm ; masculin 1,6 mm ; féminin 3,3 mm).
Le critère « étirement maximal » compare des arêtes différentes de chaque côté (6 % des arêtes n'ont pas d'image miroir),
donc il mesure la topologie, pas la déformation (entrée 153).

## Critère retenu (à appliquer tel quel, sans réglage)
Pour chaque mouvement X :
1. Appariement des arêtes : chaque arête gauche (sommets a, b) est associée à l'arête droite de sommets
   (image(a), image(b)) si elle existe. Seules les paires appariées sont retenues (≈ 94 % des arêtes).
2. Étirement par arête : rapport longueur posée / longueur de repos, arêtes de repos ≥ 5 mm (entrée 151).
3. Comparaison par distribution : p99 des rapports côté gauche (G) et côté droit (D), sur les paires appariées.
   Critère : |p99_G − p99_D| / p99_D < 5 %. (Le seuil de 5 % est celui du test existant ; il n'est pas relâché.)
4. Déformation : critère existant inchangé (écart p99 < 2 mm, après soustraction de l'écart au repos).
5. Retournements : non évalués par ce critère pour Maria ; comptés et rapportés (l'entrée 153 montre que le
   décompte absolu est sensible aux poids).

## Ce qui n'est PAS fait
- Aucun passage « vert » n'est déclaré si le critère 3 échoue : l'échec est rapporté et analysé.
- Le critère « étirement maximal » reste dans `test_symetrie.py` et reste en place ; il n'est pas retiré.
