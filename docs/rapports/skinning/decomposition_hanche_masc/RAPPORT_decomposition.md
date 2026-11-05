# Décomposition mathématique de la déformation locale (entrejambe masculin, hanche G 120°)

Objet : séparer le défaut LBS de l'amplification SQ, et déterminer si SQ amplifie par sa géométrie d'arête, par ses
transformations locales ou par la propagation des rotations voisines. Aucun critère, seuil ou méthode de référence
n'a été modifié. Aucun candidat n'est proposé.

Fichiers : `engine/validation/skinning/investigation_decomposition.py` (blocs 1 à 4),
`engine/validation/skinning/investigation_propagation.py` (test de propagation),
`resultats.json` et `propagation.json` dans ce dossier.

## Conclusion (à lire en premier)

- **Cause du défaut LBS** : non démontrée au sens mathématique. Mesurée : le LBS est déjà à 2,47 au sommet 8734,
  et il est très sensible aux poids de l'entrejambe. Redistribuer ces poids entre les deux cuisses (somme égale à 1)
  fait passer le maximum LBS de 1,0 à 10,4 avec 14 à 19 retournements (sweep). Le défaut LBS est donc une propriété
  des poids de l'entrejambe, pas une erreur de SQ.
- **Cause de l'amplification par SQ** : **non démontrée**. Les mesures écartent plusieurs mécanismes (ci-dessous) et
  retiennent une propagation : SQ transmet aux sommets un déplacement imposé par les rotations de leurs voisins, y
  compris à des sommets dont le LBS est rigide. Ce mécanisme est visible dans le test à poids modifiés (t = 0), pas
  démontré à poids d'origine.
- **Facteurs aggravants** : petites arêtes et petits triangles (écart d'aire SQ − LBS médian 0,128 pour le tiers
  le plus petit, 0,058 pour le tiers le plus grand) ; présence d'un poids mixte entre deux cuisses.
- **Hypothèses réfutées** : voir le tableau section 4.
- **Mécanismes incertains** : la propagation est mesurée sur un seul changement de poids, pas sur les poses
  originales ; le phénomène n'a pas été reproduit sur un patch synthétique à géométrie contrôlée (voir section 6).

## 1. Arêtes incidentes aux 24 défauts (69 arêtes)

| Grandeur | Valeur (médiane sauf indication) |
|---|---|
| Amplification SQ − LBS (en fraction de la longueur au repos) | +0,022 ; maximum +0,305 |
| Part de la variation d'arête dans la direction de l'arête (|along| / |Δ|) | 0,45 |
| Cosinus entre les déplacements SQ − LBS des deux extrémités | 0,91 |
| Cible de rétrécissement de R_ab (|R_ab d_0| / |d_0|) | 0,998 |
| Plus petite valeur singulière de R_ab | 0,996 |
| Écart LBS à la cible SQ (sur la longueur de repos) | 0,63 |
| Écart SQ à la cible SQ | 0,52 |
| Angle entre les rotations des deux extrémités | 10,5° |

Corrélations avec l'amplification (sur les 69 arêtes) :

| Variable | Corrélation |
|---|---|
| Composante de variation le long de l'arête | **0,85** |
| Composante perpendiculaire | 0,20 |
| Longueur au repos | 0,18 |
| Rétrécissement de la cible R_ab | 0,43 |
| Plus petite valeur singulière de R_ab | 0,42 |
| Angle entre les rotations des extrémités | −0,37 |
| Écart LBS à la cible | −0,17 |

Lecture : l'amplification est **une variation de longueur le long de l'arête**, non une rotation de l'arête. Les deux
extrémités bougent presque dans la même direction (cosinus 0,91) : la différence entre elles, qui fixe la longueur,
est faible et ne se produit que dans la direction de l'arête.

Question « un sommet est-il trop modifié ? » : le déplacement SQ − LBS des sommets défectueux est de 0,8 cm en
médiane (poids d'origine). Question « les deux extrémités sont-elles modifiées différemment ? » : oui, mais la
différence est dans l'axe de l'arête (section précédente). Question « le repère local donne-t-il une mauvaise
direction ? » : la cible R_ab ne rétrécit presque pas les arêtes (0,998) ; la corrélation de 0,43 est réelle mais
d'amplitude de 0,2 %.

## 2. Transformations locales par triangle (81 triangles incidents)

| Grandeur | LBS | SQ |
|---|---|---|
| Rapport d'aire (médiane) | 0,878 | 0,943 |
| Rapport d'aire (min ; max) | — | 0,24 ; 1,54 |
| Triangles en compression (aire < 1) | — | 45 / 81 |
| Anisotropie s1 / s2 (médiane) | 3,11 | 2,88 |
| Écart du gradient au gradient moyen Mv (médiane) | 0,58 | 0,57 |

- **Rotation extraite** : l'angle entre la rotation locale LBS et la rotation locale SQ est de **2,4°** (médiane).
  SQ ne donne donc pas une rotation incohérente triangle par triangle. Les deux méthodes tournent presque pareil.
- **Rotation Mv** : l'angle entre la rotation LBS et la rotation polaire de Mv est de 25° (médiane). Mv n'est donc
  pas le gradient réel du LBS sur ces triangles, car le terme de gradient des poids y est grand (écart 0,58). Mais
  cet écart ne prédit pas la variation d'aire de SQ (corrélation 0,12).
- **Cisaillement** : l'anisotropie médiane (≈ 3) montre que le LBS déforme déjà fortement en cisaillement ; SQ
  réduit légèrement cette anisotropie.
- **Compression** : SQ comprime davantage une partie des triangles (45 sur 81, minimum 0,24), tout en augmentant
  l'aire médiane. Le défaut est donc une combinaison de compression et d'étirement localisés, non une compression
  générale.
- **Taille** : l'écart d'aire SQ − LBS est plus grand sur les petits triangles (0,128) que sur les grands (0,058) ;
  corrélation taille / écart −0,23. Le phénomène dépend donc de la taille locale, dans le sens où une même erreur
  absolue pèse plus sur les petites arêtes. L'homogénéité d'échelle est exacte (écart 0 pour des échelles 0,5 et 2),
  donc ce n'est pas un artefact numérique.

## 3. Vérification du solveur

Le solveur réimplémenté (R_ab fourni par arête) donne exactement le même résultat que `ARAP.solve_fixe` (écart 0). La
suite de l'analyse repose donc sur le même calcul.

## 4. Un seul facteur modifié à la fois

Maillage complet (les mesures sont limitées aux sommets et arêtes du patch, défauts plus voisins).

| Variante | Max défauts | Médiane défauts | Max global | p99 global | Retournements | Variation de volume |
|---|---|---|---|---|---|---|
| LBS (référence) | 2,471 | 1,785 | 2,471 | 1,185 | 4 | −0,045 |
| SQ (moyenne des rotations) | 2,590 | 1,847 | 2,590 | 1,132 | 1 | −0,069 |
| SQ, R_ab = polaire(moyenne) *(diagnostic)* | 2,592 | 1,852 | 2,592 | 1,132 | 1 | −0,069 |
| SQ, R_ab = identité *(diagnostic)* | 3,172 | 2,000 | 10,838 | 1,244 | 128 | −0,181 |

Hypothèses testées :

| Réf. | Hypothèse | Résultat | Statut |
|---|---|---|---|
| H-a | Le rétrécissement de R_ab (moyenne non orthogonale) cause l'amplification | Polaire de la moyenne : 2,592 contre 2,590 | **Réfutée** |
| H-b | La rotation extraite de SQ est incohérente triangle par triangle | Angle LBS/SQ de 2,4° | **Réfutée** |
| H-c | Le repère Mv (non rigide) cause la variation d'aire | Corrélation 0,12 avec la variation d'aire | **Réfutée comme cause principale** |
| H-d | La rotation locale est nécessaire à la stabilité | Identité : 128 retournements, max global 10,8 | **Confirmée** (la rotation est nécessaire, mais ne corrige pas le défaut) |
| H-e | Le défaut est une variation de longueur le long des arêtes | Corrélation 0,85 | **Soutenue** |
| H-f | SQ propage la rotation des voisins vers des sommets rigides en LBS | Test t = 0 (section 5) | **Soutenue sur un changement de poids, non démontrée à poids d'origine** |

## 5. Test de propagation (poids modifiés)

Les 50 sommets à deux cuisses du patch reçoivent, pour t = 0, tout le poids de la cuisse droite (somme conservée).

| Grandeur | Poids d'origine | t = 0 |
|---|---|---|
| Sommets défectueux : classe | mixte | cuisse droite seule |
| Déplacement SQ − LBS des défauts (médiane) | 0,8 cm | **4,8 cm** |
| Amplification SQ − LBS, médiane des arêtes défectueuses | +0,022 | −0,068 |
| Amplification SQ − LBS, maximum | +0,305 | **+1,222** |
| Maximum LBS sur les défauts | 2,47 | **1,00** (rigide) |
| Maximum SQ sur les défauts | 2,59 | 2,22 |

Lecture : à t = 0, LBS laisse les sommets défectueux rigides, mais SQ les déplace de 4,8 cm et crée un étirement de
1,22 sur des arêtes dont les deux extrémités sont en LBS « cuisse droite seule ». Le déplacement n'a donc pas pour
origine le poids propre du sommet : il vient des rotations voisines, transmises par le système de contraintes. C'est
la propagation annoncée en H-f. À poids d'origine, tous les sommets défectueux sont de classe « mixte », donc le test
par classe ne peut pas séparer les arêtes : la propagation n'y est pas isolée.

## 6. Limites et ce qui n'a pas été fait

- **Patch extrait** : non fait. SQ est un système linéaire global : un patch isolé changerait les conditions aux limites
  et donc le résultat. Les mesures restent sur le maillage complet, limitées au patch.
- **Géométrie synthétique contrôlée** : non faite. Un plan ou une grille avec mêmes poids et transformations
  permettrait de voir si le phénomène disparaît hors de la géométrie réelle. À faire avant toute conclusion.
- **Un seul changement de poids** (t = 0) pour la propagation. La sensibilité aux autres distributions (sweep) n'est
  pas encore analysée par classe.
- **Rotation orthonormée par arête** : non lancée, comme demandé. Une arête seule ne définit pas de rotation 3D.
- **Généralisation** (HBM féminin, Maria, poses indépendantes) : non faite, car aucun candidat n'existe.

## 7. Décision

Aucune cause précise n'est démontrée pour l'amplification SQ. Trois faits sont solides : le défaut LBS vient des
poids de l'entrejambe ; l'amplification est une variation de longueur le long des arêtes ; le repère de SQ n'est pas
incohérent triangle par triangle. La propagation des rotations voisines est la piste la plus directe, à tester sur
une géométrie synthétique à poids contrôlés avant toute proposition de méthode.
